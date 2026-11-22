import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventario", "0042_snapshotrisco_detalhes"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="PerdaFinanceira", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("categoria", models.CharField(choices=[("C", "Confidencialidade"), ("I", "Integridade"), ("A", "Disponibilidade")], max_length=1)),
        ("natureza", models.CharField(choices=[("REAL", "Incidente real declarado"), ("SIMULADA", "Demonstração ou exercício")], max_length=8)),
        ("valor", models.DecimalField(decimal_places=2, max_digits=18, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10**15)])),
        ("data", models.DateField()),
        ("origem", models.CharField(max_length=200)),
        ("registrado_em", models.DateTimeField(default=django.utils.timezone.now)),
        ("incidente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="perdas_financeiras", to="inventario.incidente")),
        ("registrado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
    ], options={"constraints": [models.UniqueConstraint(fields=("incidente", "categoria"), name="perda_incidente_categoria_unica")]})]
