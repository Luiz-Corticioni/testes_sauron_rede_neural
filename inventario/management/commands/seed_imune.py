"""Cenário exclusivamente demonstrativo, não aplicado a bases preenchidas."""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import Ativo, Incidencia


class Command(BaseCommand):
    help = "Cria, só em banco vazio, dois servidores semelhantes para demonstração imune."

    @transaction.atomic
    def handle(self, *args, **options):
        if Ativo.objects.exists():
            self.stdout.write("Seed imune ignorado: o banco já contém ativos.")
            return
        call_command("seed_demo", stdout=self.stdout)
        origem = Ativo.objects.get(pk="1D00001")
        alvo = Ativo.objects.create(
            tipo="1",
            nome="Servidor semelhante (SIMULADO)",
            fabricante="Dell",
            modelo="PowerEdge",
            sistema_operacional="Linux",
            versao="9",
            responsavel="Equipe de demonstração",
            sala=origem.sala,
            exposto_internet=True,
        )
        # A demonstração começa com uma hipótese, confirmada pelo usuário no menu 3.
        for i in Incidencia.objects.all():
            i.status = "SUGERIDA"
            i.save(update_fields=["status"])
        self.stdout.write(
            f"Demo SIMULADO: confirme INC-0002 no menu 3; alvo {alvo.pk}; "
            "execute o ciclo no menu 13. Não é evidência de falha real."
        )
