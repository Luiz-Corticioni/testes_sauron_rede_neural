from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta
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
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from inventario.aplicacao.cobertura import salvar_perimetro, preparar_revisao, registrar_revisao
        from inventario.aplicacao.relacoes import salvar_relacao
        from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
        from inventario.infraestrutura.exportacao import inventario_completo
        from inventario.models import Ativo, Sala

        usuario = get_user_model().objects.create_superuser("admin-pg", "teste@example.org", "senha-sintetica")
        sala = Sala.objects.create(id="SALA-PG", nome="Sala fictícia")
        origem = Ativo.objects.create(tipo="1", nome="Origem", fabricante="Dell", sala=sala)
        destino_ativo = Ativo.objects.create(tipo="1", nome="Destino", fabricante="Dell", sala=sala)
        hoje = timezone.localdate()
        relacao = salvar_relacao({"origem_id": origem.pk, "destino_id": destino_ativo.pk,
            "tipo": "REDE", "escopo": "pg", "protocolo": "tcp", "porta": 443,
            "principal": "", "privilegio": "", "fonte": "Fonte sintética", "evidencia": "Evidência sintética",
            "observada_em": hoje, "revisar_em": hoje + timedelta(days=10), "vigente": True}, usuario)
        perimetro = salvar_perimetro(usuario, "pg", "Escopo de teste", [origem.pk, destino_ativo.pk])
        _, contexto = preparar_revisao(usuario, perimetro.pk, "REDE", origem.pk)
        registrar_revisao(usuario, perimetro.pk, "REDE", origem.pk, "", "REVISADO",
            "Revisão sintética", hoje, hoje + timedelta(days=10), contexto["sha256"])
        colecoes = inventario_completo()["colecoes"]
        self.assertEqual(colecoes["relacaoativos"][0]["fonte"], relacao.fonte)
        self.assertEqual(len(colecoes["membroperimetro"]), 2)
        self.assertEqual(len(colecoes["revisaocobertura"]), 1)
        with TemporaryDirectory(prefix="sauron-pg-backup-") as pasta:
            with override_settings(DATA_DIR=Path(pasta), SAURON_BACKUP_KEY=Fernet.generate_key().decode(),
                                   SAURON_BACKUP_DESTINO_ADICIONAL=""):
                destino = Path(pasta) / "restaurado.sqlite3"
                restaurar_backup(backup_sqlite(), destino)
                with closing(sqlite3.connect(destino)) as banco:
                    nomes = banco.execute("SELECT nome FROM inventario_sala WHERE id = ?", ("SALA-PG",)).fetchall()
                    relacao_recuperada = banco.execute("SELECT origem_id, destino_id, fonte, criada_por_id FROM inventario_relacaoativos").fetchone()
                    membros = banco.execute("SELECT count(*) FROM inventario_membroperimetro").fetchone()[0]
                    revisao = banco.execute("SELECT resultado FROM inventario_revisaocobertura").fetchone()[0]
                self.assertEqual(nomes, [("Sala fictícia",)])
                self.assertEqual(relacao_recuperada, (origem.pk, destino_ativo.pk, relacao.fonte, usuario.pk))
                self.assertEqual(membros, 2)
                self.assertEqual(revisao, "REVISADO")
