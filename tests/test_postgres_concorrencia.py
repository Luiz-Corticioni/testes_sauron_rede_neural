from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier
from unittest import skipUnless
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3

from django.db import close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from cryptography.fernet import Fernet

from inventario.infraestrutura.auditoria import registrar_evento, verificar_cadeia
from inventario.models import RegistroAuditoria


@skipUnless(connection.vendor == "postgresql", "Teste exige PostgreSQL real.")
class BackupEmTransacaoPostgres(TestCase):
    def test_backup_aninhado_e_recusado_sem_invalidar_transacao(self):
        from inventario.infraestrutura.backup import backup_sqlite

        with self.assertRaisesMessage(ValueError, "fora de uma transação existente"):
            backup_sqlite()
        self.assertEqual(RegistroAuditoria.objects.count(), 0)


@skipUnless(connection.vendor == "postgresql", "Teste exige PostgreSQL real.")
class ConcorrenciaPostgres(TransactionTestCase):
    def test_gravacoes_simultaneas_preservam_cadeia(self):
        trabalhadores = 8
        barreira = Barrier(trabalhadores)

        def gravar(indice):
            close_old_connections()
            try:
                barreira.wait(timeout=15)
                with transaction.atomic():
                    registrar_evento("TESTE_PG", "Concorrencia", str(indice))
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=trabalhadores) as executor:
            list(executor.map(gravar, range(trabalhadores)))
        self.assertEqual(RegistroAuditoria.objects.filter(acao="TESTE_PG").count(), trabalhadores)
        self.assertTrue(verificar_cadeia(verificar_ancora=False)["integra"])

    def test_backup_postgres_e_restauracao_sqlite_preservam_dados(self):
        from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
        from inventario.models import Sala

        Sala.objects.create(id="SALA-PG", nome="Sala fictícia")
        with TemporaryDirectory(prefix="sauron-pg-backup-") as pasta:
            with override_settings(DATA_DIR=Path(pasta), SAURON_BACKUP_KEY=Fernet.generate_key().decode(),
                                   SAURON_BACKUP_DESTINO_ADICIONAL=""):
                destino = Path(pasta) / "restaurado.sqlite3"
                restaurar_backup(backup_sqlite(), destino)
                with closing(sqlite3.connect(destino)) as banco:
                    nomes = banco.execute("SELECT nome FROM inventario_sala WHERE id = ?", ("SALA-PG",)).fetchall()
                self.assertEqual(nomes, [("Sala fictícia",)])
