from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command

from inventario.aplicacao.honeypot import importar_eventos, revisar_evento, salvar_sensor
from inventario.models import EventoHoneypot, RegistroAuditoria, RevisaoEventoHoneypot, SensorHoneypot
from .base import BancoTeste
from .test_honeypot import arquivo, evento


class TriagemHoneypot(BancoTeste):
    def setUp(self):
        super().setUp()
        self.sensor = salvar_sensor(SensorHoneypot(nome="Sensor de demonstração", responsavel="SOC"), self.usuario)
        importar_eventos(self.sensor.pk, arquivo(evento()), self.usuario)
        self.evento = EventoHoneypot.objects.get(sensor=self.sensor)

    def test_revisoes_preservam_autoria_historico_e_ambiente(self):
        primeira = revisar_evento(self.evento.pk, "TESTE", "EXERCICIO", self.usuario)
        segunda = revisar_evento(self.evento.pk, "INCONCLUSIVO", "SEM_CONTEXTO", self.usuario)
        self.assertEqual(list(self.evento.revisoes.values_list("pk", flat=True)), [segunda.pk, primeira.pk])
        self.assertEqual(primeira.autor_id, self.usuario.pk)
        self.assertEqual(primeira.evento.sensor.ambiente, "DEMONSTRACAO")
        registro = RegistroAuditoria.objects.filter(acao="REVISAR", entidade="EventoHoneypot").latest("id")
        self.assertEqual(registro.usuario_id, self.usuario.pk)
        self.assertNotIn(self.evento.origem_ip, str(registro.detalhes))
        self.assertEqual(RegistroAuditoria.objects.filter(acao="REVISAR", entidade="EventoHoneypot").count(), 2)

    def test_sem_permissao_e_observacao_livre_sao_rejeitadas(self):
        usuario = get_user_model().objects.create_user("sem-triagem")
        with self.assertRaises(PermissionDenied):
            revisar_evento(self.evento.pk, "TESTE", "EXERCICIO", usuario)
        with self.assertRaises(ValidationError):
            revisar_evento(self.evento.pk, "TESTE", "senha teste", self.usuario)
        with self.assertRaises(ValidationError):
            revisar_evento(self.evento.pk, "INVALIDO", "EXERCICIO", self.usuario)
        self.assertFalse(RevisaoEventoHoneypot.objects.exists())

    def test_falha_na_auditoria_reverte_revisao(self):
        with patch("inventario.aplicacao.honeypot.registrar_evento", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                revisar_evento(self.evento.pk, "SUSPEITO", "ANALISAR", self.usuario)
        self.assertFalse(RevisaoEventoHoneypot.objects.exists())

    def test_fluxo_web_permissoes_e_mfa(self):
        url = f"/honeypot/eventos/{self.evento.pk}/revisar/"
        self.assertContains(self.client.get("/honeypot/"), url)
        self.assertEqual(self.client.post(url, {"classificacao": "SUSPEITO", "observacao": "ANALISAR"}).status_code, 302)
        self.assertContains(self.client.get(url), "Requer análise adicional")
        sem = get_user_model().objects.create_user("sem-acesso")
        self.autenticar(sem)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {"classificacao": "TESTE", "observacao": "EXERCICIO"}).status_code, 403)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url).url, "/mfa/")

    def test_papeis_padrao_restringem_triagem_e_historico(self):
        from django.contrib.auth.models import Group
        call_command("configurar_grupos", verbosity=0)
        gerente = Group.objects.get(name="Gerentes").permissions
        self.assertTrue(gerente.filter(codename="add_revisaoeventohoneypot").exists())
        self.assertFalse(gerente.filter(codename="delete_revisaoeventohoneypot").exists())
        for nome in ("Operadores", "Auditores"):
            self.assertFalse(Group.objects.get(name=nome).permissions.filter(content_type__model="revisaoeventohoneypot").exists())
