from django.conf import settings
from django.db import models


class SugestaoCorrecao(models.Model):
    """Comparação declarada; não altera o estado da incidência."""

    incidencia = models.ForeignKey("Incidencia", on_delete=models.PROTECT, related_name="sugestoes_correcao")
    observacao = models.ForeignKey("ObservacaoImportada", on_delete=models.PROTECT)
    scan_sha256 = models.CharField(max_length=64)
    observado_em = models.DateTimeField()
    declaracao = models.CharField(max_length=500)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        default_permissions = ("view", "add")
        constraints = [models.UniqueConstraint(fields=["incidencia", "observacao", "scan_sha256"], name="sugestao_correcao_unica")]


class TicketRemediacao(models.Model):
    """Registro de tentativa; ENVIANDO e INCERTO nunca são reenviados automaticamente."""
    incidencia = models.ForeignKey("Incidencia", on_delete=models.PROTECT, related_name="tickets_remediacao")
    provedor = models.CharField(max_length=8, choices=[("jira", "Jira"), ("glpi", "GLPI")])
    estado = models.CharField(max_length=12, choices=[("ENVIANDO", "Envio iniciado"), ("CRIADO", "Criado"), ("INCERTO", "Resultado incerto")])
    referencia_externa = models.CharField(max_length=40, blank=True)
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ("view", "add")
        constraints = [models.UniqueConstraint(fields=["incidencia", "provedor"], name="ticket_remediacao_unico")]
