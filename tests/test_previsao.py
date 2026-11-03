
from unittest import TestCase
from inventario.matematica.previsao_avaliacao import brier, calibracao, pr_auc, walk_forward


class Previsao(TestCase):
    def test_metricas_conhecidas(self):
        self.assertEqual(brier([0,1],[0,1]),0)
        self.assertEqual(brier([0,1],[.5,.5]),.25)
        self.assertEqual(pr_auc([0,1],[.1,.9]),1)
        self.assertEqual(pr_auc([0,0],[.1,.9]),0)
        r=calibracao([0,1],[0,1],bins=2)
        self.assertEqual(r["ece"],0)
        self.assertEqual(sum(b["n"] for b in r["bins"]),2)

    def test_walk_forward_sem_rotulo_futuro(self):
        dados=[{"ts":i,"y":i%2,"feature":i%2} for i in range(10)]
        def prever(treino,teste):
            self.assertLess(max(r["ts"] for r in treino),min(r["ts"] for r in teste))
            self.assertFalse(any("y" in r for r in teste))
            return [r["feature"] for r in teste]
        resultado=walk_forward(dados,prever,treino_minimo=4,horizonte=2)
        self.assertEqual(len(resultado["folds"]),3)
        self.assertEqual(resultado["brier"],0)
        with self.assertRaises(ValueError):
            walk_forward(list(reversed(dados)),prever,4,2)

