"""Comparação educativa local; não serve para escolher custo em produção."""

import hashlib
import statistics
import time

from argon2 import PasswordHasher


def medir(operacao, repeticoes):
    amostras = []
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        operacao()
        amostras.append(time.perf_counter() - inicio)
    return statistics.median(amostras) * 1000


def main():
    exemplo = b"senha de exemplo sem dados reais"
    argon = PasswordHasher(time_cost=2, memory_cost=102400, parallelism=8)
    sha_ms = medir(lambda: hashlib.sha256(exemplo).digest(), 10000)
    argon_ms = medir(lambda: argon.hash(exemplo), 3)
    print(f"SHA-256 puro: mediana {sha_ms:.6f} ms (10.000 amostras)")
    print(f"Argon2id: mediana {argon_ms:.2f} ms (3 amostras, 100 MiB)")
    print("Tempos locais variam; não substituem teste de carga nem calibragem do servidor.")
    print("SHA-256 puro não é adequado para armazenamento de senhas.")


if __name__ == "__main__":
    main()
