"""Diagnóstico local: não testa a internet nem modifica cache, fontes ou inventário."""
import json
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Count, F, Max, Q
from django.utils import timezone

from inventario.infraestrutura.cve_client import CisaKevClient, IntegracaoCVEError, MAXIMO_DOWNLOAD, NvdClient
from inventario.infraestrutura.estado_consultas_fontes import ler_estado
from inventario.models import Vulnerabilidade

LIMITE_NVD = 100
LIMITE_BYTES_NVD = 4 * 1024 * 1024
DESCRICOES = {"resposta": "resposta recebida", "falha": "falha de rede ou resposta", "limitada": "fonte limitou a consulta",
              "desativada": "consulta desativada na configuração", "parcial": "resposta incompleta"}


def estado_cobertura(total, recentes, antigos=0, lacunas=0, parcial=False):
    """Classifica somente cobertura local, sem inferir conectividade ou saúde."""
    if not total or parcial or lacunas or recentes + antigos < total:
        return 'lacuna'
    return 'desatualizada' if antigos else 'atualizada'


def estado_consulta(fonte):
    dados = ler_estado(fonte)
    if not dados:
        return None
    descricoes = {**DESCRICOES, **({"resposta": "importação confirmada", "falha": "falha de processamento ou gravação"} if fonte == "scanner" else {})}
    return {chave: {"data": valor["data"], "estado": valor["estado"], "descricao": descricoes[valor["estado"]]}
            for chave, valor in dados.items()}


def idade_segundos(data):
    if isinstance(data, str):
        try:
            data = datetime.fromisoformat(data)
        except ValueError:
            return None
    if not isinstance(data, datetime) or timezone.is_naive(data):
        return None
    idade = (timezone.now() - data).total_seconds()
    return int(idade) if idade >= 0 else None


def classificar_fonte(fogueira, disponiveis, consulta, parcial=False):
    """Resumo conservador; falha indica apenas o resultado da última tentativa."""
    ultimo = (consulta or {}).get("ultima", {}).get("estado")
    if ultimo in {"falha", "limitada"}:
        return {"codigo": "inacessivel", "rotulo": "Falha na última tentativa"}
    if parcial:
        return {"codigo": "incompleto", "rotulo": "Amostra incompleta; situação indeterminada"}
    if not disponiveis:
        return {"codigo": "vazio", "rotulo": "Sem dados locais válidos"}
    if fogueira == "desatualizada":
        return {"codigo": "vencido", "rotulo": "Dados vencidos"}
    if fogueira == "atualizada" and ultimo != "parcial":
        return {"codigo": "ok", "rotulo": "Dados locais atuais"}
    return {"codigo": "incompleto", "rotulo": "Dados incompletos ou situação desconhecida"}


def _rotina_kev():
    caminho = settings.DATA_DIR / "ultima_rotina.json"
    try:
        if caminho.stat().st_size > 1024 * 1024:
            return "Registro da rotina indisponível ou inválido."
        registro = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(registro, dict) or not isinstance(registro.get("erros"), dict):
            return "Registro da rotina indisponível ou inválido."
        if registro["erros"].get("kev"):
            return "A última rotina registrou falha na etapa KEV; confira o diagnóstico da rotina."
        return "A última rotina não registrou falha na etapa KEV; isso não comprova conexão atual."
    except (OSError, ValueError, TypeError):
        return "Sem registro confiável da última rotina; conexão com a fonte desconhecida."


def estado_kev():
    caminho = settings.DATA_DIR / "cache_kev.json"
    rotina = _rotina_kev()
    if not caminho.is_file():
        return {"estado": "Sem cache", "detalhe": "Ainda não há catálogo local.", "rotina": rotina}
    try:
        if caminho.stat().st_size > MAXIMO_DOWNLOAD + 1024:
            raise IntegracaoCVEError("Cache excede o tamanho permitido.")
        dados, origem = CisaKevClient(caminho).carregar()
    except (IntegracaoCVEError, OSError):
        return {"estado": "Cache inválido", "detalhe": "O catálogo local não pôde ser validado.", "rotina": rotina}
    estado = "Desatualizado" if "expirado" in origem else "Atualizado no cache"
    if not dados["vulnerabilities"]:
        estado = "Catálogo vazio (desatualizado)" if estado == "Desatualizado" else "Catálogo vazio"
    try:
        data_cache = json.loads(caminho.read_text(encoding="utf-8"))["atualizado_em"]
    except (OSError, ValueError, KeyError, TypeError):
        data_cache = None
    return {"estado": estado, "detalhe": origem, "quantidade": len(dados["vulnerabilities"]), "rotina": rotina,
            "atualizado_em": data_cache}


def estado_nvd(qs, total):
    cliente = NvdClient(settings.NVD_API_KEY, settings.DATA_DIR / "cache" / "nvd")
    totais = {"recentes": 0, "antigos": 0, "ausentes": 0, "invalidos": 0, "nao_lidos": 0}
    restante = LIMITE_BYTES_NVD
    ultima = None
    for cve in qs.order_by("cve_id").values_list("cve_id", flat=True)[:LIMITE_NVD]:
        try:
            _, caminho = cliente._caminho(cve)
            if not caminho.is_file():
                totais["ausentes"] += 1
                continue
            tamanho = caminho.stat().st_size
            if tamanho > restante:
                totais["nao_lidos"] += 1
                continue
            restante -= tamanho
            registro = cliente.registro_cache(cve)
        except (IntegracaoCVEError, ValueError, OSError):
            totais["invalidos"] += 1
            continue
        totais["antigos" if registro["expirado"] else "recentes"] += 1
        data = registro["consultado_em"]
        ultima = max(ultima, data) if ultima else data
    return {**totais, "total": total, "examinados": sum(totais.values()), "limite": LIMITE_NVD,
            "ultima": ultima, "parcial": total > LIMITE_NVD or totais["nao_lidos"] > 0}


def estado_epss(qs, total):
    hoje = timezone.now().date()
    coerente = Q(epss__isnull=False, epss_data__isnull=False, epss_observacao__isnull=False,
                 epss_observacao__cve_id=F("cve_id"), epss_observacao__data=F("epss_data"),
                 epss_observacao__epss=F("epss"))
    recente = coerente & Q(epss_data__gte=hoje - timedelta(days=2), epss_data__lte=hoje)
    antigo = coerente & Q(epss_data__lt=hoje - timedelta(days=2))
    futuro = coerente & Q(epss_data__gt=hoje)
    dados = qs.aggregate(recentes=Count("pk", filter=recente), antigos=Count("pk", filter=antigo),
                         futuros=Count("pk", filter=futuro), ultima_coleta=Max("epss_observacao__coletado_em", filter=coerente))
    dados["sem_dados_coerentes"] = total - dados["recentes"] - dados["antigos"] - dados["futuros"]
    dados["total"] = total
    return dados


def resumo_fontes(ver_isca=False, ver_importacoes=False):
    qs = Vulnerabilidade.objects.exclude(cve_id__isnull=True).exclude(cve_id="")
    total = qs.count()
    resultado = {"kev": estado_kev(), "nvd": estado_nvd(qs, total), "epss": estado_epss(qs, total)}
    resultado["nvd"]["consulta"] = estado_consulta("nvd")
    resultado["epss"]["consulta"] = estado_consulta("epss")
    resultado["kev"]["consulta"] = estado_consulta("kev")
    kev = resultado['kev']
    kev['fogueira'] = ('atualizada' if kev['estado'] == 'Atualizado no cache' else
                       'desatualizada' if kev['estado'] in ('Desatualizado', 'Catálogo vazio (desatualizado)') else 'lacuna')
    nvd, epss = resultado['nvd'], resultado['epss']
    nvd['fogueira'] = estado_cobertura(nvd['total'], nvd['recentes'], nvd['antigos'],
        nvd['ausentes'] + nvd['invalidos'] + nvd['nao_lidos'], nvd['parcial'])
    epss['fogueira'] = estado_cobertura(epss['total'], epss['recentes'], epss['antigos'],
        epss['futuros'] + epss['sem_dados_coerentes'])
    for item, nome, data, disponiveis in (
        (kev, "CISA KEV", kev.get("atualizado_em"), kev.get("quantidade", 0)),
        (nvd, "NVD", nvd["ultima"], nvd["recentes"] + nvd["antigos"]),
        (epss, "FIRST EPSS", epss["ultima_coleta"], epss["recentes"] + epss["antigos"]),
    ):
        item["resumo"] = {**classificar_fonte(item["fogueira"], disponiveis, item.get("consulta"), item.get("parcial", False)),
                          "origem": nome, "atualizado_em": data, "idade_segundos": idade_segundos(data)}
    if ver_importacoes:
        from inventario.models import RelatorioScanner
        ultimo = RelatorioScanner.objects.order_by("-importado_em", "-pk").values(
            "origem", "observado_em", "importado_em").first()
        resultado["importacoes"] = {"total": RelatorioScanner.objects.count(), "ultima": ultimo,
            "idade_observacao_segundos": idade_segundos(ultimo["observado_em"]) if ultimo else None,
            "consulta": estado_consulta("scanner"),
            "estado": "Importação manual; validade e cobertura não determinadas" if ultimo else "Sem importações"}
    if ver_isca:
        from inventario.models import EventoHoneypot, SensorHoneypot
        resultado["isca"] = {"sensores": SensorHoneypot.objects.count(),
            "habilitados": SensorHoneypot.objects.filter(habilitado=True).count(),
            "eventos": EventoHoneypot.objects.count(),
            "ultimo_recebido": EventoHoneypot.objects.aggregate(valor=Max("recebido_em"))["valor"]}
    return resultado
