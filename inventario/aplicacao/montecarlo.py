"""Caso de uso comum à web/CLI; parâmetros por cliente recebidos sem gravação."""
import hashlib
import json
from inventario.aplicacao.cache_consultas import lembrar
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from inventario.aplicacao.risco import namespace_risco, versao_dados
from inventario.matematica.montecarlo import CUSTOS_CLIENTE, numero, validar_custos, simular
from inventario.models import Incidencia
from inventario.aplicacao.epss import sincronizar_epss, situacao_epss  # noqa: F401

STATUS_CONSIDERADOS = ("ABERTA", "TRATAMENTO", "MITIGADA", "ACEITA")
CAMPOS = {"custos", "n", "seed", "teto", "exposicao_internet", "exposicao_interna",
          "cves_corrigidas", "incidencias_corrigidas"}


def validar_parametros(dados):
    if not isinstance(dados, dict):
        raise ValueError("Envie um objeto JSON.")
    if set(dados) - CAMPOS:
        raise ValueError("Parâmetros desconhecidos: " + ", ".join(sorted(set(dados) - CAMPOS)))
    n, seed = dados.get("n", 20_000), dados.get("seed", 42)
    if type(n) is not int or not 100 <= n <= 100_000:
        raise ValueError("Número de simulações deve ser inteiro entre 100 e 100000.")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("Seed deve ser inteiro entre 0 e 4294967295.")
    r = {"n": n, "seed": seed, "custos": validar_custos(dados.get("custos", CUSTOS_CLIENTE)),
         "teto": None if dados.get("teto") is None else numero(dados["teto"], "Teto para 30 dias"),
         "exposicao_internet": numero(dados.get("exposicao_internet", 1), "Exposição internet", 0, 1),
         "exposicao_interna": numero(dados.get("exposicao_interna", 1), "Fator de cenário interno", 0, 1)}
    for campo in ("cves_corrigidas", "incidencias_corrigidas"):
        ids = dados.get(campo, [])
        if not isinstance(ids, list) or len(ids) > 10000 or any(not isinstance(i, str) or not 1 <= len(i) <= 60 for i in ids):
            raise ValueError(f"{campo}: envie lista de até 10000 identificadores de texto.")
        r[campo] = sorted(set(ids))
    return r


def incidencias_elegiveis():
    # Risco aceito e mitigado continuam presentes: não são correções comprovadas.
    return Incidencia.objects.filter(status__in=STATUS_CONSIDERADOS).exclude(
        ativo__status__in=["BAIXADO", "INATIVO"]).select_related("ativo", "vulnerabilidade__epss_observacao").order_by("ativo_id", "vulnerabilidade_id")


def calcular_montecarlo(dados=None):
    parametros = validar_parametros({} if dados is None else dados)
    with transaction.atomic():
        versao = versao_dados("puro")
        assinatura = hashlib.sha256(json.dumps(parametros, sort_keys=True, allow_nan=False).encode()).hexdigest()
        hoje = timezone.now().date()
        chave = f"montecarlo:30d-v1:{namespace_risco()}:{versao}:{hoje}:{assinatura}"
        def construir():
            incidencias = list(incidencias_elegiveis())
            # Limite explícito de trabalho/memória para requisições locais concorrentes.
            if len(incidencias) * parametros["n"] > 8_000_000:
                raise ValueError("Cenário muito grande: reduza o número de simulações (limite de 8 milhões de vínculos × cenários).")
            if set(parametros["cves_corrigidas"]) - {i.vulnerabilidade.cve_id or i.vulnerabilidade_id for i in incidencias}:
                raise ValueError("CVE/ID sem incidência elegível neste cenário.")
            if set(parametros["incidencias_corrigidas"]) - {i.id for i in incidencias}:
                raise ValueError("Incidência inexistente ou não elegível neste cenário.")
            pendencias = []
            for i in incidencias:
                v, o = i.vulnerabilidade, i.vulnerabilidade.epss_observacao
                if (v.epss is None or o is None or v.epss_data is None
                        or not hoje-timedelta(days=2) <= v.epss_data <= hoje
                        or o.cve_id != v.cve_id or o.data != v.epss_data or o.epss != v.epss):
                    pendencias.append({"incidencia": i.pk, "ativo": i.ativo_id, "cve": v.cve_id or v.pk,
                        "motivo": "EPSS ausente, sem observação de origem coerente ou fora da janela local de atualização (2 dias)."})
            if pendencias:
                return {"versao_modelo": "sauron.montecarlo/30d-v1", "horizonte_dias": 30, "disponivel": False,
                    "n": parametros["n"], "versao_dados": versao, "quantidade_incidencias": len(incidencias), "pendencias_total": len(pendencias),
                    "pendencias": pendencias[:100], "pendencias_limitadas": len(pendencias) > 100,
                    "antes": None, "depois": None,
                    "aviso": "Dados insuficientes para calcular perdas. Use a atualização EPSS nesta página ou solicite ao responsável; confira as incidências indicadas. Não foi atribuído zero ou uma probabilidade derivada de CVSS."}
            entradas = []
            for i in incidencias:
                v = i.vulnerabilidade
                entradas.append({"id": i.id, "ativo": i.ativo_id, "cve": v.cve_id or v.id,
                    "cvss": v.cvss, "epss": v.epss, "observacao_epss_id": v.epss_observacao_id,
                    "epss_situacao": situacao_epss(v), "epss_fonte": v.epss_observacao.fonte if v.epss_observacao_id else None, "epss_data": v.epss_data.isoformat() if v.epss_data else None,
                    "vetor": v.cvss_vetor, "kev": v.kev,
                    "exposicao": parametros["exposicao_internet" if i.ativo.exposto_internet else "exposicao_interna"]})
            resultado = simular(entradas, **{k: parametros[k] for k in ("custos", "n", "seed", "teto")},
                corrigidas=parametros["cves_corrigidas"] + parametros["incidencias_corrigidas"])
            resultado.update(parametros=parametros, versao_dados=versao,
                quantidade_incidencias=len(incidencias), quantidade_ativos=len({i.ativo_id for i in incidencias}),
                hipotese_epss="EPSS observado em até 2 dias é usado somente no horizonte de 30 dias. KEV é evidência de exploração e não cria piso numérico. Fatores de cenário, custos e independência entre vínculos são hipóteses, não calibração local.",
                escopo="Abertas, em tratamento, mitigadas e aceitas em ativos ativos/em manutenção. Corrigidas e sugeridas excluídas.")
            return resultado


        return lembrar(chave, construir)
