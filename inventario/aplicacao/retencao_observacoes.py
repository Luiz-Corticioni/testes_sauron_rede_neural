"""Retenção de observações, revisões e dados de sugestões relacionadas."""
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventario.aplicacao.autorizacao import exigir
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import ObservacaoImportada, PoliticaRetencaoObservacoes, RevisaoObservacao, SugestaoCorrecao

EXPIRADA = "RETENCAO_EXPIRADA"
PERMISSOES = ("inventario.view_observacaoimportada", "inventario.view_revisaoobservacao",
              "inventario.view_politicaretencaoobservacoes", "inventario.change_politicaretencaoobservacoes")


def prazo_dias():
    return PoliticaRetencaoObservacoes.objects.filter(pk=1).values_list("dias", flat=True).first() or 90


def corte_retencao():
    return timezone.now() - timedelta(days=prazo_dias())


def visiveis():
    return ObservacaoImportada.objects.filter(recebido_em__gt=corte_retencao()).exclude(erro=EXPIRADA)


@transaction.atomic
def alterar_retencao(dias, usuario):
    travar_escrita()
    usuario = exigir(usuario, *PERMISSOES)
    politica = PoliticaRetencaoObservacoes.objects.filter(pk=1).first() or PoliticaRetencaoObservacoes(pk=1)
    if type(dias) is int and dias > politica.dias:
        corte = timezone.now() - timedelta(days=politica.dias)
        pendentes = (ObservacaoImportada.objects.filter(recebido_em__lte=corte).exclude(erro=EXPIRADA).exists()
                     or RevisaoObservacao.objects.filter(criada_em__lte=corte).exists()
                     or SugestaoCorrecao.objects.filter(criado_em__lte=corte, dados_eliminados=False).exists())
        if pendentes:
            raise ValidationError("Processe os dados já vencidos antes de ampliar o prazo de retenção.")
    politica.dias, politica.atualizado_por = dias, usuario
    politica.full_clean()
    with usar_usuario(usuario):
        politica.save()
        registrar_evento("CONFIGURAR_RETENCAO", "Observacoes", "politica", {"dias": politica.dias})
    return politica


@transaction.atomic
def aplicar_retencao(limite=1000):
    """Remove conteúdo em lotes; mantém referências mínimas para integridade."""
    if type(limite) is not int or not 1 <= limite <= 1000:
        raise ValueError("O limite deve estar entre 1 e 1000 registros.")
    travar_escrita()
    dias = prazo_dias()
    corte = timezone.now() - timedelta(days=dias)
    ids_revisoes = list(RevisaoObservacao.objects.filter(criada_em__lte=corte).order_by("pk").values_list("pk", flat=True)[:limite])
    revisoes = RevisaoObservacao.objects.filter(pk__in=ids_revisoes).delete()[0]
    antigas = list(ObservacaoImportada.objects.filter(recebido_em__lte=corte).exclude(erro=EXPIRADA).order_by("pk")[:limite])
    for observacao in antigas:
        observacao.dados, observacao.identidade_fonte, observacao.versao_fonte = {}, "[EXPIRADA]", ""
        observacao.identificador, observacao.conteudo_sha256 = None, None
        observacao.confianca, observacao.erro = "NAO_INFORMADA", EXPIRADA
    if antigas:
        ObservacaoImportada.objects.bulk_update(antigas, ["dados", "identidade_fonte", "versao_fonte", "identificador",
            "conteudo_sha256", "confianca", "erro"], batch_size=100)
    sugestoes = list(SugestaoCorrecao.objects.filter(criado_em__lte=corte, dados_eliminados=False).order_by("pk")[:limite])
    for sugestao in sugestoes:
        sugestao.declaracao, sugestao.scan_sha256, sugestao.dados_eliminados = "[Removida pela retenção]", None, True
    if sugestoes:
        SugestaoCorrecao.objects.bulk_update(sugestoes, ["declaracao", "scan_sha256", "dados_eliminados"], batch_size=100)
    resultado = {"dias": dias, "observacoes_limpas": len(antigas), "revisoes_eliminadas": revisoes,
                 "sugestoes_limpas": len(sugestoes)}
    if antigas or revisoes or sugestoes:
        registrar_evento("APLICAR_RETENCAO", "Observacoes", "politica", resultado)
    return resultado
