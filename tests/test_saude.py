
from unittest.mock import patch
from django.test import override_settings
from .base import BancoTeste


class R19(BancoTeste):
    def setUp(self):
        super().setUp()
        from inventario.web.saude import limite
        limite.clear()

    def test_publico_minimo_sem_introspeccao(self):
        self.client.logout()
        with patch("django.db.backends.utils.CursorWrapper.execute",side_effect=AssertionError("Liveness não consulta DB")), patch(
                "tempfile.NamedTemporaryFile",side_effect=AssertionError("Não escreve arquivo")):
            r=self.client.get("/api/saude/")
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json(),{"status":"ok"})
        self.assertEqual(self.client.get("/api/saude/detalhe/").status_code,302)

    @override_settings(SAURON_SAUDE_LIMITE_IP=3)
    def test_rate_limit(self):
        self.client.logout()
        for _ in range(3):
            self.assertEqual(self.client.get("/api/saude/").status_code,200)
        self.assertEqual(self.client.get("/api/saude/").status_code,429)

    def test_detalhe_exige_login_e_permissao(self):
        self.assertIn(self.client.get("/api/saude/detalhe/").status_code,(200,503))

