"""Estabelece a linha de base dos registros antigos, sem afirmar integridade retroativa."""

from django.db import migrations


def encadear(apps, schema_editor):
    from inventario.infraestrutura.auditoria import calcular_hash

    Registro = apps.get_model("inventario", "RegistroAuditoria")
    Trava = apps.get_model("inventario", "TravaDominio")
    using = schema_editor.connection.alias
    Trava.objects.using(using).get_or_create(pk=1)
    anterior = ""
    for registro in Registro.objects.using(using).order_by("id").iterator():
        registro.hash_anterior = anterior
        registro.hash = calcular_hash(registro)
        Registro.objects.using(using).filter(pk=registro.pk).update(
            hash_anterior=registro.hash_anterior,
            hash=registro.hash,
        )
        anterior = registro.hash


class Migration(migrations.Migration):
    dependencies = [("inventario", "0002_travadominio_registroauditoria_hash_and_more")]
    operations = [migrations.RunPython(encadear, migrations.RunPython.noop)]
