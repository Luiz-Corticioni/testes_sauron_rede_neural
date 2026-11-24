"""Aplica ao PostgreSQL as mesmas travas de UPDATE/DELETE existentes no SQLite."""
from django.db import migrations


def instalar(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        CREATE FUNCTION sauron_auditoria_imutavel() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Auditoria imutavel'; END; $$
    """)
    schema_editor.execute("CREATE TRIGGER auditoria_sem_update BEFORE UPDATE ON inventario_registroauditoria "
                          "FOR EACH ROW EXECUTE FUNCTION sauron_auditoria_imutavel()")
    schema_editor.execute("CREATE TRIGGER auditoria_sem_delete BEFORE DELETE ON inventario_registroauditoria "
                          "FOR EACH ROW EXECUTE FUNCTION sauron_auditoria_imutavel()")
    schema_editor.execute("CREATE TRIGGER auditoria_sem_truncate BEFORE TRUNCATE ON inventario_registroauditoria "
                          "FOR EACH STATEMENT EXECUTE FUNCTION sauron_auditoria_imutavel()")


def remover(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS auditoria_sem_update ON inventario_registroauditoria")
    schema_editor.execute("DROP TRIGGER IF EXISTS auditoria_sem_delete ON inventario_registroauditoria")
    schema_editor.execute("DROP TRIGGER IF EXISTS auditoria_sem_truncate ON inventario_registroauditoria")
    schema_editor.execute("DROP FUNCTION IF EXISTS sauron_auditoria_imutavel()")


class Migration(migrations.Migration):
    dependencies = [("inventario", "0047_sugestaocorrecao_dados_eliminados_and_more")]
    operations = [migrations.RunPython(instalar, remover)]
