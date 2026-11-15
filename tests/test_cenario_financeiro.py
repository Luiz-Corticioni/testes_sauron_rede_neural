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

    def test_papeis_padrao_restringem_contexto_financeiro(self):
        call_command("configurar_grupos", verbosity=0)
        for nome in ("Operadores", "Auditores"):
            self.assertFalse(Group.objects.get(name=nome).permissions.filter(content_type__model="cenariofinanceiro").exists())
        self.assertTrue(Group.objects.get(name="Gerentes").permissions.filter(codename="view_cenariofinanceiro").exists())
