
from unittest.mock import patch
from django.db import transaction
from inventario.infraestrutura.importacao import importar_csv
from inventario.models import Sala
from .base import BancoTeste


class R9(BancoTeste):
    def setUp(self):
        super().setUp()
        # Descarta efeitos do fixture; a transação medida começa após sua preparação.
        transaction.get_connection().run_on_commit.clear()

    def test_importar_500_uma_invalidacao_zero_exports(self):
        texto = "tipo,nome,fabricante,sala,responsavel\n" + "".join(
            f"1,Importado{n},Dell,SALA-TESTE,Equipe\n" for n in range(500))
        with patch("inventario.aplicacao.servicos.exportar_inventario_json") as exportar, patch(
                "inventario.aplicacao.servicos.invalidar_cache_risco") as invalidar:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                r = importar_csv(texto, self.usuario, dry_run=False)
            self.assertEqual(r["gravados"], 500)
            self.assertEqual(len(callbacks), 1)
            invalidar.assert_called_once()
            exportar.assert_not_called()

    def test_rollback_interno_nao_perde_callback(self):
        from inventario.aplicacao.servicos import sincronizar_estado
        with patch("inventario.aplicacao.servicos.invalidar_cache_risco") as invalidar:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                try:
                    with transaction.atomic():
                        sincronizar_estado(Sala)
                        raise ValueError()
                except ValueError:
                    pass
                sincronizar_estado(Sala)
            self.assertEqual(len(callbacks), 1)
            invalidar.assert_called_once()

