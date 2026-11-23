from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


def configurar_grupos():
    permissoes = Permission.objects.filter(content_type__app_label="inventario")
    gerente, _ = Group.objects.get_or_create(name="Gerentes")
    trilhas = [
        "registroauditoria",
        "historicoincidencia",
        "snapshotrisco",
        "anticorpo",
        "tolerancia",
        "sugestaoimune",
        "revisaoeventohoneypot",
    ]
    negocio = permissoes.exclude(content_type__model__in=["travadominio", "alerta", *trilhas])
    leitura_trilhas = permissoes.filter(
        content_type__model__in=trilhas,
        codename__startswith="view_",
    )
    alertas = permissoes.filter(codename__in=["view_alerta", "reconhecer_alerta"])
    decisoes = permissoes.filter(codename="decidir_sugestao_imune")
    gerente.permissions.set(negocio | leitura_trilhas | alertas | decisoes | permissoes.filter(codename="add_revisaoeventohoneypot"))
    auditor, _ = Group.objects.get_or_create(name="Auditores")
    auditor.permissions.set(
        permissoes.filter(codename__startswith="view_").exclude(
            content_type__model__in=["travadominio", "sensorhoneypot", "eventohoneypot", "revisaoeventohoneypot", "politicaretencaohoneypot", "cenariofinanceiro", "perdafinanceira", "observacaoimportada", "revisaoobservacao"],
        )
    )
    operador, _ = Group.objects.get_or_create(name="Operadores")
    leitura = permissoes.filter(codename__startswith="view_").exclude(
        content_type__model__in=["registroauditoria", "travadominio", "sensorhoneypot", "eventohoneypot", "revisaoeventohoneypot", "politicaretencaohoneypot", "cenariofinanceiro", "perdafinanceira", "observacaoimportada", "revisaoobservacao"],
    )
    operador.permissions.set(
        leitura
        | permissoes.filter(
            codename__in=["change_incidencia", "reconhecer_alerta", "decidir_sugestao_imune", "add_revisaocobertura"]
        )
    )


class Command(BaseCommand):
    help = "Configura as permissões oficiais de Operadores, Gerentes e Auditores."

    def handle(self, *args, **options):
        configurar_grupos()
        self.stdout.write("Grupos configurados: Operadores, Gerentes e Auditores.")
