from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from inventario.aplicacao.cenario_financeiro import calcular_cenario, criar_cenario
from inventario.infraestrutura.limite_simulacoes import LimiteSimulacoes
from inventario.models import CenarioFinanceiro, RegistroAuditoria
from .base import BancoTeste


class CenáriosFinanceiros(BancoTeste):
    def test_perda_secundaria_condicional_e_curva_de_excedencia(self):
        c = self.salvar(probabilidade=Decimal('1'), probabilidade_apos=Decimal('0'),
                        controle='Hipótese de controle', custo_hora=Decimal('0'), custo_adicional=Decimal('100'))
        secundaria = {'probabilidade': 1., 'minimo': 10., 'moda': 20., 'maximo': 30.}
        r = calcular_cenario(c, self.usuario, n=1000, seed=7, limite=100, secundaria=secundaria)
        self.assertIsNone(r['qualidade_dados']['score'])
        self.assertIsNone(r['qualidade_dados']['componentes'][-1]['percentual'])
        self.assertEqual(r, calcular_cenario(c, self.usuario, n=1000, seed=7, limite=100, secundaria=secundaria))
        self.assertEqual(r['componentes']['media_primaria'], 100)
        self.assertEqual(r['componentes']['eventos_secundarios'], 1000)
        self.assertAlmostEqual(r['atual']['media'], r['componentes']['media_primaria'] + r['componentes']['media_secundaria'])
        self.assertEqual(r['apos']['media'], 0)
        self.assertEqual(r['excedencia'], 1)
        pontos = r['excedencia_pontos']
        self.assertEqual(pontos[0]['valor'], 0)
        self.assertEqual(pontos[-1]['percentual'], 0)
        self.assertTrue(all(a['percentual'] >= b['percentual'] for a, b in zip(pontos, pontos[1:])))
        zero = calcular_cenario(c, self.usuario, n=100, secundaria=secundaria | {'probabilidade': 0.})
        self.assertEqual(zero['componentes']['eventos_secundarios'], 0)
        self.assertEqual(zero['atual']['media'], 100)
        with self.assertRaises(ValueError):
            calcular_cenario(c, self.usuario, n=100, secundaria=secundaria | {'minimo': 40.})
        c.probabilidade = Decimal('0')
        self.assertEqual(calcular_cenario(c, self.usuario, n=100, secundaria=secundaria)['componentes']['eventos_secundarios'], 0)

    def test_formulario_exige_origem_e_custos_distintos_na_perda_secundaria(self):
        c = self.salvar(probabilidade=Decimal('1'), custo_hora=Decimal('0'), custo_adicional=Decimal('100'))
        url = f'/cenarios-financeiros/{c.pk}/'
        entrada = {'n': 100, 'seed': 42, 'chance_secundaria': '1', 'secundaria_min': '10',
                   'secundaria_moda': '20', 'secundaria_max': '30', 'secundaria_origem': 'Exemplo fictício',
                   'secundaria_sem_sobreposicao': 'on'}
        resposta = self.client.post(url, entrada)
        self.assertContains(resposta, 'Qualidade das evidências')
        self.assertContains(resposta, 'Composição da média simulada')
        self.assertContains(resposta, 'Quanto pode ultrapassar cada valor?')
        self.assertGreater(resposta.context['resultado']['componentes']['media_secundaria'], 0)
        entrada.pop('secundaria_sem_sobreposicao')
        self.assertContains(self.client.post(url, entrada), 'confirme que não há sobreposição')
        self.assertEqual(CenarioFinanceiro.objects.count(), 1)

    def dados(self, **alteracoes):
        dados = {"nome": "Faturamento fictício", "ativo": self.a, "descricao": "Paralisação demonstrativa",
                 "probabilidade": Decimal("0.5"), "probabilidade_apos": None, "controle": "",
                 "horas_min": Decimal("4"), "horas_moda": Decimal("8"), "horas_max": Decimal("24"),
                 "custo_hora": Decimal("1000"), "custo_adicional": Decimal("2000"),
                 "funcionarios_afetados": None, "contas_privilegiadas": None,
                 "origem": "Empresa fictícia; hipótese didática", "qualidade": "SIMULADO",
                 "data_referencia": timezone.localdate()}
        return dados | alteracoes

    def salvar(self, **alteracoes):
        return criar_cenario(CenarioFinanceiro(**self.dados(**alteracoes)), self.usuario)

    def test_comparacao_reprodutivel_sem_calcular_probabilidade_com_epss(self):
        c = self.salvar(probabilidade=Decimal("1"), probabilidade_apos=Decimal("0"), controle="Hipótese: controle adicional")
        a = calcular_cenario(c, self.usuario, n=1000, seed=9, limite=0)
        self.assertEqual(a, calcular_cenario(c, self.usuario, n=1000, seed=9, limite=0))
        self.assertEqual(a["eventos"], 1000)
        self.assertEqual(a["excedencia"], 1)
        self.assertEqual(a["apos"]["media"], 0)
        self.assertEqual(a["diferenca_media"], a["atual"]["media"])
        self.assertEqual(a["horizonte_dias"], 30)
        c.funcionarios_afetados = 999
        c.contas_privilegiadas = 50
        self.assertEqual(a, calcular_cenario(c, self.usuario, n=1000, seed=9, limite=0))

    def test_casos_extremos_e_custo_adicional(self):
        c = self.salvar(probabilidade=Decimal("0"))
        r = calcular_cenario(c, self.usuario, n=100)
        self.assertEqual(r["atual"]["media"], 0)
        self.assertIsNone(r["perda_media_condicional"])
        c.probabilidade = Decimal("1")
        c.custo_hora = 0
        c.custo_adicional = 250
        r = calcular_cenario(c, self.usuario, n=100)
        self.assertEqual(r["atual"]["media"], 250)
        self.assertEqual(r["atual"]["P95"], 250)

    def test_janela_corta_horas_apos_30_dias(self):
        c = self.salvar(probabilidade=Decimal("1"), horas_min=Decimal("700"), horas_moda=Decimal("710"),
                        horas_max=Decimal("720"), custo_hora=Decimal("1"), custo_adicional=Decimal("0"))
        r = calcular_cenario(c, self.usuario, n=10000, seed=7)
        self.assertGreater(r["atual"]["media"], 340)
        self.assertLess(r["atual"]["media"], 370)

    def test_dados_invalidos_nao_sao_gravados(self):
        exemplos = [{"horas_min": Decimal("9")}, {"probabilidade": Decimal("1.1")},
                    {"data_referencia": timezone.localdate() + timedelta(days=1)},
                    {"probabilidade_apos": Decimal("0.3")}, {"controle": "Controle sem hipótese"},
                    {"qualidade": "INVALIDA"}, {"custo_hora": Decimal("-1")}]
        for dados in exemplos:
            with self.subTest(dados=dados), self.assertRaises(ValidationError):
                self.salvar(**dados)
        self.assertFalse(CenarioFinanceiro.objects.exists())

    def test_autorizacao_e_auditoria_sem_valores_financeiros(self):
        sem = get_user_model().objects.create_user("sem-financas")
        with self.assertRaises(PermissionDenied):
            criar_cenario(CenarioFinanceiro(**self.dados()), sem)
        c = self.salvar()
        with self.assertRaises(PermissionDenied):
            calcular_cenario(c, sem, n=100)
        registro = RegistroAuditoria.objects.filter(acao="CRIAR", entidade="CenarioFinanceiro").latest("id")
        self.assertEqual(registro.usuario_id, self.usuario.pk)
        self.assertNotIn("1000", str(registro.detalhes))
        with patch("inventario.aplicacao.cenario_financeiro.registrar_evento", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.salvar(nome="Falha")
        self.assertEqual(CenarioFinanceiro.objects.count(), 1)

    def test_formulario_resultado_permissao_mfa_e_csrf(self):
        entrada = self.dados()
        entrada["ativo"] = self.a.pk
        entrada["data_referencia"] = entrada["data_referencia"].isoformat()
        entrada["funcionarios_afetados"] = ""
        entrada["contas_privilegiadas"] = ""
        entrada["probabilidade_apos"] = ""
        r = self.client.post("/cenarios-financeiros/novo/", entrada)
        self.assertEqual(r.status_code, 302)
        c = CenarioFinanceiro.objects.get()
        url = f"/cenarios-financeiros/{c.pk}/"
        r = self.client.post(url, {"n": 100, "seed": 42, "limite": 5000})
        self.assertContains(r, "Resultado simulado")
        self.assertContains(r, "não um valor garantido")
        self.assertEqual(r.context["resultado"]["versao_modelo"], "sauron.interrupcao/30d-v2")
        with patch("inventario.aplicacao.cenario_financeiro.vaga_simulacao", side_effect=LimiteSimulacoes("ocupado")):
            self.assertEqual(self.client.post(url, {"n": 100, "seed": 42}).status_code, 429)
        sem = get_user_model().objects.create_user("sem-cenario")
        self.autenticar(sem)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {"n": 100, "seed": 42}).status_code, 403)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url).url, "/mfa/")
        cliente = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, cliente)
        self.assertEqual(cliente.post(url, {"n": 100, "seed": 42}).status_code, 403)

    def test_sensibilidade_usa_mesmas_amostras_e_casos_extremos(self):
        c = self.salvar(probabilidade=Decimal("1"))
        resultado = calcular_cenario(c, self.usuario, n=1000, seed=11)
        faixa = resultado["sensibilidade_duracao"]
        self.assertLessEqual(faixa["media_min"], faixa["media_base"])
        self.assertLessEqual(faixa["media_base"], faixa["media_max"])
        self.assertEqual(faixa["media_base"], resultado["atual"]["media"])
        c.probabilidade = Decimal("0")
        faixa = calcular_cenario(c, self.usuario, n=100, seed=11)["sensibilidade_duracao"]
        self.assertEqual((faixa["media_min"], faixa["media_base"], faixa["media_max"]), (0, 0, 0))

    def test_dependencias_de_negocio_respeitam_direcao_escopo_e_permissoes(self):
        from django.contrib.auth.models import Permission
        from inventario.aplicacao.relacoes import salvar_relacao
        c = self.salvar()
        hoje = timezone.localdate()
        dados = {"origem_id": self.a.pk, "destino_id": self.b.pk, "tipo": "NEGOCIO", "escopo": "Faturamento",
                 "protocolo": "", "porta": 0, "principal": "", "privilegio": "", "fonte": "Exemplo",
                 "evidencia": "Declaração sintética", "observada_em": hoje, "revisar_em": hoje + timedelta(days=30), "vigente": True}
        salvar_relacao(dados, self.usuario)
        salvar_relacao({**dados, "escopo": "Outro escopo", "origem_id": self.b.pk, "destino_id": self.a.pk}, self.usuario)
        url = f"/cenarios-financeiros/{c.pk}/dependencias/"
        r = self.client.get(url, {"escopo": "Faturamento"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["resultado"]["alcance_base"], 1)
        self.assertEqual(r.context["resultado"]["itens"][0]["id"], self.b.pk)
        self.assertContains(r, "não modifica a simulação financeira")
        r = self.client.get(url, {"escopo": "Não cadastrado"})
        self.assertEqual(r.context["resultado"]["alcance_base"], 0)
        self.assertContains(r, "Relação ausente não comprova isolamento")
        sem_relacoes = get_user_model().objects.create_user("somente-financeiro")
        sem_relacoes.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventario", codename__in=["view_ativo", "view_cenariofinanceiro"]))
        self.autenticar(sem_relacoes)
        self.assertEqual(self.client.get(url, {"escopo": "Faturamento"}).status_code, 403)
        self.assertNotContains(self.client.get(f"/cenarios-financeiros/{c.pk}/"), "Analisar dependências")

    def test_dependencias_nao_duplicam_ciclo_e_excluem_relacao_vencida(self):
        from inventario.aplicacao.relacoes import salvar_relacao
        from inventario.models import Ativo
        c = self.salvar()
        terceiro = Ativo.objects.create(tipo="1", nome="Sistema dependente", fabricante="Exemplo", sala=self.sala)
        quarto = Ativo.objects.create(tipo="1", nome="Sistema vencido", fabricante="Exemplo", sala=self.sala)
        hoje = timezone.localdate()
        base = {"tipo": "NEGOCIO", "escopo": "Empresa", "protocolo": "", "porta": 0, "principal": "", "privilegio": "",
                "fonte": "Exemplo", "evidencia": "Dado sintético", "observada_em": hoje - timedelta(days=1),
                "revisar_em": hoje + timedelta(days=30), "vigente": True}
        for origem, destino in ((self.a, self.b), (self.b, terceiro), (self.a, terceiro), (terceiro, self.a)):
            salvar_relacao({**base, "origem_id": origem.pk, "destino_id": destino.pk}, self.usuario)
        salvar_relacao({**base, "origem_id": self.a.pk, "destino_id": quarto.pk, "revisar_em": hoje}, self.usuario)
        r = self.client.get(f"/cenarios-financeiros/{c.pk}/dependencias/", {"escopo": "Empresa"})
        self.assertEqual(r.status_code, 200)
        resultado = r.context["resultado"]
        self.assertEqual(resultado["alcance_base"], 2)
        self.assertEqual(resultado["excluidas"], 1)
        self.assertEqual({item["id"] for item in resultado["itens"]}, {self.b.pk, terceiro.pk})
        self.assertEqual(resultado["ciclos_base"]["total_grupos"], 1)

    def test_causa_compartilhada_conta_servicos_uma_vez_em_ciclos_e_caminhos_paralelos(self):
        from inventario.aplicacao.cenario_financeiro import calcular_compartilhado
        from inventario.aplicacao.relacoes import salvar_relacao
        from inventario.models import Ativo, RelacaoAtivos
        terceiro = Ativo.objects.create(tipo="1", nome="Banco de teste", fabricante="Exemplo", sala=self.sala)
        c = self.salvar(probabilidade=Decimal("1"), custo_hora=Decimal("0"), custo_adicional=Decimal("10"))
        hoje = timezone.localdate()
        base = {"tipo": "NEGOCIO", "escopo": "Empresa", "protocolo": "", "porta": 0, "principal": "", "privilegio": "",
                "fonte": "Exemplo", "evidencia": "Dado sintético", "observada_em": hoje - timedelta(days=1),
                "revisar_em": hoje + timedelta(days=30), "vigente": True}
        for origem, destino in ((self.a, self.b), (self.a, terceiro), (self.b, terceiro), (terceiro, self.a)):
            salvar_relacao({**base, "origem_id": origem.pk, "destino_id": destino.pk}, self.usuario)
        impactos = [{"ativo_id": self.b.pk, "custo_hora": Decimal("0"), "custo_adicional": Decimal("20"), "justificativa": "Despesa distinta B"},
                    {"ativo_id": terceiro.pk, "custo_hora": Decimal("0"), "custo_adicional": Decimal("30"), "justificativa": "Despesa distinta C"}]
        resultado = calcular_compartilhado(c, self.usuario, "Empresa", impactos, True, n=100, seed=1)
        self.assertEqual(resultado["atual"]["media"], 60)
        self.assertEqual(resultado["versao_modelo"], "sauron.interrupcao-compartilhada/30d-v1")
        self.assertEqual(len(resultado["custos_servicos"]), 2)
        self.assertEqual(resultado, calcular_compartilhado(c, self.usuario, "Empresa", impactos, True, n=100, seed=1))
        parciais = [{**impactos[0], "probabilidade_condicional": 0}, {**impactos[1], "probabilidade_condicional": 1}]
        parcial = calcular_compartilhado(c, self.usuario, "Empresa", parciais, True, n=100, seed=1)
        self.assertEqual(parcial["atual"]["media"], 40)
        self.assertEqual(parcial["excedencia_pontos"], [{"valor": 0., "percentual": 100.}, {"valor": 40., "percentual": 0.}])
        self.assertEqual(parcial["afetacoes_por_servico"], [0, 100])
        self.assertEqual(parcial, calcular_compartilhado(c, self.usuario, "Empresa", parciais, True, n=100, seed=1))
        meio = [{**impactos[0], "probabilidade_condicional": .5}]
        resultado_meio = calcular_compartilhado(c, self.usuario, "Empresa", meio, True, n=10000, seed=1)
        self.assertGreater(resultado_meio["atual"]["media"], 19)
        self.assertLess(resultado_meio["atual"]["media"], 21)
        with self.assertRaises(ValueError):
            calcular_compartilhado(c, self.usuario, "Empresa", [{**impactos[0], "probabilidade_condicional": 1.1}], True, n=100)
        for lista, declaracao in ((impactos + [impactos[0]], True), (impactos, False),
                                  ([{**impactos[0], "ativo_id": self.a.pk}], True)):
            with self.subTest(lista=lista, declaracao=declaracao), self.assertRaises(ValueError):
                calcular_compartilhado(c, self.usuario, "Empresa", lista, declaracao, n=100)
        RelacaoAtivos.objects.filter(origem=self.a, destino=terceiro, escopo="Empresa").update(vigente=False)
        RelacaoAtivos.objects.filter(origem=self.b, destino=terceiro, escopo="Empresa").update(vigente=False)
        with self.assertRaises(ValueError):
            calcular_compartilhado(c, self.usuario, "Empresa", impactos, True, n=100)

    def test_causa_compartilhada_web_e_permissoes(self):
        from django.contrib.auth.models import Permission
        from inventario.aplicacao.relacoes import salvar_relacao
        c = self.salvar(probabilidade=Decimal("1"), custo_hora=Decimal("0"), custo_adicional=Decimal("10"))
        hoje = timezone.localdate()
        salvar_relacao({"origem_id": self.a.pk, "destino_id": self.b.pk, "tipo": "NEGOCIO", "escopo": "Empresa",
            "protocolo": "", "porta": 0, "principal": "", "privilegio": "", "fonte": "Exemplo", "evidencia": "Sintético",
            "observada_em": hoje, "revisar_em": hoje + timedelta(days=30), "vigente": True}, self.usuario)
        url = f"/cenarios-financeiros/{c.pk}/compartilhado/"
        dados = {"escopo": "Empresa", "sem_sobreposicao": "on", "n": 100, "seed": 42, "limite": "",
                 "servicos-TOTAL_FORMS": "3", "servicos-INITIAL_FORMS": "0", "servicos-MIN_NUM_FORMS": "0", "servicos-MAX_NUM_FORMS": "10",
                 "servicos-0-ativo": self.b.pk, "servicos-0-custo_hora": "0", "servicos-0-custo_adicional": "20",
                 "servicos-0-justificativa": "Custo adicional independente"}
        resposta = self.client.post(url, dados)
        self.assertContains(resposta, "Resultado da hipótese compartilhada")
        self.assertContains(resposta, "Qualidade das evidências")
        self.assertIsNone(resposta.context["resultado"]["qualidade_dados"]["score"])
        self.assertEqual(resposta.context["resultado"]["atual"]["media"], 30)
        dados["servicos-0-probabilidade_condicional"] = "0"
        resposta = self.client.post(url, dados)
        self.assertContains(resposta, "chance condicional")
        self.assertEqual(resposta.context["resultado"]["atual"]["media"], 10)
        dados.pop("sem_sobreposicao")
        self.assertNotContains(self.client.post(url, dados), "Resultado da hipótese compartilhada")
        sem = get_user_model().objects.create_user("sem-relacao-compartilhada")
        sem.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventario", codename__in=["view_ativo", "view_cenariofinanceiro"]))
        self.autenticar(sem)
        self.assertEqual(self.client.post(url, dados).status_code, 403)

    def test_faixas_de_custo_e_probabilidade_usam_amostras_comuns(self):
        from inventario.aplicacao.cenario_financeiro import analisar_sensibilidade
        c = self.salvar(probabilidade=Decimal("0.5"), custo_hora=Decimal("0"), custo_adicional=Decimal("100"))
        faixas = {"probabilidade": (0, 1), "custo_adicional": (0, 200)}
        r = analisar_sensibilidade(c, self.usuario, faixas, n=1000, seed=7)
        self.assertEqual(r, analisar_sensibilidade(c, self.usuario, faixas, n=1000, seed=7))
        self.assertEqual(r["media_base"], calcular_cenario(c, self.usuario, n=1000, seed=7)["atual"]["media"])
        prob, custo = r["faixas"]
        self.assertEqual((prob["media_min"], prob["media_max"]), (0, 100))
        self.assertEqual(custo["media_min"], 0)
        self.assertEqual(custo["media_max"], r["media_base"] * 2)
        self.assertEqual(c.probabilidade, Decimal("0.5"))
        self.assertEqual(c.custo_adicional, Decimal("100"))
        for intervalo in ({}, {"probabilidade": (.6, .9)}, {"probabilidade": (0, float("nan"))}, {"outro": (0, 1)}):
            with self.subTest(intervalo=intervalo), self.assertRaises(ValueError):
                analisar_sensibilidade(c, self.usuario, intervalo, n=100)
        with self.assertRaises(ValueError):
            analisar_sensibilidade(c, self.usuario, faixas, n=20001)

    def test_sensibilidade_formulario_e_acesso(self):
        c = self.salvar()
        url = f"/cenarios-financeiros/{c.pk}/sensibilidade/"
        dados = {"origem": "Estimativa sintética", "probabilidade_min": "0.1", "probabilidade_max": "0.8", "n": 100, "seed": 42}
        r = self.client.post(url, dados)
        self.assertContains(r, "Resultado por premissa")
        self.assertContains(r, "Qualidade das evidências")
        self.assertIsNone(r.context["resultado"]["qualidade_dados"]["score"])
        self.assertEqual(r.context["resultado"]["faixas"][0]["campo"], "probabilidade")
        dados["probabilidade_min"] = "0.6"
        self.assertContains(self.client.post(url, dados), "deve incluir o valor original")
        dados["probabilidade_min"] = ""
        self.assertContains(self.client.post(url, dados), "Informe mínimo e máximo")
        sem = get_user_model().objects.create_user("sem-sensibilidade")
        self.autenticar(sem)
        self.assertEqual(self.client.post(url, dados).status_code, 403)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url).url, "/mfa/")

    def test_papeis_padrao_restringem_contexto_financeiro(self):
        call_command("configurar_grupos", verbosity=0)
        for nome in ("Operadores", "Auditores"):
            self.assertFalse(Group.objects.get(name=nome).permissions.filter(content_type__model="cenariofinanceiro").exists())
        self.assertTrue(Group.objects.get(name="Gerentes").permissions.filter(codename="view_cenariofinanceiro").exists())
