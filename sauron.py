#!/usr/bin/env python
"""Entrada única da interface de terminal do Sauron."""

import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sauron_web.settings")

import django

django.setup()

from django.core.management import call_command
from django.conf import settings
from inventario.cli import SauronCLI


def main():
    # Garante que um projeto recém-extraído esteja pronto sem iniciar o servidor web.
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    banco = settings.DATABASES["default"]
    if banco["ENGINE"] == "django.db.backends.sqlite3" and str(banco["NAME"]) != ":memory:":
        Path(banco["NAME"]).parent.mkdir(parents=True, exist_ok=True)
    call_command("migrate", interactive=False, verbosity=0)
    call_command('configurar_grupos', verbosity=0)
    SauronCLI().executar()


if __name__ == "__main__":
    main()

