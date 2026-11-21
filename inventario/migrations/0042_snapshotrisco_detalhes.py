from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventario", "0041_limiteorigemapi")]
    operations = [migrations.AddField(model_name="snapshotrisco", name="detalhes",
                                     field=models.JSONField(blank=True, null=True))]
