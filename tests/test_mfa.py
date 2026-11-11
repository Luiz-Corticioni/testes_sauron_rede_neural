
from django.utils import timezone
from io import StringIO
import base64
from django.core.management import call_command
from django.test import Client
from .base import BancoTeste


class R16(BancoTeste):
    def test_chave_manual_provisionada_permite_login_totp_real(self):
        from django_otp.oath import totp
        from django_otp.plugins.otp_totp.models import TOTPDevice

        TOTPDevice.objects.filter(user=self.usuario).delete()
        saida = StringIO()
        call_command('provisionar_mfa', usuario=self.usuario.username, stdout=saida)
        chave = next(linha.split(': ', 1)[1] for linha in saida.getvalue().splitlines()
                     if linha.startswith('Chave (Base32): '))
        dispositivo = TOTPDevice.objects.get(user=self.usuario)
        self.assertEqual(base64.b32decode(chave), dispositivo.bin_key)
        self.assertFalse(dispositivo.confirmed)
        cliente = Client(enforce_csrf_checks=True)
        cliente.get('/entrar/')
        csrf = cliente.cookies['csrftoken'].value
        resposta = cliente.post('/entrar/', {'username': self.usuario.username,
            'password': 'senha-teste-123', 'csrfmiddlewaretoken': csrf})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(cliente.get('/').url, '/mfa/')
        token = str(totp(base64.b32decode(chave), step=dispositivo.step, t0=dispositivo.t0,
                         digits=dispositivo.digits)).zfill(dispositivo.digits)
        csrf = cliente.cookies['csrftoken'].value
        resposta = cliente.post('/mfa/', {'acao': 'totp', 'dispositivo': dispositivo.pk,
            'password': 'senha-teste-123', 'token': token, 'csrfmiddlewaretoken': csrf})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(cliente.get('/').status_code, 200)
        dispositivo.refresh_from_db()
        self.assertTrue(dispositivo.confirmed)

    def test_staff_sem_otp_redireciona(self):
        sessao=self.client.session
        sessao.pop("otp_device_id",None)
        sessao.save()
        resposta=self.client.get("/")
        self.assertEqual(resposta.status_code,302)
        self.assertIn("/mfa/",resposta.url)

    def test_ociosidade_expira_sessao(self):
        sessao=self.client.session
        sessao["sauron_ultima_atividade"]=timezone.now().timestamp()-31*60
        sessao.save()
        self.assertEqual(self.client.get("/").status_code,302)
        self.assertNotIn("_auth_user_id",self.client.session)

    def test_aprovacao_exige_reautenticacao_recente(self):
        sessao=self.client.session
        sessao["sauron_reauth_em"]=timezone.now().timestamp()-301
        sessao.save()
        r=self.client.post(f"/admin/inventario/ativo/{self.a.pk}/change/",{})
        self.assertEqual(r.status_code,302)
        self.assertIn("/mfa/",r.url)


    def test_token_real_e_replay(self):
        from django_otp.oath import totp
        from django_otp.plugins.otp_totp.models import TOTPDevice
        dispositivo=TOTPDevice.objects.get(user=self.usuario)
        token=totp(dispositivo.bin_key,step=dispositivo.step,t0=dispositivo.t0,
                   digits=dispositivo.digits,drift=dispositivo.drift)
        sessao=self.client.session
        sessao.pop("otp_device_id",None)
        sessao.save()
        r=self.client.post("/mfa/",{"dispositivo":dispositivo.pk,"password":"senha-teste-123","token":str(token)})
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.client.get("/").status_code,200)
        dispositivo.refresh_from_db()
        self.assertFalse(dispositivo.verify_token(str(token)))
