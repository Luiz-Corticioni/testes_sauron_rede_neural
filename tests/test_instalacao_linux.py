from argparse import Namespace
from io import StringIO
from pathlib import Path
import os
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.test import SimpleTestCase
from scripts.configurar_linux import preparar
from .base import BancoTeste


class ConfiguracaoLinux(BancoTeste):
    def setUp(self):
        super().setUp()
        existente = patch("scripts.configurar_linux.Path.exists", return_value=True)
        existente.start()
        self.addCleanup(existente.stop)

    def opcoes(self, atualizar=False, verificar=False):
        return Namespace(atualizar=atualizar, verificar=verificar)

    def test_instalacao_nova_prepara_ancora_e_verifica(self):
        banco = settings.DATA_DIR / "novo.sqlite3"
        with patch("scripts.configurar_linux.Path.exists", return_value=False), patch("django.core.management.call_command") as comando, patch("sys.stdout", new_callable=StringIO):
            preparar(self.opcoes())
        self.assertEqual([c.args[0] for c in comando.call_args_list], ["preparar_servidor", "ancorar_auditoria", "verificar_auditoria"])
        self.assertFalse(os.path.exists(banco))

    def test_atualizacao_faz_backup_antes_de_migrar(self):
        with patch("django.core.management.call_command") as comando, patch("sys.stdout", new_callable=StringIO):
            preparar(self.opcoes(atualizar=True))
        self.assertEqual([c.args[0] for c in comando.call_args_list], ["verificar_auditoria", "backup", "preparar_servidor", "ancorar_auditoria", "verificar_auditoria"])

    def test_backup_falha_impede_migracao(self):
        def falha(nome):
            if nome == "backup":
                raise ValueError("chave ausente")
        with patch("django.core.management.call_command", side_effect=falha) as comando:
            with self.assertRaisesMessage(ValueError, "chave ausente"):
                preparar(self.opcoes(atualizar=True))
        self.assertEqual([c.args[0] for c in comando.call_args_list], ["verificar_auditoria", "backup"])

    def test_reexecucao_preserva_banco_sem_migrar(self):
        executor = MagicMock()
        executor.migration_plan.return_value = []
        with patch("django.db.migrations.executor.MigrationExecutor", return_value=executor), patch("django.core.management.call_command") as comando, patch("sys.stdout", new_callable=StringIO):
            preparar(self.opcoes())
        self.assertEqual([c.args[0] for c in comando.call_args_list], ["verificar_auditoria", "diagnosticar"])

    def test_migracao_pendente_exige_atualizacao_explicita(self):
        executor = MagicMock()
        executor.migration_plan.return_value = ["pendente"]
        with patch("django.db.migrations.executor.MigrationExecutor", return_value=executor), patch("django.core.management.call_command") as comando:
            with self.assertRaisesMessage(ValueError, "--atualizar"):
                preparar(self.opcoes())
        self.assertEqual([c.args[0] for c in comando.call_args_list], ["verificar_auditoria"])


class GeracaoEnv(SimpleTestCase):
    def test_segredos_privados_preservados_sem_sobrescrita(self):
        raiz = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as pasta:
            destino = Path(pasta) / ".env"
            comando = [sys.executable, str(raiz / "scripts/preparar_ambiente.py"), "--saida", str(destino)]
            primeiro = subprocess.run(comando, capture_output=True, text=True, check=True)
            conteudo = destino.read_bytes()
            self.assertIn(b"SAURON_BACKUP_KEY=", conteudo)
            self.assertIn(b"http://127.0.0.1:2228", conteudo)
            self.assertIn(b"http://localhost:2228", conteudo)
            self.assertNotIn(conteudo.decode().splitlines()[0], primeiro.stdout)
            subprocess.run(comando, capture_output=True, text=True, check=True)
            self.assertEqual(conteudo, destino.read_bytes())
            if os.name != "nt":
                self.assertEqual(destino.stat().st_mode & 0o777, 0o600)

    def test_origem_https_usa_o_host_sem_porta_local(self):
        raiz = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as pasta:
            destino = Path(pasta) / ".env"
            subprocess.run([sys.executable, str(raiz / "scripts/preparar_ambiente.py"),
                            "--saida", str(destino), "--host", "sauron.example.org"],
                           capture_output=True, text=True, check=True)
            conteudo = destino.read_text(encoding="utf-8")
            self.assertIn("SAURON_CSRF_TRUSTED_ORIGINS=https://sauron.example.org", conteudo)
            self.assertNotIn("http://127.0.0.1:2228", conteudo)
