from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command, CommandError
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from .base import BancoTeste


class PoliticaAcesso(BancoTeste):
    def leitor(self, nome='leitor'):
        u = get_user_model().objects.create_user(nome, email='leitor@example.org', password='senha-teste-123')
        u.user_permissions.set(Permission.objects.filter(content_type__app_label='inventario', codename__startswith='view_'))
        return u

    def test_leitor_sem_dispositivo_e_novo_login_exigem_mfa(self):
        u = self.leitor()
        self.client.force_login(u)
        self.assertEqual(self.client.get('/ativos/').url, '/mfa/')
        self.autenticar(u)
        self.assertEqual(self.client.get('/ativos/').status_code, 200)
        self.client.logout()
        self.client.force_login(u)
        self.assertEqual(self.client.get('/ativos/').url, '/mfa/')

    def test_confirmacao_email_nao_dispensa_mfa_em_nova_sessao(self):
        from inventario.aplicacao.mfa_email import hash_email
        from inventario.models import DispositivoEmail
        u = self.leitor()
        DispositivoEmail.objects.filter(user=u).update(confirmed=True, email_confirmado_hash=hash_email(u.email))
        self.client.force_login(u)
        self.assertEqual(self.client.get('/ativos/').url, '/mfa/')

    def test_leitor_com_mfa_nao_entra_no_admin_nem_muta(self):
        u = self.leitor()
        self.autenticar(u)
        for url in ('/admin/', '/admin/auth/user/', '/admin/auth/group/', '/admin/auth/user/add/', '/ativos/novo/', f'/ativos/{self.a.pk}/editar/', f'/ativos/{self.a.pk}/remover/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(f'/ativos/{self.a.pk}/remover/').status_code, 403)
        self.a.refresh_from_db()

    def test_staff_com_permissao_auth_nao_eleva_privilegios(self):
        u = self.leitor()
        u.is_staff = True
        u.save()
        u.user_permissions.add(*Permission.objects.filter(content_type__app_label='auth'))
        self.autenticar(u)
        for url in ('/admin/auth/user/', '/admin/auth/user/add/', '/admin/auth/group/', f'/admin/auth/user/{u.pk}/change/'):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(f'/admin/auth/user/{u.pk}/change/', {'is_superuser': 'on'}).status_code, 403)
        u.refresh_from_db()
        self.assertFalse(u.is_superuser)

    def test_admin_pode_solicitar_email_quando_smtp_configurado(self):
        self.client.force_login(self.usuario)
        with patch('inventario.web.views_mfa.enviar_codigo', return_value='nonce') as enviar:
            self.assertContains(self.client.post('/mfa/', {'acao': 'enviar_email'}), 'aceitou o envio')
            enviar.assert_called_once()

    def test_promocao_revoga_fator_email_existente(self):
        from inventario.aplicacao.mfa_email import hash_email
        from inventario.models import DispositivoEmail
        u = self.leitor()
        d = DispositivoEmail.objects.get(user=u)
        d.confirmed = True
        d.email_confirmado_hash = hash_email(u.email)
        d.save()
        self.client.force_login(u)
        s = self.client.session
        s['otp_device_id'] = d.persistent_id
        s.save()
        self.assertEqual(self.client.get('/ativos/').status_code, 200)
        get_user_model().objects.filter(pk=u.pk).update(is_staff=True)
        self.assertEqual(self.client.get('/ativos/').url, '/mfa/')

    def test_totp_de_outro_usuario_nao_valida(self):
        u = self.leitor()
        self.client.force_login(u)
        d = TOTPDevice.objects.get(user=self.usuario)
        token = totp(d.bin_key)
        self.assertEqual(self.client.post('/mfa/', {'dispositivo': d.pk, 'password': 'senha-teste-123', 'token': str(token)}).status_code, 200)
        self.assertEqual(self.client.get('/ativos/').url, '/mfa/')

    def test_totp_recusa_senha_alterada_antes_da_trava(self):
        from django.contrib.auth.hashers import make_password
        from inventario.infraestrutura.auditoria import travar_escrita
        self.client.force_login(self.usuario)
        dispositivo = TOTPDevice.objects.get(user=self.usuario)
        token = str(totp(dispositivo.bin_key)).zfill(dispositivo.digits)
        nova_senha = make_password('SenhaNovaForte456!')
        def trocar():
            get_user_model().objects.filter(pk=self.usuario.pk).update(password=nova_senha)
            travar_escrita()
        with patch('inventario.infraestrutura.auditoria.travar_escrita', side_effect=trocar):
            resposta = self.client.post('/mfa/', {'dispositivo': dispositivo.pk, 'password': 'senha-teste-123', 'token': token})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Senha ou código do autenticador inválido')

    def test_recuperacao_revoga_sessao_e_exige_confirmacao_novo_totp(self):
        antigo = TOTPDevice.objects.get(user=self.usuario)
        with self.assertRaises(CommandError):
            call_command('provisionar_mfa', usuario=self.usuario.username, substituir=True, stdout=StringIO())
        call_command('provisionar_mfa', usuario=self.usuario.username, substituir=True, motivo='ticket-123 validado presencialmente', stdout=StringIO())
        self.assertFalse(TOTPDevice.objects.filter(pk=antigo.pk).exists())
        novo = TOTPDevice.objects.get(user=self.usuario)
        self.assertFalse(novo.confirmed)
        self.assertEqual(self.client.get('/').url, '/mfa/')
        codigo = totp(novo.bin_key, step=novo.step, t0=novo.t0, digits=novo.digits, drift=novo.drift)
        self.assertEqual(self.client.post('/mfa/', {'dispositivo': novo.pk, 'password': 'senha-teste-123', 'token': str(codigo)}).status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_cli_criacao_admin_nao_autentica_sem_mfa(self):
        from inventario.cli import SauronCLI
        cli = SauronCLI(entrada=lambda _: '', saida=lambda _: None)
        cli.usuario = self.usuario
        with patch.object(cli, '_exigir', return_value=True), patch.object(cli, '_texto', side_effect=['novo-admin', 'novo@example.org']), patch('inventario.cli_menus.sistema.getpass', return_value='SenhaForte2026!'):
            cli.criar_admin()
        self.assertIsNone(cli.usuario)
        self.assertTrue(get_user_model().objects.get(username='novo-admin').is_superuser)

    def test_cli_revogacao_permissao_e_desativacao_sao_imediatas(self):
        from inventario.cli import SauronCLI
        cli = SauronCLI(entrada=lambda _: '', saida=lambda _: None)
        u = self.leitor()
        cli.usuario = u
        self.assertTrue(cli._exigir('inventario.view_ativo'))
        u.user_permissions.clear()
        self.assertFalse(cli._exigir('inventario.view_ativo'))
        get_user_model().objects.filter(pk=u.pk).update(is_active=False)
        self.assertFalse(cli._exigir('inventario.view_ativo'))
        self.assertIsNone(cli.usuario)

    def test_cli_dispositivo_recuperado_revoga_sessao(self):
        from inventario.cli import SauronCLI
        cli = SauronCLI(entrada=lambda _: '', saida=lambda _: None)
        cli.usuario = self.usuario
        d = TOTPDevice.objects.get(user=self.usuario)
        cli._mfa_cli_id = d.persistent_id
        d.delete()
        self.assertFalse(cli._exigir('inventario.view_ativo'))
        self.assertIsNone(cli.usuario)

    def test_paginas_e_apis_locais_integram_sem_erros_e_valores_nao_finitos(self):
        import json
        paginas = ('/', '/ativos/', f'/ativos/{self.a.pk}/', '/vulnerabilidades/', '/incidencias/', '/dependencias/', '/salas/', '/software/', '/mapa/', '/matrizes/', '/prioridades/', '/imune/', '/alertas/', '/auditoria/', '/modo-euler/', '/montecarlo/', '/comparar-cvss/', '/guia/', '/importar/')
        for url in paginas:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        for url in ('/api/ativos/', '/api/risco/', '/api/risco/historico/', '/api/auditoria/verificar/'):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200)
                json.dumps(r.json(), allow_nan=False)
        dados = self.client.get('/api/ativos/').json()
        self.assertEqual(dados['quantidade'], len(dados['ativos']))
        self.assertIn(self.a.pk, [a['id'] for a in dados['ativos']])

    def test_producao_recusa_host_externo_sem_tls(self):
        import os
        import secrets
        import subprocess
        import sys
        env = dict(os.environ, SAURON_DEBUG='0', SAURON_SECRET_KEY=secrets.token_urlsafe(64), SAURON_AUDIT_HMAC_KEY=secrets.token_urlsafe(64), SAURON_ALLOWED_HOSTS='sauron.example.org', SAURON_SECURE_COOKIES='0', SAURON_SSL_REDIRECT='0')
        r = subprocess.run([sys.executable, '-c', 'from sauron_web import settings'], env=env, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Hosts externos exigem', r.stderr)

    def test_escrita_sem_staff_tambem_exige_totp(self):
        from inventario.seguranca_mfa import usuario_privilegiado
        u = self.leitor()
        self.assertFalse(usuario_privilegiado(u))
        u.user_permissions.add(Permission.objects.get(content_type__app_label='inventario', codename='add_ativo'))
        u = get_user_model().objects.get(pk=u.pk)
        self.assertFalse(u.is_staff)
        self.assertTrue(usuario_privilegiado(u))

    def test_cli_escrita_exige_reautenticacao_recente(self):
        from inventario.cli import SauronCLI
        import time
        cli = SauronCLI(entrada=lambda _: '', saida=lambda _: None)
        cli.usuario = self.usuario
        cli._reauth_cli = time.monotonic() - 301
        with patch('inventario.cli.getpass', return_value='senha-teste-123'), patch.object(cli, '_validar_mfa_cli', return_value=False) as validar:
            self.assertFalse(cli._exigir('inventario.add_ativo'))
            validar.assert_called_once()
