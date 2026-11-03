from django.conf import settings
from django.db import models


class AvaliacaoSSVC(models.Model):
    incidencia = models.ForeignKey("Incidencia", null=True, on_delete=models.SET_NULL, related_name="avaliacoes_ssvc")
    incidencia_codigo = models.CharField(max_length=30)
    entradas = models.JSONField()
    resultado = models.JSONField()
    contexto = models.JSONField()
    contexto_sha256 = models.CharField(max_length=64)
    evidencia = models.TextField()
    remediacao = models.CharField(max_length=1000)
    revisar_em = models.DateField()
    por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em", "-pk"]
        default_permissions = ()  # Usa view/change_incidencia, sem novo papel.
