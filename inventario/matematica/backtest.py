"""Experimento offline: prioridades contrafactuais sobre um recorte histórico."""
from datetime import date
import hashlib
import math
import platform

import numpy as np
import scipy

from inventario.dominio.vulnerabilidades import CVE_RE, VUL_RE, Dependencia, Incidencia, Vulnerabilidade
from inventario.matematica.risco import ModeloRisco

VERSAO = "sauron.backtest/1"
ACOES = {"defer": 0, "scheduled": 1, "out-of-cycle": 2, "immediate": 3}
MAX_CVES, MAX_ATIVOS, MAX_ARESTAS = 1000, 1000, 10000


def data(valor, nome):
    if not isinstance(valor, str) or len(valor) != 10:
        raise ValueError(f"{nome}: use data ISO AAAA-MM-DD.")
    try:
        return date.fromisoformat(valor)
    except ValueError as erro:
        raise ValueError(f"{nome}: data inválida.") from erro


def numero(valor, nome, minimo, maximo):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or not minimo <= valor <= maximo:
        raise ValueError(f"{nome}: valor inválido.")
    return float(valor)


def observacao(objeto, corte, nome):
    """Rejeita inconsistências e ignora registros não disponíveis no corte."""
    if objeto is None:
        return None
    if not isinstance(objeto, dict) or not {"valor", "observado_em", "disponivel_em"} <= objeto.keys():
        raise ValueError(f"{nome}: observação exige valor, observado_em e disponivel_em.")
    observado = data(objeto["observado_em"], nome)
    disponivel = data(objeto["disponivel_em"], nome)
    if observado > disponivel:
        raise ValueError(f"{nome}: disponibilidade anterior à observação.")
    if observado > corte or disponivel > corte:
        return None
    return objeto["valor"]


def intervalo_wilson(acertos, total):
    if total == 0:
        return None
    z = 1.959963984540054
    proporcao = acertos / total
    denominador = 1 + z*z / total
    centro = (proporcao + z*z / (2*total)) / denominador
    margem = z * math.sqrt(proporcao*(1-proporcao)/total + z*z/(4*total*total)) / denominador
    return [min(proporcao, max(0., centro-margem)), max(proporcao, min(1., centro+margem))]


def executar(dados, orcamento, seed=42):
    if not isinstance(dados, dict) or dados.get("formato") != VERSAO:
        raise ValueError("Formato de backtest não reconhecido.")
    if type(seed) is not int or not 0 <= seed <= 2**32-1:
        raise ValueError("A semente deve ser um inteiro entre 0 e 4294967295.")
    corte, fim = data(dados.get("corte"), "corte"), data(dados.get("fim"), "fim")
    if fim <= corte:
        raise ValueError("O fim da observação deve ser posterior ao corte.")
    fontes = dados.get("fontes")
    chaves_fontes = {"inventario", "cvss", "epss", "kev", "ssvc", "exploracao"}
    if (not isinstance(fontes, dict) or set(fontes) != chaves_fontes or
            any(not isinstance(v, str) or not 1 <= len(v.strip()) <= 300 for v in fontes.values())):
        raise ValueError("Informe fonte e versão para inventário, CVSS, EPSS, KEV, SSVC e exploração.")
    inventario = dados.get("inventario")
    if not isinstance(inventario, dict):
        raise ValueError("Informe o snapshot do inventário.")
    observado = data(inventario.get("observado_em"), "inventário observado")
    disponivel = data(inventario.get("disponivel_em"), "inventário disponível")
    if not observado <= disponivel <= corte:
        raise ValueError("O snapshot do inventário precisa estar disponível até o corte.")
    configuracao = inventario.get("modelo_sauron")
    if not isinstance(configuracao, dict) or configuracao.get("perfil") not in {"puro", "operacional"}:
        raise ValueError("O snapshot exige o perfil histórico do modelo do Sauron.")
    perfil = configuracao["perfil"]
    kappa = numero(configuracao.get("kappa"), "Kappa", 0, 100)
    ativos, vinculos, dependencias = (inventario.get(k) for k in ("ativos", "incidencias", "dependencias"))
    if not all(isinstance(x, list) for x in (ativos, vinculos, dependencias)) or not ativos or len(ativos) > MAX_ATIVOS or len(vinculos) > MAX_ARESTAS or len(dependencias) > MAX_ARESTAS:
        raise ValueError("Inventário vazio, inválido ou acima dos limites do experimento.")
    fatores = {}
    for ativo in ativos:
        if not isinstance(ativo, dict) or not isinstance(ativo.get("id"), str) or not 1 <= len(ativo["id"]) <= 60 or ativo["id"] in fatores:
            raise ValueError("Ativo inválido ou repetido.")
        fatores[ativo["id"]] = numero(ativo.get("fator_exposicao"), "Exposição", 0, 100)
    deps, arestas = [], set()
    for dep in dependencias:
        if not isinstance(dep, dict) or dep.get("dependente") not in fatores or dep.get("fornecedor") not in fatores:
            raise ValueError("Dependência aponta para ativo inexistente.")
        chave = (dep["dependente"], dep["fornecedor"])
        if chave in arestas:
            raise ValueError("Dependência repetida.")
        arestas.add(chave)
        deps.append(Dependencia(*chave, numero(dep.get("peso"), "Peso da dependência", 0, 0.999999)))
    catalogo = dados.get("kev")
    if not isinstance(catalogo, dict) or catalogo.get("completo") is not True or data(catalogo.get("disponivel_em"), "Catálogo KEV") > corte or not isinstance(catalogo.get("cves"), list) or len(catalogo["cves"]) > 100000:
        raise ValueError("Informe catálogo KEV completo e disponível até o corte.")
    kev = set()
    for item in catalogo["cves"]:
        if not isinstance(item, dict) or not isinstance(item.get("cve"), str) or not CVE_RE.fullmatch(item["cve"]):
            raise ValueError("Entrada KEV inválida.")
        if data(item.get("adicionada_em"), "Data KEV") <= corte:
            kev.add(item["cve"].upper())
    linhas = dados.get("vulnerabilidades")
    if not isinstance(linhas, list) or len(linhas) > MAX_CVES:
        raise ValueError("Lista de vulnerabilidades inválida ou acima do limite.")
    excluidas, candidatos, ids_vul, cves_vistas = [], {}, set(), set()
    for item in linhas:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not VUL_RE.fullmatch(item["id"]) or not isinstance(item.get("cve"), str) or not CVE_RE.fullmatch(item["cve"]):
            raise ValueError("Cada vulnerabilidade exige ID e CVE válidos.")
        identificador, cve = item["id"], item["cve"].upper()
        if identificador in ids_vul or cve in cves_vistas:
            raise ValueError("ID ou CVE repetida no universo.")
        ids_vul.add(identificador)
        cves_vistas.add(cve)
        cvss = observacao(item.get("cvss"), corte, "CVSS")
        epss = observacao(item.get("epss"), corte, "EPSS")
        ssvc = observacao(item.get("ssvc"), corte, "SSVC")
        if ssvc is not None:
            registro = item["ssvc"]
            if registro.get("contexto_valido") is not True or data(registro.get("revisar_em"), "Revisão SSVC") <= corte:
                ssvc = None
        ambiental = observacao(item.get("cvss_ambiental"), corte, "CVSS ambiental")
        if cvss is None or epss is None or ssvc is None or ssvc == "pending" or ambiental is None:
            excluidas.append({"cve": cve, "motivo": "CVSS, CVSS ambiental, EPSS ou SSVC ausente, pendente ou indisponível no corte."})
            continue
        cvss, epss = numero(cvss, "CVSS", 0, 10), numero(epss, "EPSS", 0, 1)
        if not isinstance(ssvc, str) or ssvc not in ACOES:
            raise ValueError("Ação SSVC inválida.")
        ambiental = numero(ambiental, "CVSS ambiental", 0, 10)
        vulnerabilidade = Vulnerabilidade(identificador, "Snapshot histórico", "BACKTEST", cvss, cve_id=cve)
        candidatos[cve] = {"vul": vulnerabilidade, "epss": epss, "ssvc": ssvc, "ambiental": ambiental}
    ocorrencias, ids_inc, pares = [], set(), set()
    for item in vinculos:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"] or item["id"] in ids_inc or item.get("ativo") not in fatores or not isinstance(item.get("cve"), str):
            raise ValueError("Incidência inválida ou repetida.")
        ids_inc.add(item["id"])
        cve = item["cve"].upper()
        if cve not in cves_vistas:
            raise ValueError("Incidência aponta para CVE fora do universo.")
        status = item.get("status")
        if status not in {"ABERTA", "TRATAMENTO", "ACEITA", "MITIGADA", "CORRIGIDA", "SUGERIDA"}:
            raise ValueError("Status de incidência inválido.")
        par = (item["ativo"], cve)
        if par in pares:
            raise ValueError("Par ativo/CVE repetido.")
        pares.add(par)
        if cve in candidatos and status in {"ABERTA", "TRATAMENTO", "ACEITA"}:
            ocorrencias.append(Incidencia(item["id"], item["ativo"], candidatos[cve]["vul"].id, status=status))
    ativos_candidatos = {i.vulnerabilidade_id for i in ocorrencias}
    for cve in list(candidatos):
        if candidatos[cve]["vul"].id not in ativos_candidatos:
            excluidas.append({"cve": cve, "motivo": "Sem incidência elegível no snapshot."})
            del candidatos[cve]
    if not candidatos:
        raise ValueError("Não há CVEs com dados comparáveis e incidência elegível no corte.")
    if type(orcamento) is not int or not 1 <= orcamento <= len(candidatos):
        raise ValueError("Orçamento deve estar entre 1 e o tamanho do universo comparável.")
    eventos = dados.get("eventos")
    if not isinstance(eventos, list) or len(eventos) > 100000:
        raise ValueError("Informe uma lista de eventos documentados dentro do limite.")
    metadados_eventos = dados.get("eventos_metadados")
    if not isinstance(metadados_eventos, dict):
        raise ValueError("Declare a cobertura temporal e a data de extração dos eventos.")
    cobertura_eventos = data(metadados_eventos.get("cobertura_ate"), "Cobertura dos eventos")
    extracao_eventos = data(metadados_eventos.get("extraido_em"), "Extração dos eventos")
    if cobertura_eventos < fim or extracao_eventos < cobertura_eventos:
        raise ValueError("Os eventos devem cobrir o fim da janela e ser extraídos após essa cobertura.")
    observadas = set()
    for evento in eventos:
        if not isinstance(evento, dict) or not isinstance(evento.get("cve"), str) or not CVE_RE.fullmatch(evento["cve"]) or not isinstance(evento.get("fonte"), str) or not evento["fonte"].strip():
            raise ValueError("Evento exige CVE e fonte não vazia.")
        quando = data(evento.get("observado_em"), "Evento observado")
        disponivel = data(evento.get("disponivel_em"), "Evento disponível")
        if quando > disponivel:
            raise ValueError("Evento disponível antes de observado.")
        cve = evento["cve"].upper()
        if corte < quando <= fim and disponivel <= fim and cve in candidatos:
            observadas.add(cve)
    def desempate(cve):
        return hashlib.sha256(f"{seed}|{cve}".encode()).hexdigest()
    ordenadas = sorted(candidatos, key=desempate)
    ordem_cvss = sorted(ordenadas, key=lambda c: -candidatos[c]["vul"].cvss)
    ordem_kev = sorted(ordenadas, key=lambda c: (-(c in kev), -candidatos[c]["vul"].cvss))
    ordem_epss = sorted(ordenadas, key=lambda c: -candidatos[c]["epss"])
    ordem_ssvc = sorted(ordenadas, key=lambda c: -ACOES[candidatos[c]["ssvc"]])
    ambientais = {candidatos[c]["vul"].id: candidatos[c]["ambiental"] for c in ordenadas}
    modelo = ModeloRisco(sorted(fatores), [candidatos[c]["vul"] for c in ordenadas], ocorrencias, deps,
                         fatores, {candidatos[c]["vul"].id for c in kev if c in candidatos}, scores_ambientais=ambientais)
    prioridade = modelo.calcular(perfil=perfil, kappa=kappa).prioridade_correcao
    ordem_sauron = [item["cve_id"] for item in prioridade]
    ordens = {"cvss": ordem_cvss, "cvss_kev": ordem_kev, "epss": ordem_epss, "ssvc": ordem_ssvc, "sauron": ordem_sauron}
    resultados = {}
    for nome, ordem in ordens.items():
        escolhidas = ordem[:orcamento]
        acertos = len(set(escolhidas) & observadas)
        resultados[nome] = {"selecionadas": escolhidas, "esforco_cves": len(escolhidas), "observadas_selecionadas": acertos,
            "cobertura": acertos / len(observadas) if observadas else None,
            "cobertura_ic95_wilson": intervalo_wilson(acertos, len(observadas)),
            "eficiencia": acertos / len(escolhidas), "eficiencia_ic95_wilson": intervalo_wilson(acertos, len(escolhidas))}
    return {"formato": VERSAO, "corte": corte.isoformat(), "fim": fim.isoformat(), "seed": seed,
        "fontes": fontes, "universo_total": len(linhas), "universo_comparavel": len(candidatos),
        "eventos_metadados": {"cobertura_ate": cobertura_eventos.isoformat(), "extraido_em": extracao_eventos.isoformat()},
        "excluidas": excluidas, "eventos_observados": len(observadas), "orcamento": orcamento,
        "modelo_sauron": {"perfil": perfil, "kappa": kappa, "ordenacao": "CVSS ambiental, depois redução estimada"},
        "versoes": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        "resultados": resultados,
        "aviso": "Seleção contrafactual de CVEs, não correções realizadas. Ausência de registro de exploração não prova ausência de exploração; intervalos supõem amostragem independente."}
