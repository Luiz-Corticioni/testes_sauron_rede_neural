"""Prepara um cenário v2 apenas com relações e premissas declaradas."""
from datetime import timedelta
import hashlib
import json

from django.db import transaction
from django.utils import timezone

from inventario.aplicacao.autorizacao import exigir
from inventario.aplicacao.cache_consultas import lembrar
from inventario.aplicacao.montecarlo import incidencias_elegiveis, validar_parametros
from inventario.aplicacao.relacoes import carregar_recorte
from inventario.aplicacao.risco import namespace_risco, versao_dados
from inventario.dominio.cobertura import motivo
from inventario.dominio.grafo_relacoes import GrafoRelacoes
from inventario.infraestrutura.limite_simulacoes import vaga_simulacao
from inventario.matematica.montecarlo_v2 import FATORES, simular_v2

PERMISSOES = ("inventario.view_ativo", "inventario.view_vulnerabilidade", "inventario.view_incidencia",
              "inventario.view_dependencia", "inventario.view_relacaoativos")
CAMPOS = {"origem_ativo", "escopo", "incidencias", "fatores", "custos", "n", "seed", "teto", "correlacao", "intervencoes", "apetite", "sensibilidade", "calibrar"}


def calcular(usuario, dados):
    exigir(usuario, *PERMISSOES)
    if not isinstance(dados, dict) or set(dados) - CAMPOS:
        raise ValueError("Envie apenas os parâmetros conhecidos do cenário v2.")
    origem, escopo, ids = dados.get("origem_ativo"), dados.get("escopo"), dados.get("incidencias")
    if not isinstance(origem, str) or not origem or not isinstance(escopo, str) or not escopo.strip():
        raise ValueError("Informe um ativo de origem e um escopo de rede declarado.")
    if not isinstance(ids, list) or not ids or len(ids) > 1000 or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Informe de 1 a 1000 incidências distintas.")
    fatores = dados.get("fatores", {})
    if not isinstance(fatores, dict) or set(fatores) - set(ids):
        raise ValueError("Fatores devem corresponder às incidências selecionadas.")
    if "custos" not in dados:
        raise ValueError("Informe explicitamente os custos hipotéticos de C, I e A.")
    parametros = validar_parametros({k: dados[k] for k in ("custos", "n", "seed", "teto") if k in dados})
    usar_calibracao = dados.get("calibrar", False)
    if type(usar_calibracao) is not bool:
        raise ValueError("Calibração deve ser verdadeira ou falsa.")
    if usar_calibracao:
        from inventario.aplicacao.perdas_financeiras import LEITURA
        exigir(usuario, *LEITURA)
    if parametros["n"] * len(ids) > 1_000_000:
        raise ValueError("Reduza o cenário: limite de um milhão de vínculos × simulações.")
    with transaction.atomic():
        ativos, linhas, perimetro = carregar_recorte("REDE", escopo)
        if perimetro is None:
            raise ValueError("O escopo precisa corresponder a um perímetro declarado.")
        nos = {a["id"] for a in ativos}
        if origem not in nos:
            raise ValueError("A origem deve pertencer ao perímetro operacional.")
        hoje = timezone.localdate()
        hoje_epss = timezone.now().date()
        elegiveis = [linha for linha in linhas if motivo(linha, nos, hoje) == "ELEGIVEL"]
        grafo = GrafoRelacoes(sorted(nos), elegiveis)
        anteriores, distancias = grafo.busca(origem)
        incidencias = list(incidencias_elegiveis().filter(pk__in=ids).select_related("software"))
        if {i.pk for i in incidencias} != set(ids):
            raise ValueError("Há incidência inexistente ou inelegível no cenário.")
        pendencias, entradas, caminhos, datas_epss = [], [], [], []
        for i in incidencias:
            v, obs = i.vulnerabilidade, i.vulnerabilidade.epss_observacao
            epss_valido = not (not v.cve_id or v.epss is None or obs is None or v.epss_data is None or
                    not hoje_epss - timedelta(days=2) <= v.epss_data <= hoje_epss or obs.cve_id != v.cve_id or
                    obs.data != v.epss_data or obs.epss != v.epss)
            if epss_valido:
                datas_epss.append(v.epss_data)
            caminho = grafo.caminho(i.ativo_id, anteriores, distancias)
            if not caminho["alcancavel"] or not caminho["completo"]:
                pendencias.append({"incidencia": i.pk, "campo": "alcance", "motivo": "Caminho declarado completo não disponível; isso não comprova isolamento."})
            declarados = fatores.get(i.pk, {})
            for campo in FATORES:
                fator = declarados.get(campo) if isinstance(declarados, dict) else None
                if (not isinstance(fator, dict) or fator.get("faixa") is None or
                        not isinstance(fator.get("origem"), str) or not fator["origem"].strip()):
                    pendencias.append({"incidencia": i.pk, "campo": campo, "motivo": "Informe faixa e origem da hipótese."})
            causas = [f"relacao:{passo['relacao']}" for passo in caminho["passos"]]
            if i.software_id and i.software.purl:
                causas.append("componente:" + i.software.purl)
            entradas.append({"id": i.pk, "ativo": i.ativo_id, "cve": v.cve_id or v.pk, "cvss": v.cvss,
                "epss": v.epss if epss_valido else None, "epss_data": v.epss_data.isoformat() if epss_valido else None,
                "epss_fonte": obs.fonte if epss_valido else None, "observacao_epss_id": v.epss_observacao_id if epss_valido else None,
                "vetor": v.cvss_vetor, "kev": v.kev, "exposicao": 1, "causas": causas})
            caminhos.append({"incidencia": i.pk, "ativo": i.ativo_id, "caminho": caminho})
        if pendencias:
            return {"versao_modelo": "sauron.montecarlo/30d-v2", "horizonte_dias": 30,
                    "disponivel": False, "pendencias_total": len(pendencias), "pendencias": pendencias[:100],
                    "pendencias_limitadas": len(pendencias) > 100,
                    "aviso": "Sem evidências e hipóteses suficientes não é possível calcular o cenário."}
        custos = parametros["custos"]
        calibracao = {"calibrado": False, "motivo": "Ajuste local não solicitado."}
        if usar_calibracao:
            from inventario.aplicacao.perdas_financeiras import calibrar
            custos, calibracao = calibrar(usuario, custos)
            comparacoes = dados.get("intervencoes") or []
            if not isinstance(comparacoes, list) or len(ids) * parametros["n"] * (1 + len(comparacoes) + 6 * int(dados.get("sensibilidade") is True)) * 2 > 8_000_000:
                raise ValueError("Reduza o cenário: limite de trabalho para comparação da calibração excedido.")
        assinatura_grafo = hashlib.sha256(json.dumps({"ativos": ativos, "relacoes": linhas, "data": hoje.isoformat()},
            sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()
        assinatura = hashlib.sha256(json.dumps({"dados": dados, "entradas": entradas, "grafo": assinatura_grafo,
            "custos_calibrados": custos, "calibracao": calibracao, "data_epss_utc": hoje_epss.isoformat()},
            sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        versao = versao_dados("puro")
        chave = f"montecarlo:30d-v2:{namespace_risco()}:{versao}:{assinatura}"

        def construir():
            from inventario.aplicacao.qualidade_dados import qualidade_montecarlo
            with vaga_simulacao():
                resultado = simular_v2(entradas, fatores, custos=custos, n=parametros["n"],
                    seed=parametros["seed"], teto=parametros["teto"], correlacao=dados.get("correlacao", 0),
                    intervencoes=dados.get("intervencoes"), apetite=dados.get("apetite"),
                    sensibilidade=dados.get("sensibilidade", False))
                if calibracao["calibrado"]:
                    anterior = simular_v2(entradas, fatores, custos=parametros["custos"], n=parametros["n"],
                        seed=parametros["seed"], teto=parametros["teto"], correlacao=dados.get("correlacao", 0))
                    calibracao["antes"] = anterior["antes"]
                    calibracao["depois"] = resultado["antes"]
            qualidade = qualidade_montecarlo(len(incidencias), len(incidencias)-len(datas_epss), min(datas_epss).isoformat() if datas_epss else None)
            qualidade["componentes"][2]["motivo"] = "Perímetro e caminho declarados; a revisão completa da cobertura não foi avaliada nesta simulação."
            resultado.update(origem_ativo=origem, escopo=escopo.strip(), perimetro_id=perimetro.pk,
                grafo_sha256=assinatura_grafo, caminhos=caminhos,
                relacoes_excluidas=len(linhas)-len(elegiveis), data_contexto=hoje.isoformat(), calibracao=calibracao,
                qualidade_dados=qualidade, versao_dados=versao, custos_originais=parametros["custos"])
            return resultado

        return lembrar(chave, construir)
