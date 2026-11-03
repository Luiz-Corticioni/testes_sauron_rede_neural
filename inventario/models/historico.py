from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


class HistoricoIncidencia(models.Model):
    # A cópia do código mantém a referência depois de remover o vínculo original.
    incidencia = models.ForeignKey(
        "Incidencia", null=True, on_delete=models.SET_NULL, related_name="historico"
    )
    incidencia_codigo = models.CharField(max_length=30)
    de = models.CharField(max_length=20, blank=True)
    para = models.CharField(max_length=20)
    em = models.DateTimeField(default=timezone.now)
    por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)

    class Meta:
        ordering = ["em", "id"]


class SnapshotRisco(models.Model):
    ts = models.DateTimeField(default=timezone.now)
    risco_total = models.FloatField(validators=[MinValueValidator(0)])
    por_ativo = models.JSONField(default=dict)
    perfil = models.CharField(max_length=12, default="puro")
    chave = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["ts", "id"]


class RegistroAuditoria(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    acao = models.CharField(max_length=40)
    entidade = models.CharField(max_length=80)
    entidade_id = models.CharField(max_length=80)
    detalhes = models.JSONField(default=dict)
    ocorrido_em = models.DateTimeField(default=timezone.now)
    cadeia_versao = models.PositiveSmallIntegerField(default=2)
    hash_anterior = models.CharField(max_length=64, blank=True)
    hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-ocorrido_em"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Registros de auditoria são imutáveis.")
        from inventario.infraestrutura.auditoria import preparar_registro

        using = kwargs.get("using", "default")
        with transaction.atomic(using=using):
            preparar_registro(self, using)
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Registros de auditoria não podem ser excluídos.")
