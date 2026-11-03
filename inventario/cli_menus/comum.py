"""Cores opcionais e recuperação de erros no próprio submenu."""

from functools import wraps
import os
import sys
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.db.models import ProtectedError
from inventario.aplicacao.autorizacao import sessao_interativa
from inventario.infraestrutura.cve_client import IntegracaoCVEError

ERROS_MENU = (
    ValidationError,
    ValueError,
    IntegrityError,
    ProtectedError,
    PermissionDenied,
    ObjectDoesNotExist,
    OSError,
    IntegracaoCVEError,
    CommandError,
)


class Cor:
    ATIVA = sys.stdout.isatty() and not os.getenv("NO_COLOR")

    @classmethod
    def usar(cls, codigo, texto):
        return f"\033[{codigo}m{texto}\033[0m" if cls.ATIVA else str(texto)

    titulo = classmethod(lambda cls, t: cls.usar("1;38;5;203", t))
    destaque = classmethod(lambda cls, t: cls.usar("38;5;209", t))
    sucesso = classmethod(lambda cls, t: cls.usar("38;5;78", t))
    aviso = classmethod(lambda cls, t: cls.usar("38;5;221", t))
    erro = classmethod(lambda cls, t: cls.usar("38;5;203", t))
    fraco = classmethod(lambda cls, t: cls.usar("38;5;245", t))


def menu_seguro(permissao=""):
    def decorar(funcao):
        @wraps(funcao)
        def executar(cli, *args, **kwargs):
            if permissao and not cli._exigir("inventario." + permissao):
                return
            while True:
                try:
                    with sessao_interativa(cli):
                        return funcao(cli, *args, **kwargs)
                except ERROS_MENU as erro:
                    cli._falha(erro)
                    cli._pausa()

        return executar

    return decorar
