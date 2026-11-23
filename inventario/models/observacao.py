from django.conf import settings
from django.db import models


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
    identificador = models.CharField(max_length=64)
    conteudo_sha256 = models.CharField(max_length=64)
    observado_em = models.DateTimeField()
    recebido_em = models.DateTimeField(auto_now_add=True)
    confianca = models.CharField(max_length=16, choices=CONFIANCAS, default="NAO_INFORMADA")
    erro = models.CharField(max_length=40, blank=True)
    dados = models.JSONField()
    recebido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-recebido_em", "-pk"]
        default_permissions = ("view", "add")
        constraints = [models.UniqueConstraint(fields=["formato", "identidade_fonte", "identificador"], name="observacao_externa_unica")]


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
