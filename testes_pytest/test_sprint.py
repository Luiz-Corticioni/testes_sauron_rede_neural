"""Testes pytest independentes do banco; a suíte Django continua cobrindo a integração."""

import pytest

from inventario.aplicacao.catalogo_educacional import CatalogoEducacional
from inventario.dominio.equipamentos import Notebook, Servidor
from inventario.dominio.vulnerabilidades import Dependencia, Incidencia, Vulnerabilidade
from inventario.infraestrutura.repositorio_json import RepositorioJSON, RepositorioMemoria
from inventario.matematica.risco import ModeloRisco


@pytest.fixture(params=["memoria", "json"])
def repositorio(request, tmp_path):
    return RepositorioJSON(tmp_path / "ativos.json") if request.param == "json" else RepositorioMemoria()


def test_persistencia_factory_e_duplicata(repositorio):
    catalogo = CatalogoEducacional(repositorio)
    catalogo.cadastrar(Servidor(id="1D00001", nome="Servidor", hostname="srv", fabricante="Dell"))
    catalogo.cadastrar(Notebook(id="2D00001", nome="Notebook", hostname="nb", fabricante="Dell"))
    assert {type(a) for a in catalogo.listar()} == {Notebook, Servidor}
    with pytest.raises(ValueError):
        catalogo.cadastrar(catalogo.listar()[0])


@pytest.mark.parametrize("cvss,esperado", [(0, [0, 0]), (8, [8, 4]), (10, [10, 5])])
def test_risco_puro(cvss, esperado):
    vulnerabilidade = Vulnerabilidade("VUL-RCE-0001", "Exemplo", "RCE", cvss)
    resultado = ModeloRisco(["A", "B"], [vulnerabilidade],
        [Incidencia("I", "A", vulnerabilidade.id)], [Dependencia("B", "A", 0.5)]).calcular()
    assert resultado.risco_efetivo == pytest.approx(esperado)


def test_valida_json_corrompido(tmp_path):
    caminho = tmp_path / "ativos.json"
    caminho.write_text('[1]', encoding="utf-8")
    with pytest.raises(ValueError):
        RepositorioJSON(caminho).listar()
    caminho.write_text('[{"valor": NaN}]', encoding="utf-8")
    with pytest.raises(ValueError):
        RepositorioJSON(caminho).listar()
