from django.core.management.base import BaseCommand, CommandError
from inventario.infraestrutura.backup import restaurar_backup


class Command(BaseCommand):
    help = "Decifra e restaura em arquivo SQLite novo; nunca sobrescreve o banco em uso."

    def add_arguments(self,parser):
        parser.add_argument("--arquivo",required=True)
        parser.add_argument("--saida",required=True)

    def handle(self,*args,**options):
        try:
            self.stdout.write(str(restaurar_backup(options["arquivo"],options["saida"])))
        except (ValueError,OSError) as erro:
            raise CommandError(str(erro)) from erro

