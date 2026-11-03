"""Menu de risco: adaptador de terminal."""

from __future__ import annotations
from inventario.models import HistoricoIncidencia
from inventario.aplicacao.servicos import analisar_historico_risco, calcular_risco_banco, simular_correcao
from inventario.cli_menus.comum import Cor, menu_seguro


class RiscoMenu:

    def _acesso_risco(self):
        permissoes = ("view_ativo", "view_vulnerabilidade", "view_incidencia", "view_dependencia")
        return all((self._exigir(f"inventario.{p}") for p in permissoes))

    @menu_seguro("")
    def menu_risco(self):
        if not self._acesso_risco():
            return
        opcoes = [
            ("1", "Perfil puro — cenário acadêmico"),
            ("2", "Perfil operacional — exposição e KEV"),
            ("3", "Exibir matrizes M, v e A"),
            ("4", "Prioridade por sensibilidade"),
            ("5", "Série de Neumann por saltos"),
            ("6", "Simular correções sem salvar"),
            ("7", "Tendência e risco-dia do histórico"),
            ("8", "Histórico de estados das incidências"),
            ("9", "Conferir solução, transformação M e polimorfismo"),
            ("10", "Cenários de custo em 30 dias — Monte Carlo"),
        ]
        while True:
            op = self._submenu("ANÁLISE MATRICIAL", opcoes)
            if op == "0":
                return
            try:
                if op == "10":
                    self.montecarlo_terminal()
                elif op == "6":
                    self.simular_risco_terminal()
                elif op == "7":
                    self.historico_risco_terminal()
                elif op == "8":
                    self.historico_incidencias_terminal()
                elif op == "9":
                    self.diagnostico_linear_terminal()
                elif op in {"1", "2", "3", "4", "5"}:
                    perfil = "operacional" if op == "2" else "puro"
                    r = calcular_risco_banco(perfil=perfil)
                    if op in {"1", "2"}:
                        self._mostrar_risco(r)
                    elif op == "3":
                        self._mostrar_matrizes(r)
                    elif op == "4":
                        linhas = [
                            [
                                i + 1,
                                v["cve_id"] or v["vulnerabilidade_id"],
                                v["cvss"],
                                v["reducao_total_estimada"],
                            ]
                            for i, v in enumerate(r["prioridade_correcao"])
                        ]
                        self._tabela(["Pos.", "Vulnerabilidade", "CVSS", "Redução"], linhas)
                    else:
                        for k, termo in enumerate(r["series_saltos"]):
                            self.saida(f"A^{k}b = {termo}")
                else:
                    raise ValueError("Opção inválida.")
            except ValueError as erro:
                self._falha(erro)
            self._pausa()

    def _mostrar_risco(self, r):
        linhas = [
            [aid, b, x, peso, relatorio, indice]
            for aid, b, x, peso, relatorio, indice in zip(
                r["ids_ativos"],
                r["risco_proprio"],
                r["risco_efetivo"],
                r["pesos_relatorio"],
                r["risco_relatorio"],
                r["indices"],
            )
        ]
        self._tabela(["Ativo", "Próprio b", "Efetivo x", "Peso", "Relatório R", "Índice"], linhas)
        self.saida(f"Perfil: {r['perfil']} | cond(I-A) = {r['numero_condicao']}")
        self.saida(f"Raio espectral = {r['raio_espectral']} | tau = {r['tau']}")
        self.saida(r["origem_kev"])
        self.saida("Índice 0–100 é uma escala de apresentação, não probabilidade de ataque.")

    def simular_risco_terminal(self):
        ids = self._texto("IDs das incidências separados por vírgula (ex.: INC-0001,INC-0002)")
        perfil = self._texto("Perfil puro ou operacional", padrao="puro")
        r = simular_correcao([i.strip() for i in ids.split(",") if i.strip()], perfil=perfil)
        linhas = [
            [aid, antes, depois, ganho]
            for aid, antes, depois, ganho in zip(
                r["antes"]["ids_ativos"],
                r["antes"]["risco_efetivo"],
                r["depois"]["risco_efetivo"],
                r["ganho_por_ativo"],
            )
        ]
        self._tabela(["Ativo", "Antes", "Depois", "Ganho"], linhas)
        self.saida(f"Redução total: {r['ganho_total']}; simulação sem alteração de cadastros.")

    def historico_risco_terminal(self):
        if not self._acesso_risco():
            return
        inicio = self._texto("Início ISO com fuso (vazio = primeiro snapshot)", permitir_vazio=True)
        fim = self._texto("Fim ISO com fuso (vazio = último snapshot)", permitir_vazio=True)
        r = analisar_historico_risco(inicio or None, fim or None)
        if not r["disponivel"]:
            self.saida(r["mensagem"])
            return
        self.saida(f"Risco-dia: {r['risco_dia']} | taxa: {r['taxa_por_dia']} pontos/dia")
        self.saida(r["metodo"])
        for alerta in r["alertas"]:
            self.saida(Cor.aviso(f"{alerta['tipo']}: {alerta['mensagem']}"))

    def historico_incidencias_terminal(self):
        if not self._exigir("inventario.view_historicoincidencia"):
            return
        codigo = self._texto("ID da incidência (vazio = todas)", permitir_vazio=True)
        registros = HistoricoIncidencia.objects.select_related("por").order_by("-em", "-id")
        if codigo:
            registros = registros.filter(incidencia_codigo=codigo)
        linhas = [
            [
                h.incidencia_codigo,
                h.de or "CADASTRO",
                h.para,
                h.em.isoformat(),
                h.por.username if h.por else "sistema",
            ]
            for h in registros[:50]
        ]
        self._tabela(["Incidência", "De", "Para", "Em", "Por"], linhas)

    def _mostrar_matrizes(self, r):
        from inventario.matematica.representacao import janela
        if max(len(r["ids_ativos"]), len(r["ids_vulnerabilidades"])) > 40:
            self.saida("Exibindo janela de até 40 × 40; o cálculo usa o inventário completo.")
        self.saida(Cor.destaque("\nM — incidência"))
        for linha in janela(r["matriz_incidencia"]):
            self.saida("  " + str(linha))
        self.saida(Cor.destaque("\nv — CVSS\n  ") + str(r["vetor_cvss"]))
        self.saida(Cor.destaque("\nA — dependências"))
        for linha in janela(r["matriz_dependencias"]):
            self.saida("  " + str(linha))

    def diagnostico_linear_terminal(self):
        from inventario.aplicacao.analise_linear import explicar_modelo

        if not self._acesso_risco():
            return
        termo = self._texto("Ativo: número, código ou hostname (vazio = primeiro)", permitir_vazio=True)
        perfil = self._texto("Perfil puro ou operacional", padrao="puro")
        r = explicar_modelo(self.usuario, termo or None, perfil)
        self.saida(f"M: {r['n']} × {r['m']}; {r['dimensao']}")
        if r["posto_limitado"]:
            self.saida("Posto/nulidade não calculados acima de 200 linhas ou colunas.")
        else:
            self.saida(f"Posto: {r['posto']}; dimensão do núcleo: {r['nulidade']}.")
        self.saida(f"Colunas sem incidências consideradas: {len(r['colunas_nulas'])}; "
                   f"primeiras 20: {r['colunas_nulas'][:20]}")
        self.saida(f"Resíduo absoluto: {r['residuo_absoluto']:.3e}; normalizado: {r['residuo_relativo']:.3e}.")
        self.saida(f"Condição: {r['numero_condicao']}. Resíduo pequeno não comprova fidelidade da rede cadastrada.")
        e = r["equacao"]
        if e:
            self.saida(f"{r['hostname']}: fator aplicado {e['fator_aplicado']}")
            for p in e["parcelas"]:
                self.saida(f"  {p['vulnerabilidade']}: CVSS {p['cvss']}; severidade utilizada {p['severidade']}")
            self.saida(f"  b = {e['risco_proprio']}")
            for f in e["fornecedores"]:
                self.saida(f"  Fornecedor {f['id']}: {f['peso']} × {f['risco_efetivo']} = {f['parcela']:.6f}")
            self.saida(f"  x = b + parcelas recebidas = {e['risco_efetivo']}")
        self.saida("Núcleo: variações Δv que mantêm Mv, não contagem de CVEs inofensivas.")
        if r["amostra_limitada"]:
            self.saida("Polimorfismo: amostra dos primeiros 12 objetos cadastrados.")
        for obj in r["objetos"]:
            self.saida(f"  {obj['classe']}: {obj['detalhes']} | fator do subtipo {obj['fator_exposicao']} "
                       f"| isinstance(Equipamento): {obj['equipamento']}")


    def montecarlo_terminal(self):
        from inventario.aplicacao.montecarlo import calcular_montecarlo
        import json
        if not self._acesso_risco():
            return
        texto = self._texto("Parâmetros JSON do cliente (vazio = custos fictícios padrão)", permitir_vazio=True)
        r = calcular_montecarlo(json.loads(texto) if texto.strip() else {})
        if not r["disponivel"]:
            self.saida(r["aviso"])
            for pendencia in r["pendencias"]:
                self.saida(f"{pendencia['ativo']} · {pendencia['cve']}: {pendencia['motivo']}")
            self.saida("Atualização de EPSS: menu CVE, opção 8, ou python manage.py sync_epss no servidor.")
            return
        moeda = lambda v: "R$ " + f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        self.saida(f"Em cerca de 9 de cada 10 cenários hipotéticos de 30 dias a perda é de até {moeda(r['antes']['P90'])}; "
                   f"a mediana é {moeda(r['antes']['P50'])}.")
        self.saida(f"Perda média em 30 dias: {moeda(r['antes']['media'])}; P95: {moeda(r['antes']['P95'])}; "
                   f"ganho com correções: {moeda(r['ganho_media'])}.")
        self.saida(r["aviso"])
        self.saida(r["hipotese_epss"])
