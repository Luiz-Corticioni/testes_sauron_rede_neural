"""Menu de cves: adaptador de terminal."""

from __future__ import annotations
from inventario.aplicacao.servicos import salvar_cadastro

from django.conf import settings
from inventario.aplicacao.catalogo_cves import autocomplete_cves, consultar_internet, resumo_cve, resumo_cvss
from inventario.dominio.autocomplete import normalizar_cve
from inventario.matematica.cvss import CalculadoraCVSS31
from inventario.infraestrutura.cve_client import CisaKevClient, IntegracaoCVEError, NvdClient
from inventario.models import Vulnerabilidade
from inventario.aplicacao.risco import caminho_cache_kev
from inventario.cli_menus.comum import Cor, menu_seguro


class CvesMenu:

    def sincronizar_epss_terminal(self):
        from inventario.aplicacao.epss import sincronizar_epss
        import json
        if not self._exigir("inventario.change_vulnerabilidade"):
            return
        if self._confirmar("Consultar a FIRST pela internet e atualizar até 50 CVEs? Os dados mais antigos são priorizados."):
            if self._exigir("inventario.change_vulnerabilidade", interativo=False):
                self.saida(json.dumps(sincronizar_epss(usuario=self.usuario, limite=50), ensure_ascii=False, indent=2))

    @menu_seguro("view_vulnerabilidade")
    def menu_cve_cvss(self):
        while True:
            op = self._submenu(
                "CVE, KEV E CVSS",
                [
                    ("1", "Listar 15 adições recentes ao KEV"),
                    ("2", "Consultar CVE na NVD"),
                    ("3", "Importar CVE como vulnerabilidade"),
                    ("4", "Calcular CVSS 3.1"),
                    ("5", "Buscar com sugestões por CVE ou produto"),
                    ("6", "Revisar e vincular CVE a um ativo"),
                    ("7", "Comparar CVSS 3.1 local e 4.0 da NVD"),
                    ("8", "Atualizar EPSS observado na FIRST"),
                ],
            )
            if op == "0":
                return
            try:
                if op == "1":
                    self.listar_kev()
                elif op == "2":
                    self.consultar_nvd()
                elif op == "3":
                    self.importar_cve()
                elif op == "4":
                    self.calcular_cvss()
                elif op == "5":
                    self.buscar_com_sugestoes()
                elif op == "6":
                    self.importar_cve(vincular=True)
                elif op == "7":
                    self.comparar_cvss_terminal()
                elif op == "8":
                    self.sincronizar_epss_terminal()
                else:
                    self._falha("Opção inválida.")
            except (IntegracaoCVEError, ValueError) as erro:
                self._falha(erro)
            self._pausa()

    def listar_kev(self):
        self.saida("Listagem do cache local. Para sincronizar pela internet: menu 11, opção 5.")
        dados = CisaKevClient(caminho_cache_kev()).listar_recentes(15)
        self.saida(Cor.fraco(f"Fonte: {dados['origem']}"))
        self._tabela(
            ["CVE", "Adicionado", "Vulnerabilidade"],
            [
                [x.get("cveID"), x.get("dateAdded"), x.get("vulnerabilityName")]
                for x in dados["vulnerabilidades"]
            ],
            [19, 10, 55],
        )

    def _registro_nvd(self, cve):
        cliente = NvdClient(settings.NVD_API_KEY, settings.DATA_DIR / "cache" / "nvd")
        try:
            return cliente.buscar(cve)
        except IntegracaoCVEError:
            self.saida('Sem cache NVD válido para esta CVE.')
            if self._confirmar('Consultar agora a NVD pela internet?'):
                return cliente.atualizar(cve)
            raise IntegracaoCVEError('Consulta cancelada; nenhum cadastro foi alterado.')

    def buscar_com_sugestoes(self):
        self.saida('Exemplos: cve 2021 44228, Log4Shell, Apache Log4j. Sugestões não confirmam falhas.')
        termo = self._texto('CVE ou produto')
        dados = autocomplete_cves(termo)
        for aviso in dados['avisos']:
            self.saida(aviso)
        sugestoes = dados['sugestoes']
        self._tabela(['Nº', 'CVE', 'Descrição', 'Fonte'],
                     [[i+1, r['id'], r['titulo'], r['origem']] for i,r in enumerate(sugestoes)],
                     [3, 20, 55, 30])
        if sugestoes:
            escolha = self._texto('Número da sugestão (Enter mantém o texto)', permitir_vazio=True)
            if escolha:
                if not escolha.isdigit() or not 1 <= int(escolha) <= len(sugestoes):
                    raise ValueError('Escolha um dos números exibidos.')
                termo = sugestoes[int(escolha)-1]['id']
        if not self._confirmar('Consultar esta busca na NVD pela internet?'):
            return
        resposta = consultar_internet(termo, forcar=True)
        self.saida(f"Fonte: {resposta['origem']} · consulta: {resposta['consultado_em']}")
        for item in resposta['resultados']:
            cvss = item['cvss']
            self.saida(f"\n{item['id']} · CVSS {cvss['score']} (v{cvss['versao']})\n{item['descricao']}")
            self.saida(f"Vetor: {cvss['vetor']}\nRecálculo base 3.1: {cvss['score_recalculado']}")
            if cvss['aviso']:
                self.saida(cvss['aviso'])
        self.saida(resposta['aviso'])
        if resposta['truncado']:
            self.saida('Exibidos até 20 resultados. Refine a busca por produto/versão.')
        self.saida('Resultados ficaram no cache. Use a opção 3 para revisar e importar uma CVE.')

    def _descricao_nvd(self, r):
        return resumo_cve(r)['descricao']

    def _cvss_nvd(self, r):
        resumo = resumo_cvss(r)
        return resumo['score'], resumo['vetor'], resumo['versao']

    def consultar_nvd(self):
        cve = normalizar_cve(self._texto("CVE"))
        r = self._registro_nvd(cve)
        score, vetor, versao = self._cvss_nvd(r)
        if score is None:
            self.saida("CVSS não informado pela fonte; ausência não equivale a zero.")
        self.saida(
            f"\n{Cor.titulo(r.get('id', cve))}\nPublicado: {r.get('published', '—')}"
            f"\nCVSS: {score} (v{versao})\nVetor: {vetor or 'não informado'}"
            f"\nDescrição: {self._descricao_nvd(r)}"
        )
        resumo = resumo_cvss(r)
        if resumo['score_recalculado'] is not None:
            self.saida(f"Recálculo local CVSS 3.1: {resumo['score_recalculado']} · confere: {resumo['consistente']}")
        if resumo['aviso']:
            self.saida(resumo['aviso'])

    def importar_cve(self, vincular=False):
        if not self._exigir("inventario.add_vulnerabilidade"):
            return
        if vincular and not all(self._exigir(f"inventario.{p}") for p in ("view_ativo", "add_incidencia")):
            return
        cve = normalizar_cve(self._texto("CVE"))
        if vincular:
            from inventario.aplicacao.vinculos import vincular_existente
            from inventario.models import Incidencia

            existente = Vulnerabilidade.objects.filter(cve_id=cve).first()
            if existente:
                ativo = self._ativo()
                self.saida(f"{cve} já cadastrado: {existente.descricao}")
                if not self._confirmar(f"Vincular a {ativo.hostname} aguardando confirmação?"):
                    return
                inc, criada = vincular_existente(Incidencia(
                    ativo=ativo, vulnerabilidade=existente, status="SUGERIDA"), self.usuario)
                self._ok(f"Vínculo {inc.pk} {'criado como SUGERIDA' if criada else 'já existente; estado preservado'}.")
                return
        r = self._registro_nvd(cve)
        score, vetor, versao = self._cvss_nvd(r)
        fonte = "NVD"
        if score is None:
            fonte = "NVD; CVSS manual/CLI"
            self.saida("A fonte não informou CVSS; não será tratado como zero.")
            score = self._decimal("CVSS informado manualmente", 0, 10)
            versao = "3.1"
        categoria = self._texto("Categoria interna", padrao="OUTRA").upper()
        v = Vulnerabilidade(
            id=self._novo_id_vul(categoria),
            cve_id=cve,
            descricao=self._descricao_nvd(r),
            categoria=categoria,
            cvss=score,
            cvss_vetor=vetor,
            cvss_versao=versao,
            fonte=fonte,
            referencias=[x.get("url") for x in r.get("references", [])[:10] if isinstance(x, dict) and x.get("url")],
        )
        if vincular:
            from inventario.aplicacao.vinculos import cadastrar_e_vincular

            ativo = self._ativo()
            self.saida(f"{cve} · CVSS {score} · categoria {categoria}\n{v.descricao}\n{vetor}")
            if not self._confirmar(f"Salvar cadastro e vínculo SUGERIDA para {ativo.hostname}?"):
                return
            inc = cadastrar_e_vincular(v, ativo, self.usuario)
            self._ok(f"{v.id} e {inc.pk} salvos juntos; confirme aplicabilidade pelo menu 3.")
        else:
            salvar_cadastro(v, self.usuario)
            self._ok(f"{cve} importado como {v.id}.")

    def calcular_cvss(self):
        vetor = self._texto("Vetor CVSS:3.1")
        r = CalculadoraCVSS31.calcular(vetor)
        self.saida(
            f"\nScore: {Cor.destaque(r.score)}  ·  Severidade: {r.severidade}"
            f"\nImpacto: {r.impacto}\nExplorabilidade: {r.explorabilidade}"
            f"\nVetor normalizado: {r.vetor}"
        )

    def comparar_cvss_terminal(self):
        from inventario.aplicacao.comparacao_cvss import comparar
        cve=normalizar_cve(self._texto("CVE"))
        vetor=self._texto("Vetor base 3.1 (Enter usa a NVD)",permitir_vazio=True)
        atualizar=self._confirmar("Atualizar este registro na NVD pela internet?")
        r=comparar(cve,vetor,atualizar,"vetor informado" if vetor else None)
        self.saida(f"Origem: {r['consulta']['origem']}; consulta: {r['consulta']['consultado_em'] or 'não disponível'}")
        self._tabela(["Avaliação","Nota","Publicador/origem"],[
            ["Base 3.1 local",r["local31"]["nota"],r["local31"]["origem"]],
            ["3.1 na NVD",r["nvd31"]["nota"],r["nvd31"]["publicador"]],
            ["4.0 na NVD",r["nvd40"]["nota"],r["nvd40"]["publicador"]]])
        for nome,valor in (("4.0 − 3.1 local",r["diferenca_40_menos_31"]),
                           ("3.1 NVD − local",r["diferenca_31_nvd_menos_local"])):
            self.saida(f"{nome}: {valor if valor is not None else 'não disponível'} pontos")
        for chave in ("local31","nvd31","nvd40"):
            self.saida(f"{chave}: {r[chave]['vetor'] or 'sem vetor'}")
        for aviso in r["avisos"]:
            self.saida(aviso)
        self.saida(r["aviso_versoes"])
        self.saida("O score 4.0 é publicado pela fonte e não é recalculado localmente.")
