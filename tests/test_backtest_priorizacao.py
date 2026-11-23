from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase

from django.core.management import call_command
from inventario.aplicacao.backtest import gravar_novo, ler_executar
from inventario.matematica.backtest import executar, intervalo_wilson

FIXTURE = Path(__file__).parent / "fixtures" / "backtest_sintetico.json"


class Backtest(TestCase):
    def setUp(self):
        self.dados = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_compara_estrategias_no_mesmo_universo_e_orcamento(self):
        resultado = executar(self.dados, 2, 42)
        self.assertEqual(resultado["universo_comparavel"], 5)
        self.assertEqual(resultado["eventos_observados"], 3)
        self.assertEqual(len(resultado["excluidas"]), 1)
        self.assertEqual(set(resultado["resultados"]), {"cvss", "cvss_kev", "epss", "ssvc", "sauron"})
        for item in resultado["resultados"].values():
            self.assertEqual(item["esforco_cves"], 2)
            self.assertEqual(item["cobertura"], item["observadas_selecionadas"] / 3)
            self.assertEqual(item["eficiencia"], item["observadas_selecionadas"] / 2)
            self.assertLessEqual(item["cobertura_ic95_wilson"][0], item["cobertura"])
            self.assertGreaterEqual(item["cobertura_ic95_wilson"][1], item["cobertura"])
        self.assertEqual(resultado["resultados"]["sauron"]["selecionadas"][0], "CVE-2025-0003")
        self.assertEqual(resultado, executar(self.dados, 2, 42))

    def test_desfechos_nao_alteram_as_prioridades(self):
        original = executar(self.dados, 2)
        dados = deepcopy(self.dados)
        dados["eventos"] = [{"cve": "CVE-2025-0002", "observado_em": "2025-01-18",
                            "disponivel_em": "2025-01-19", "fonte": "Evento sintético"}]
        alterado = executar(dados, 2)
        for estrategia in original["resultados"]:
            self.assertEqual(original["resultados"][estrategia]["selecionadas"], alterado["resultados"][estrategia]["selecionadas"])

    def test_sauron_reproduz_a_fila_do_modelo_operacional(self):
        import hashlib
        from inventario.dominio.vulnerabilidades import Dependencia, Incidencia, Vulnerabilidade
        from inventario.matematica.risco import ModeloRisco

        linhas = self.dados["vulnerabilidades"][:5]
        linhas = sorted(linhas, key=lambda item: hashlib.sha256(f"42|{item['cve']}".encode()).hexdigest())
        vs = [Vulnerabilidade(item["id"], "Snapshot histórico", "BACKTEST", item["cvss"]["valor"], cve_id=item["cve"]) for item in linhas]
        mapa = {v.cve_id: v.id for v in vs}
        ocorrencias = [Incidencia(i["id"], i["ativo"], mapa[i["cve"]], status=i["status"])
                       for i in self.dados["inventario"]["incidencias"] if i["cve"] in mapa]
        ambientais = {item["id"]: item["cvss_ambiental"]["valor"] for item in linhas}
        modelo = ModeloRisco(["A", "B"], vs, ocorrencias, [Dependencia("B", "A", .3)],
                             {"A": 1, "B": 1.2}, {mapa["CVE-2025-0002"]}, scores_ambientais=ambientais)
        esperado = [item["cve_id"] for item in modelo.calcular(perfil="operacional", kappa=.3).prioridade_correcao[:2]]
        self.assertEqual(executar(self.dados, 2, 42)["resultados"]["sauron"]["selecionadas"], esperado)

    def test_conhecimento_futuro_nao_influencia_o_corte(self):
        dados = deepcopy(self.dados)
        dados["vulnerabilidades"][0]["epss"]["disponivel_em"] = "2025-01-11"
        dados["vulnerabilidades"][0]["epss"]["valor"] = 1.0
        r = executar(dados, 2)
        self.assertEqual(r["universo_comparavel"], 4)
        self.assertTrue(any(x["cve"] == "CVE-2025-0001" for x in r["excluidas"]))
        for estrategia in r["resultados"].values():
            self.assertNotIn("CVE-2025-0001", estrategia["selecionadas"])
        antes = executar(self.dados, 2)
        dados = deepcopy(self.dados)
        dados["kev"]["cves"].append({"cve": "CVE-2025-0001", "adicionada_em": "2025-01-20"})
        depois = executar(dados, 2)
        self.assertEqual(antes["resultados"], depois["resultados"])

    def test_ssvc_vencido_ou_contexto_invalido_e_excluido(self):
        for campo, valor in (("revisar_em", "2025-01-10"), ("contexto_valido", False)):
            dados = deepcopy(self.dados)
            dados["vulnerabilidades"][0]["ssvc"][campo] = valor
            self.assertEqual(executar(dados, 2)["universo_comparavel"], 4)
        dados = deepcopy(self.dados)
        dados["vulnerabilidades"][0].pop("cvss_ambiental")
        self.assertEqual(executar(dados, 2)["universo_comparavel"], 4)

    def test_sem_eventos_nao_inventa_cobertura_e_recusa_dados_invalidos(self):
        dados = deepcopy(self.dados)
        dados["eventos"] = []
        r = executar(dados, 2)
        self.assertIsNone(r["resultados"]["cvss"]["cobertura"])
        self.assertIsNone(r["resultados"]["cvss"]["cobertura_ic95_wilson"])
        self.assertIsNone(intervalo_wilson(0, 0))
        for alteracao in ("futuro", "kev", "evento", "janela"):
            dados = deepcopy(self.dados)
            if alteracao == "futuro":
                dados["inventario"]["disponivel_em"] = "2025-01-11"
            elif alteracao == "kev":
                dados["kev"]["completo"] = False
            elif alteracao == "evento":
                dados["eventos"][0]["disponivel_em"] = "2025-01-01"
            else:
                dados["eventos_metadados"]["cobertura_ate"] = "2025-02-08"
            with self.subTest(alteracao=alteracao), self.assertRaises(ValueError):
                executar(dados, 2)

    def test_script_comando_e_saida_sem_sobrescrita(self):
        esperado = ler_executar(FIXTURE, 2, 42)
        saida = io.StringIO()
        call_command("backtest_priorizacao", str(FIXTURE), orcamento=2, seed=42, stdout=saida)
        self.assertEqual(json.loads(saida.getvalue()), esperado)
        raiz = FIXTURE.parents[2]
        processo = subprocess.run([sys.executable, str(raiz / "scripts" / "backtest_priorizacao.py"), str(FIXTURE), "--orcamento", "2"],
                                  cwd=raiz, check=True, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(json.loads(processo.stdout), esperado)
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "resultado.json"
            gravar_novo(caminho, esperado)
            with self.assertRaises(FileExistsError):
                gravar_novo(caminho, esperado)
            self.assertEqual(json.loads(caminho.read_text(encoding="utf-8")), esperado)

    def test_arquivo_json_ambiguo_e_rejeitado(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "entrada.json"
            caminho.write_text('{"formato": "x", "formato": "y"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicada"):
                ler_executar(caminho, 1)

    def test_saida_no_terminal_com_codigo_de_pagina_limitado(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "entrada.json"
            dados = deepcopy(self.dados)
            dados["fontes"]["inventario"] = "Fixture de teste 💻"
            caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
            raiz = FIXTURE.parents[2]
            ambiente = {**os.environ, "PYTHONIOENCODING": "cp1252"}
            processo = subprocess.run([sys.executable, str(raiz / "scripts" / "backtest_priorizacao.py"),
                                      str(caminho), "--orcamento", "2"], cwd=raiz, env=ambiente,
                                     check=True, capture_output=True, text=True, encoding="ascii")
            self.assertEqual(json.loads(processo.stdout)["fontes"]["inventario"], "Fixture de teste 💻")
