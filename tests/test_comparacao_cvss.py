from copy import deepcopy
from unittest import TestCase
from inventario.dominio.comparacao_cvss import comparar_notas, selecionar_metrica

V31 = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
V40 = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"


def registro():
    return {
        "id": "CVE-2024-12345",
        "vulnStatus": "Analyzed",
        "lastModified": "2026-10-27T12:00:00.000",
        "metrics": {
            "cvssMetricV31": [
                {
                    "source": "nvd@nist.gov",
                    "type": "Primary",
                    "cvssData": {"version": "3.1", "baseScore": 9.8, "vectorString": V31},
                }
            ],
            "cvssMetricV40": [
                {
                    "source": "security@example.org",
                    "type": "Secondary",
                    "cvssData": {"version": "4.0", "baseScore": 9.3, "vectorString": V40},
                }
            ],
        },
    }


class ComparacaoCVSS(TestCase):
    def test_diferenca_entre_versoes_e_conferencia_31(self):
        r = comparar_notas(registro())
        self.assertEqual(r["local31"]["nota"], 9.8)
        self.assertEqual(r["nvd40"]["nota"], 9.3)
        self.assertEqual(r["diferenca_40_menos_31"], -0.5)
        self.assertEqual(r["diferenca_31_nvd_menos_local"], 0)
        self.assertEqual(r["nvd40"]["publicador"], "security@example.org")
        self.assertEqual(r["nvd40"]["origem"], "NVD")
        self.assertEqual(r["nvd40"]["verificacao"], "estrutura; nota não recalculada localmente")

    def test_zero_e_ausencia_sao_distintos(self):
        c = registro()
        c["metrics"].pop("cvssMetricV40")
        self.assertIsNone(comparar_notas(c)["diferenca_40_menos_31"])
        c["metrics"]["cvssMetricV40"] = deepcopy(registro()["metrics"]["cvssMetricV40"])
        c["metrics"]["cvssMetricV40"][0]["cvssData"].update(
            baseScore=0, vectorString=V40.replace("VC:H/VI:H/VA:H", "VC:N/VI:N/VA:N")
        )
        self.assertEqual(comparar_notas(c)["diferenca_40_menos_31"], -9.8)
        c["metrics"].pop("cvssMetricV31")
        self.assertIsNone(comparar_notas(c)["local31"]["nota"])
        self.assertEqual(comparar_notas(c)["nvd40"]["nota"], 0)

    def test_prioridade_nvd_e_multiplos_publicadores(self):
        c = registro()
        outro = deepcopy(c["metrics"]["cvssMetricV31"][0])
        outro.update(source="cna@example.org", type="Primary")
        outro["cvssData"]["baseScore"] = 8.1
        c["metrics"]["cvssMetricV31"].insert(0, outro)
        self.assertEqual(selecionar_metrica(c, "3.1")["nota"], 9.8)
        self.assertEqual(len(comparar_notas(c)["avaliacoes"]), 3)

    def test_vetor_local_distinto_nao_e_erro_do_algoritmo(self):
        r = comparar_notas(registro(), V31.replace("AC:L", "AC:H"), "vetor informado")
        self.assertEqual(r["local31"]["nota"], 8.1)
        self.assertFalse(r["mesmo_vetor31"])
        self.assertTrue(any("vetores diferentes" in a.lower() for a in r["avisos"]))
        self.assertEqual(r["diferenca_31_nvd_menos_local"], 1.7)

    def test_nota_31_divergente_e_sinalizada(self):
        c = registro()
        c["metrics"]["cvssMetricV31"][0]["cvssData"]["baseScore"] = 8.1
        r = comparar_notas(c)
        self.assertTrue(r["mesmo_vetor31"])
        self.assertEqual(r["diferenca_31_nvd_menos_local"], -1.7)
        self.assertTrue(any("divergência" in a.lower() for a in r["avisos"]))

    def test_4_com_metricas_nao_base_nao_gera_delta_base(self):
        c = registro()
        c["metrics"]["cvssMetricV40"][0]["cvssData"]["vectorString"] += "/E:U"
        r = comparar_notas(c)
        self.assertEqual(r["nvd40"]["nomenclatura"], "CVSS-BT")
        self.assertIsNone(r["diferenca_40_menos_31"])

    def test_dados_malformados_nao_fabricam_comparacao(self):
        for metrics in (None, [], "inválido", {"cvssMetricV40": [None, {}, "x"]}):
            with self.subTest(metrics=metrics):
                r = comparar_notas({"metrics": metrics})
                self.assertIsNone(r["diferenca_40_menos_31"])
        for nota in (True, "9.3", float("nan"), float("inf"), -1, 11, 9.35):
            c = registro()
            c["metrics"]["cvssMetricV40"][0]["cvssData"]["baseScore"] = nota
            self.assertIsNone(comparar_notas(c)["nvd40"]["nota"])
        for vetor in ("CVSS:4.0/AV:N", V40 + "/AV:P", V40.replace("AT:N", "AT:X")):
            c = registro()
            c["metrics"]["cvssMetricV40"][0]["cvssData"]["vectorString"] = vetor
            self.assertIsNone(comparar_notas(c)["diferenca_40_menos_31"])

    def test_v30_nao_vira_31_e_cve_rejeitada_nao_compara(self):
        c = registro()
        c["metrics"]["cvssMetricV31"][0]["cvssData"]["version"] = "3.0"
        self.assertIsNone(comparar_notas(c)["local31"]["nota"])
        c = registro()
        c["vulnStatus"] = "Rejected"
        self.assertIsNone(comparar_notas(c)["diferenca_40_menos_31"])
