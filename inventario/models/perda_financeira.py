from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from inventario.models.base import ModeloAuditavel


class PerdaFinanceira(ModeloAuditavel):
    CATEGORIAS = [("C", "Confidencialidade"), ("I", "Integridade"), ("A", "Disponibilidade")]
    NATUREZAS = [("REAL", "Incidente real declarado"), ("SIMULADA", "Demonstração ou exercício")]
    incidente = models.ForeignKey("Incidente", on_delete=models.PROTECT, related_name="perdas_financeiras")
    categoria = models.CharField(max_length=1, choices=CATEGORIAS)
    natureza = models.CharField(max_length=8, choices=NATUREZAS)
    valor = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(10**15)])
    data = models.DateField()
    origem = models.CharField(max_length=200)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    registrado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["incidente", "categoria"], name="perda_incidente_categoria_unica")]

    def clean(self):
        super().clean()
        self.origem = self.origem.strip()
        if not self.origem:
            raise ValidationError({"origem": "Informe a origem da perda observada."})
        if self.data and self.data > timezone.localdate():
            raise ValidationError({"data": "A data da perda não pode estar no futuro."})
        if self.incidente_id and not self.incidente.encerrado_em:
            raise ValidationError({"incidente": "Somente incidentes encerrados podem compor a calibração."})
        if self.incidente_id and self.data and self.data < timezone.localtime(self.incidente.aberto_em).date():
            raise ValidationError({"data": "A perda não pode anteceder a abertura do incidente."})
