from django.db import migrations, models


def preencher_numeros(apps, schema_editor):
    Ativo = apps.get_model("inventario", "Ativo")
    Contador = apps.get_model("inventario", "ContadorAtivo")
    using = schema_editor.connection.alias
    numero = 0
    for numero, codigo in enumerate(
        Ativo.objects.using(using).order_by("pk").values_list("pk", flat=True), start=1
    ):
        Ativo.objects.using(using).filter(pk=codigo).update(id_numerico=numero)
    Contador.objects.using(using).update_or_create(pk=1, defaults={"ultimo": numero})


class Migration(migrations.Migration):
    dependencies = [("inventario", "0008_alter_anticorpo_origem_alter_sugestaoimune_anticorpo_and_more")]
    operations = [
        migrations.CreateModel(
            name="ContadorAtivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ultimo", models.PositiveBigIntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name="ativo", name="id_numerico",
            field=models.PositiveBigIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(preencher_numeros, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="ativo", name="id_numerico",
            field=models.PositiveBigIntegerField(blank=True, editable=False, unique=True),
        ),
    ]
