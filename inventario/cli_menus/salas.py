"""Menu de salas: adaptador de terminal."""

from __future__ import annotations
from inventario.aplicacao.servicos import salvar_cadastro, remover_cadastro

from inventario.dominio.enums import TipoEquipamento
from inventario.models import Sala
from inventario.cli_menus.comum import Cor, menu_seguro


class SalasMenu:

    @menu_seguro("view_sala")
    def menu_salas(self):
        while True:
            opcao = self._submenu(
                "ESTRUTURA FÍSICA",
                [
                    ("1", "Exibir árvore e tabela de IDs"),
                    ("2", "Criar sala ou subsetor"),
                    ("3", "Atualizar"),
                    ("4", "Remover"),
                ],
            )
            if opcao == "0":
                return
            {
                "1": self.listar_salas,
                "2": self.criar_sala,
                "3": self.atualizar_sala,
                "4": self.remover_sala,
            }.get(opcao, lambda: self._falha("Opção inválida."))()
            self._pausa()

    def listar_salas(self):

        def ramo(sala, nivel=0):
            tipos = ",".join(sala.tipos_permitidos) or "todos"
            self.saida(
                f"{'  ' * nivel}└─ {Cor.destaque(sala.id)}  {sala.nome}  "
                f"[{sala.categoria}]  tipos: {tipos}"
            )
            for filho in sala.subsetores.all():
                ramo(filho, nivel + 1)

        raizes = Sala.objects.filter(parent__isnull=True)
        if not raizes:
            self.saida(Cor.fraco("Nenhuma sala cadastrada."))
        for sala in raizes:
            ramo(sala)
        self.saida("\nConvenção: SALA-<SETOR>-<NÚMERO>, ex.: SALA-TI-001 ou SALA-DC-002.")

    def _novo_id_sala(self, codigo):
        from inventario.aplicacao.servicos import proximo_id_sala

        return proximo_id_sala(codigo)

    def criar_sala(self):
        if not self._exigir("inventario.add_sala"):
            return
        codigo = self._texto("Código do setor (TI, DC, ADM; até 6 letras/números)").upper()
        import re

        if not re.fullmatch(r"[A-Z0-9]{1,6}", codigo):
            raise ValueError("Use de 1 a 6 letras/números, sem espaços, ex. TI ou LAB.")
        self.listar_salas()
        pai = self._texto("ID da sala-pai (vazio = raiz)", permitir_vazio=True).upper() or None
        self.saida(
            "Tipos: 1 Servidor, 2 Notebook, 3 Estação, 4 Switch, "
            "5 Roteador, 6 Impressora, 7 Web, 8 Banco, 9 Software"
        )
        tipos = [
            x.strip()
            for x in self._texto(
                "Tipos permitidos separados por vírgula (vazio = todos)", permitir_vazio=True
            ).split(",")
            if x.strip()
        ]
        if any((t not in {x.value for x in TipoEquipamento} for t in tipos)):
            raise ValueError("Há um tipo inválido.")
        sala = Sala(
            id=self._texto("ID", padrao=self._novo_id_sala(codigo)).upper(),
            nome=self._texto("Nome"),
            categoria=codigo,
            parent_id=pai,
            tipos_permitidos=tipos,
            restrita=self._confirmar("Sala restrita?"),
        )
        salvar_cadastro(sala, self.usuario)
        self._ok(f"Sala {sala.id} criada.")

    def atualizar_sala(self):
        if not self._exigir("inventario.change_sala"):
            return
        sala = Sala.objects.get(pk=self._texto("ID da sala").upper())
        self.saida("  1 - Nome\n  2 - Tipos permitidos\n  3 - Restrição")
        op = self._texto("Campo")
        if op == "1":
            sala.nome = self._texto("Novo nome")
        elif op == "2":
            sala.tipos_permitidos = [
                x.strip()
                for x in self._texto("Tipos separados por vírgula", permitir_vazio=True).split(",")
                if x.strip()
            ]
        elif op == "3":
            sala.restrita = self._confirmar("Marcar como restrita?")
        else:
            raise ValueError("Campo inválido.")
        salvar_cadastro(sala, self.usuario)
        self._ok("Sala atualizada.")

    def remover_sala(self):
        if not self._exigir("inventario.delete_sala"):
            return
        sala = Sala.objects.get(pk=self._texto("ID da sala").upper())
        if self._confirmar(f"Remover {sala.id}?"):
            _sid = sala.id
            remover_cadastro(sala, self.usuario)
            self._ok("Sala removida.")
