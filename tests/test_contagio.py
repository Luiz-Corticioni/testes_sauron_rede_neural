
from unittest import TestCase
import numpy as np
from inventario.matematica.contagio import simular, mttr_historico


class Contagio(TestCase):
    def test_mttr_e_efeito_correcao_sis_sir(self):
        historico=[{"incidencia_codigo":"1","para":"ABERTA","em":"2026-01-01T00:00:00+00:00"},
                   {"incidencia_codigo":"1","para":"CORRIGIDA","em":"2026-01-11T00:00:00+00:00"}]
        self.assertEqual(mttr_historico(historico),10)
        for modelo in ("SIS","SIR"):
            for metodo in ("euler","rk4"):
                r=simular([[0,1],[1,0]],[.1,0],exposicao=[4,4],epss=[.8,.8],
                    historico=historico,dias=10,passos=200,modelo=modelo,metodo=metodo,
                    vulnerabilidades={"CVE-1":[0,1]},corrigir_vulnerabilidades=["CVE-1"])
                estados=np.array(r["antes"]["estados"])
                np.testing.assert_allclose(estados.sum(axis=2),1,atol=1e-10)
                self.assertGreater(r["efeito_correcao"],0)
                self.assertTrue(np.all((estados>=0)&(estados<=1)))

