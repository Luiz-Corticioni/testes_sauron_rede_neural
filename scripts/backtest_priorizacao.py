"""Execute o backtest localmente, sem consultar redes ou banco de dados."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inventario.aplicacao.backtest import gravar_novo, ler_executar  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Compara estratégias com snapshots históricos locais.")
    parser.add_argument("entrada", help="JSON local no formato sauron.backtest/1")
    parser.add_argument("--orcamento", type=int, required=True, help="Quantidade de CVEs hipoteticamente corrigidas")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--saida", help="Arquivo JSON novo; não sobrescreve arquivos existentes")
    args = parser.parse_args()
    try:
        resultado = ler_executar(args.entrada, args.orcamento, args.seed)
        if args.saida:
            gravar_novo(args.saida, resultado)
        else:
            print(json.dumps(resultado, ensure_ascii=True, indent=2, allow_nan=False))
    except (ValueError, OSError, RecursionError, TypeError) as erro:
        parser.error(str(erro))


if __name__ == "__main__":
    main()
