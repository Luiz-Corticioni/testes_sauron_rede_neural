"""Leitura simples do .env, sem dependência adicional ou execução de código."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def carregar_ambiente(caminho: Path) -> None:
    """Aceita CHAVE=valor e aspas externas; o ambiente do processo tem prioridade."""
    if not caminho.is_file():
        return
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8-sig").splitlines(), 1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        chave, separador, valor = linha.partition("=")
        chave = chave.strip()
        if not separador or not chave.isidentifier():
            raise ImproperlyConfigured(f".env inválido na linha {numero}: use CHAVE=valor.")
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        os.environ.setdefault(chave, valor)


def lista_ambiente(nome: str, padrao: str = "") -> list[str]:
    return [valor.strip() for valor in os.getenv(nome, padrao).split(",") if valor.strip()]


def validar_chave(chave: str, desenvolvimento: bool) -> None:
    """Em produção, recusa ausência, placeholders e chaves sabidamente públicas."""
    padroes = {"dev-only-change-me", "troque-esta-chave-no-env"}
    placeholder = any(texto in chave.lower() for texto in ["gere-", "troque-", "defina-"])
    if not desenvolvimento and (len(chave) < 50 or chave in padroes or placeholder):
        raise ImproperlyConfigured(
            "SAURON_SECRET_KEY deve ser uma chave privada aleatória com pelo menos "
            "50 caracteres quando SAURON_DEBUG=0. Execute "
            "python scripts/preparar_ambiente.py ou configure o .env."
        )
