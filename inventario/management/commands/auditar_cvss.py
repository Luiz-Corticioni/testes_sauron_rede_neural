import json
from django.core.management.base import BaseCommand, CommandError
from inventario.aplicacao.auditoria_cvss import auditar_notas
from inventario.models import Vulnerabilidade


class Command(BaseCommand):
    help = "Confere notas CVSS cadastradas sem modificar o inventário; recalcula a base 3.1."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        r = auditar_notas(
            Vulnerabilidade.objects.order_by("pk")
            .values("id", "cve_id", "cvss", "cvss_versao", "cvss_vetor")
            .iterator()
        )
        if options["json"]:
            self.stdout.write(json.dumps(r, ensure_ascii=False, allow_nan=False))
        else:
            self.stdout.write(
                f"Registros: {r['verificados']}; base 3.1 conferida: {r['base31_conferida']}; sem vetor: {r['sem_vetor31']}; outras versões: {r['outras_versoes']}."
            )
            for item in r["divergencias"]:
                self.stdout.write(f"{item['id']}: {item['erro']}")
            self.stdout.write(r["escopo"])
        if not r["ok"]:
            raise CommandError(
                "Há notas ou vetores que precisam de revisão. Nenhum cadastro foi alterado."
            )
