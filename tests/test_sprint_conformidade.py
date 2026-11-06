"""Contratos didáticos e exemplo numérico independente para o Trabalho 2."""

import json
import io
import random
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase
from django.core.management import call_command

from inventario.aplicacao.catalogo_educacional import CatalogoEducacional, por_tipo
from inventario.dominio.algoritmos_sprint import ArvoreBinaria, TabelaHash, dfs_ciclos, merge_sort, quick_sort
from inventario.dominio.equipamentos import Notebook, Servidor
from inventario.dominio.vulnerabilidades import Dependencia, Incidencia, Vulnerabilidade
from inventario.infraestrutura.repositorio_json import RepositorioJSON, RepositorioMemoria
from inventario.matematica.risco import ModeloRisco
from scripts import prova_24h
from .base import BancoTeste


class TesteSprint(SimpleTestCase):
    def test_estruturas_e_ordenacao(self):
        tabela = TabelaHash(1)  # Força colisão.
        tabela.inserir("a", 1)
        tabela.inserir("b", 2)
        tabela.inserir("a", 3)
        self.assertEqual((tabela.buscar("a"), tabela.buscar("b")), (3, 2))
        with self.assertRaises(KeyError):
            tabela.buscar("ausente")
        arvore = ArvoreBinaria()
        for chave in (4, 2, 6, 1, 3, 5, 7, 4):
            arvore.inserir(chave)
        self.assertEqual(arvore.altura(), 3)
        self.assertTrue(arvore.buscar(3))
        self.assertFalse(arvore.buscar(8))
        self.assertEqual(arvore.percurso(), [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(arvore.percurso("pre"), [4, 2, 1, 3, 6, 5, 7])
        self.assertEqual(arvore.percurso("pos"), [1, 3, 2, 5, 7, 6, 4])
        self.assertEqual(arvore.percurso("nivel"), [4, 2, 6, 1, 3, 5, 7])
        dados = [(2, "a"), (1, "b"), (2, "c"), (0, "d")]
        self.assertEqual(merge_sort(dados, chave=lambda x: x[0]), [(0, "d"), (1, "b"), (2, "a"), (2, "c")])
        self.assertEqual([i[0] for i in quick_sort(dados, chave=lambda x: x[0])], [0, 1, 2, 2])
        self.assertEqual(quick_sort(list(range(40)), randomizador=random.Random(42)), list(range(40)))
        self.assertEqual(dfs_ciclos({"A": ["B"], "B": ["C"], "C": ["B"]}, "A"), (["B", "C"], True))
        self.assertEqual(dfs_ciclos({"A": ["B"], "B": []}, "A"), (["B"], False))

    def test_repositorios_e_factory(self):
        with TemporaryDirectory() as pasta:
            for repo in (RepositorioMemoria(), RepositorioJSON(Path(pasta) / "ativos.json")):
                with self.subTest(repositorio=type(repo).__name__):
                    catalogo = CatalogoEducacional(repo)
                    catalogo.cadastrar(Servidor(id="1D00001", nome="Zeta", hostname="s", fabricante="Dell"))
                    catalogo.cadastrar(Notebook(id="2D00002", nome="Alfa", hostname="n", fabricante="Dell"))
                    self.assertEqual([type(a) for a in catalogo.listar()], [Notebook, Servidor])
                    self.assertEqual([type(a) for a in catalogo.listar(por_tipo)], [Servidor, Notebook])
                    with self.assertRaises(ValueError):
                        catalogo.cadastrar(catalogo.listar()[0])
                    dados = repo.listar()
                    dados[0]["nome"] = "alteração não persistida"
                    self.assertEqual(repo.listar()[0]["nome"], "Zeta")
                    with self.assertRaises(ValueError):
                        repo.salvar_todos(["não é objeto"])
            self.assertIsInstance(json.loads((Path(pasta) / "ativos.json").read_text(encoding="utf-8")), list)

    def test_equacao_com_solucao_calculada_a_mao(self):
        vulnerabilidade = Vulnerabilidade("VUL-RCE-0001", "Exemplo", "RCE", 8.0)
        modelo = ModeloRisco(
            ["A", "B", "C"], [vulnerabilidade],
            [Incidencia("I1", "A", vulnerabilidade.id)],
            [Dependencia("B", "A", 0.5), Dependencia("C", "B", 0.25),
             Dependencia("C", "A", 0.1)],
        )
        resultado = modelo.calcular(perfil="puro")
        self.assertEqual(resultado.risco_proprio, [8.0, 0.0, 0.0])
        for obtido, esperado in zip(resultado.risco_efetivo, [8.0, 4.0, 1.8]):
            self.assertAlmostEqual(obtido, esperado)
        self.assertLess(resultado.residuo_absoluto, 1e-10)

    def test_monitor_descobre_servico_compose(self):
        with TemporaryDirectory() as pasta:
            saida = str(Path(pasta) / "evidencia.log")
            with patch("sys.argv", ["prova_24h", "--horas", "0.000000001", "--saida", saida]), \
                 patch.object(prova_24h, "docker", return_value="container-real") as comando, \
                 patch.object(prova_24h, "coletar", return_value={"ts": "agora", "status": "running", "health": "healthy"}) as coletar, \
                 patch.object(prova_24h, "gravar"), \
                 patch.object(prova_24h.time, "monotonic", side_effect=[0, 1, 1]):
                prova_24h.main()
            comando.assert_called_once_with("compose", "ps", "-q", "sauron")
            coletar.assert_called_once_with("container-real")


class TesteRelatorioSprint(BancoTeste):
    def test_ranking_e_alcance_sobre_banco_real(self):
        saida = io.StringIO()
        call_command("relatorio_sprint", stdout=saida)
        relatorio = json.loads(saida.getvalue())
        self.assertEqual([item["id"] for item in relatorio["ranking"]], [self.a.pk, self.b.pk])
        self.assertEqual(relatorio["alcance_estrutural"][0]["alcancaveis"], [self.b.pk])

    def test_sql_usa_dados_e_parametro(self):
        saida = io.StringIO()
        call_command("relatorio_sql_sprint", limiar=9, stdout=saida)
        registros = json.loads(saida.getvalue())
        self.assertEqual([(r["id"], r["soma_cvss"]) for r in registros], [(self.a.pk, 10)])
        saida = io.StringIO()
        call_command("relatorio_sql_sprint", limiar=11, stdout=saida)
        self.assertEqual(json.loads(saida.getvalue()), [])
