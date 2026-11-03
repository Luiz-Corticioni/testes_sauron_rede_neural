"""Observações EPSS preservam a evidência sem confundir API e modelo."""
from django.db import models


class ObservacaoEPSS(models.Model):
    cve_id = models.CharField(max_length=30, db_index=True)
    data = models.DateField()
    epss = models.FloatField()
    percentil = models.FloatField()
    modelo = models.CharField(max_length=40, blank=True)
    fonte = models.URLField(default="https://api.first.org/data/v1/epss")
    assinatura = models.CharField(max_length=64)
    coletado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-coletado_em', '-pk']
        default_permissions = ()  # Acesso vinculado à permissão da vulnerabilidade.
        constraints = [models.UniqueConstraint(fields=['cve_id', 'data', 'assinatura'], name='epss_observacao_unica'),
                       models.CheckConstraint(condition=models.Q(epss__gte=0, epss__lte=1, percentil__gte=0, percentil__lte=1), name='epss_intervalos_validos')]
