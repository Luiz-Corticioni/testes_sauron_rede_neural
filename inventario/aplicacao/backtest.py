"""Leitura de arquivo local e geração reproduzível; sem rede ou escrita no banco."""
import hashlib
import json
from pathlib import Path

from inventario.matematica.backtest import executar

LIMITE_ARQUIVO = 10 * 1024 * 1024


def pares_unicos(pares):
    resultado = {}
    for chave, valor in pares:
        if chave in resultado:
            raise ValueError("JSON contém chave duplicada.")
        resultado[chave] = valor
    return resultado


def rejeitar_nao_finito(valor):
    raise ValueError(f"Número JSON inválido: {valor}.")


def ler_executar(caminho, orcamento, seed=42):
    caminho = Path(caminho)
    with caminho.open("rb") as arquivo:
        conteudo = arquivo.read(LIMITE_ARQUIVO + 1)
    if len(conteudo) > LIMITE_ARQUIVO:
        raise ValueError("Arquivo excede 10 MiB.")
    try:
        dados = json.loads(conteudo.decode("utf-8-sig"), object_pairs_hook=pares_unicos, parse_constant=rejeitar_nao_finito)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as erro:
        raise ValueError("Arquivo deve conter JSON UTF-8 válido.") from erro
    resultado = executar(dados, orcamento, seed)
    resultado["entrada_sha256"] = hashlib.sha256(conteudo).hexdigest()
    pasta = Path(__file__).resolve().parents[1] / "matematica"
    resultado["codigo_sha256"] = {nome: hashlib.sha256((pasta / nome).read_bytes()).hexdigest()
                                    for nome in ("backtest.py", "risco.py", "estabilidade.py")}
    return resultado


def gravar_novo(caminho, resultado):
    with Path(caminho).open("x", encoding="utf-8", newline="\n") as arquivo:
        json.dump(resultado, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
        arquivo.write("\n")
