"""Menu de dependencias: adaptador de terminal."""

from __future__ import annotations
from inventario.aplicacao.servicos import salvar_cadastro, remover_cadastro

from inventario.models import Dependencia
from inventario.cli_menus.comum import menu_seguro


class DependenciasMenu:

    @menu_seguro("view_dependencia")
    def menu_dependencias(self):
        while True:
            op = self._submenu(
                "DEPENDÊNCIAS",
                [("1", "Listar"), ("2", "Cadastrar"), ("3", "Atualizar peso"), ("4", "Remover"),
                 ("5", "Consultar dependentes diretos e indiretos")],
            )
            if op == "0":
                return
            {
                "1": self.listar_dependencias,
                "2": self.criar_dependencia,
                "3": self.atualizar_dependencia,
                "4": self.remover_dependencia,
                "5": self.impacto_dependencias,
            }.get(op, lambda: self._falha("Opção inválida."))()
            self._pausa()

    def listar_dependencias(self):
        self._tabela(
            ["ID", "Dependente i", "Fornecedor j", "Peso Aij", "Descrição"],
            [
                [d.id, d.dependente.hostname, d.fornecedor.hostname, d.peso, d.descricao]
                for d in Dependencia.objects.select_related("dependente", "fornecedor")
            ],
            [5, 24, 24, 9, 28],
        )

    def impacto_dependencias(self):
        from inventario.aplicacao.impacto import analisar_impacto

        if not self._exigir("inventario.view_ativo"):
            return
        r = analisar_impacto(self._texto("Fornecedor: número, código ou hostname"), self.usuario)
        self.saida(f"{r['ativo']['hostname']} alcança {r['total_dependentes']} outro(s) ativo(s).")
        self.saida(r["aviso"])
        for item in r["itens"]:
            self.saida(f"  #{item['id_numerico']} {item['hostname']} — {item['saltos']} salto(s)")
            self.saida("    Caminho: " + " → ".join(item["caminho"]))
        if r["limitado"]:
            self.saida(f"Análise completa; primeiros {r['limite']} caminhos exibidos.")

    def criar_dependencia(self):
        if not self._exigir("inventario.add_dependencia"):
            return
        self.listar_ativos()
        dependente = self._ativo("ID do ativo dependente i").pk
        fornecedor = self._ativo("ID do fornecedor j").pk
        peso = self._decimal("Peso transmitido Aij", 0, 0.999999)
        d = Dependencia(
            dependente_id=dependente,
            fornecedor_id=fornecedor,
            peso=peso,
            descricao=self._texto("Descrição", permitir_vazio=True),
        )
        salvar_cadastro(d, self.usuario)
        self._ok("Dependência cadastrada.")

    def atualizar_dependencia(self):
        if not self._exigir("inventario.change_dependencia"):
            return
        self.listar_dependencias()
        d = Dependencia.objects.get(pk=self._inteiro("ID"))
        novo = self._decimal("Novo peso", 0, 0.999999)
        d.peso = novo
        salvar_cadastro(d, self.usuario)
        self._ok("Peso atualizado.")

    def remover_dependencia(self):
        if not self._exigir("inventario.delete_dependencia"):
            return
        self.listar_dependencias()
        d = Dependencia.objects.get(pk=self._inteiro("ID"))

        if self._confirmar(f"Remover dependência {d.pk}?"):
            remover_cadastro(d, self.usuario)
            self._ok("Dependência removida.")
