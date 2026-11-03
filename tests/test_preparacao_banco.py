
from pathlib import Path
from unittest.mock import patch, Mock
from sauron_web.banco import configurar_banco
from inventario.management.commands.preparar_servidor import Command
from .base import BancoTeste


class PreparacaoBanco(BancoTeste):
    def test_parser_e_preparacao_sem_caminho_no_postgres(self):
        config=configurar_banco("postgresql://usuario:p%40ss@banco:5432/sauron?sslmode=require",{})
        self.assertEqual(config["PASSWORD"],"p@ss")
        self.assertEqual(config["ENGINE"],"django.db.backends.postgresql")
        settings=Mock(DATA_DIR=Path(self.diretorio.name),DATABASES={"default":config})
        with patch("inventario.management.commands.preparar_servidor.settings",settings), patch(
                "inventario.management.commands.preparar_servidor.call_command"):
            Command().handle(sem_estaticos=True)

