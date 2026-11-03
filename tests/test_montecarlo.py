from django.test import SimpleTestCase
from inventario.matematica.montecarlo import simular, prob_30dias


class NucleoMonteCarlo(SimpleTestCase):
    custos = {"C": 100., "I": 20., "A": 30.}
    def entrada(self, **kw):
        return {"ativo": "A", "cve": "CVE-1", "cvss": 10, "epss": .1,
                "vetor": "CVSS:3.1/C:H/I:H/A:H", **kw}

    def rodar(self, entradas=None, **kw):
        return simular(entradas if entradas is not None else [self.entrada()], custos=self.custos, n=2000, **kw)

    def test_zero_um_fixo(self):
        self.assertEqual(self.rodar([self.entrada(epss=0)])["antes"]["media"], 0)
        r = self.rodar([self.entrada(epss=1)])
        for campo in ("media", "P5", "P50", "P95", "P99"):
            self.assertEqual(r["antes"][campo], 150)
        self.assertEqual(r["antes"]["probabilidade_perda"], 1)

    def test_determinismo_monotonicidade(self):
        r = self.rodar()
        self.assertEqual(r, self.rodar())
        maior = self.rodar([self.entrada(epss=.2)])
        for campo in ("media", "P5", "P50", "P95", "P99", "probabilidade_perda"):
            self.assertGreaterEqual(maior["antes"][campo], r["antes"][campo])
        self.assertEqual(r["horizonte_dias"], 30)
        self.assertEqual(prob_30dias(self.entrada())[0], .1)
        self.assertNotIn("mensal", r)

    def test_maximo_soma_correcao_teto(self):
        v = [self.entrada(epss=1), self.entrada(epss=1, cve="CVE-2")]
        self.assertEqual(self.rodar(v)["antes"]["media"], 150)
        v.append(self.entrada(epss=1, ativo="B"))
        r = self.rodar(v, corrigidas=["CVE-1"], teto=200)
        self.assertEqual(r["antes"]["media"], 200)
        self.assertEqual(r["depois"]["media"], 150)
        self.assertEqual(r["ganho_media"], 50)
        self.assertAlmostEqual(sum(c["media_atribuida"] for c in r["contribuicoes"]), 200)
        self.assertEqual(r["contribuicoes"][0]["ganho_correcao"], 50)

    def test_comuns_pert_ordem(self):
        v = [self.entrada(), self.entrada(ativo="B", cve="CVE-2")]
        kw = {"custos": {d: (1, 3, 20) for d in "CIA"}, "n": 2000}
        r = simular(v, corrigidas=["CVE-1"], **kw)
        self.assertEqual(r["antes"], simular(list(reversed(v)), **kw)["antes"])
        self.assertEqual(r["depois"], simular(v[1:], **kw)["antes"])

    def test_sem_epss_nao_inventa_probabilidade_e_kev_nao_cria_piso(self):
        with self.assertRaises(ValueError):
            self.rodar([self.entrada(epss=None)])
        r = self.rodar([self.entrada(epss=0, vetor="", kev=True)])
        self.assertTrue(r["entradas"][0]["impacto_estimado"])
        self.assertEqual(r["entradas"][0]["probabilidade_cenario_30d"], 0)
        self.assertEqual(self.rodar([])["antes"]["media"], 0)

    def test_invalidos(self):
        for extra in ({"epss": -1}, {"epss": float("nan")}, {"cvss": 11}, {"exposicao": 2},
                      {"vetor": "CVSS:3.1/C:X/I:H/A:H"}, {"kev": 1}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.rodar([self.entrada(**extra)])
        for kw in ({"n": True}, {"seed": -1}, {"teto": -1}, {"corrigidas": 1},
                   {"custos": {d: (1, 1, 2) for d in "CIA"}}, {"corrigidas": ["desconhecida"]}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                simular([self.entrada()], **kw)
        with self.assertRaises(ValueError):
            self.rodar([self.entrada(), self.entrada()])


    def test_ganhos_marginais_conferem_com_correcao(self):
        entradas = [self.entrada(cve="alta", epss=.04),
                    self.entrada(cve="baixa", epss=.3, vetor="CVSS:3.1/C:L/I:N/A:N"),
                    self.entrada(ativo="B", cve="alta", epss=.02)]
        base = self.rodar(entradas, teto=180)
        for item in base["contribuicoes"]:
            correcao = self.rodar(entradas, teto=180, corrigidas=[item["cve"]])
            self.assertAlmostEqual(item["ganho_correcao"], correcao["ganho_media"])
            self.assertGreaterEqual(correcao["ganho_media"], 0)
        self.assertAlmostEqual(sum(c["media_atribuida"] for c in base["contribuicoes"]), base["antes"]["media"])
        probabilidades = [p["probabilidade"] for p in base["excedencia"]]
        self.assertEqual(probabilidades, sorted(probabilidades, reverse=True))
