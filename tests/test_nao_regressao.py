
"""Referência independente FIRST §7 e Apêndice A, sem importar constantes da calculadora."""
from itertools import product
from math import floor
from pathlib import Path
from unittest import TestCase
from inventario.matematica.cvss import CalculadoraCVSS31
from inventario.matematica.euler import FuncaoMatematica


def roundup(valor):
    inteiro = round(valor * 100000)
    if inteiro % 10000 == 0:
        return inteiro / 100000
    return (floor(inteiro / 10000) + 1) / 10


def referencia(m):
    av = {"N":.85,"A":.62,"L":.55,"P":.2}[m["AV"]]
    ac = {"L":.77,"H":.44}[m["AC"]]
    pr = ({"N":.85,"L":.62,"H":.27} if m["S"]=="U" else {"N":.85,"L":.68,"H":.5})[m["PR"]]
    ui = {"N":.85,"R":.62}[m["UI"]]
    c,i,a = ({"N":0,"L":.22,"H":.56}[m[k]] for k in ("C","I","A"))
    iss = 1-(1-c)*(1-i)*(1-a)
    impacto = 6.42*iss if m["S"]=="U" else 7.52*(iss-.029)-3.25*(iss-.02)**15
    if impacto <= 0:
        return 0
    explorabilidade = 8.22*av*ac*pr*ui
    return roundup(min((impacto+explorabilidade)*(1 if m["S"]=="U" else 1.08),10))


class NaoRegressao(TestCase):
    def test_2592_vetores_first(self):
        quantidade = 0
        for valores in product("NALP","LH","NLH","NR","UC","NLH","NLH","NLH"):
            m = dict(zip(("AV","AC","PR","UI","S","C","I","A"), valores))
            vetor = "CVSS:3.1/" + "/".join(f"{k}:{v}" for k,v in m.items())
            with self.subTest(vetor=vetor):
                self.assertEqual(CalculadoraCVSS31.calcular(vetor).score, referencia(m))
            quantidade += 1
        self.assertEqual(quantidade, 2592)

    def test_scores_publicos(self):
        for nome, metricas, esperado in (
            ("Log4Shell","AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",10),
            ("EternalBlue","AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H",8.1),
            ("Dirty COW","AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",7.8),
            ("XSS refletido","AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",6.1)):
            with self.subTest(nome=nome):
                self.assertEqual(CalculadoraCVSS31.calcular("CVSS:3.1/"+metricas).score, esperado)

    def test_payloads_euler(self):
        payloads = ["__import__('os')", "().__class__", "x.__class__", "lambda:x",
            "[x for x in (1,)]", "{x for x in (1,)}", "{x:x for x in (1,)}",
            "(x for x in (1,))", "f'{x}'", "(x:=1)", "x[0]", "open('x')",
            "exec('x')", "eval('1')", "globals()", "locals()", "getattr(x,'x')",
            "1e309", "exp(9999)", "log(0)", "1/0", "sqrt(-1)", "True", "'texto'",
            "10**10**100", "sin()", "sin(x,x)", "sin(x=1)", "x if x else 1",
            "(1,2)", "abs", "x;1", "9"*300, "abs("*30+"x"+")"*30]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                FuncaoMatematica(payload).avaliar(1)

    def test_csp_e_front_sem_innerhtml(self):
        from inventario.seguranca import AutoriaECabecalhosMiddleware
        self.assertNotIn("unsafe-inline", AutoriaECabecalhosMiddleware.CSP)
        self.assertNotIn("unsafe-eval", AutoriaECabecalhosMiddleware.CSP)
        raiz = Path(__file__).resolve().parents[1]
        for p in (raiz/"inventario"/"static").rglob("*.js"):
            self.assertNotIn("innerHTML", p.read_text(encoding="utf-8"), str(p))

    def test_controles_ci(self):
        raiz = Path(__file__).resolve().parents[1]
        texto = (raiz/".github/workflows/ci.yml").read_text(encoding="utf-8")
        for controle in ("ruff", "bandit", "pip-audit", "cyclonedx", "trivy", "manage.py test"):
            self.assertIn(controle, texto)
        self.assertTrue((raiz/".github/dependabot.yml").exists())

