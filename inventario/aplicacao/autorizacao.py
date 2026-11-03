"""Autorizações usam uma instância atual do banco, sem reutilizar cache de permissões."""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from contextlib import contextmanager
from contextvars import ContextVar

SESSAO_CLI = ContextVar("sauron_sessao_cli", default=None)


@contextmanager
def sessao_interativa(cli):
    token = SESSAO_CLI.set(cli)
    try:
        yield
    finally:
        SESSAO_CLI.reset(token)


def exigir(usuario, *permissoes):
    cli = SESSAO_CLI.get()
    if cli and any(not p.split(".", 1)[-1].startswith("view_") for p in permissoes):
        # Não solicita senha/MFA enquanto o serviço mantém uma transação aberta.
        pk = getattr(usuario, "pk", None)
        if (getattr(cli.usuario, "pk", None) != pk
                or not all(cli._exigir(p, interativo=False) for p in permissoes)
                or getattr(cli.usuario, "pk", None) != pk):
            raise PermissionDenied("A sessão ou autorização mudou durante o preenchimento. Volte ao menu, autentique-se e refaça a operação.")
    atual = None
    if getattr(usuario, "is_authenticated", False):
        atual = get_user_model().objects.filter(pk=usuario.pk, is_active=True).first()
    if atual is None or not atual.has_perms(permissoes):
        raise PermissionDenied("Sua conta não tem autorização atual para esta operação. Verifique suas permissões com o administrador.")
    return atual
