"""Leituras locais de CISA/NVD; somente sincronização explícita acessa a rede."""

from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from inventario.infraestrutura.arquivos import salvar_json_atomico, trava_arquivo

URL_KEV = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
URL_NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CVE_RE = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,}$", re.IGNORECASE)
TTL = 24 * 3600
MAXIMO_DOWNLOAD = 10 * 1024 * 1024
TIMEOUT_FONTE = 20


class IntegracaoCVEError(RuntimeError):
    pass


class FonteLimitada(IntegracaoCVEError):
    def __init__(self, espera=1):
        self.espera = min(30, max(1, espera))
        super().__init__("Fonte externa temporariamente limitada.")


class CVENaoEncontrada(IntegracaoCVEError):
    pass


def _baixar_json(url, api_key=None):
    destino = urlsplit(url)
    if (destino.scheme != "https" or destino.hostname not in
            {"www.cisa.gov", "services.nvd.nist.gov", "api.first.org"}
            or destino.username or destino.password or destino.port not in (None, 443)):
        raise IntegracaoCVEError("Destino externo não permitido.")
    headers = {"User-Agent": "Sauron-Inventario/3.0 (uso academico)"}
    if api_key:
        headers["apiKey"] = api_key
    try:
        prazo = time.monotonic() + TIMEOUT_FONTE
        # Destino HTTPS e host validados acima.
        with urlopen(Request(url, headers=headers), timeout=TIMEOUT_FONTE) as resposta:  # nosec B310
            tamanho = int(resposta.headers.get("Content-Length", "0"))
            if tamanho > MAXIMO_DOWNLOAD:
                raise IntegracaoCVEError("Resposta externa excede 10 MB.")
            partes = []
            total = 0
            while True:
                if time.monotonic() >= prazo:
                    raise IntegracaoCVEError("Timeout de download da fonte externa.")
                parte = resposta.read(min(65536, MAXIMO_DOWNLOAD + 1 - total))
                if not parte:
                    break
                total += len(parte)
                if total > MAXIMO_DOWNLOAD:
                    raise IntegracaoCVEError("Resposta externa excede 10 MB.")
                partes.append(parte)
            dados = json.loads(b"".join(partes))
            if not isinstance(dados, dict):
                raise IntegracaoCVEError("A fonte externa não retornou um objeto JSON.")
            return dados
    except HTTPError as erro:
        if erro.code in {429, 503}:
            try:
                espera = float(erro.headers.get("Retry-After", "1"))
            except (ValueError, TypeError, AttributeError):
                espera = 1
            raise FonteLimitada(espera) from erro
        raise IntegracaoCVEError(f"Fonte externa respondeu HTTP {erro.code}.") from erro
    except (URLError, TimeoutError, ValueError, OSError) as erro:
        raise IntegracaoCVEError("Falha de rede ou formato da fonte externa.") from erro


def validar_kev(dados):
    if not isinstance(dados, dict):
        raise IntegracaoCVEError("Catálogo KEV inválido: esperado objeto JSON.")
    itens = dados.get("vulnerabilities")
    if not isinstance(itens, list):
        raise IntegracaoCVEError("Catálogo KEV inválido: falta lista de vulnerabilidades.")
    for item in itens:
        identificador = item.get("cveID") if isinstance(item, dict) else None
        if not isinstance(identificador, str) or not CVE_RE.fullmatch(identificador):
            raise IntegracaoCVEError("Identificador CVE inválido no catálogo.")
        for campo in ("dateAdded", "dueDate"):
            texto = item.get(campo, "")
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
                    raise ValueError
                date.fromisoformat(texto)
            except (TypeError, ValueError) as erro:
                raise IntegracaoCVEError(f"Data inválida no campo {campo}.") from erro


class CisaKevClient:
    def __init__(self, cache):
        self.cache = Path(cache)

    def atualizar(self, forcar=False):
        with trava_arquivo(self.cache.with_suffix(".lock")):
            if self.cache.is_file() and not forcar:
                try:
                    dados, _ = self.carregar()
                    envelope = json.loads(self.cache.read_text(encoding="utf-8"))
                    instante = datetime.fromisoformat(envelope["atualizado_em"])
                    if 0 <= (datetime.now(timezone.utc) - instante).total_seconds() < TTL:
                        return dados
                except (IntegracaoCVEError, ValueError, KeyError, TypeError, OSError):
                    pass
            dados = _baixar_json(URL_KEV)
            validar_kev(dados)
            salvar_json_atomico(
                self.cache,
                {
                    "atualizado_em": datetime.now(timezone.utc).isoformat(),
                    "fonte": "CISA KEV",
                    "dados": dados,
                },
            )
            return dados

    def carregar(self, permitir_rede=False):
        # Parâmetro legado permanece compatível, mas nunca autoriza rede por leitura.
        if not self.cache.is_file():
            raise IntegracaoCVEError("Sem cache KEV. Um gerente deve executar sync_kev.")
        try:
            envelope = json.loads(self.cache.read_text(encoding="utf-8"))
            if not isinstance(envelope, dict):
                raise ValueError("Envelope KEV inválido.")
            instante = datetime.fromisoformat(envelope["atualizado_em"])
            idade = (datetime.now(timezone.utc) - instante).total_seconds()
            dados = envelope["dados"]
            validar_kev(dados)
        except (ValueError, KeyError, TypeError, OSError) as erro:
            raise IntegracaoCVEError("Cache KEV inválido; execute sync_kev --forcar.") from erro
        estado = "cache expirado" if not 0 <= idade < TTL else "cache válido"
        return dados, f"{estado} de {envelope['atualizado_em']}"

    def listar_recentes(self, limite=15, permitir_rede=False):
        if not 1 <= limite <= 100:
            raise ValueError("O limite deve estar entre 1 e 100.")
        dados, origem = self.carregar()
        itens = sorted(dados["vulnerabilities"], key=lambda i: i["dateAdded"], reverse=True)
        return {
            "origem": origem,
            "quantidade": min(limite, len(itens)),
            "vulnerabilidades": itens[:limite],
        }


class NvdClient:
    def __init__(self, api_key=None, cache_dir=None):
        self.api_key = api_key
        padrao = Path(os.getenv("SAURON_DATA_DIR", "dados")) / "cache/nvd"
        self.cache_dir = Path(cache_dir or padrao)

    def reservar_requisicao(self):
        caminho = self.cache_dir / "limite.json"
        for _ in range(4):
            with trava_arquivo(caminho.with_suffix(".lock")):
                agora = time.time()
                try:
                    estado = json.loads(caminho.read_text()) if caminho.exists() else {}
                except (ValueError, OSError):
                    estado = {}
                recentes = estado.get("requisicoes", []) if isinstance(estado, dict) else []
                if not isinstance(recentes, list):
                    recentes = []
                instantes = [t for t in recentes if type(t) in (int, float) and 0 <= agora-t < 30]
                if len(instantes) < (50 if self.api_key else 5):
                    salvar_json_atomico(caminho, {"requisicoes": instantes+[agora]})
                    return
                espera = min(30, max(.01, 30-(agora-min(instantes))+.01))
            time.sleep(espera)
        raise IntegracaoCVEError("Limite NVD persistente após espera/retry.")

    def baixar(self, url, api_key=None):
        from inventario.infraestrutura.auditoria import registrar_evento
        registrar_evento("CONSULTA_CVE", "NVD", "consulta", {"url":url})
        for tentativa in range(4):
            self.reservar_requisicao()
            try:
                return _baixar_json(url, self.api_key)
            except FonteLimitada as erro:
                if tentativa == 3:
                    raise
                time.sleep(min(30, max(erro.espera, 2**tentativa)))

    def _caminho(self, cve_id):
        if not isinstance(cve_id, str):
            raise ValueError("Informe o identificador CVE como texto.")
        cve_id = cve_id.strip().upper()
        if len(cve_id) > 32 or not CVE_RE.fullmatch(cve_id):
            raise ValueError("CVE inválido. Ex.: CVE-2021-44228.")
        return cve_id, self.cache_dir / f"{cve_id}.json"

    def _ler_cache(self, cve_id, caminho):
        try:
            envelope = json.loads(caminho.read_text(encoding="utf-8"))
            if not isinstance(envelope, dict):
                raise ValueError("Envelope NVD inválido.")
            idade = time.time() - float(envelope["ts"])
            cve = envelope["cve"]
            if not 0 <= idade < TTL or not isinstance(cve, dict) or cve.get("id") != cve_id:
                raise ValueError
            return cve
        except (ValueError, KeyError, TypeError, OSError) as erro:
            raise IntegracaoCVEError(
                f"Cache NVD ausente, inválido ou expirado. Execute sync_kev --nvd {cve_id}."
            ) from erro

    def buscar(self, cve_id):
        cve_id, caminho = self._caminho(cve_id)
        return self._ler_cache(cve_id, caminho)

    def registro_cache(self, cve_id):
        """Snapshot local com data; permite exibir cache expirado com aviso explícito."""
        import math
        cve_id, caminho = self._caminho(cve_id)
        try:
            if caminho.stat().st_size > MAXIMO_DOWNLOAD:
                raise ValueError("Cache grande demais.")
            envelope = json.loads(caminho.read_text(encoding="utf-8"))
            if not isinstance(envelope, dict):
                raise ValueError("Envelope inválido.")
            ts, cve = envelope["ts"], envelope["cve"]
            if (type(ts) not in (int, float) or not math.isfinite(ts) or ts < 0
                    or ts > time.time() or not isinstance(cve, dict) or cve.get("id") != cve_id):
                raise ValueError("Cache inválido.")
            return {"cve": cve, "consultado_em": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                    "expirado": time.time()-ts >= TTL}
        except (ValueError, KeyError, TypeError, OSError, OverflowError) as erro:
            raise IntegracaoCVEError("Sem registro NVD local válido. Consulte a NVD pela internet.") from erro

    def atualizar(self, cve_id, forcar=False):
        cve_id, caminho = self._caminho(cve_id)
        with trava_arquivo(caminho.with_suffix(".lock")):
            if not forcar:
                try:
                    return self._ler_cache(cve_id, caminho)
                except IntegracaoCVEError:
                    pass
            dados = self.baixar(f"{URL_NVD}?{urlencode({'cveId': cve_id})}", self.api_key)
            itens = dados.get("vulnerabilities", [])
            if not isinstance(itens, list) or not itens or not isinstance(itens[0], dict):
                raise CVENaoEncontrada(f"{cve_id} não encontrado na NVD.")
            cve = itens[0].get("cve", {})
            if not isinstance(cve, dict) or cve.get("id") != cve_id:
                raise IntegracaoCVEError("A resposta NVD contém identificador inesperado.")
            for campo in ("published", "lastModified"):
                if campo in cve:
                    try:
                        datetime.fromisoformat(cve[campo])
                    except (TypeError, ValueError) as erro:
                        raise IntegracaoCVEError(f"Data NVD inválida em {campo}.") from erro
            salvar_json_atomico(caminho, {"ts": time.time(), "cve": cve})
            return cve

    def pesquisar(self, termo, forcar=False):
        """Busca por palavras na API 2.0, limitada a 20 resultados e com cache."""
        if not isinstance(termo, str) or not 2 <= len(termo.strip()) <= 120:
            raise ValueError("A busca precisa ter entre 2 e 120 caracteres.")
        termo = ' '.join(termo.split())
        nome = hashlib.sha256(termo.casefold().encode()).hexdigest()
        caminho = self.cache_dir / f"BUSCA-{nome}.json"
        with trava_arquivo(caminho.with_suffix('.lock')):
            if not forcar:
                try:
                    envelope = json.loads(caminho.read_text(encoding='utf-8'))
                    ts = float(envelope['ts'])
                    r = envelope['resultado']
                    if (0 <= time.time()-ts < TTL and envelope['termo'] == termo.casefold()
                            and isinstance(r, dict) and isinstance(r['cves'], list)
                            and type(r['total']) is int and r['total'] >= len(r['cves'])
                            and len(r['cves']) <= 20
                            and all(isinstance(c, dict) and CVE_RE.fullmatch(str(c.get('id', ''))) for c in r['cves'])):
                        return r, ts
                except (OSError, ValueError, KeyError, TypeError):
                    pass
            parametros = {'keywordSearch': termo, 'resultsPerPage': 20, 'startIndex': 0}
            dados = self.baixar(f"{URL_NVD}?{urlencode(parametros)}", self.api_key)
            itens, total = dados.get('vulnerabilities'), dados.get('totalResults')
            if (not isinstance(itens, list) or len(itens) > 20 or type(total) is not int
                    or total < len(itens) or dados.get('startIndex') != 0):
                raise IntegracaoCVEError('Resposta de busca NVD inválida.')
            cves, ts = [], time.time()
            for item in itens:
                cve = item.get('cve') if isinstance(item, dict) else None
                if not isinstance(cve, dict) or not CVE_RE.fullmatch(str(cve.get('id', ''))):
                    raise IntegracaoCVEError('Identificador inválido na busca NVD.')
                cves.append(cve)
                salvar_json_atomico(self._caminho(cve['id'])[1], {'ts': ts, 'cve': cve})
            resultado = {'cves': cves, 'total': total, 'truncado': len(cves) < total}
            salvar_json_atomico(caminho, {'ts': ts, 'termo': termo.casefold(), 'resultado': resultado})
            return resultado, ts

    def consultar_cpe(self, cpe23, sem_rede=False):
        """Até 5 páginas de 200 CVEs; incompletude é explícita, nunca silêncio."""
        from inventario.dominio.classificacao import validar_cpe

        validar_cpe(cpe23)
        nome = hashlib.sha256(cpe23.encode()).hexdigest()
        caminho = self.cache_dir / f"CPE-{nome}.json"
        with trava_arquivo(caminho.with_suffix(".lock")):
            try:
                envelope = json.loads(caminho.read_text(encoding="utf-8"))
                if envelope["cpe23"] == cpe23 and 0 <= time.time() - envelope["ts"] < TTL:
                    return envelope["resultado"]
            except (KeyError, TypeError, ValueError, OSError):
                pass
            if sem_rede:
                raise IntegracaoCVEError("Consulta CPE sem cache válido; sincronize com rede.")
            cves, indice, total = [], 0, 0
            for _ in range(5):
                parametros = {"cpeName": cpe23, "resultsPerPage": 200, "startIndex": indice}
                dados = self.baixar(f"{URL_NVD}?{urlencode(parametros)}", self.api_key)
                itens = dados.get("vulnerabilities")
                total = dados.get("totalResults")
                if (
                    not isinstance(itens, list)
                    or type(total) is not int
                    or total < 0
                    or dados.get("startIndex") != indice
                    or len(itens) > 200
                ):
                    raise IntegracaoCVEError("Paginação NVD inválida.")
                for item in itens:
                    cve = item.get("cve", {}) if isinstance(item, dict) else {}
                    if not isinstance(cve.get("id"), str) or not CVE_RE.fullmatch(cve["id"]):
                        raise IntegracaoCVEError("CVE inválido na consulta por CPE.")
                    cves.append(cve)
                indice += len(itens)
                if indice >= total:
                    break
                if not itens:
                    raise IntegracaoCVEError("NVD retornou página vazia antes do fim.")
            resultado = {"cves": cves, "total": total, "truncado": indice < total}
            salvar_json_atomico(
                caminho, {"ts": time.time(), "cpe23": cpe23, "resultado": resultado}
            )
            return resultado


class EpssClient:
    """FIRST EPSS: somente chamada explícita; nunca consulta durante simulação."""
    def buscar(self, cves):
        import math
        if os.getenv("SAURON_ROTINAS_SEM_REDE") == "1":
            raise IntegracaoCVEError("Sincronização EPSS desabilitada por SAURON_ROTINAS_SEM_REDE=1.")
        if not isinstance(cves, list) or not 1 <= len(cves) <= 100 or any(
            not isinstance(c, str) or not CVE_RE.fullmatch(c) for c in cves
        ):
            raise IntegracaoCVEError("EPSS exige entre 1 e 100 identificadores CVE válidos.")
        if len(",".join(cves)) > 2000:
            raise IntegracaoCVEError("Consulta EPSS excede 2000 caracteres de CVEs.")
        dados = _baixar_json("https://api.first.org/data/v1/epss?" + urlencode({"cve": ",".join(cves)}))
        itens = dados.get("data")
        if not isinstance(itens, list) or len(itens) > len(cves):
            raise IntegracaoCVEError("Resposta EPSS inválida.")
        encontrados = {}
        for item in itens:
            try:
                cve, data = item["cve"], item["date"]
                if not isinstance(item["epss"], (str, int, float)) or isinstance(item["epss"], bool):
                    raise ValueError
                if not isinstance(item["percentile"], (str, int, float)) or isinstance(item["percentile"], bool):
                    raise ValueError
                valor, percentil = float(item["epss"]), float(item["percentile"])
                if cve not in cves or cve in encontrados or any(not math.isfinite(v) or not 0 <= v <= 1 for v in (valor, percentil)):
                    raise ValueError
                if not isinstance(data, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
                    raise ValueError
                if date.fromisoformat(data) > datetime.now(timezone.utc).date():
                    raise ValueError
                modelo = item.get("model_version", "")
                if not isinstance(modelo, str) or len(modelo) > 40:
                    raise ValueError
            except (KeyError, TypeError, ValueError, OverflowError) as erro:
                raise IntegracaoCVEError("CVE, probabilidade, percentil, data ou modelo EPSS inválidos.") from erro
            encontrados[cve] = {"epss": valor, "percentil": percentil, "data": data, "modelo": modelo}
        return encontrados
