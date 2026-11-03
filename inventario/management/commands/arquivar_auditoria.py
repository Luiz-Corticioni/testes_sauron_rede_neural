from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from inventario.infraestrutura.ancoras import ancorar
from inventario.infraestrutura.auditoria import dados_objeto, verificar_cadeia, registrar_evento
from inventario.infraestrutura.arquivos import salvar_json_atomico
from inventario.models import RegistroAuditoria


class Command(BaseCommand):
    help = "Exporta e ancora segmento preservando os elos originais e a trilha online."

    def add_arguments(self, parser):
        parser.add_argument("--ate-id", type=int, required=True)
        parser.add_argument("--saida", required=True)

    def handle(self, *args, **options):
        if not verificar_cadeia()["integra"]:
            raise CommandError("Cadeia inválida; arquivamento recusado.")
        registros=RegistroAuditoria.objects.filter(pk__lte=options["ate_id"]).order_by("pk")
        salvar_json_atomico(Path(options["saida"]), [dados_objeto(r) for r in registros.iterator()])
        ancora=ancorar(options["ate_id"])
        registrar_evento("ARQUIVAR_AUDITORIA","Auditoria",options["ate_id"],
                        {"saida":options["saida"], "ancora":ancora})
        self.stdout.write("Segmento exportado e ancorado; originais preservados.")

