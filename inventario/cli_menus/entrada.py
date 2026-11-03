"""Leitura validada, tabelas e mensagens do terminal."""

import math
import shutil
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from inventario.cli_menus.comum import Cor


class EntradaMenu:

    def _ativo(self, mensagem="ID do ativo", padrao=None):
        from inventario.aplicacao.consultas import consultar_ativo

        return consultar_ativo(self._texto(mensagem, padrao=padrao))

    def _texto(self, mensagem: str, permitir_vazio: bool = False, padrao: str | None = None) -> str:
        while True:
            sufixo = f" [{padrao}]" if padrao not in (None, "") else ""
            valor = self.entrada(
                f"{mensagem.rstrip()}{sufixo}: " if not mensagem.endswith(": ") else mensagem
            ).strip()
            if valor == "-" and permitir_vazio and (padrao is not None):
                return ""
            if not valor and padrao is not None:
                return str(padrao)
            if valor or permitir_vazio:
                return valor
            self._falha("Este campo é obrigatório.")

    def _inteiro(
        self,
        mensagem: str,
        minimo: int | None = None,
        maximo: int | None = None,
        padrao: int | None = None,
    ) -> int:
        while True:
            try:
                valor = int(
                    self._texto(mensagem, padrao=str(padrao) if padrao is not None else None)
                )
                if abs(valor) > 2**63 - 1:
                    raise ValueError
                if minimo is not None and valor < minimo:
                    raise ValueError
                if maximo is not None and valor > maximo:
                    raise ValueError
                return valor
            except ValueError:
                self._falha(
                    "Informe um inteiro"
                    + (
                        f" entre {minimo} e {maximo}"
                        if minimo is not None and maximo is not None
                        else ""
                    )
                    + "."
                )

    def _decimal(
        self,
        mensagem: str,
        minimo: float | None = None,
        maximo: float | None = None,
        padrao: float | None = None,
    ) -> float:
        while True:
            try:
                texto = self._texto(
                    mensagem, padrao=str(padrao) if padrao is not None else None
                ).replace(",", ".")
                valor = float(texto)
                if not math.isfinite(valor):
                    raise ValueError
                if minimo is not None and valor < minimo:
                    raise ValueError
                if maximo is not None and valor > maximo:
                    raise ValueError
                return valor
            except ValueError:
                self._falha("Informe um número válido dentro da faixa solicitada.")

    def _data(self, mensagem: str, permitir_vazio: bool = True):
        while True:
            texto = self._texto(mensagem + " (AAAA-MM-DD)", permitir_vazio=permitir_vazio)
            if not texto and permitir_vazio:
                return None
            try:
                return datetime.strptime(texto, "%Y-%m-%d").date()
            except ValueError:
                self._falha("Data inválida. Use AAAA-MM-DD.")

    def _confirmar(self, mensagem: str) -> bool:
        while True:
            texto = self._texto(f"{mensagem} [s/N]", permitir_vazio=True).lower()
            if texto in {"s", "sim"}:
                return True
            if texto in {"", "n", "nao", "não"}:
                return False
            self._falha("Responda s para sim ou n para não; Enter significa não.")

    def _pausa(self):
        self.entrada(Cor.fraco("\nPressione Enter para continuar..."))

    def _ok(self, mensagem):
        self.saida(Cor.sucesso(f"[SUCESSO] {mensagem}"))

    def _falha(self, erro):
        if isinstance(erro, ValidationError):
            texto = "; ".join(erro.messages)
        elif isinstance(erro, ObjectDoesNotExist):
            texto = "Registro não encontrado. Consulte a listagem e informe o ID completo."
        else:
            texto = str(erro)
        self.saida(Cor.erro(f"[ERRO] {texto}"))

    def _tabela(
        self, cabecalhos: list[str], linhas: list[list[object]], larguras: list[int] | None = None
    ):
        if not linhas:
            self.saida(Cor.fraco("Nenhum registro encontrado."))
            return
        if not larguras:
            larguras = [
                min(
                    30,
                    max(len(str(h)), *(len(str(linha[i] if linha[i] is not None else "")) for linha in linhas)),
                )
                for i, h in enumerate(cabecalhos)
            ]
        larguras = list(larguras)
        limite = min(shutil.get_terminal_size((100, 24)).columns, 100)
        while sum(larguras) + 2 * (len(larguras) - 1) > limite and max(larguras) > 4:
            indice = larguras.index(max(larguras))
            larguras[indice] -= 1

        def celula(valor, largura):
            texto = str(valor if valor is not None else "—").replace("\n", " ")
            return texto if len(texto) <= largura else texto[: largura - 1] + "…"

        self.saida("  ".join((celula(h.upper(), w).ljust(w) for h, w in zip(cabecalhos, larguras))))
        self.saida("  ".join(("─" * w for w in larguras)))
        for linha in linhas:
            self.saida("  ".join((celula(v, w).ljust(w) for v, w in zip(linha, larguras))))
