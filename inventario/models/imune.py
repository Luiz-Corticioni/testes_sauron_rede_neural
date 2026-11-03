from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from inventario.models.base import ModeloAuditavel


class Anticorpo(ModeloAuditavel):
    vulnerabilidade = models.ForeignKey("Vulnerabilidade", on_delete=models.PROTECT)
    origem = models.ForeignKey("Incidencia", null=True, blank=True, on_delete=models.SET_NULL)
    prototipo = models.JSONField(default=dict)
    ignorados = models.JSONField(default=list, blank=True)
    forca = models.FloatField(default=1, validators=[MinValueValidator(0), MaxValueValidator(1)])
    confirmacoes = models.PositiveIntegerField(default=1)
    rejeicoes = models.PositiveIntegerField(default=0)
    estado = models.CharField(
        max_length=12,
        default="ATIVO",
        choices=[
            ("ATIVO", "Ativo"),
            ("SUSPENSO", "Suspenso"),
            ("ARQUIVADO", "Arquivado"),
            ("DESCARTADO", "Linha de base saudável"),
        ],
    )
    descartado_por_ativo = models.ForeignKey("Ativo", null=True, blank=True, on_delete=models.PROTECT,
                                             related_name="anticorpos_descartados")
    chave = models.CharField(max_length=64, unique=True)
    linhagem = models.CharField(max_length=64, db_index=True)
    reforcado_em = models.DateTimeField(default=timezone.now)

    def para_dominio(self):
        from inventario.dominio.sistema_imune import Anticorpo as Memoria

        return Memoria(
            str(self.pk),
            self.vulnerabilidade_id,
            self.prototipo,
            self.forca,
            self.confirmacoes,
            self.rejeicoes,
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        self.para_dominio()
        resultado = super().save(*args, **kwargs)
        if self.estado == "ARQUIVADO" and self.origem_id:
            from inventario.models import Incidencia
            Incidencia.objects.filter(pk=self.origem_id).update(imune_aprendida=False)
        return resultado


class Tolerancia(ModeloAuditavel):
    anticorpo = models.ForeignKey("Anticorpo", null=True, blank=True, on_delete=models.SET_NULL)
    linhagem = models.CharField(max_length=64, db_index=True)
    ativo = models.ForeignKey("Ativo", on_delete=models.PROTECT)
    legado_remediacao = models.JSONField(default=dict, blank=True, editable=False)
    valida_ate = models.DateField()
    motivo = models.TextField()
    por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["anticorpo", "ativo"], name="tolerancia_imune_unica")
        ]

    def clean(self):
        super().clean()
        from inventario.aplicacao.decisoes import validar_validade
        validar_validade(self.valida_ate, settings.SAURON_TOLERANCIA_MAX_DIAS, "valida_ate")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SugestaoImune(ModeloAuditavel):
    ativo = models.ForeignKey("Ativo", on_delete=models.PROTECT)
    vulnerabilidade = models.ForeignKey("Vulnerabilidade", on_delete=models.PROTECT)
    anticorpo = models.ForeignKey("Anticorpo", null=True, blank=True, on_delete=models.SET_NULL)
    codigo_anticorpo = models.CharField(max_length=30)
    afinidade = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    tipo_vinculo = models.CharField(max_length=20, default="HIPOTESE")
    explicacao = models.JSONField(default=list, blank=True)
    prioridade = models.FloatField(default=0)
    sinal2 = models.BooleanField(default=False)
    sinais = models.JSONField(default=list, blank=True)
    estado = models.CharField(
        max_length=12,
        default="OBSERVACAO",
        choices=[
            ("OBSERVACAO", "Sem segundo sinal"),
            ("PENDENTE", "Revisão necessária"),
            ("CONFIRMADA", "Confirmada"),
            ("REJEITADA", "Rejeitada"),
            ("EXPIRADA", "Retirada"),
        ],
    )
    criada_em = models.DateTimeField(default=timezone.now)
    decidido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    decidido_em = models.DateTimeField(null=True)

    class Meta:
        permissions = [("decidir_sugestao_imune", "Pode confirmar/rejeitar sugestão imune")]
        constraints = [
            models.UniqueConstraint(
                fields=["ativo", "vulnerabilidade"],
                condition=models.Q(estado__in=["PENDENTE", "OBSERVACAO"]),
                name="sugestao_imune_aberta_unica",
            )
        ]
