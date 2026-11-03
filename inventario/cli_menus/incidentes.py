"""Menu de incidentes: adaptador de terminal."""

from __future__ import annotations
from inventario.aplicacao.servicos import salvar_cadastro, remover_cadastro

from django.utils import timezone
from inventario.models import CertificadoDigital, Incidente
from inventario.cli_menus.comum import menu_seguro


class IncidentesMenu:

    @menu_seguro("view_incidente")
    def menu_incidentes(self):
        while True:
            op = self._submenu(
                "INCIDENTES E CERTIFICADOS",
                [
                    ("1", "Listar incidentes"),
                    ("2", "Registrar incidente"),
                    ("3", "Encerrar incidente"),
                    ("4", "Listar certificados"),
                    ("5", "Cadastrar certificado"),
                    ("6", "Remover certificado"),
                ],
            )
            if op == "0":
                return
            {
                "1": self.listar_incidentes,
                "2": self.criar_incidente,
                "3": self.encerrar_incidente,
                "4": self.listar_certificados,
                "5": self.criar_certificado,
                "6": self.remover_certificado,
            }.get(op, lambda: self._falha("Opção inválida."))()
            self._pausa()

    def listar_incidentes(self):
        self._tabela(
            ["ID", "Ativo", "Título", "Gravidade", "Aberto", "Encerrado"],
            [
                [
                    i.id,
                    i.ativo_id,
                    i.titulo,
                    i.gravidade,
                    i.aberto_em.strftime("%Y-%m-%d"),
                    i.encerrado_em.strftime("%Y-%m-%d") if i.encerrado_em else "aberto",
                ]
                for i in Incidente.objects.select_related("ativo")
            ],
            [5, 8, 35, 9, 10, 10],
        )

    def criar_incidente(self):
        if not self._exigir("inventario.add_incidente"):
            return

        i = Incidente(
            ativo=self._ativo(),
            titulo=self._texto("Título"),
            descricao=self._texto("Descrição"),
            gravidade=self._inteiro("Gravidade: 1 baixa, 2 média, 3 alta, 4 crítica", 1, 4),
        )
        i.full_clean()
        salvar_cadastro(i, self.usuario)
        self._ok(f"Incidente {i.pk} registrado.")

    def encerrar_incidente(self):
        if not self._exigir("inventario.change_incidente"):
            return
        self.listar_incidentes()
        i = Incidente.objects.get(pk=self._inteiro("ID"))
        i.encerrado_em = timezone.now()
        salvar_cadastro(i, self.usuario)
        self._ok("Incidente encerrado.")

    def listar_certificados(self):
        self._tabela(
            ["ID", "Ativo", "Domínio", "Emissor", "Expira"],
            [
                [c.id, c.ativo_id, c.dominio, c.emissor, c.expira_em]
                for c in CertificadoDigital.objects.select_related("ativo")
            ],
            [5, 8, 32, 22, 10],
        )

    def criar_certificado(self):
        if not self._exigir("inventario.add_certificadodigital"):
            return

        c = CertificadoDigital(
            ativo=self._ativo(),
            dominio=self._texto("Domínio, ex. portal.exemplo.com"),
            emissor=self._texto("Emissor"),
            expira_em=self._data("Expiração", False),
        )
        c.full_clean()
        salvar_cadastro(c, self.usuario)
        self._ok(f"Certificado {c.pk} cadastrado.")

    def remover_certificado(self):
        if not self._exigir("inventario.delete_certificadodigital"):
            return
        self.listar_certificados()
        c = CertificadoDigital.objects.get(pk=self._inteiro("ID"))
        if self._confirmar("Remover certificado?"):
            _cid = str(c.id)
            remover_cadastro(c, self.usuario)
            self._ok("Certificado removido.")
