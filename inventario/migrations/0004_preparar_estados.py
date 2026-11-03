"""Normaliza apenas caixa/espaços; interrompe sem inventar status desconhecidos."""

from django.db import migrations


def preparar_estados(apps, schema_editor):
    permitidos = {
        "Ativo": {"ATIVO", "MANUTENCAO", "INATIVO", "BAIXADO"},
        "Incidencia": {"ABERTA", "TRATAMENTO", "MITIGADA", "CORRIGIDA", "ACEITA", "SUGERIDA"},
    }
    for nome, escolhas in permitidos.items():
        modelo = apps.get_model("inventario", nome)
        for pk, status in modelo.objects.values_list("pk", "status"):
            normalizado = status.strip().upper()
            if normalizado not in escolhas:
                raise RuntimeError(
                    f"Status legado desconhecido em {nome} {pk}: {status!r}. "
                    "Revise o cadastro antes de migrar; nenhum status foi presumido."
                )
            if normalizado != status:
                modelo.objects.filter(pk=pk).update(status=normalizado)


class Migration(migrations.Migration):
    dependencies = [("inventario", "0003_encadear_auditoria_legada")]
    operations = [migrations.RunPython(preparar_estados, migrations.RunPython.noop)]
