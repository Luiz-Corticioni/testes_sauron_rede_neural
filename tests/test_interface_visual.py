"""Contrato da interface: navegação, permissões e estados compreensíveis."""
from html.parser import HTMLParser
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse
from .base import BancoTeste


class InterfaceVisual(BancoTeste):
    def test_tabelas_de_uso_diario_identificam_contexto_e_colunas(self):
        for url, legenda in (("ativos", "Ativos que correspondem aos filtros"),
                             ("vulnerabilidades", "Vulnerabilidades que correspondem aos filtros"),
                             ("alertas", "Alertas na seleção atual")):
            with self.subTest(url=url):
                resposta = self.client.get(reverse(url))
                self.assertContains(resposta, f"<caption>{legenda}</caption>")
                self.assertContains(resposta, 'scope="col"')

    def test_atalhos_do_painel_financeiro_apontam_para_secoes_presentes(self):
        resposta = self.client.get(reverse("montecarlo"))
        for destino in ("mc-executivo-titulo", "mc-controles-titulo", "mc-corrigir-titulo", "mc-tabelas-titulo"):
            self.assertContains(resposta, f'href="#{destino}"')
            self.assertContains(resposta, f'id="{destino}"')

    def test_erros_de_formulario_tem_descricoes_existentes(self):
        class Campos(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids, self.descricoes_invalidas = [], []
            def handle_starttag(self, tag, attrs):
                dados = dict(attrs)
                if "id" in dados:
                    self.ids.append(dados["id"])
                if dados.get("aria-invalid") == "true":
                    self.descricoes_invalidas.append(dados.get("aria-describedby", "").split())

        resposta = self.client.post(reverse("criar_ativo"), {})
        self.assertContains(resposta, "Confira os campos indicados")
        parser = Campos()
        parser.feed(resposta.content.decode("utf-8"))
        self.assertTrue(parser.descricoes_invalidas)
        for referencias in parser.descricoes_invalidas:
            self.assertTrue(referencias)
            for referencia in referencias:
                self.assertEqual(parser.ids.count(referencia), 1)

    def test_erro_de_campo_oculto_permanece_visivel(self):
        from django import forms
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        class FormularioTeste(forms.Form):
            versao = forms.CharField(widget=forms.HiddenInput, label="Versão")

        request = RequestFactory().get("/")
        request.user = self.usuario
        form = FormularioTeste(data={})
        self.assertFalse(form.is_valid())
        pagina = render_to_string("inventario/formulario.html", {"form": form, "titulo": "Teste"}, request)
        self.assertIn("Versão:", pagina)
        self.assertIn("Este campo é obrigatório", pagina)

    @override_settings(SAURON_EMAIL_ENABLED=False)
    def test_totp_fica_visivel_quando_email_nao_esta_configurado(self):
        resposta = self.client.get(reverse("mfa"))
        self.assertContains(resposta, 'class="decision" open')
        self.assertContains(resposta, "código atual de seis dígitos")

    def test_painel_tem_inventario_e_nao_diz_monitoramento_automatico(self):
        resposta = self.client.get(reverse("dashboard"))
        self.assertContains(resposta, "Visão geral de segurança")
        self.assertContains(resposta, "Ativos cadastrados")
        self.assertContains(resposta, "Incidências pendentes")
        self.assertContains(resposta, "buscar-menu")
        self.assertContains(resposta, "inventario/interface.css")
        self.assertNotContains(resposta, 'class="nav-index"')

    def test_menu_de_usuario_comum_nao_expoe_acoes_restritas(self):
        usuario = get_user_model().objects.create_user("leitor-interface", password="senha-teste-123")
        self.autenticar(usuario)
        resposta = self.client.get(reverse("guia"))
        self.assertContains(resposta, "buscar-menu")
        self.assertNotContains(resposta, 'href="/admin/"')
        self.assertNotContains(resposta, 'href="/alertas/"')
        self.assertNotContains(resposta, 'href="/imune/"')
        self.assertContains(resposta, 'class="brand" href="/guia/"')
        self.assertNotContains(resposta, "Cadastrar ativo</a>")
        self.assertNotContains(resposta, "Importar CSV</b>")

    def test_certificados_sem_permissao_nao_parecem_lista_vazia(self):
        usuario = get_user_model().objects.create_user("leitor-dashboard", password="senha-teste-123")
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario",
            codename__in=["view_ativo", "view_vulnerabilidade", "view_incidencia", "view_dependencia"]))
        self.autenticar(usuario)
        resposta = self.client.get(reverse("dashboard"))
        self.assertContains(resposta, "Sua conta não tem permissão para consultar certificados.")

    def test_ausencia_de_dados_nao_se_apresenta_como_indice_zero(self):
        from unittest.mock import patch
        from inventario.aplicacao.painel import contexto_painel
        contexto = contexto_painel()
        contexto.update(risco=None, risco_json={}, indicadores=[], indice_medio=0, erro_risco="indisponível")
        with patch("inventario.aplicacao.painel.contexto_painel", return_value=contexto):
            resposta = self.client.get(reverse("dashboard"))
        self.assertContains(resposta, "Índice global indisponível")
        self.assertContains(resposta, "Índice indisponível; confira")
        self.assertNotContains(resposta, 'data-global-index>0')
