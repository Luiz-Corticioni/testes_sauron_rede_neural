"""Qualidade de evidências existentes, separada do cálculo de risco."""
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Count, F, Min, Q
from django.utils import timezone

from inventario.aplicacao.autorizacao import exigir
from inventario.aplicacao.cobertura import LEITURA, analisar_cobertura, preparar_revisao, ultimas_revisoes
from inventario.dominio.cobertura import estado
from inventario.dominio.qualidade_dados import avaliar, componente
from inventario.models import Ativo, Incidencia, ServicoNegocio

PERMISSOES = (*LEITURA, "inventario.view_incidencia", "inventario.view_vulnerabilidade")
STATUS = ("ABERTA", "TRATAMENTO", "MITIGADA", "ACEITA")
PERMISSOES_RISCO = ("inventario.view_ativo", "inventario.view_vulnerabilidade", "inventario.view_incidencia", "inventario.view_dependencia")


def componente_epss(qs):
    hoje = timezone.now().date()
    coerente = Q(vulnerabilidade__cve_id__isnull=False, vulnerabilidade__epss__isnull=False,
        vulnerabilidade__epss_data__isnull=False, vulnerabilidade__epss_observacao__isnull=False,
        vulnerabilidade__epss_observacao__cve_id=F("vulnerabilidade__cve_id"),
        vulnerabilidade__epss_observacao__data=F("vulnerabilidade__epss_data"),
        vulnerabilidade__epss_observacao__epss=F("vulnerabilidade__epss"))
    recente = coerente & ~Q(vulnerabilidade__cve_id="") & Q(vulnerabilidade__epss_data__gte=hoje - timedelta(days=2),
                          vulnerabilidade__epss_data__lte=hoje)
    dados = qs.aggregate(total=Count("pk"), recentes=Count("pk", filter=recente),
                         mais_antiga=Min("vulnerabilidade__epss_data", filter=recente))
    resultado = componente("epss", "Observações EPSS recentes e coerentes",
        dados["recentes"] if dados["total"] else None, dados["total"] or None,
        "Observações EPSS locais associadas a incidências elegíveis; data da mais antiga recente (janela de 2 dias)",
        data=dados["mais_antiga"].isoformat() if dados["mais_antiga"] else None,
        motivo="Sem incidências elegíveis; não é possível inferir cobertura." if not dados["total"] else "")
    resultado["idade_dias"] = (hoje - dados["mais_antiga"]).days if dados["mais_antiga"] else None
    return resultado


def incidencias_ativas():
    return Incidencia.objects.filter(status__in=STATUS).exclude(ativo__status__in=("BAIXADO", "INATIVO"))


def qualidade_recorte_risco(usuario, ativos=None):
    """Componentes do recorte observado; sem perímetro, revisão não é inferida."""
    exigir(usuario, *PERMISSOES_RISCO)
    qs = Incidencia.objects.filter(status__in=("ABERTA", "TRATAMENTO", "ACEITA"))
    if ativos is not None:
        qs = qs.filter(ativo_id__in=ativos)
    epss = componente_epss(qs)
    epss["origem"] = "Incidências abertas, em tratamento ou aceitas do recorte; EPSS não entra na fórmula de risco"
    revisao = componente("revisao", "Revisão da cobertura de relações", None, None,
        "Perímetro e camada não selecionados neste recorte",
        motivo="Informe um perímetro e uma camada na avaliação de cobertura para examinar as revisões.")
    return {**avaliar([epss, componente_fontes(), revisao]),
            "escopo": "Ativos filtrados" if ativos is not None else "Todos os ativos do modelo"}


def componente_fontes():
    from inventario.aplicacao.estado_fontes import resumo_fontes

    fontes = resumo_fontes()
    resumos = [fontes[nome]["resumo"] for nome in ("nvd", "kev")]
    parcial = any(item["codigo"] == "incompleto" for item in resumos)
    resultado = componente("fontes", "Atualidade local de NVD e KEV",
        None if parcial else sum(item["codigo"] == "ok" for item in resumos), None if parcial else 2,
        "Estado local global de NVD e CISA KEV",
        motivo="Amostra NVD incompleta; não é possível avaliar todas as fontes." if parcial
               else "Estado global do inventário; não comprova conectividade atual nem aplicabilidade ao ativo.")
    resultado["fontes"] = resumos
    return resultado


def qualidade_montecarlo(total, faltantes, data=None):
    epss = componente("epss", "Observações EPSS recentes e coerentes",
        total - faltantes if total else None, total or None, "Entradas elegíveis da simulação de 30 dias",
        data=data, motivo="Sem incidências elegíveis." if not total else "")
    epss["idade_dias"] = (timezone.now().date() - date.fromisoformat(data)).days if data else None
    premissas = componente("premissas", "Validação das premissas financeiras", None, None,
        "Premissas do cenário", motivo="Não existe registro de validação independente das premissas.")
    revisoes = componente("revisao", "Cobertura de relações do cenário", None, None,
        "Contexto da simulação", motivo="A simulação não identifica perímetro e camada para esta avaliação.")
    return avaliar([epss, premissas, revisoes])


def qualidade_premissas(cenario):
    """Declarações de origem não são evidência de validação independente."""
    if hasattr(cenario, "origem_frequencia"):
        origens = [("frequência", cenario.origem_frequencia), ("perdas", cenario.origem_perdas)]
        if cenario.premissas.get("modo") != "LEF":
            origens.append(("suscetibilidade ou controles", cenario.origem_suscetibilidade))
    else:
        origens = [("premissas", cenario.origem)]
    data = cenario.data_referencia
    declaradas = componente("origens", "Origens declaradas das premissas",
        sum(bool(isinstance(valor, str) and valor.strip()) for _, valor in origens), len(origens),
        "Campos declarados no cenário; conteúdo não verificado",
        data=data.isoformat() if data else None,
        motivo=f"Classificação declarada: {cenario.qualidade}; não representa validação independente.")
    declaradas["fontes_declaradas"] = [{"campo": campo, "descricao": valor} for campo, valor in origens]
    declaradas["idade_dias"] = (timezone.localdate() - data).days if data and data <= timezone.localdate() else None
    validacao = componente("validacao", "Validação independente das premissas", None, None,
        "Cenário financeiro", motivo="Não existe registro de validação independente neste fluxo.")
    return avaliar([declaradas, validacao])


@transaction.atomic
def qualidade_ativo(usuario, ativo_id, perimetro=None, tipo="REDE", principal=""):
    exigir(usuario, *PERMISSOES)
    ativo = Ativo.objects.get(pk=ativo_id)
    epss = componente_epss(incidencias_ativas().filter(ativo=ativo))
    if perimetro is None:
        revisao = componente("revisao", "Revisão da cobertura de relações", None, None,
            "Perímetro e camada declarados", motivo="Selecione um perímetro e uma camada para avaliar a revisão.")
    else:
        p, contexto = preparar_revisao(usuario, perimetro, tipo, ativo.pk, principal)
        ultima = ultimas_revisoes(p.pk, tipo, principal).filter(ativo=ativo).values(
            "contexto_sha256", "revisar_em", "resultado", "observada_em").first()
        situacao = estado(ultima, contexto, timezone.localdate())
        valida = situacao in {"REVISADO", "SEM_RELACOES"}
        revisao = componente("revisao", "Revisão da cobertura de relações", int(valida), 1,
            f"Perímetro {p.nome}; camada {tipo}",
            data=ultima["observada_em"].isoformat() if ultima else None,
            motivo=f"Situação da revisão: {situacao}. Não comprova descoberta completa.")
        revisao["idade_dias"] = (timezone.localdate() - ultima["observada_em"]).days if ultima else None
    return {**avaliar([epss, revisao, componente_fontes()]), "ativo_id": ativo.pk, "perimetro_id": perimetro,
            "tipo": tipo if perimetro is not None else None}


@transaction.atomic
def qualidade_servico(usuario, servico_id):
    exigir(usuario, *PERMISSOES, "inventario.view_serviconegocio")
    servico = ServicoNegocio.objects.select_related("perimetro").get(pk=servico_id)
    cobertura = analisar_cobertura(usuario, servico.perimetro_id, "NEGOCIO", limite=1)
    total = cobertura["ativos_operacionais"]
    revisoes = componente("revisao", "Revisões de relações de negócio no prazo",
        cobertura["revisados_no_prazo"] if total else None, total or None,
        f"Perímetro {servico.perimetro.nome}; camada NEGOCIO",
        data=cobertura["data"], motivo="Cobertura declarada; não comprova descoberta completa.")
    membros = servico.perimetro.membros.values("ativo_id")
    epss = componente_epss(incidencias_ativas().filter(ativo_id__in=membros))
    return {**avaliar([epss, revisoes, componente_fontes()]), "servico_id": servico.pk, "perimetro_id": servico.perimetro_id}
