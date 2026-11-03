
from unittest import TestCase
from inventario.matematica.series import SerieRisco


class M4(TestCase):
    def test_area_degrau(self):
        self.assertEqual(SerieRisco([0,1,2],[2,5,5]).analisar()["risco_dia"],7)

    def test_20_minutos_nao_alerta(self):
        resultado=SerieRisco([0,10/1440,20/1440],[0,3,6]).analisar()
        self.assertEqual(resultado["alertas"],[])
        self.assertIsNone(resultado["taxa_por_dia"])

    def test_regressao_em_janela_minima(self):
        resultado=SerieRisco([0,.5,1],[0,6,12]).analisar()
        self.assertAlmostEqual(resultado["taxa_por_dia"],12)

