
from unittest import TestCase
import numpy as np
from scipy.sparse import csr_matrix
from inventario.matematica.risco_noisy_or import calcular


class NoisyOR(TestCase):
    def test_convergencia_monotona_e_limites(self):
        a=csr_matrix([[0,.8,.8],[.5,0,.8],[.9,.9,0]])
        r=calcular([.01,.02,.03],a,historico=True)
        historico=np.array(r["historico"])
        self.assertTrue(np.all(np.diff(historico,axis=0)>=-1e-14))
        self.assertTrue(np.all((historico>=0)&(historico<=1)))
        self.assertLess(r["residuo"],1e-10)

    def test_limites_e_comparacao_leontief(self):
        self.assertEqual(calcular([0,0],[[0,.5],[.5,0]])["probabilidades"],[0,0])
        self.assertEqual(calcular([1,1],[[0,1],[1,0]])["probabilidades"],[1,1])
        a=np.array([[0,.1],[.1,0]])
        p=np.array([.001,.002])
        linear=np.linalg.solve(np.eye(2)-a,p)
        obtido=calcular(p,a)["probabilidades"]
        self.assertTrue(np.all(obtido<=linear))
        np.testing.assert_allclose(obtido,linear,atol=1e-6)

