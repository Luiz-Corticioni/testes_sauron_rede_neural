
from unittest import TestCase
from inventario.matematica.caminhos_ataque import construir_grafo, menor_custo, pontos_estrangulamento


class Caminhos(TestCase):
    def test_zona_porta_caminho_e_gargalo(self):
        ativos=[{"id":"internet","zona_rede":"externa","portas_servicos":[]},
                {"id":"web","zona_rede":"dmz","portas_servicos":[443]},
                {"id":"db","zona_rede":"interna","portas_servicos":[5432]}]
        regras=[{"origem":"externa","destino":"dmz","portas":[443],"custo":2},
                {"origem":"dmz","destino":"interna","portas":[5432],"custo":3}]
        grafo=construir_grafo(ativos,regras)
        self.assertEqual(menor_custo(grafo,"internet","db"),{"custo":5,"caminho":["internet","web","db"]})
        self.assertEqual(pontos_estrangulamento(grafo,"internet",["db"]),{"web":["db"]})
        self.assertIsNone(menor_custo(construir_grafo(ativos,[]),"internet","db"))

    def test_caminhos_alternativos(self):
        grafo={"s":{"a":1,"b":2},"a":{"t":3},"b":{"t":1},"t":{}}
        self.assertEqual(menor_custo(grafo,"s","t")["caminho"],["s","b","t"])
        self.assertEqual(pontos_estrangulamento(grafo,"s",["t"]),{})

