
from unittest.mock import patch
from django.db import connection
from inventario.aplicacao import imune
from .test_remediacao_imune import MemoriaTeste


class I10(MemoriaTeste):
    def test_matching_fora_da_transacao_de_escrita(self):
        self.preparar()
        profundidade=len(connection.savepoint_ids)
        original=imune.afinidade
        def conferir(*args):
            self.assertEqual(len(connection.savepoint_ids),profundidade)
            return original(*args)
        with patch("inventario.aplicacao.imune.afinidade",side_effect=conferir):
            imune.executar_ciclo()


    def test_alteracao_concorrente_adia_lote(self):
        from inventario.infraestrutura.auditoria import registrar_evento
        self.preparar()
        original=imune.afinidade
        mudou=False
        def alterar(*args):
            nonlocal mudou
            if not mudou:
                registrar_evento("TESTE_CONCORRENCIA","Teste","snapshot")
                mudou=True
            return original(*args)
        with patch("inventario.aplicacao.imune.afinidade",side_effect=alterar):
            resultado=imune.executar_ciclo()
        self.assertTrue(resultado["adiado_por_concorrencia"])
