"""Finaliza a instalação usando o Python do ambiente virtual, no Linux ou Windows."""

import argparse
import os
from pathlib import Path

# Subprocessos executam apenas Python e script local, sem shell.
import subprocess  # nosec B404
import sys

RAIZ = Path(__file__).resolve().parents[1]


def executar(*argumentos):
    subprocess.run([sys.executable, *argumentos], cwd=RAIZ, check=True)  # nosec B603


def preparar(args):
    """Só uma atualização explícita pode aplicar migrações a um banco existente."""
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    banco = settings.DATABASES["default"]
    sqlite = banco["ENGINE"] == "django.db.backends.sqlite3"
    existe = not sqlite or Path(banco["NAME"]).exists()
    if args.verificar:
        if sqlite and not existe:
            raise ValueError("Banco ausente. Execute a instalação antes do diagnóstico.")
        call_command("diagnosticar")
        call_command("verificar_auditoria")
        return
    if existe:
        call_command("verificar_auditoria")
        if not args.atualizar:
            executor = MigrationExecutor(connection)
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                raise ValueError(
                    "Há migrações pendentes. Pare web/agendador e repita com --atualizar; será criado backup cifrado."
                )
            print(
                "Banco existente preservado; sem migrações pendentes. Use --atualizar para reaplicar a preparação."
            )
            call_command("diagnosticar")
            return
        # Se a chave ou o backup falhar, nenhuma migração será aplicada.
        call_command("backup")
    call_command("preparar_servidor")
    call_command("ancorar_auditoria")
    call_command("verificar_auditoria")
    python = r'.\.venv\Scripts\python.exe' if os.name == 'nt' else '.venv-linux/bin/python'
    print(f"Instalação concluída. Primeiro administrador: {python} manage.py cadastrar_administrador --usuario admin")
    print(
        "Configure o Gmail no .env para receber códigos por e-mail; consulte docs/EMAIL_E_MFA.md."
    )
    print(f"Alternativa: {python} manage.py provisionar_mfa --usuario SEU_USUARIO")
    if os.name == 'nt':
        print(f'Web local: & "{python}" scripts/iniciar_web.py')
        print(f'Terminal: & "{python}" sauron.py | Rotinas: & "{python}" scripts/agendador.py')
    else:
        print("Web local: bash iniciar_linux.sh --web | Terminal: bash iniciar_linux.sh --terminal")
        print("Rotinas (outro terminal): bash iniciar_linux.sh --agendador")
    if os.name != 'nt' and not settings.DEBUG and settings.SECURE_SSL_REDIRECT:
        print(
            "Servidor: bash iniciar_linux.sh --servidor; configure proxy HTTPS e CIDRs confiáveis conforme docs/INSTALACAO_LINUX.md."
        )
    else:
        print("HTTP local: abra http://127.0.0.1:8000/entrar/ . Não exponha este servidor à rede.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true")
    parser.add_argument("--atualizar", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--https", action="store_true")
    args = parser.parse_args(argv)
    if args.verificar and not (RAIZ / ".env").is_file():
        parser.error(".env ausente; execute primeiro a instalação.")
    if not args.verificar:
        comando = ["scripts/preparar_ambiente.py", "--host", args.host]
        if args.https:
            comando.append("--https")
        executar(*comando)
    sys.path.insert(0, str(RAIZ))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sauron_web.settings")
    import django

    django.setup()
    preparar(args)
    return 0


if __name__ == "__main__":
    from django.core.management.base import CommandError

    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError, CommandError) as erro:
        # Exceções de processo contêm apenas o argv local, sem segredos.
        print(f"Instalação interrompida: {erro}", file=sys.stderr)
        raise SystemExit(1)
