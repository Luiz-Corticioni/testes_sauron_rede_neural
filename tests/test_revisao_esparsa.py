import json
from unittest import TestCase
from unittest.mock import patch
from inventario.matematica.diagnostico import DiagnosticoLinear
from inventario.matematica.representacao import como_csr
from inventario.web.visualizacao import grafo_dependencias, mapas_calor
from . import test_risco_esparso as fixture


class SerializacaoEsparsa(TestCase):
    def test_5000_calcula_serializa_e_apresenta_sem_matriz_densa_integral(self):
        resultado = fixture.R14().modelo(5000).calcular()
        with patch("inventario.matematica.risco.VisaoMatriz.tolist", side_effect=AssertionError("Não densificar")):
            dados = resultado.to_dict()
            serializado = json.dumps(dados)
        self.assertLess(len(serializado), 3_000_000)
        self.assertEqual(dados["matriz_dependencias"]["formato"], "csr")
        self.assertEqual(como_csr(dados["matriz_dependencias"]).nnz, 4999)
        diagnostico = DiagnosticoLinear.analisar(dados, "1")
        self.assertTrue(diagnostico["posto_limitado"])
        self.assertEqual(diagnostico["equacao"]["fornecedores"][0]["id"], "0")
        grafo = grafo_dependencias(dados, {})
        self.assertEqual(len(grafo["nos"]), 60)
        mapas, inversa = mapas_calor(dados)
        self.assertEqual(len(mapas[1]["linhas"]), 40)
        self.assertEqual(inversa, [])

    def test_inventario_pequeno_preserva_arrays_do_contrato(self):
        dados = fixture.R14().modelo(2).calcular().to_dict()
        self.assertIsInstance(dados["matriz_dependencias"], list)
        self.assertEqual(dados["matriz_dependencias"], [[0, 0], [.2, 0]])
