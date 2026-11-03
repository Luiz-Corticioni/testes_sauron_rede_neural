"""Documentos são evidências declaradas; não comprovam instalação ou ausência de risco."""
from django.conf import settings
from django.db import models


class DocumentoInventario(models.Model):
    ativo = models.ForeignKey("Ativo", on_delete=models.PROTECT, related_name="documentos_inventario")
    tipo = models.CharField(max_length=12)
    identificador = models.CharField(max_length=512, blank=True)
    versao = models.PositiveIntegerField()
    escopo = models.CharField(max_length=200)
    origem = models.CharField(max_length=200)
    sha256 = models.CharField(max_length=64)
    conteudo = models.TextField()  # JSON normalizado exato: o banco não reescreve números/ordenação.
    importado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    importado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-importado_em", "-pk"]
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["ativo", "tipo", "sha256", "origem", "escopo"], name="documento_conteudo_unico")]


class ItemSBOM(models.Model):
    documento = models.ForeignKey(DocumentoInventario, on_delete=models.CASCADE, related_name="componentes")
    referencia = models.CharField(max_length=512)
    software = models.ForeignKey("Software", null=True, on_delete=models.PROTECT, related_name="itens_sbom")
    depende_de = models.JSONField(default=list)

    class Meta:
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["documento", "referencia"], name="sbom_referencia_unica")]


class AchadoComponente(models.Model):
    software = models.ForeignKey("Software", on_delete=models.PROTECT, related_name="achados_componentes")
    cve_id = models.CharField(max_length=30)
    incidencia = models.ForeignKey("Incidencia", null=True, on_delete=models.SET_NULL, related_name="achados_componentes")
    fontes = models.ManyToManyField(DocumentoInventario, related_name="achados")

    class Meta:
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["software", "cve_id"], name="achado_componente_cve_unico")]


class DeclaracaoVEX(models.Model):
    documento = models.ForeignKey(DocumentoInventario, on_delete=models.CASCADE, related_name="declaracoes")
    purl = models.CharField(max_length=512)
    cve_id = models.CharField(max_length=30)
    status = models.CharField(max_length=24)
    justificativa = models.CharField(max_length=80, blank=True)
    texto = models.TextField(blank=True)

    class Meta:
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["documento", "purl", "cve_id"], name="vex_declaracao_unica")]
