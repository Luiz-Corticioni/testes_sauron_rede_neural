"""Configura SQLite em cada conexão aberta pelo ORM, pela CLI ou pelo Gunicorn."""

from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created, dispatch_uid="sauron.sqlite.pragmas")
def configurar_sqlite(sender, connection, **kwargs):
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        # WAL permite leitura enquanto outro worker grava. Em memória fica 'memory'.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=20000")
        cursor.execute("PRAGMA synchronous=NORMAL")
