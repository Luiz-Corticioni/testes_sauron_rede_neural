from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch
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
    @override_settings(SAURON_TICKETS_JIRA_ENABLED=True, SAURON_JIRA_URL="https://jira.example",
        SAURON_JIRA_USER="sintetico", SAURON_JIRA_API_TOKEN="falso", SAURON_JIRA_PROJECT="SAU", SAURON_JIRA_ISSUE_TYPE="Task")
    def test_solicitacoes_simultaneas_de_ticket_nao_duplicam_envio(self):
        from django.contrib.auth import get_user_model
        from inventario.aplicacao.tickets import criar_ticket
        from inventario.models import Ativo, Incidencia, Sala, TicketRemediacao, Vulnerabilidade

        usuario = get_user_model().objects.create_superuser("tickets-pg", "teste@example.org", "senha-sintetica")
        sala = Sala.objects.create(id="SALA-TICKET-PG", nome="Sala fictícia")
        ativo = Ativo.objects.create(tipo="1", nome="Origem", fabricante="Dell", sala=sala)
        vuln = Vulnerabilidade.objects.create(id="VUL-TICKET-PG", descricao="Exemplo", categoria="RCE", cvss=5.3)
        inc = Incidencia.objects.create(id="INC-TICKET-PG", ativo=ativo, vulnerabilidade=vuln)
        barreira = Barrier(2)

        def criar(_):
            close_old_connections()
            try:
                barreira.wait(timeout=15)
                return criar_ticket(inc.pk, "jira", usuario).pk
            finally:
                connections.close_all()

        with patch("inventario.infraestrutura.tickets.Jira.criar", return_value="SAU-123") as envio:
            with ThreadPoolExecutor(max_workers=2) as executor:
                resultados = list(executor.map(criar, range(2)))
        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(envio.call_count, 1)
        self.assertEqual(TicketRemediacao.objects.count(), 1)
        self.assertTrue(verificar_cadeia(verificar_ancora=False)["integra"])

    @override_settings(SAURON_IMPORTACAO_OBSERVACOES_ENABLED=True)
    def test_importacoes_simultaneas_sao_idempotentes(self):
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from inventario.aplicacao.observacoes import importar
        from inventario.models import ObservacaoImportada

        usuario = get_user_model().objects.create_superuser("observacao-pg", "teste@example.org", "senha-sintetica")
        instante = timezone.now().isoformat()
        conteudo = b'[{"id":"1","name":"Sintetico","itemtype":"Computer"}]'
        barreira = Barrier(2)

        def gravar(_):
            close_old_connections()
            try:
                barreira.wait(timeout=15)
                return importar("glpi_json", conteudo, "fonte-pg", "1", instante, "MEDIA", usuario)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(gravar, range(2)))
        self.assertEqual(sum(r["novos"] for r in resultados), 1)
        self.assertEqual(sum(r["repetidos"] for r in resultados), 1)
        self.assertEqual(ObservacaoImportada.objects.count(), 1)
        self.assertTrue(verificar_cadeia(verificar_ancora=False)["integra"])

    @override_settings(SAURON_IMPORTACAO_OBSERVACOES_ENABLED=True)
    def test_promocoes_simultaneas_criam_uma_unica_relacao(self):
        import json
        from django.contrib.auth import get_user_model
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        from inventario.aplicacao.observacoes import importar, revisar
        from inventario.models import Ativo, ObservacaoImportada, RelacaoAtivos, Sala

        usuario = get_user_model().objects.create_superuser("promocao-pg", "teste@example.org", "senha-sintetica")
        sala = Sala.objects.create(id="SALA-OBS-PG", nome="Sala fictícia")
        origem = Ativo.objects.create(tipo="1", nome="Origem", fabricante="Dell", sala=sala)
        destino = Ativo.objects.create(tipo="1", nome="Destino", fabricante="Dell", sala=sala)
        arquivo = json.dumps({"rules": [{"id": "R1", "acao": "allow", "origem_ativo": origem.pk,
            "destino_ativo": destino.pk, "escopo": "Rede", "protocolo": "tcp", "porta": 443}]}).encode()
        importar("firewall", arquivo, "fonte-pg", "1", timezone.now().isoformat(), "MEDIA", usuario)
        obs = ObservacaoImportada.objects.get()
        barreira = Barrier(2)

        def promover(_):
            close_old_connections()
            try:
                barreira.wait(timeout=15)
                try:
                    revisar(obs.pk, "RELACAO_CRIADA", "Revisão sintética", usuario, timezone.localdate()+timedelta(days=30))
                    return True
                except ValidationError:
                    return False
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(promover, range(2)))
        self.assertEqual(sum(resultados), 1)
        self.assertEqual(RelacaoAtivos.objects.count(), 1)
        self.assertTrue(verificar_cadeia(verificar_ancora=False)["integra"])

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

    def test_limite_de_credencial_e_atomico_em_acessos_simultaneos(self):
        from django.contrib.auth import get_user_model
        from inventario.aplicacao.credenciais_api import criar, autenticar, LimiteCredencial
        from inventario.models import CredencialAPI

        usuario = get_user_model().objects.create_superuser("integracao-pg", "teste@example.org", "senha-sintetica")
        credencial, segredo = criar(usuario, ["ativos"], 1)
        barreira = Barrier(8)

        def consultar(_):
            close_old_connections()
            try:
                barreira.wait(timeout=15)
                try:
                    autenticar(segredo, "ativos")
                    return True
                except LimiteCredencial:
                    return False
            finally:
                connections.close_all()

        with patch("inventario.aplicacao.credenciais_api.LIMITE_POR_MINUTO", 4):
            with ThreadPoolExecutor(max_workers=8) as executor:
                resultados = list(executor.map(consultar, range(8)))
        self.assertEqual(sum(resultados), 4)
        self.assertEqual(CredencialAPI.objects.get(pk=credencial.pk).requisicoes_janela, 4)
        self.assertTrue(verificar_cadeia(verificar_ancora=False)["integra"])

    def test_backup_postgres_e_restauracao_sqlite_preservam_dados(self):
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from inventario.aplicacao.cobertura import salvar_perimetro, preparar_revisao, registrar_revisao
        from inventario.aplicacao.credenciais_api import criar
        from inventario.aplicacao.relacoes import salvar_relacao
        from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
        from inventario.infraestrutura.exportacao import inventario_completo
        from inventario.models import Ativo, Sala

        usuario = get_user_model().objects.create_superuser("admin-pg", "teste@example.org", "senha-sintetica")
        _, segredo = criar(usuario, ["ativos"], 1)
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
        self.assertNotIn("credencialapi", colecoes)
        self.assertEqual(colecoes["relacaoativos"][0]["fonte"], relacao.fonte)
        self.assertEqual(len(colecoes["membroperimetro"]), 2)
        self.assertEqual(len(colecoes["revisaocobertura"]), 1)
        with TemporaryDirectory(prefix="sauron-pg-backup-") as pasta:
            chave = Fernet.generate_key()
            with override_settings(DATA_DIR=Path(pasta), SAURON_BACKUP_KEY=chave.decode(),
                                   SAURON_BACKUP_DESTINO_ADICIONAL=""):
                destino = Path(pasta) / "restaurado.sqlite3"
                arquivo = backup_sqlite()
                self.assertNotIn(segredo.encode(), Fernet(chave).decrypt(arquivo.read_bytes()))
                restaurar_backup(arquivo, destino)
                with closing(sqlite3.connect(destino)) as banco:
                    nomes = banco.execute("SELECT nome FROM inventario_sala WHERE id = ?", ("SALA-PG",)).fetchall()
                    relacao_recuperada = banco.execute("SELECT origem_id, destino_id, fonte, criada_por_id FROM inventario_relacaoativos").fetchone()
                    membros = banco.execute("SELECT count(*) FROM inventario_membroperimetro").fetchone()[0]
                    revisao = banco.execute("SELECT resultado FROM inventario_revisaocobertura").fetchone()[0]
                    credenciais = banco.execute("SELECT count(*) FROM inventario_credencialapi").fetchone()[0]
                self.assertEqual(nomes, [("Sala fictícia",)])
                self.assertEqual(relacao_recuperada, (origem.pk, destino_ativo.pk, relacao.fonte, usuario.pk))
                self.assertEqual(membros, 2)
                self.assertEqual(revisao, "REVISADO")
                self.assertEqual(credenciais, 0)
