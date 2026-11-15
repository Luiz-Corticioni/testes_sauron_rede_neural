from pathlib import Path
import os
import runpy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from .base import BancoTeste


class SegurancaCargaCompose(BancoTeste):
    def test_fixture_recusa_execucao_sem_habilitacao_e_banco_com_dados(self):
        caminho = Path(__file__).resolve().parents[1] / "scripts" / "carga_compose" / "preparar.py"
        antes = get_user_model().objects.count()
        with patch.dict(os.environ, {"SAURON_CARGA_DESCARTAVEL": "0"}):
            with self.assertRaisesRegex(RuntimeError, "exige"):
                runpy.run_path(str(caminho))
        with patch.dict(os.environ, {"SAURON_CARGA_DESCARTAVEL": "1"}):
            with self.assertRaisesRegex(RuntimeError, "não está vazio"):
                runpy.run_path(str(caminho))
        self.assertEqual(get_user_model().objects.count(), antes)
