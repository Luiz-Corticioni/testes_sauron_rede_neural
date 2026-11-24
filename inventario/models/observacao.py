from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class ObservacaoImportada(models.Model):
    """Evidência externa minimizada; não altera automaticamente o inventário."""
    VERSAO = "sauron.observacao/1"
    CONFIANCAS = [("NAO_INFORMADA", "Não informada"), ("BAIXA", "Baixa declarada"),
                  ("MEDIA", "Média declarada"), ("ALTA", "Alta declarada")]
    versao_contrato = models.CharField(max_length=40, default=VERSAO)
    formato = models.CharField(max_length=20)
    tipo = models.CharField(max_length=20)
    identidade_fonte = models.CharField(max_length=120)
    versao_fonte = models.CharField(max_length=120)
    identificador = models.CharField(max_length=64, null=True)
    conteudo_sha256 = models.CharField(max_length=64, null=True)
    observado_em = models.DateTimeField()
    recebido_em = models.DateTimeField(auto_now_add=True)
    confianca = models.CharField(max_length=16, choices=CONFIANCAS, default="NAO_INFORMADA")
    erro = models.CharField(max_length=40, blank=True)
    dados = models.JSONField()
    recebido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-recebido_em", "-pk"]
        default_permissions = ("view", "add")
        constraints = [models.UniqueConstraint(fields=["formato", "identidade_fonte", "identificador"], name="observacao_externa_unica"),
            models.CheckConstraint(condition=(models.Q(erro="RETENCAO_EXPIRADA", identificador__isnull=True, conteudo_sha256__isnull=True)
                | (~models.Q(erro="RETENCAO_EXPIRADA") & models.Q(identificador__isnull=False, conteudo_sha256__isnull=False))),
                name="observacao_retencao_coerente")]


class RevisaoObservacao(models.Model):
    CLASSIFICACOES = [("VALIDA", "Evidência revisada"), ("INCORRETA", "Incorreta"),
                      ("INCONCLUSIVA", "Inconclusiva"), ("RELACAO_CRIADA", "Relação criada")]
    observacao = models.ForeignKey(ObservacaoImportada, on_delete=models.PROTECT, related_name="revisoes")
    classificacao = models.CharField(max_length=20, choices=CLASSIFICACOES)
    justificativa = models.CharField(max_length=500)
    relacao = models.ForeignKey("RelacaoAtivos", null=True, blank=True, on_delete=models.PROTECT)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em", "-pk"]
        default_permissions = ("view", "add")


class PoliticaRetencaoObservacoes(models.Model):
    dias = models.PositiveSmallIntegerField(default=90, validators=[MinValueValidator(30), MaxValueValidator(180)])
    atualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ("view", "change")
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="politica_observacao_unica"),
                       models.CheckConstraint(condition=models.Q(dias__gte=30, dias__lte=180), name="politica_observacao_prazo")]
