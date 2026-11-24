"""Resumo executivo a partir de registros existentes, sem calcular previsões novas."""
from datetime import timedelta
from math import isfinite

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.template.loader import render_to_string
from django.utils import timezone

from inventario.aplicacao.autorizacao import exigir
from inventario.aplicacao.qualidade_dados import componente_epss, componente_fontes, incidencias_ativas
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import ExecucaoFAIR, HistoricoIncidencia, Incidencia, ServicoNegocio, SnapshotRisco

LEITURA = ("inventario.view_ativo", "inventario.view_vulnerabilidade", "inventario.view_incidencia",
           "inventario.view_cenariofinanceiro", "inventario.view_serviconegocio", "inventario.view_perimetrorelacoes",
           "inventario.view_snapshotrisco", "inventario.view_historicoincidencia")
EXPORTACAO = (*LEITURA, "inventario.change_incidencia")
DESTINOS = {"diretoria": "Diretoria", "revisao_interna": "Revisão interna", "arquivo_local": "Arquivo local"}


def financeiro(execucao):
    if not execucao:
        return None
    resultado = execucao.resultado if isinstance(execucao.resultado, dict) else {}
    perda = resultado.get("perda")
    if not isinstance(perda, dict) or any(type(perda.get(k)) not in (int, float) or not isfinite(perda[k]) or perda[k] < 0 for k in ("media", "P5", "P95")):
        return None
    if perda["P5"] > perda["P95"] or resultado.get("horizonte_dias") != 30:
        return None
    premissas = execucao.premissas_snapshot if isinstance(execucao.premissas_snapshot, dict) else {}
    return {"id": execucao.pk, "nome": premissas.get("nome", "Cenário"),
            "escopo": premissas.get("escopo", "Não informado"),
            "qualidade": premissas.get("qualidade", "Não informada"),
            "data_referencia": premissas.get("data_referencia"),
            "modelo": execucao.versao_modelo, "criada_em": execucao.criado_em,
            "n": execucao.n, "media": perda["media"], "p5": perda["P5"], "p95": perda["P95"],
            "qualidade_dados": resultado.get("qualidade_dados")}


def montar(usuario, execucao_id=None):
    exigir(usuario, *LEITURA)
    agora = timezone.now()
    inicio = agora - timedelta(days=7)
    servicos = list(ServicoNegocio.objects.annotate(pendencias=Count(
        "perimetro__membros__ativo__incidencia", distinct=True,
        filter=Q(perimetro__membros__ativo__incidencia__status__in=("ABERTA", "TRATAMENTO", "MITIGADA", "ACEITA"))
               & ~Q(perimetro__membros__ativo__status__in=("INATIVO", "BAIXADO"))))
        .filter(pendencias__gt=0).order_by("-pendencias", "-criticidade", "nome")[:5])
    candidatos = ExecucaoFAIR.objects.order_by("-criado_em", "-pk")
    execucao = candidatos.filter(pk=execucao_id).first() if execucao_id else candidatos.first()
    if execucao_id and not execucao:
        raise ValidationError("Execução financeira não encontrada.")
    atual = SnapshotRisco.objects.filter(perfil="puro", ts__gte=inicio, ts__lte=agora).order_by("-ts", "-pk").first()
    anterior = SnapshotRisco.objects.filter(perfil="puro", ts__lte=inicio).order_by("-ts", "-pk").first()
    mudanca = None
    if atual and anterior:
        mudanca = {"atual": atual.ts, "anterior": anterior.ts, "variacao": atual.risco_total - anterior.risco_total,
                   "simulado": atual.chave.startswith("DEMO-") or anterior.chave.startswith("DEMO-")}
    historico = HistoricoIncidencia.objects.filter(em__gte=inicio, em__lte=agora)
    return {"gerado_em": agora, "inicio": inicio, "servicos": servicos,
            "financeiro": financeiro(execucao), "execucao_selecionada": execucao.pk if execucao else None,
            "execucoes": list(candidatos.values("pk", "criado_em", "premissas_snapshot")[:30]),
            "epss": componente_epss(incidencias_ativas()), "fontes": componente_fontes(),
            "decisoes": Incidencia.objects.exclude(decisao_pendente="").count(),
            "vencidas": Incidencia.objects.pendentes_sla().filter(prazo_correcao__lt=timezone.localdate()).count(),
            "correcoes_semana": historico.filter(para="CORRIGIDA").count(),
            "reaberturas_semana": historico.filter(para="ABERTA").exclude(de="").count(), "mudanca": mudanca}


@transaction.atomic
def exportar(usuario, destino, execucao_id=None):
    travar_escrita()
    usuario = exigir(usuario, *EXPORTACAO)
    if destino not in DESTINOS:
        raise ValidationError("Selecione um destino permitido para a exportação.")
    dados = montar(usuario, execucao_id)
    dados["destino"] = DESTINOS[destino]
    conteudo = render_to_string("inventario/executivo_exportacao.html", dados)
    import hashlib
    with usar_usuario(usuario):
        registrar_evento("EXPORTAR_EXECUTIVO", "RelatorioExecutivo", "html",
            {"destino": destino, "execucao": dados["execucao_selecionada"],
             "sha256": hashlib.sha256(conteudo.encode("utf-8")).hexdigest()})
    return conteudo
