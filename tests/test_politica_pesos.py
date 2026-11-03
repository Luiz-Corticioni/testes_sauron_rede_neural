
from django.test import override_settings
from inventario.aplicacao.risco import carregar_modelo_risco
from inventario.aplicacao.cadastros import salvar_cadastro
from inventario.models import Ativo, Dependencia
from .base import BancoTeste


class M2(BancoTeste):
    @override_settings(RISCO_FATORES_EXPOSICAO={"1":2})
    def test_fator_configuravel(self):
        modelo,_=carregar_modelo_risco()
        self.assertEqual(modelo.fatores[self.a.pk],2)

    @override_settings(RISCO_POLITICA="noisy-or")
    def test_soma_linha_maior_que_um_em_laboratorio(self):
        terceiro=Ativo.objects.create(tipo="1",nome="terceiro",fabricante="Dell",sala=self.sala)
        salvar_cadastro(Dependencia(dependente=self.b,fornecedor=terceiro,peso=.9),self.usuario)
        self.assertGreater(sum(Dependencia.objects.filter(dependente=self.b).values_list("peso",flat=True)),1)


    def test_configuracao_de_exposicao_versiona_cache(self):
        from inventario.aplicacao.risco import versao_dados
        with override_settings(RISCO_FATORES_EXPOSICAO={"1":2}):
            anterior=versao_dados("operacional")
        with override_settings(RISCO_FATORES_EXPOSICAO={"1":3}):
            self.assertNotEqual(versao_dados("operacional"),anterior)
