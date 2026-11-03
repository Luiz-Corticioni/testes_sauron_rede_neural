
from unittest import TestCase
from inventario.dominio.matching import comparar_versoes, extrair_faixas, avaliar_componente


CPE = "cpe:2.3:a:apache:log4j:*:*:*:*:*:*:*:*"
FAIXAS = [{"criteria":CPE, "vulnerable":True,
           "versionStartIncluding":"2.0", "versionEndExcluding":"2.15"}]


class R13(TestCase):
    def test_limites_e_versoes(self):
        for a,b,c in [("2.9","2.10",-1),("1.0","1.0.0",0),("1.0rc1","1.0",-1),("2.0","1.99",1)]:
            self.assertEqual(comparar_versoes(a,b),c)
        for versao, esperado in [("2.0",True),("2.14.1",True),("2.15",False),("2.17.1",False)]:
            self.assertEqual(avaliar_componente(CPE,versao,FAIXAS),esperado)

    def test_nvd_e_vex_e_contexto(self):
        dados = {"configurations":[{"nodes":[{"operator":"OR","cpeMatch":FAIXAS}]}]}
        self.assertEqual(extrair_faixas(dados),FAIXAS)
        vex = [{"cpe23":CPE, "status":"not_affected","justificativa":"Componente sem caminho executável"}]
        self.assertFalse(avaliar_componente(CPE,"2.14.1",FAIXAS,vex))
        complexo = [{"operator":"AND", "nodes":[{"operator":"OR","cpeMatch":FAIXAS},
              {"operator":"OR","cpeMatch":[{"criteria":"cpe:2.3:o:linux:linux_kernel:*:*:*:*:*:*:*:*", "vulnerable":False}]}]}]
        self.assertIsNone(avaliar_componente(CPE,"2.14.1",extrair_faixas({"configurations":complexo})))

    def test_fixture_precisao_recall(self):
        import json
        from pathlib import Path
        fixture = json.loads(Path(__file__).with_name("matching_rotulado.json").read_text())
        tp=fp=fn=0
        for item in fixture:
            predito = avaliar_componente(item["cpe"], item["versao"], FAIXAS) is True
            tp += predito and item["afetado"]
            fp += predito and not item["afetado"]
            fn += not predito and item["afetado"]
        self.assertGreaterEqual(tp/(tp+fp), .95)
        self.assertGreaterEqual(tp/(tp+fn), .95)

