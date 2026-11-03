from datetime import timedelta
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.management.commands.configurar_grupos import configurar_grupos
from django.utils import timezone

from inventario.models import (
    Ativo,
    CertificadoDigital,
    Dependencia,
    Incidencia,
    Incidente,
    Sala,
    Vulnerabilidade,
)


class Command(BaseCommand):
    help = "Cria o cenário demonstrativo web → app → banco → switch."

    def add_arguments(self, parser):
        parser.add_argument(
            "--operacional",
            action="store_true",
            help="Inclui prazos vencidos, aceite fictício e série simulada.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        configurar_grupos()
        # Um banco parcialmente preenchido pertence ao usuário e não recebe o demo.
        modelos = (Sala, Ativo, Vulnerabilidade, Incidencia, Dependencia)
        if any(modelo.objects.exists() for modelo in modelos):
            self.stdout.write("Seed ignorado: o banco já contém dados do inventário.")
            return
        salas = {
            "SALA-TI-001": (
                "Tecnologia da Informação",
                "TI",
                None,
                ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            ),
            "SALA-DC-001": ("Datacenter", "DATACENTER", "SALA-TI-001", ["1", "4", "5", "7", "8"]),
            "SALA-TI-APP": ("Subsetor de Aplicações", "TI", "SALA-TI-001", ["1", "7", "8", "9"]),
            "SALA-ADM-01": ("Administrativo", "ADMINISTRATIVO", None, ["2", "3", "6"]),
        }
        for codigo, (nome, categoria, pai, tipos) in salas.items():
            Sala.objects.get_or_create(
                id=codigo,
                defaults={
                    "nome": nome,
                    "categoria": categoria,
                    "parent_id": pai,
                    "tipos_permitidos": tipos,
                },
            )

        ativos = [
            (
                "7N00001",
                "7",
                "Portal Web",
                "SAU-WEB-NGIN-00001",
                "Nginx",
                "Proxy",
                "SALA-TI-APP",
                "10.0.0.10",
                "Ubuntu",
                "24.04",
                "Equipe Web",
            ),
            (
                "1D00001",
                "1",
                "Servidor de Aplicação",
                "SAU-SRV-DELL-00001",
                "Dell",
                "PowerEdge",
                "SALA-DC-001",
                "10.0.0.20",
                "Linux",
                "9",
                "Equipe Backend",
            ),
            (
                "8P00001",
                "8",
                "Banco Principal",
                "SAU-DBS-POST-00001",
                "PostgreSQL",
                "Cluster",
                "SALA-DC-001",
                "10.0.0.30",
                "PostgreSQL",
                "16",
                "DBA",
            ),
            (
                "4H00001",
                "4",
                "Switch Core",
                "SAU-SWT-HUAW-00001",
                "Huawei",
                "S5735",
                "SALA-DC-001",
                "10.0.0.40",
                "VRP",
                "V200",
                "Redes",
            ),
        ]
        objetos = {}
        for identificador, tipo, nome, hostname, fab, modelo, sala, ip, so, versao, resp in ativos:
            obj, _ = Ativo.objects.get_or_create(
                id=identificador,
                defaults={
                    "tipo": tipo,
                    "nome": nome,
                    "hostname": hostname,
                    "fabricante": fab,
                    "modelo": modelo,
                    "sala_id": sala,
                    "ip": ip,
                    "sistema_operacional": so,
                    "versao": versao,
                    "responsavel": resp,
                    "criticidade": 4 if tipo in {"7", "8"} else 3,
                    "fim_suporte": timezone.localdate()
                    + timedelta(days=60 if tipo == "4" else 500),
                },
            )
            objetos[identificador] = obj

        vulns = [
            (
                "VUL-RCE-0001",
                None,  # Nota do exercício; não atribuir este 9.8 a uma CVE real.
                "Execução remota de código",
                "RCE",
                9.8,
                "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            ),
            (
                "VUL-AUTH-0001",
                None,
                "Autenticação insuficiente",
                "AUTH",
                7.5,
                "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
            ),
            (
                "VUL-CFG-0001",
                None,
                "Configuração insegura com impacto crítico",
                "CFG",
                9.8,
                "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            ),
            (
                "VUL-PRIV-0001",
                None,
                "Escalação de privilégio",
                "PRIV",
                7.5,
                "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:N",
            ),
            ("VUL-DOS-0001", None, "Negação de serviço compartilhada", "DOS", 5.0, ""),
        ]
        for vid, cve, desc, cat, score, vetor in vulns:
            Vulnerabilidade.objects.get_or_create(
                id=vid,
                defaults={
                    "cve_id": cve,
                    "descricao": desc,
                    "categoria": cat,
                    "cvss": score,
                    "cvss_vetor": vetor,
                    "fonte": "Cenário demonstrativo",
                },
            )

        vinculos = [
            ("INC-0001", "7N00001", "VUL-RCE-0001"),
            ("INC-0002", "1D00001", "VUL-AUTH-0001"),
            ("INC-0003", "1D00001", "VUL-CFG-0001"),
            ("INC-0004", "8P00001", "VUL-PRIV-0001"),
            ("INC-0005", "8P00001", "VUL-DOS-0001"),
            ("INC-0006", "4H00001", "VUL-DOS-0001"),
        ]
        for iid, aid, vid in vinculos:
            Incidencia.objects.get_or_create(
                id=iid, defaults={"ativo_id": aid, "vulnerabilidade_id": vid, "status": "ABERTA"}
            )

        for dependente, fornecedor, peso in [
            ("7N00001", "1D00001", 0.5),
            ("1D00001", "8P00001", 0.6),
            ("8P00001", "4H00001", 0.3),
        ]:
            Dependencia.objects.get_or_create(
                dependente_id=dependente,
                fornecedor_id=fornecedor,
                defaults={"peso": peso, "descricao": "Propagação de risco do cenário manual"},
            )

        CertificadoDigital.objects.get_or_create(
            ativo_id="7N00001",
            dominio="sauron.exemplo.local",
            defaults={
                "emissor": "CA Acadêmica",
                "expira_em": timezone.localdate() + timedelta(days=30),
            },
        )
        Incidente.objects.get_or_create(
            ativo_id="1D00001",
            titulo="Tentativas de acesso anômalas",
            defaults={"descricao": "Incidente demonstrativo vinculado ao ativo.", "gravidade": 2},
        )

        usuario = os.getenv("SAURON_ADMIN_USER")
        senha = os.getenv("SAURON_ADMIN_PASSWORD")
        if usuario and senha:
            admin, criado = User.objects.get_or_create(
                username=usuario, defaults={"is_staff": True, "is_superuser": True}
            )
            if criado:
                admin.set_password(senha)
                admin.save()
                self.stdout.write(
                    self.style.WARNING("Administrador criado a partir das variáveis de ambiente.")
                )

        if options["operacional"]:
            from inventario.aplicacao.demo_operacional import preparar_demo_operacional

            preparar_demo_operacional()
            self.stdout.write(
                self.style.WARNING(
                    "Demo operacional: aceite e série histórica são SIMULADOS, não evidência real."
                )
            )
        self.stdout.write(self.style.SUCCESS("Cenário criado: b=[9.8, 17.3, 12.5, 5.0]."))
