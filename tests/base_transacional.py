"""Permite ao runner limpar somente o banco descartável de testes PostgreSQL."""
from django.db import connection
from django.test import TransactionTestCase


class BancoTransacionalTeste(TransactionTestCase):
    def _fixture_teardown(self):
        if connection.vendor != "postgresql":
            return super()._fixture_teardown()
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE inventario_registroauditoria DISABLE TRIGGER auditoria_sem_truncate")
        try:
            return super()._fixture_teardown()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE inventario_registroauditoria ENABLE TRIGGER auditoria_sem_truncate")
