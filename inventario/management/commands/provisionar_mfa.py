"""Provisionamento e recuperação locais, com revogação do dispositivo anterior."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_otp.plugins.otp_totp.models import TOTPDevice
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita
from inventario.models import DispositivoEmail


class Command(BaseCommand):
    help = "Provisiona TOTP. Recuperação exige --substituir --motivo. A URI é segredo."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True)
        parser.add_argument("--substituir", action="store_true")
        parser.add_argument("--motivo", default="")

    def handle(self, *args, **options):
        if options["substituir"] and not options["motivo"].strip():
            raise CommandError("Recuperação exige --motivo para auditoria.")
        with transaction.atomic():
            travar_escrita()
            usuario = get_user_model().objects.select_for_update().filter(username=options["usuario"], is_active=True).first()
            if not usuario:
                raise CommandError("Usuário ativo não encontrado.")
            existentes = TOTPDevice.objects.filter(user=usuario)
            if existentes.exists() and not options["substituir"]:
                raise CommandError("Já existe dispositivo; recuperação exige --substituir --motivo.")
            if options["substituir"]:
                existentes.delete()
                DispositivoEmail.objects.filter(user=usuario).update(confirmed=False, codigo_hash="", nonce="", pode_adotar=False, expira_em=None, email_confirmado_hash="")
            device = TOTPDevice.objects.create(user=usuario, name="Autenticador", confirmed=False)
            registrar_evento("MFA_RECUPERADO" if options["substituir"] else "MFA_PROVISIONADO", "Autenticacao", usuario.username, {"motivo": options["motivo"][:1000]})
        self.stdout.write("SEGREDO: cadastrar em autenticador TOTP e descartar esta saída com segurança.")
        self.stdout.write(device.config_url)
