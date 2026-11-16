from django.conf import settings
from django.db import models


class RelatorioScanner(models.Model):
    ativo = models.ForeignKey("Ativo", on_delete=models.PROTECT)
    escopo = models.CharField(max_length=200)
    origem = models.CharField(max_length=200)
    observado_em = models.DateTimeField()
    sha256 = models.CharField(max_length=64)
    achados = models.JSONField()
    ignorados = models.PositiveIntegerField(default=0)
    importado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    importado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-importado_em", "-pk"]
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["ativo", "escopo", "origem", "sha256"], name="scanner_relatorio_unico")]
