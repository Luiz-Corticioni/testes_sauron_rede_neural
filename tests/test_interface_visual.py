"""Contrato da interface: navegação, permissões e estados compreensíveis."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from .base import BancoTeste


class InterfaceVisual(BancoTeste):
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
