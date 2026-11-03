from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from inventario.infraestrutura.cve_client import CisaKevClient, IntegracaoCVEError, NvdClient
from inventario.aplicacao.risco import caminho_cache_kev


class Command(BaseCommand):
    help = "Atualiza o catálogo CISA KEV ou os CVEs NVD especificados em --nvd."

    def add_arguments(self, parser):
        parser.add_argument("--forcar", action="store_true")
        parser.add_argument("--nvd", nargs="+", metavar="CVE")

    def handle(self, *args, **options):
        try:
            if options["nvd"]:
                cliente = NvdClient(settings.NVD_API_KEY, settings.DATA_DIR / "cache" / "nvd")
                for identificador in options["nvd"]:
                    dados = cliente.atualizar(identificador, forcar=options["forcar"])
                    self.stdout.write(self.style.SUCCESS(f"NVD atualizado: {dados['id']}"))
                return
            dados = CisaKevClient(caminho_cache_kev()).atualizar(forcar=options["forcar"])
        except (IntegracaoCVEError, ValueError) as erro:
            raise CommandError(str(erro)) from erro
        quantidade = len(dados.get("vulnerabilities", []))
        from inventario.aplicacao.operacao import enriquecer_kev

        alteradas = enriquecer_kev(dados)
        self.stdout.write(f"Vulnerabilidades enriquecidas: {alteradas}.")
        self.stdout.write(self.style.SUCCESS(f"KEV atualizado: {quantidade} registros."))
