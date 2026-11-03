import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.management.base import BaseCommand, CommandError

from inventario.infraestrutura.importacao import MAX_BYTES, importar_csv


class Command(BaseCommand):
    help = "Importa novos ativos; dry-run por padrão. --aplicar grava após validar todo o lote."

    def add_arguments(self, parser):
        parser.add_argument("arquivo")
        parser.add_argument("--usuario", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--aplicar", action="store_true")

    def handle(self, *args, **options):
        if options["dry_run"] and options["aplicar"]:
            raise CommandError("Escolha --dry-run ou --aplicar.")
        try:
            arquivo = Path(options["arquivo"])
            if arquivo.stat().st_size > MAX_BYTES:
                raise ValueError("CSV excede 1 MB.")
            usuario = get_user_model().objects.get(username=options["usuario"])
            resultado = importar_csv(
                arquivo.read_text(encoding="utf-8-sig"), usuario, dry_run=not options["aplicar"]
            )
        except (OSError, ValueError, PermissionDenied, get_user_model().DoesNotExist) as erro:
            raise CommandError(str(erro)) from erro
        self.stdout.write(json.dumps(resultado, ensure_ascii=False, indent=2))
        if resultado["erros"]:
            raise CommandError("Lote recusado: nenhum ativo foi importado.")
