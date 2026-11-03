
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from .base import BancoTeste


class SegurancaRevisada(BancoTeste):
    def test_operador_que_confirma_correcao_precisa_mfa(self):
        operador = get_user_model().objects.create_user("operador-mfa")
        operador.user_permissions.add(Permission.objects.get(codename="change_incidencia"))
        self.client.force_login(operador)
        r = self.client.get(f"/incidencias/{self.i.pk}/editar/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/mfa/", r.url)

    @override_settings(SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
        SAURON_TRUSTED_PROXIES=["127.0.0.0/8"])
    def test_proto_falso_fora_do_proxy_nao_burla_redirect(self):
        self.client.logout()
        r = self.client.get("/entrar/", REMOTE_ADDR="198.51.100.9", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(r.status_code, 301)
        r = self.client.get("/entrar/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(r.status_code, 200)

    def test_csv_invalido_volta_com_erro_legivel(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        arquivo = SimpleUploadedFile("lote.csv", b"cabecalho,errado\n1,2\n", content_type="text/csv")
        r = self.client.post("/importar/", {"arquivo":arquivo, "aplicar":""})
        self.assertEqual(r.status_code, 200)
        self.assertIn("erros", r.context["resultado"])
        self.assertEqual(r.context["resultado"]["gravados"], 0)

