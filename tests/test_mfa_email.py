from unittest import skip
import re
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, override_settings
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from .base import BancoTeste


CONFIG = dict(
    SAURON_EMAIL_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST="smtp.example.org",
    DEFAULT_FROM_EMAIL="sauron@example.org",
    EMAIL_USE_TLS=True,
    EMAIL_USE_SSL=False,
)


@override_settings(**CONFIG)
class VerificacaoEmail(BancoTeste):
    @override_settings(EMAIL_HOST_USER="conta@example.org", EMAIL_HOST_PASSWORD="")
    def test_configuracao_smtp_rejeita_credenciais_incompletas(self):
        from inventario.aplicacao.mfa_email import configuracao_valida, ErroMFAEmail
        with self.assertRaises(ErroMFAEmail):
            configuracao_valida()

    @skip("MFA desativado nesta branch de apresentação")
    def test_codigo_por_email_funciona_para_gmail_e_ufu_inclusive_administrador(self):
        for n, dominio in enumerate(('gmail.com', 'ufu.br')):
            with self.subTest(dominio=dominio):
                u = get_user_model().objects.create_user(f'teste-dominio-{n}', email=f'usuario@{dominio}', password='SenhaDeTeste123!', is_staff=n == 1, is_superuser=n == 1)
                if n == 0:
                    from django.contrib.auth.models import Permission
                    u.user_permissions.set(Permission.objects.filter(content_type__app_label='inventario', codename__in=['view_ativo', 'view_vulnerabilidade', 'view_incidencia', 'view_dependencia']))
                self.client.force_login(u)
                mail.outbox.clear()
                resposta = self.client.post('/mfa/', {'acao': 'enviar_email'})
                self.assertContains(resposta, 'aceitou o envio')
                self.assertEqual(mail.outbox[-1].to, [f'usuario@{dominio}'])
                codigo = re.search(r'\b[0-9]{6}\b', mail.outbox[-1].body).group()
                self.assertEqual(self.client.post('/mfa/', {'acao': 'verificar_email', 'password': 'SenhaDeTeste123!', 'token': codigo}).status_code, 302)
                self.assertEqual(self.client.get('/').status_code, 200)

    def test_administrador_usa_email_no_terminal(self):
        from inventario.cli import SauronCLI
        u = get_user_model().objects.create_superuser('admin-email', email='admin@ufu.br', password='SenhaDeTeste123!')
        cli = SauronCLI(entrada=lambda _: '', saida=lambda _: None)
        mail.outbox.clear()
        def codigo(_):
            return re.search(r'\b[0-9]{6}\b', mail.outbox[-1].body).group()
        with patch('inventario.cli.getpass', side_effect=codigo):
            self.assertTrue(cli._validar_mfa_cli(u, 'SenhaDeTeste123!'))
        self.assertEqual(mail.outbox[-1].to, ['admin@ufu.br'])

    def criar(self):
        with self.captureOnCommitCallbacks(execute=True):
            return self._criar_leitor(
                "primeiro_admin", "dono@example.org", "SenhaDeTeste123!"
            )

    def _criar_leitor(self, *args):
        from django.contrib.auth.models import Permission
        u = get_user_model().objects.create_user(*args)
        u.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario", codename__startswith="view_"))
        return u

    def entrar(self, usuario):
        self.client.logout()
        self.assertTrue(self.client.login(username=usuario.username, password="SenhaDeTeste123!"))
        return self.client.get("/")

    def codigo(self):
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["dono@example.org"])
        return re.search(r"\b[0-9]{6}\b", mail.outbox[0].body).group()

    @skip("MFA desativado nesta branch de apresentação")
    def test_senha_alterada_entre_calculo_e_trava_impede_autenticacao(self):
        from django.contrib.auth.hashers import make_password
        from inventario.aplicacao.mfa_email import adotar_desafio_inicial, verificar_codigo
        from inventario.infraestrutura.auditoria import travar_escrita
        u = self.criar()
        codigo = self.codigo()
        nonce = adotar_desafio_inicial(u)
        nova_senha = make_password('OutraSenhaForte456!')
        def trocar():
            get_user_model().objects.filter(pk=u.pk).update(password=nova_senha)
            travar_escrita()
        with patch('inventario.aplicacao.mfa_email.travar_escrita', side_effect=trocar):
            self.assertIsNone(verificar_codigo(u, nonce, codigo, 'SenhaDeTeste123!'))

    @skip("MFA desativado nesta branch de apresentação")
    def test_leitor_recebe_email_e_acessa_com_codigo(self):
        u = self.criar()
        codigo = self.codigo()
        self.assertEqual(self.entrar(u).url, "/mfa/")
        # Login real instala o desafio criado no cadastro na sessão.
        self.client.logout()
        self.client.post("/entrar/", {"username": u.username, "password": "SenhaDeTeste123!"})
        r = self.client.post(
            "/mfa/", {"acao": "verificar_email", "password": "SenhaDeTeste123!", "token": codigo}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 200)
        from inventario.models import DispositivoEmail

        d = DispositivoEmail.objects.get(user=u)
        self.assertTrue(d.confirmed)
        self.assertFalse(d.codigo_hash)
        from inventario.models import RegistroAuditoria

        self.assertNotIn(codigo, [str(value) for value in DispositivoEmail.objects.values().get(pk=d.pk).values()])
        for registro in RegistroAuditoria.objects.values("detalhes"):
            self.assertNotEqual(registro["detalhes"], codigo)
        self.client.logout()
        self.client.login(username=u.username, password="SenhaDeTeste123!")
        self.assertEqual(
            self.client.post(
                "/mfa/",
                {"acao": "verificar_email", "password": "SenhaDeTeste123!", "token": codigo},
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get("/").status_code, 302)

    @skip("MFA desativado nesta branch de apresentação")
    def test_codigo_errado_expirado_e_excesso_de_tentativas(self):
        from inventario.aplicacao.mfa_email import verificar_codigo
        from inventario.models import DispositivoEmail

        u = self.criar()
        codigo = self.codigo()
        d = DispositivoEmail.objects.get(user=u)
        nonce = d.nonce
        for _ in range(5):
            self.assertIsNone(
                verificar_codigo(
                    u, nonce, "999999" if codigo != "999999" else "888888", "SenhaDeTeste123!"
                )
            )
        d.refresh_from_db()
        self.assertIsNotNone(d.bloqueado_ate)
        self.assertIsNone(verificar_codigo(u, nonce, codigo, "SenhaDeTeste123!"))
        d.bloqueado_ate = timezone.now() - timedelta(seconds=1)
        d.expira_em = timezone.now() - timedelta(seconds=1)
        d.save(update_fields=["bloqueado_ate", "expira_em"])
        self.assertIsNone(verificar_codigo(u, nonce, codigo, "SenhaDeTeste123!"))

    @skip("MFA desativado nesta branch de apresentação")
    def test_reenvio_tem_limite_e_falha_de_email_nao_libera_codigo(self):
        from inventario.aplicacao.mfa_email import enviar_codigo, ErroMFAEmail
        from inventario.models import DispositivoEmail

        u = self.criar()
        with self.assertRaises(ErroMFAEmail):
            enviar_codigo(u)
        d = DispositivoEmail.objects.get(user=u)
        d.reenviar_apos = timezone.now() - timedelta(seconds=1)
        d.save(update_fields=["reenviar_apos"])
        with patch("inventario.aplicacao.mfa_email.send_mail", side_effect=OSError("smtp")):
            with self.assertRaises(ErroMFAEmail):
                enviar_codigo(u)
        d.refresh_from_db()
        self.assertFalse(d.codigo_hash)
        self.assertIsNone(d.reenviar_apos)

    @skip("MFA desativado nesta branch de apresentação")
    def test_troca_de_email_revoga_sessao_validada_por_email(self):
        from inventario.aplicacao.mfa_email import verificar_codigo
        from inventario.models import DispositivoEmail
        from django_otp import DEVICE_ID_SESSION_KEY

        u = self.criar()
        codigo = self.codigo()
        d = DispositivoEmail.objects.get(user=u)
        d = verificar_codigo(u, d.nonce, codigo, "SenhaDeTeste123!")
        self.client.force_login(u)
        sessao = self.client.session
        sessao[DEVICE_ID_SESSION_KEY] = d.persistent_id
        sessao["sauron_reauth_em"] = timezone.now().timestamp()
        sessao.save()
        self.assertEqual(self.client.get("/").status_code, 200)
        get_user_model().objects.filter(pk=u.pk).update(email="novo@example.org")
        self.assertEqual(self.client.get("/").url, "/mfa/")

    def test_totp_existe_como_alternativa(self):
        from django_otp.oath import totp

        u = self.criar()
        d = TOTPDevice.objects.create(user=u, name="App autenticador", confirmed=True)
        self.client.logout()
        self.client.post("/entrar/", {"username": u.username, "password": "SenhaDeTeste123!"})
        token = totp(d.bin_key, step=d.step, t0=d.t0, digits=d.digits, drift=d.drift)
        r = self.client.post(
            "/mfa/", {"dispositivo": d.pk, "password": "SenhaDeTeste123!", "token": str(token)}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 200)

    @skip("MFA desativado nesta branch de apresentação")
    def test_formularios_exigem_csrf(self):
        u = self.criar()
        c = Client(enforce_csrf_checks=True)
        c.force_login(u)
        self.assertEqual(c.post("/mfa/", {"acao": "enviar_email"}).status_code, 403)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(SAURON_EMAIL_ENABLED=False)
    @skip("MFA desativado nesta branch de apresentação")
    def test_sem_smtp_da_instrucoes_sem_burlar_mfa(self):
        u = self.criar()
        self.assertEqual(len(mail.outbox), 0)
        self.client.logout()
        self.client.force_login(u)
        r = self.client.get("/mfa/")
        self.assertContains(r, "configurar o envio de e-mail")
        self.assertEqual(self.client.get("/").url, "/mfa/")

    @skip("MFA desativado nesta branch de apresentação")
    def test_admin_cria_usuario_com_email_obrigatorio_e_envia_apos_commit(self):
        r = self.client.post(
            "/admin/auth/user/add/",
            {
                "username": "analista",
                "password1": "SenhaBemForte2026!",
                "password2": "SenhaBemForte2026!",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="analista").exists())
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/admin/auth/user/add/",
                {
                    "username": "analista",
                    "email": "analista@example.org",
                    "password1": "SenhaBemForte2026!",
                    "password2": "SenhaBemForte2026!",
                },
            )
        self.assertEqual(r.status_code, 302)
        u = get_user_model().objects.get(username="analista")
        self.assertFalse(u.dispositivo_email.confirmed)
        self.assertEqual(mail.outbox[0].to, ["analista@example.org"])
        # Conta nova sem privilégios também confirma o e-mail antes do primeiro acesso.
        self.client.logout()
        self.client.post("/entrar/", {"username": "analista", "password": "SenhaBemForte2026!"})
        self.assertEqual(self.client.get("/software/").url, "/mfa/")
        codigo = re.search(r"\b[0-9]{6}\b", mail.outbox[0].body).group()
        self.assertEqual(
            self.client.post(
                "/mfa/",
                {"acao": "verificar_email", "password": "SenhaBemForte2026!", "token": codigo},
            ).status_code,
            302,
        )
        u.dispositivo_email.refresh_from_db()
        self.assertTrue(u.dispositivo_email.confirmed)

    def test_transacao_cancelada_nao_envia_mensagem(self):
        from django.db import transaction

        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    get_user_model().objects.create_user(
                        "cancelado", email="destino@example.org", password="SenhaTeste123!"
                    )
                    raise ValueError("rollback")
            except ValueError:
                pass
        self.assertFalse(get_user_model().objects.filter(username="cancelado").exists())
        self.assertEqual(len(mail.outbox), 0)

    @skip("MFA desativado nesta branch de apresentação")
    def test_novo_email_exige_confirmacao_e_recebe_novo_codigo(self):
        from inventario.aplicacao.mfa_email import verificar_codigo
        from inventario.models import DispositivoEmail

        u = self.criar()
        d = DispositivoEmail.objects.get(user=u)
        self.assertIsNotNone(verificar_codigo(u, d.nonce, self.codigo(), "SenhaDeTeste123!"))
        with self.captureOnCommitCallbacks(execute=True):
            u.email = "novo@example.org"
            u.save(update_fields=["email"])
        d.refresh_from_db()
        self.assertFalse(d.confirmed)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[-1].to, ["novo@example.org"])

    @skip("MFA desativado nesta branch de apresentação")
    def test_leitor_existente_pode_solicitar_e_usar_codigo_com_zeros(self):
        with override_settings(SAURON_EMAIL_ENABLED=False):
            u = self._criar_leitor("existente", "", "SenhaDeTeste123!")
            get_user_model().objects.filter(pk=u.pk).update(email="dono@example.org")
        self.client.logout()
        self.client.post("/entrar/", {"username": "existente", "password": "SenhaDeTeste123!"})
        with patch("inventario.aplicacao.mfa_email.secrets.randbelow", return_value=0):
            r = self.client.post("/mfa/", {"acao": "enviar_email"})
        self.assertContains(r, "servidor de e-mail aceitou")
        self.assertEqual(self.codigo(), "000000")
        r = self.client.post(
            "/mfa/", {"acao": "verificar_email", "password": "SenhaDeTeste123!", "token": "000000"}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 200)

    @skip("MFA desativado nesta branch de apresentação")
    def test_codigo_inicial_so_pode_ser_adotado_por_uma_sessao(self):
        u = self.criar()
        codigo = self.codigo()
        c1 = Client()
        c2 = Client()
        c1.post("/entrar/", {"username": u.username, "password": "SenhaDeTeste123!"})
        c2.post("/entrar/", {"username": u.username, "password": "SenhaDeTeste123!"})
        self.assertTrue(c1.session.get("sauron_email_desafio"))
        self.assertFalse(c2.session.get("sauron_email_desafio"))
        r = c2.post(
            "/mfa/", {"acao": "verificar_email", "password": "SenhaDeTeste123!", "token": codigo}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(c2.get("/").url, "/mfa/")
        r = c1.post(
            "/mfa/", {"acao": "verificar_email", "password": "SenhaDeTeste123!", "token": codigo}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(c1.get("/").status_code, 200)

    def test_diagnostico_apenas_envia_quando_solicitado(self):
        from io import StringIO
        from django.core.management import call_command

        output = StringIO()
        call_command("diagnosticar_email", stdout=output)
        self.assertEqual(len(mail.outbox), 0)
        self.assertNotIn("PASSWORD", output.getvalue())
        call_command("diagnosticar_email", enviar_para="teste@example.org", stdout=output)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["teste@example.org"])
        self.assertNotRegex(mail.outbox[0].body, r"\b[0-9]{6}\b")

    @skip("MFA desativado nesta branch de apresentação")
    def test_terminal_usa_o_codigo_inicial_como_alternativa(self):
        from inventario.cli import SauronCLI

        u = self.criar()
        codigo = self.codigo()
        cli = SauronCLI(entrada=lambda _: "n", saida=lambda _: None)
        with patch("inventario.cli.getpass", return_value=codigo):
            self.assertTrue(cli._validar_mfa_cli(u, "SenhaDeTeste123!"))
        self.assertTrue(u.dispositivo_email.__class__.objects.get(user=u).confirmed)

    @skip("MFA desativado nesta branch de apresentação")
    def test_senha_errada_no_autenticador_tambem_tem_limite(self):
        dispositivo = TOTPDevice.objects.get(user=self.usuario)
        sessao = self.client.session
        sessao.pop("otp_device_id", None)
        sessao.save()
        r = self.client.post(
            "/mfa/", {"dispositivo": dispositivo.pk, "password": "senha errada", "token": "123456"}
        )
        self.assertEqual(r.status_code, 200)
        dispositivo.refresh_from_db()
        self.assertGreater(dispositivo.throttling_failure_count, 0)
