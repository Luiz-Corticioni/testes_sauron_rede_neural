from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from inventario.infraestrutura.auditoria import verificar_cadeia
from inventario.models import Ativo, Incidencia, Sala, SnapshotRisco


class CenarioOperacional(TestCase):
    def setUp(self):
        pasta = TemporaryDirectory(prefix="sauron-demo-")
        self.addCleanup(pasta.cleanup)
        self.config = override_settings(DATA_DIR=Path(pasta.name), SAURON_EXIGIR_ANCORA=False,
            CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.ambiente = patch.dict("os.environ", {"SAURON_ADMIN_USER": "", "SAURON_ADMIN_PASSWORD": ""})
        self.ambiente.start()
        self.addCleanup(self.ambiente.stop)

    def test_seed_operacional_usa_aprovacao_segregada_e_repeticao_e_segura(self):
        saida = StringIO()
        call_command("seed_demo", operacional=True, stdout=saida)
        i = Incidencia.objects.get(pk="INC-0002")
        self.assertEqual(i.status, "ACEITA")
        self.assertNotEqual(i.aceita_por_id, i.aprovada_por_id)
        self.assertGreaterEqual(i.aceita_ate, timezone.localdate())
        self.assertIn("SIMULAÇÃO", i.justificativa)
        self.assertTrue(SnapshotRisco.objects.filter(chave__startswith="DEMO-").exists())
        self.assertTrue(verificar_cadeia(verificar_ancora=False)["integra"])
        self.assertFalse(get_user_model().objects.get(pk=i.aceita_por_id).has_usable_password())
        self.assertFalse(get_user_model().objects.get(pk=i.aprovada_por_id).has_usable_password())
        total = (Ativo.objects.count(), Incidencia.objects.count(), SnapshotRisco.objects.count())
        call_command("seed_demo", operacional=True, stdout=saida)
        self.assertEqual(total, (Ativo.objects.count(), Incidencia.objects.count(), SnapshotRisco.objects.count()))
        self.assertIn("ignorado", saida.getvalue())

    def test_falha_no_meio_do_seed_reverte_cenario_e_auditoria(self):
        antes = verificar_cadeia(verificar_ancora=False)
        with patch("inventario.aplicacao.operacao.emitir_alerta", side_effect=RuntimeError("falha simulada")):
            with self.assertRaisesMessage(RuntimeError, "falha simulada"):
                call_command("seed_demo", operacional=True, stdout=StringIO())
        self.assertFalse(Ativo.objects.exists())
        self.assertFalse(Incidencia.objects.exists())
        self.assertFalse(SnapshotRisco.objects.exists())
        self.assertEqual(verificar_cadeia(verificar_ancora=False), antes)

    def test_base_existente_nao_recebe_nem_altera_dados_de_demo(self):
        sala = Sala.objects.create(id="SALA-REAL-1", nome="Local existente")
        saida = StringIO()
        call_command("seed_demo", operacional=True, stdout=saida)
        sala.refresh_from_db()
        self.assertEqual(sala.nome, "Local existente")
        self.assertEqual(Sala.objects.count(), 1)
        self.assertFalse(Ativo.objects.exists())
        self.assertFalse(SnapshotRisco.objects.exists())
        self.assertIn("ignorado", saida.getvalue())
