import json
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from inventario.aplicacao.cowrie import converter
from inventario.models import EventoHoneypot, RegistroAuditoria, SensorHoneypot
from .base import BancoTeste

LOTE = "a47ac10b-58cc-4372-a567-0e02b2c3d479"


class CowrieTeste(BancoTeste):
    def setUp(self):
        super().setUp()
        self.sensor = SensorHoneypot.objects.create(nome="Sensor", responsavel="Equipe", ativo=self.a)
        evento = {"eventid": "cowrie.login.failed", "timestamp": "2026-11-13T12:00:00Z",
                  "src_ip": "192.0.2.10", "username": "segredo_usuario", "password": "segredo_senha"}
        self.conteudo = (json.dumps(evento) + "\n" + json.dumps(evento) + "\n" +
                         json.dumps({"eventid": "cowrie.session.input", "input": "segredo_comando"})).encode()

    def test_conversao(self):
        reduzido, ignorados = converter(self.conteudo, LOTE)
        self.assertEqual(ignorados, 1)
        self.assertEqual(len(json.loads(reduzido)), 2)
        self.assertNotIn(b"segredo", reduzido)
        with self.assertRaises(ValidationError):
            converter(b'{"eventid":', LOTE)

    def test_previa_confirmacao_idempotencia_e_segredos(self):
        endereco = f"/honeypot/{self.sensor.pk}/cowrie/"
        def upload():
            return SimpleUploadedFile("cowrie.json", self.conteudo)
        resposta = self.client.post(endereco, {"arquivo": upload(), "lote": LOTE})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(EventoHoneypot.objects.count(), 0)
        token = resposta.context["form"].initial["confirmacao"]
        resposta = self.client.post(endereco, {"arquivo": upload(), "lote": LOTE, "confirmacao": token})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(EventoHoneypot.objects.count(), 2)
        self.client.post(endereco, {"arquivo": upload(), "lote": LOTE, "confirmacao": token})
        self.assertEqual(EventoHoneypot.objects.count(), 2)
        self.assertNotIn("segredo", str(list(EventoHoneypot.objects.values())))
        self.assertNotIn("segredo", str(list(RegistroAuditoria.objects.values())))

    def test_token_nao_autoriza_arquivo_alterado(self):
        endereco = f"/honeypot/{self.sensor.pk}/cowrie/"
        resposta = self.client.post(endereco, {"arquivo": SimpleUploadedFile("a", self.conteudo), "lote": LOTE})
        token = resposta.context["form"].initial["confirmacao"]
        alterado = self.conteudo.replace(b"192.0.2.10", b"192.0.2.11")
        resposta = self.client.post(endereco, {"arquivo": SimpleUploadedFile("a", alterado), "lote": LOTE, "confirmacao": token})
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(EventoHoneypot.objects.exists())
