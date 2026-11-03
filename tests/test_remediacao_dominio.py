
from unittest import TestCase
from inventario.dominio.sistema_imune import Anticorpo, Antigeno, avaliar_sinais


class R4(TestCase):
    def test_versoes_produto_e_eixos(self):
        origem = Antigeno("RCE", "1", "Dell", "log4j", "2", "14", True, "N")
        memoria = Anticorpo("1", "v", origem.to_dict())
        for menor in ("16", "17"):
            with self.subTest(menor=menor):
                self.assertLess(memoria.avaliar(Antigeno("RCE", "1", "Dell", "log4j", "2", menor, True, "N")), .75)
        iis = Anticorpo("1", "v", Antigeno("RCE", "1", "Microsoft", "IIS", "10", "0", True, "N").to_dict())
        self.assertLess(iis.avaliar(Antigeno("RCE", "1", "Microsoft", "SQL Server", "10", "0", True, "N")), .75)
        self.assertFalse(any(k.startswith(("categoria=", "vetor_ataque=")) for k in origem.normalizado()))

    def test_fronteira_seis_de_oito(self):
        self.assertEqual(avaliar_sinais(0.7499999999999999, ["KEV"]), "PENDENTE")
        self.assertIsNone(avaliar_sinais(.74999, ["KEV"]))

