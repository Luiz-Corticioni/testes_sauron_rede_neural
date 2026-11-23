from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from inventario.aplicacao.tickets import criar_ticket
from inventario.infraestrutura.tickets import GLPI, Jira
from inventario.models import Ativo, Incidencia, Sala, TicketRemediacao, Vulnerabilidade


class AdaptadoresTickets(SimpleTestCase):
    def test_jira_e_glpi_formatam_chamadas_sem_rede(self):
        transporte = Mock(return_value={"key": "SAU-123"})
        jira = Jira("https://jira.example", "Basic TOKEN", "SAU", "Task", transporte)
        self.assertEqual(jira.criar("Título", "Referência"), "SAU-123")
        self.assertEqual(transporte.call_args.args[0], "https://jira.example/rest/api/3/issue")
        self.assertEqual(transporte.call_args.args[2]["fields"]["project"], {"key": "SAU"})
        transporte = Mock(return_value={"id": 42})
        glpi = GLPI("https://glpi.example", "sessao", "app", transporte)
        self.assertEqual(glpi.criar("Título", "Referência"), "42")
        self.assertEqual(transporte.call_args.args[0], "https://glpi.example/apirest.php/Ticket")

    def test_recusa_url_insegura_credencial_e_resposta_malformada(self):
        for endereco in ("http://jira.example", "https://a:b@jira.example", "https://jira.example/?token=x"):
            with self.subTest(endereco=endereco), self.assertRaises(ValueError):
                Jira(endereco, "segredo", "SAU", "Task")
        with self.assertRaises(ValueError):
            GLPI("https://glpi.example", "sessao\nX: y", "app")
        with self.assertRaises(ValueError):
            Jira("https://jira.example", "segredo", "SAU", "Task", Mock(return_value={})).criar("x", "y")


@override_settings(SAURON_TICKETS_JIRA_ENABLED=True, SAURON_JIRA_URL="https://jira.example",
                   SAURON_JIRA_USER="synthetic", SAURON_JIRA_API_TOKEN="FAKE", SAURON_JIRA_PROJECT="SAU", SAURON_JIRA_ISSUE_TYPE="Task")
class EnvioTicket(TransactionTestCase):
    def _fixture_teardown(self):
        # O flush de TransactionTestCase precisa limpar o banco de teste SQLite;
        # a trava de exclusão de auditoria é restaurada imediatamente após o flush.
        from django.db import connection
        if connection.vendor != "sqlite":
            return super()._fixture_teardown()
        with connection.cursor() as cursor:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name='auditoria_sem_delete'")
            linha = cursor.fetchone()
            if linha:
                cursor.execute("DROP TRIGGER auditoria_sem_delete")
        try:
            return super()._fixture_teardown()
        finally:
            if linha:
                with connection.cursor() as cursor:
                    cursor.execute(linha[0])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        config = override_settings(DATA_DIR=Path(self.temp.name), SAURON_EXIGIR_ANCORA=False,
                                   SAURON_AUDIT_ANCHOR_PATH=Path(self.temp.name) / "anchor.jsonl")
        config.enable()
        self.addCleanup(config.disable)
        self.usuario = get_user_model().objects.create_superuser("admin", "admin@example.org", "teste")
        sala = Sala.objects.create(id="SALA", nome="Sala")
        ativo = Ativo.objects.create(tipo="1", nome="Servidor", fabricante="Dell", sala=sala)
        vuln = Vulnerabilidade.objects.create(id="VUL-TICKET", descricao="Exemplo", categoria="RCE", cvss=5.3)
        self.inc = Incidencia.objects.create(id="INC-TEST", ativo=ativo, vulnerabilidade=vuln)

    @patch("inventario.infraestrutura.tickets.Jira.criar", return_value="SAU-123")
    def test_cria_uma_vez_e_informa_sla(self, enviar):
        item = criar_ticket(self.inc.pk, "jira", self.usuario)
        self.assertEqual((item.estado, item.referencia_externa), ("CRIADO", "SAU-123"))
        self.assertIn(str(self.inc.prazo_correcao), enviar.call_args.args[1])
        self.assertEqual(criar_ticket(self.inc.pk, "jira", self.usuario).pk, item.pk)
        self.assertEqual(enviar.call_count, 1)

    @patch("inventario.infraestrutura.tickets.Jira.criar", side_effect=TimeoutError("segredo"))
    def test_falha_incerta_nao_reenvia_nem_registra_detalhe(self, enviar):
        item = criar_ticket(self.inc.pk, "jira", self.usuario)
        self.assertEqual(item.estado, "INCERTO")
        self.assertEqual(item.referencia_externa, "")
        self.assertEqual(criar_ticket(self.inc.pk, "jira", self.usuario).pk, item.pk)
        self.assertEqual(enviar.call_count, 1)
        from inventario.models import RegistroAuditoria
        self.assertNotIn("segredo", str(list(RegistroAuditoria.objects.values_list("detalhes", flat=True))))

    @patch("inventario.infraestrutura.tickets.Jira.criar")
    def test_permissao_flag_e_falha_auditoria_impedem_envio(self, enviar):
        leitor = get_user_model().objects.create_user("leitor")
        with self.assertRaises(PermissionDenied):
            criar_ticket(self.inc.pk, "jira", leitor)
        with override_settings(SAURON_TICKETS_JIRA_ENABLED=False), self.assertRaises(ValidationError):
            criar_ticket(self.inc.pk, "jira", self.usuario)
        with patch("inventario.aplicacao.tickets.registrar_evento", side_effect=RuntimeError("erro")):
            with self.assertRaises(RuntimeError):
                criar_ticket(self.inc.pk, "jira", self.usuario)
        enviar.assert_not_called()
        self.assertFalse(TicketRemediacao.objects.exists())

    @patch("inventario.infraestrutura.tickets.Jira.criar")
    def test_identificador_com_marcacao_nao_e_enviado(self, enviar):
        vuln = Vulnerabilidade.objects.create(id="<b>invalido</b>", descricao="Exemplo", categoria="RCE", cvss=5.3)
        inc = Incidencia.objects.create(id="INC-HTML", ativo=self.inc.ativo, vulnerabilidade=vuln)
        with self.assertRaises(ValidationError):
            criar_ticket(inc.pk, "jira", self.usuario)
        enviar.assert_not_called()
