"""Oráculos analíticos e referência Decimal independente das constantes do produto."""

from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING, localcontext
from itertools import product
import math
import random
from unittest import TestCase
import numpy as np
from scipy import sparse
from inventario.matematica.cvss import CalculadoraCVSS31, round_up_1
from inventario.matematica.euler import FuncaoMatematica, Derivador, Integrador, metodo_euler, rk4
from inventario.matematica.estabilidade import validar_matriz
from inventario.matematica.risco import ModeloRisco
from inventario.dominio.vulnerabilidades import Vulnerabilidade, Incidencia, Dependencia
from inventario.matematica.series import SerieRisco


def ambiental_referencia(m):
    D = Decimal

    def num(x):
        return D(str(x))

    def mod(k):
        return m.get("M" + k, "X") if m.get("M" + k, "X") != "X" else m[k]

    def ru(x):
        return x.quantize(D(".00001"), rounding=ROUND_HALF_UP).quantize(
            D(".1"), rounding=ROUND_CEILING
        )

    req = {"X": D(1), "L": D(".5"), "M": D(1), "H": D("1.5")}
    cia = {"N": D(0), "L": D(".22"), "H": D(".56")}
    c, i, a = (cia[mod(k)] * req[m.get(r, "X")] for k, r in zip("CIA", ("CR", "IR", "AR")))
    miss = min(1 - (1 - c) * (1 - i) * (1 - a), D(".915"))
    scope = mod("S")
    impact = (
        D("6.42") * miss
        if scope == "U"
        else D("7.52") * (miss - D(".029")) - D("3.25") * (miss * D(".9731") - D(".02")) ** 13
    )
    if impact <= 0:
        return 0.0
    av = num({"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}[mod("AV")])
    ac = num({"L": 0.77, "H": 0.44}[mod("AC")])
    ui = num({"N": 0.85, "R": 0.62}[mod("UI")])
    pr = num(
        ({"N": 0.85, "L": 0.62, "H": 0.27} if scope == "U" else {"N": 0.85, "L": 0.68, "H": 0.5})[
            mod("PR")
        ]
    )
    e = num({"X": 1, "H": 1, "F": 0.97, "P": 0.94, "U": 0.91}[m.get("E", "X")])
    rl = num({"X": 1, "U": 1, "W": 0.97, "T": 0.96, "O": 0.95}[m.get("RL", "X")])
    rc = num({"X": 1, "C": 1, "R": 0.96, "U": 0.92}[m.get("RC", "X")])
    return float(
        ru(
            ru(
                min(
                    (impact + D("8.22") * av * ac * pr * ui) * (1 if scope == "U" else D("1.08")),
                    D(10),
                )
            )
            * e
            * rl
            * rc
        )
    )


class AuditoriaNumerica(TestCase):
    def test_ambiental_2000_vetores_com_modificadas_e_temporais(self):
        rng = random.Random(312026)
        opcoes = {
            "AV": "NALP",
            "AC": "LH",
            "PR": "NLH",
            "UI": "NR",
            "S": "UC",
            "C": "NLH",
            "I": "NLH",
            "A": "NLH",
            "E": "XHFPU",
            "RL": "XUWTO",
            "RC": "XCRU",
            "CR": "XHML",
            "IR": "XHML",
            "AR": "XHML",
            "MAV": "XNALP",
            "MAC": "XLH",
            "MPR": "XNLH",
            "MUI": "XNR",
            "MS": "XUC",
            "MC": "XNLH",
            "MI": "XNLH",
            "MA": "XNLH",
        }
        with localcontext() as contexto:
            contexto.prec = 45
            for _ in range(2000):
                m = {k: rng.choice(v) for k, v in opcoes.items()}
                vetor = "CVSS:3.1/" + "/".join(k + ":" + v for k, v in m.items())
                with self.subTest(vetor=vetor):
                    self.assertEqual(
                        CalculadoraCVSS31.ambiental(vetor).score, ambiental_referencia(m)
                    )

    def test_arredondamento_e_normalizacao(self):
        for x, esperado in (
            (4.000000000000001, 4.0),
            (4.000004, 4.0),
            (4.000005, 4.1),
            (9.9999999, 10.0),
        ):
            self.assertEqual(round_up_1(x), esperado)
        v = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        self.assertEqual(CalculadoraCVSS31.ambiental("  " + v + "  ").score, 9.8)

    def test_metodos_numericos_contra_solucoes_analiticas(self):
        for x in (-2.0, 0.0, 1.5):
            self.assertAlmostEqual(Derivador.central(lambda z: z**3, x), 3 * x * x, places=6)
            self.assertAlmostEqual(Derivador.segunda(lambda z: z * z, x), 2.0, places=6)
        self.assertAlmostEqual(Integrador.simpson(lambda x: x**3, 0, 2, 20), 4.0, places=12)
        self.assertAlmostEqual(Integrador.simpson(math.sin, 0, math.pi, 100), 2.0, places=6)
        self.assertAlmostEqual(
            Integrador.trapezios(lambda x: 2 * x + 1, 2, -1, 10), -6.0, places=12
        )
        self.assertAlmostEqual(FuncaoMatematica("log(x,10)+sin(pi/2)").avaliar(100), 3.0)
        for metodo in (metodo_euler, rk4):
            grosso = abs(metodo(lambda t, y: y, 1.0, 0, 1, 10)["estados"][-1] - math.e)
            fino = abs(metodo(lambda t, y: y, 1.0, 0, 1, 20)["estados"][-1] - math.e)
            self.assertLess(fino, grosso)

    def test_matrizes_50_grafos_contra_solucao_densa_e_simulacao(self):
        rng = np.random.default_rng(20261027)
        for _ in range(50):
            n = 6
            ids = [str(i) for i in range(n)]
            a = rng.random((n, n)) * 0.06
            np.fill_diagonal(a, 0)
            deps = [
                Dependencia(ids[i], ids[j], float(a[i, j]))
                for i, j in product(range(n), repeat=2)
                if a[i, j]
            ]
            vs = [
                Vulnerabilidade("VUL-RCE-0001", "a", "RCE", 8),
                Vulnerabilidade("VUL-DOS-0002", "b", "DOS", 4),
            ]
            incs = [Incidencia("INC-0", ids[0], vs[0].id), Incidencia("INC-1", ids[1], vs[1].id)]
            fatores = {k: 1.5 for k in ids}
            modelo = ModeloRisco(ids, vs, incs, deps, fatores, {vs[0].id})
            for perfil in ("puro", "operacional"):
                r = modelo.calcular(perfil=perfil, precisao=12)
                b = (
                    np.array([8.0, 4.0, 0.0, 0.0, 0.0, 0.0])
                    if perfil == "puro"
                    else np.array([15.6, 6.0, 0.0, 0.0, 0.0, 0.0])
                )
                esperado = np.linalg.solve(np.eye(n) - a, b)
                np.testing.assert_allclose(r.risco_efetivo, esperado, atol=1e-10)
                self.assertLess(r.residuo_relativo, 1e-12)
                sim = modelo.simular(["INC-0"], perfil=perfil, precisao=12)
                self.assertGreater(sim["ganho_total"], 0)
                self.assertAlmostEqual(sim["ganho_total"], sum(sim["ganho_por_ativo"]), places=5)
                np.testing.assert_allclose(r.indices, -100 * np.expm1(-esperado / 25), atol=1e-10)

    def test_raio_espectral_de_grafo_aciclico_grande_e_zero(self):
        a = sparse.diags([0.2] * 400, -1, shape=(401, 401), format="csr")
        _, raio = validar_matriz(a)
        self.assertEqual(raio, 0.0)

    def test_risco_dia_em_intervalo_parcial_e_tendencia_constante(self):
        r = SerieRisco([0, 1, 2, 3], [2, 5, 5, 5]).analisar(0.5, 2.5)
        self.assertEqual(r["risco_dia"], 8.5)
        r = SerieRisco([0, 1, 2, 3], [7, 7, 7, 7]).analisar(janela_minima_dias=2)
        self.assertEqual(r["risco_dia"], 21.0)
        self.assertEqual(r["taxa_por_dia"], 0.0)

    def test_raio_espectral_de_ciclo_grande_uniforme(self):
        a = sparse.diags([0.2] * 400, -1, shape=(401, 401), format="lil")
        a[0, 400] = 0.2
        self.assertAlmostEqual(validar_matriz(a.tocsr())[1], 0.2, places=9)

    def test_derivadas_recusam_passo_sem_resolucao_ou_denominador_nulo(self):
        for metodo, x, h in (
            (Derivador.central, 1e20, 1e-5),
            (Derivador.segunda, 1e20, 1e-4),
            (Derivador.segunda, 0.0, 1e-200),
        ):
            with self.subTest(metodo=metodo.__name__, x=x, h=h), self.assertRaises(ValueError):
                metodo(lambda z: z * z, x, h)
