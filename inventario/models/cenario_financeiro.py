"""Premissas explícitas para uma análise financeira de interrupção de serviço."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class CenarioFinanceiro(models.Model):
    QUALIDADE = [("SIMULADO", "Fictício ou demonstrativo"), ("ESTIMADO", "Estimativa fundamentada"),
                 ("MEDIDO", "Observação medida")]
    nome = models.CharField(max_length=120)
    ativo = models.ForeignKey("Ativo", on_delete=models.PROTECT, related_name="cenarios_financeiros")
    descricao = models.CharField(max_length=500, help_text="Cenário, processo de negócio e limites da análise.")
    probabilidade = models.DecimalField(max_digits=7, decimal_places=6, validators=[MinValueValidator(0), MaxValueValidator(1)], help_text="Hipótese de ocorrência neste cenário em 30 dias, de 0 a 1; não é EPSS.")
    probabilidade_apos = models.DecimalField(max_digits=7, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)], help_text="Opcional: hipótese após o controle, de 0 a 1; não calculada automaticamente.")
    controle = models.CharField(max_length=200, blank=True, help_text="Controle comparado e justificativa resumida da hipótese após sua aplicação.")
    horas_min = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(720)])
    horas_moda = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(720)])
    horas_max = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(720)])
    custo_hora = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(1000000000)], help_text="R$ de perda incremental por hora, sem contar receitas ou custos duas vezes.")
    custo_adicional = models.DecimalField(max_digits=16, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(1000000000000)], help_text="R$ adicionais por incidente, não incluídos no custo por hora; informe 0 somente quando aplicável.")
    funcionarios_afetados = models.PositiveIntegerField(null=True, blank=True, validators=[MaxValueValidator(100000000)], help_text="Contexto declarado; não altera automaticamente o cálculo.")
    contas_privilegiadas = models.PositiveIntegerField(null=True, blank=True, validators=[MaxValueValidator(100000000)], help_text="Quantidade agregada relevante; não altera automaticamente a probabilidade.")
    origem = models.CharField(max_length=300, help_text="Origem e justificativa das premissas; não inclua credenciais ou dados pessoais.")
    qualidade = models.CharField(max_length=10, choices=QUALIDADE)
    data_referencia = models.DateField(help_text="Data de referência das premissas.")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-pk"]
        default_permissions = ("view", "add")

    def clean(self):
        super().clean()
        if all(v is not None for v in (self.horas_min, self.horas_moda, self.horas_max)) and not self.horas_min < self.horas_moda < self.horas_max:
            raise ValidationError("A duração exige mínima < mais provável < máxima, dentro de 30 dias.")
        if self.data_referencia and self.data_referencia > timezone.localdate():
            raise ValidationError({"data_referencia": "A data de referência não pode estar no futuro."})
        if (self.probabilidade_apos is not None) != bool(self.controle.strip()):
            raise ValidationError("Para comparar, informe tanto o controle quanto a probabilidade após ele.")
