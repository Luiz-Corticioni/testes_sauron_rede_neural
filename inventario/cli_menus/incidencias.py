"""Menu de incidencias: adaptador de terminal."""

from __future__ import annotations
from inventario.aplicacao.servicos import salvar_cadastro, remover_cadastro

from inventario.models import Incidencia
from inventario.cli_menus.comum import menu_seguro


class IncidenciasMenu:

    @menu_seguro("view_incidencia")
    def menu_incidencias(self):
        while True:
            opcao = self._submenu(
                "INCIDÊNCIAS — RELAÇÃO N:M",
                [
                    ("1", "Listar vínculos"),
                    ("2", "Vincular vulnerabilidade a ativo"),
                    ("3", "Alterar status"),
                    ("4", "Desvincular"),
                    ("5", "SSVC: consultar ou avaliar"),
                ],
            )
            if opcao == "0":
                return
            {
                "1": self.listar_incidencias,
                "2": self.criar_incidencia,
                "3": self.atualizar_incidencia,
                "4": self.remover_incidencia,
                "5": self.ssvc_terminal,
            }.get(opcao, lambda: self._falha("Opção inválida."))()
            self._pausa()

    def listar_incidencias(self):
        qs = Incidencia.objects.select_related("ativo", "vulnerabilidade")
        self._tabela(
            ["ID", "Ativo", "Vulnerabilidade", "CVSS", "Status", "Detecção"],
            [
                [
                    i.id,
                    i.ativo.hostname,
                    i.vulnerabilidade.cve_id or i.vulnerabilidade_id,
                    i.vulnerabilidade.cvss,
                    i.status,
                    i.detectada_em,
                ]
                for i in qs
            ],
            [12, 24, 19, 5, 12, 10],
        )

    def _novo_id_inc(self):
        from inventario.aplicacao.servicos import proximo_id_incidencia

        return proximo_id_incidencia()

    def criar_incidencia(self):
        if not self._exigir("inventario.add_incidencia"):
            return
        self.listar_ativos()
        aid = self._ativo().pk
        self.listar_vulnerabilidades()
        vid = self._texto("ID da vulnerabilidade").upper()
        inc = Incidencia(
            id=self._novo_id_inc(),
            ativo_id=aid,
            vulnerabilidade_id=vid,
            status="ABERTA",
            versao_afetada=self._texto("Versão afetada", permitir_vazio=True),
            observacoes=self._texto("Observações", permitir_vazio=True),
        )
        salvar_cadastro(inc, self.usuario)
        self._ok(f"Vínculo {inc.id} criado.")

    def atualizar_incidencia(self):
        from inventario.aplicacao.servicos import alterar_status

        if not self._exigir("inventario.change_incidencia"):
            return
        inc = Incidencia.objects.get(pk=self._texto("ID da incidência").upper())
        for codigo, nome in Incidencia.STATUS:
            self.saida(f"  {codigo:<12} {nome}")
        status = self._texto("Novo status").upper()
        justificativa, validade = ("", None)
        if inc.decisao_pendente == status:
            permissao = "inventario.aprovar_aceite_risco" if status == "ACEITA" else "inventario.change_incidencia"
            if not self._exigir(permissao):
                return
        elif status == "ACEITA":
            if not self._exigir("inventario.aceitar_risco"):
                return
            justificativa = self._texto("Justificativa do aceite")
            validade = self._data("Aceita até", permitir_vazio=False)
        alterar_status(inc.pk, status, self.usuario, justificativa, validade,
                       evidencia=self._texto("Evidência/ID do scan") if status in ("CORRIGIDA", "MITIGADA") and inc.decisao_pendente != status else "")
        self._ok("Status atualizado com auditoria.")

    @menu_seguro("")
    def menu_operacional(self):
        from inventario.cli_operacional import menu_operacional

        menu_operacional(self)

    def remover_incidencia(self):
        if not self._exigir("inventario.delete_incidencia"):
            return
        inc = Incidencia.objects.get(pk=self._texto("ID da incidência").upper())
        if self._confirmar(f"Desvincular {inc.ativo_id} de {inc.vulnerabilidade_id}?"):
            _iid = inc.id
            remover_cadastro(inc, self.usuario)
            self._ok("Vínculo removido.")

    def ssvc_terminal(self):
        from inventario.aplicacao.ssvc import PERMISSOES_LEITURA, contexto_atual, registrar_avaliacao, situacao
        from inventario.dominio.ssvc import PONTOS
        for permissao in PERMISSOES_LEITURA:
            if not self._exigir(permissao):
                return
        inc = Incidencia.objects.get(pk=self._texto("ID da incidência").upper())
        _, assinatura = contexto_atual(inc)
        self.saida("SSVC Deployer: prioridade sugerida; não modifica status, aceite ou SLA.")
        for r in inc.avaliacoes_ssvc.select_related("por")[:10]:
            self.saida(f"{r.resultado['rotulo']} · {situacao(r, assinatura)} · {r.remediacao}")
        if not self._confirmar("Registrar nova avaliação?") or not self._exigir("inventario.change_incidencia"):
            return
        self.saida("KEV exige active. EPSS não prova exploração. Impacto considera pessoas e missão, não CVSS.")
        entradas = {nome: self._texto(nome + " (" + ", ".join(valores) + "; vazio = desconhecido)", permitir_vazio=True).lower()
                    for nome, valores in PONTOS.items()}
        remediacao = self._texto("Remediação/mitigação avaliada")
        evidencia = self._texto("Evidências e justificativa de cada resposta")
        revisar = self._data("Revisar em", permitir_vazio=False)
        if not self._exigir("inventario.change_incidencia"):
            return
        registro = registrar_avaliacao(inc.pk, self.usuario, entradas, evidencia, revisar, assinatura, remediacao)
        self._ok(registro.resultado["rotulo"])
