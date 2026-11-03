
from time import perf_counter
from unittest import TestCase
import numpy as np
from scipy.sparse import issparse
from inventario.matematica.risco import ModeloRisco
from inventario.dominio.vulnerabilidades import Vulnerabilidade, Incidencia, Dependencia


class R14(TestCase):
    def modelo(self,n):
        ids=[str(i) for i in range(n)]
        v=Vulnerabilidade("VUL-RCE-0001","fixture","RCE",8)
        return ModeloRisco(ids,[v],[Incidencia("INC-1","0",v.id)],
            [Dependencia(str(i),str(i-1),.2) for i in range(1,n)])

    def test_esparso_equivale_denso(self):
        modelo=self.modelo(30)
        m,v,a,_=modelo.montar()
        self.assertTrue(issparse(a))
        esperado=np.linalg.solve(np.eye(30)-a.toarray(),m@v)
        obtido=modelo.calcular(precisao=12)
        np.testing.assert_allclose(obtido.risco_efetivo,esperado,atol=1e-8)
        self.assertLess(obtido.residuo_relativo,1e-10)

    def test_5000_sem_alocacao_densa_e_benchmark(self):
        modelo=self.modelo(5000)
        self.assertTrue(issparse(modelo.montar()[2]))
        inicio=perf_counter()
        resultado=modelo.calcular()
        duracao=perf_counter()-inicio
        self.assertEqual(len(resultado.risco_efetivo),5000)
        self.assertLess(duracao,1.0) # Meta 100 ms; margem de 10x para CI compartilhado.
        print(f"Benchmark R14: 5000 ativos, 1 vulnerabilidade, 4999 arestas: {duracao*1000:.1f} ms")

