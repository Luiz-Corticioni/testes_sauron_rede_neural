from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from inventario.models.base import ModeloAuditavel
from inventario.models.conversoes import ConversaoIncidencia


class IncidenciasQuerySet(models.QuerySet):
    def pendentes_sla(self):
        return self.filter(status__in=["ABERTA", "TRATAMENTO"])


class Incidencia(ConversaoIncidencia, ModeloAuditavel):
    class Status(models.TextChoices):
        ABERTA = "ABERTA", "Aberta"
        TRATAMENTO = "TRATAMENTO", "Em tratamento"
        MITIGADA = "MITIGADA", "Mitigada"
        CORRIGIDA = "CORRIGIDA", "Corrigida"
        ACEITA = "ACEITA", "Risco aceito"
        SUGERIDA = "SUGERIDA", "Aguardando confirmação"

    STATUS = Status.choices  # Compatibilidade com o menu antigo da CLI.
    objects = IncidenciasQuerySet.as_manager()
    id = models.CharField(primary_key=True, max_length=30)
    ativo = models.ForeignKey("Ativo", on_delete=models.CASCADE)
    vulnerabilidade = models.ForeignKey("Vulnerabilidade", on_delete=models.PROTECT)
    software = models.ForeignKey("Software", null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=STATUS, default="ABERTA")
    detectada_em = models.DateField(default=timezone.localdate)
    prazo_correcao = models.DateField(null=True, blank=True)
    versao_afetada = models.CharField(max_length=80, blank=True)
    observacoes = models.TextField(blank=True)
    aceita_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="riscos_aceitos",
    )
    justificativa = models.TextField(blank=True)
    aceita_ate = models.DateField(null=True, blank=True)
    legado_remediacao = models.JSONField(default=dict, blank=True, editable=False)
    evidencia = models.TextField(blank=True)
    decisao_pendente = models.CharField(max_length=20, blank=True,
        choices=[("ACEITA", "Aceite"), ("CORRIGIDA", "Correção"), ("MITIGADA", "Mitigação")])
    solicitada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="decisoes_solicitadas")
    aprovada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="decisoes_aprovadas")
    imune_aprendida = models.BooleanField(default=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["ativo", "status"], name="inc_ativo_status_idx")]
        permissions = [("aceitar_risco", "Pode aceitar risco com prazo"),
                       ("aprovar_aceite_risco", "Pode ser segundo aprovador de aceite de risco")]
        constraints = [
            models.UniqueConstraint(fields=["ativo", "vulnerabilidade"], name="incidencia_unica"),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "ABERTA",
                        "TRATAMENTO",
                        "MITIGADA",
                        "CORRIGIDA",
                        "ACEITA",
                        "SUGERIDA",
                    ]
                ),
                name="incidencia_status_valido",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(status="ACEITA")
                    | (
                        models.Q(aceita_por__isnull=False, aceita_ate__isnull=False)
                        & ~models.Q(justificativa="")
                    )
                ),
                name="aceite_completo",
            ),
        ]

    def clean(self):
        super().clean()
        from inventario.aplicacao.decisoes import validar_decisao
        validar_decisao(self)
        if self.software_id and self.software.ativo_id != self.ativo_id:
            raise ValidationError({"software": "O componente deve pertencer ao ativo da incidência."})
        if self.status == self.Status.ACEITA:
            if not self.aceita_por_id or not self.aceita_ate or not self.justificativa.strip():
                raise ValidationError("Aceite exige autorizador, justificativa e data de validade.")
            if not self.aceita_por.has_perm("inventario.aceitar_risco"):
                raise ValidationError("O autorizador não possui permissão para aceitar risco.")

    def save(self, *args, **kwargs):
        from inventario.aplicacao.operacao import prazo_sla

        if self.prazo_correcao is None and self.status != self.Status.SUGERIDA:
            self.prazo_correcao = prazo_sla(self)
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = set(kwargs["update_fields"]) | {"prazo_correcao"}
        from inventario.infraestrutura.auditoria import AUTOR
        anterior = Incidencia.objects.filter(pk=self.pk).first()
        for campo in ("aceita_por_id", "solicitada_por_id", "aprovada_por_id"):
            valor = getattr(self, campo)
            if valor and (not anterior or valor != getattr(anterior, campo)) and valor != AUTOR.get():
                raise ValidationError("Autoria da decisão deve corresponder ao usuário da operação.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ativo_id} × {self.vulnerabilidade_id}"
