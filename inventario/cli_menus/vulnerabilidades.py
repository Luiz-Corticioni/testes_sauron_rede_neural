"""Menu de vulnerabilidades: adaptador de terminal."""

from __future__ import annotations
from inventario.aplicacao.servicos import salvar_cadastro, remover_cadastro

from inventario.matematica.cvss import CalculadoraCVSS31
from django.db.models import Count
from inventario.models import Vulnerabilidade
from inventario.cli_menus.comum import menu_seguro


class VulnerabilidadesMenu:

    @menu_seguro("view_vulnerabilidade")
    def menu_vulnerabilidades(self):
        while True:
            opcao = self._submenu(
                "VULNERABILIDADES",
                [
                    ("1", "Listar"),
                    ("2", "Cadastrar"),
                    ("3", "Atualizar CVSS/status descritivo"),
                    ("4", "Remover"),
                ],
            )
            if opcao == "0":
                return
            {
                "1": self.listar_vulnerabilidades,
                "2": self.criar_vulnerabilidade,
                "3": self.atualizar_vulnerabilidade,
                "4": self.remover_vulnerabilidade,
            }.get(opcao, lambda: self._falha("Opção inválida."))()
            self._pausa()

    def listar_vulnerabilidades(self):
        self._tabela(
            ["ID", "CVE", "Categoria", "CVSS", "Severidade", "Ativos"],
            [
                [v.id, v.cve_id, v.get_categoria_display(), v.cvss, v.severidade, v.total_ativos]
                for v in Vulnerabilidade.objects.annotate(total_ativos=Count("ativos"))
            ],
            [17, 18, 23, 5, 11, 6],
        )

    def _novo_id_vul(self, categoria: str) -> str:
        from inventario.aplicacao.servicos import proximo_id_vulnerabilidade

        return proximo_id_vulnerabilidade(categoria)

    def criar_vulnerabilidade(self):
        if not self._exigir("inventario.add_vulnerabilidade"):
            return
        for codigo, nome in Vulnerabilidade.CATEGORIAS:
            self.saida(f"  {codigo:<6} {nome}")
        categoria = self._texto("Categoria").upper()
        if categoria not in dict(Vulnerabilidade.CATEGORIAS):
            raise ValueError("Categoria inválida.")
        vetor = self._texto("Vetor CVSS 3.1 (opcional)", permitir_vazio=True)
        if vetor:
            resultado = CalculadoraCVSS31.calcular(vetor)
            score = resultado.score
            self.saida(f"CVSS calculado: {score} — {resultado.severidade}")
        else:
            score = self._decimal("CVSS", 0, 10)
        v = Vulnerabilidade(
            id=self._texto("ID interno", padrao=self._novo_id_vul(categoria)).upper(),
            cve_id=self._texto("CVE (opcional)", permitir_vazio=True).upper() or None,
            descricao=self._texto("Descrição"),
            categoria=categoria,
            cvss=score,
            cvss_versao="3.1",
            cvss_vetor=vetor.upper(),
            fonte=self._texto("Fonte", padrao="Manual/CLI"),
            publicada_em=self._data("Publicada em", True),
        )
        salvar_cadastro(v, self.usuario)
        self._ok(f"Vulnerabilidade {v.id} cadastrada.")

    def atualizar_vulnerabilidade(self):
        if not self._exigir("inventario.change_vulnerabilidade"):
            return
        v = Vulnerabilidade.objects.get(pk=self._texto("ID interno").upper())
        self.saida("  1 - CVSS/vetor\n  2 - Descrição\n  3 - Fonte")
        opcao = self._texto("Campo")
        if opcao == "1":
            vetor = self._texto("Novo vetor (vazio = pontuação manual)", permitir_vazio=True)
            if vetor:
                r = CalculadoraCVSS31.calcular(vetor)
                v.cvss, v.cvss_vetor, v.cvss_versao = (r.score, r.vetor, "3.1")
            else:
                v.cvss = self._decimal("Novo CVSS", 0, 10)
                v.cvss_vetor = ""
        elif opcao == "2":
            v.descricao = self._texto("Nova descrição")
        elif opcao == "3":
            v.fonte = self._texto("Nova fonte")
        else:
            raise ValueError("Campo inválido.")
        salvar_cadastro(v, self.usuario)
        self._ok(f"{v.id} atualizada.")

    def remover_vulnerabilidade(self):
        if not self._exigir("inventario.delete_vulnerabilidade"):
            return
        v = Vulnerabilidade.objects.get(pk=self._texto("ID interno").upper())
        if not self._confirmar(f"Remover {v.id}?"):
            return
        vid = v.id
        remover_cadastro(v, self.usuario)
        self._ok(f"{vid} removida.")
