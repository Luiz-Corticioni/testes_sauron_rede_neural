
from unittest.mock import patch
from django.test import RequestFactory, override_settings
from inventario.models import RegistroAuditoria
from .base import BancoTeste


@override_settings(SAURON_TRUSTED_PROXIES=["127.0.0.0/8", "10.0.0.0/8"],
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class R8(BancoTeste):
    def test_cadeia_proxy_confiavel(self):
        from inventario.seguranca import ip_cliente
        rf = RequestFactory()
        self.assertEqual(ip_cliente(rf.get("/", REMOTE_ADDR="127.0.0.1",
            HTTP_X_FORWARDED_FOR="8.8.8.8, 203.0.113.9, 10.0.0.2")), "203.0.113.9")
        self.assertEqual(ip_cliente(rf.get("/", REMOTE_ADDR="203.0.113.3",
            HTTP_X_FORWARDED_FOR="8.8.8.8")), "203.0.113.3")

    @patch("inventario.seguranca.time.sleep")
    def test_par_bloqueia_outro_ip_nao_e_global_nao_bloqueia(self, dormir):
        self.client.logout()
        for _ in range(5):
            self.client.post("/entrar/", {"username":"teste", "password":"errada"},
                             REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.1")
        self.assertEqual(self.client.post("/entrar/", {"username":"teste","password":"errada"},
            REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.1").status_code, 429)
        self.assertNotEqual(self.client.post("/entrar/", {"username":"teste","password":"errada"},
            REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.2").status_code, 429)
        self.assertTrue(dormir.called)

    @patch("inventario.seguranca.time.sleep")
    def test_spraying_e_nome_desconhecido_privado(self, dormir):
        self.client.logout()
        for n in range(20):
            self.client.post("/entrar/", {"username":f"inexistente{n}", "password":"errada"})
        self.assertEqual(self.client.post("/entrar/", {"username":"mais-um", "password":"errada"}).status_code, 429)
        registros = RegistroAuditoria.objects.filter(acao="LOGIN_FALHOU")
        self.assertEqual(registros.count(), 20)
        for r in registros:
            self.assertTrue(r.entidade_id.startswith("<desconhecido:"))
            self.assertNotIn("inexistente", str(r.detalhes))


class Grupos(BancoTeste):
    def test_permissoes_e_rotas_por_grupo(self):
        from django.contrib.auth.models import Group
        from django.contrib.auth import get_user_model
        from django.urls import reverse
        from inventario.management.commands.configurar_grupos import configurar_grupos
        configurar_grupos()
        for nome in ("Gerentes", "Operadores", "Auditores"):
            usuario = get_user_model().objects.create_user(nome)
            usuario.groups.add(Group.objects.get(name=nome))
            self.autenticar(usuario)
            self.assertEqual(self.client.get("/").status_code, 200)
            self.assertEqual(usuario.has_perm("inventario.declarar_linha_base_saudavel"), nome=="Gerentes")
            self.assertEqual(usuario.has_perm("inventario.aprovar_aceite_risco"), nome=="Gerentes")
            if nome=="Auditores":
                self.assertEqual(self.client.post(reverse("status_incidencia_web", args=[self.i.pk]),
                    {"status":"TRATAMENTO"}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get("/").status_code, 302)

