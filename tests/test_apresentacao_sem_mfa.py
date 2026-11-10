"""Contrato da branch de apresentação: autenticação por senha e permissões."""

import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from .base import BancoTeste


class ApresentacaoSemMFA(BancoTeste):
    def entrar(self, usuario, senha):
        cliente = Client(enforce_csrf_checks=True)
        cliente.get("/entrar/")
        resposta = cliente.post("/entrar/", {"username": usuario, "password": senha,
            "csrfmiddlewaretoken": cliente.cookies["csrftoken"].value})
        return cliente, resposta

    def test_administrador_entra_por_senha_sem_mfa(self):
        cliente, resposta = self.entrar("teste", "senha-teste-123")
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(cliente.get("/").status_code, 200)
        self.assertContains(cliente.get("/admin/"), "MFA DESATIVADO")
        self.assertNotIn("otp_device_id", cliente.session)
        self.assertContains(cliente.get("/"), "MFA DESATIVADO")
        self.assertEqual(cliente.get("/mfa/").url, "/")

    def test_usuario_comum_nao_acessa_admin_nem_grava(self):
        usuario = get_user_model().objects.create_user("leitor-sem-mfa", password="SenhaTeste123!")
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario",
            codename__in=["view_ativo", "view_vulnerabilidade", "view_incidencia", "view_dependencia"]))
        cliente, resposta = self.entrar(usuario.username, "SenhaTeste123!")
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(cliente.get("/").status_code, 200)
        self.assertEqual(cliente.get("/admin/").status_code, 403)
        self.assertEqual(cliente.get("/ativos/novo/").status_code, 403)
        self.assertEqual(cliente.post("/ativos/novo/", {
            "csrfmiddlewaretoken": cliente.cookies["csrftoken"].value,
        }).status_code, 403)

    def test_senha_incorreta_e_csrf_continuam_bloqueados(self):
        cliente, resposta = self.entrar("teste", "senha-errada")
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("_auth_user_id", cliente.session)
        cliente = Client(enforce_csrf_checks=True)
        self.assertEqual(cliente.post("/entrar/", {"username": "teste", "password": "senha-teste-123"}).status_code, 403)

    @override_settings(SAURON_EMAIL_ENABLED=True, EMAIL_HOST="smtp.example.org",
                       EMAIL_HOST_USER="teste", EMAIL_HOST_PASSWORD="senha",
                       DEFAULT_FROM_EMAIL="sauron@example.org", EMAIL_USE_TLS=True, EMAIL_USE_SSL=False)
    def test_cadastro_nao_envia_codigos(self):
        with patch("inventario.aplicacao.mfa_email.send_mail") as enviar, \
             self.captureOnCommitCallbacks(execute=True):
            get_user_model().objects.create_user("novo-sem-mfa", email="novo@example.org", password="SenhaTeste123!")
        enviar.assert_not_called()

    def test_terminal_entra_sem_mfa_e_reautentica_apenas_senha(self):
        from inventario.cli import SauronCLI
        cli = SauronCLI(entrada=lambda _: "teste", saida=lambda _: None)
        with patch("inventario.cli.getpass", return_value="senha-teste-123"), \
             patch.object(cli, "_validar_mfa_cli", side_effect=AssertionError("MFA não deve ser solicitado")):
            self.assertTrue(cli.login())
            cli._reauth_cli = time.monotonic() - 301
            self.assertTrue(cli._exigir("inventario.add_ativo"))
