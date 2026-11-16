from datetime import timedelta
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from inventario.aplicacao.honeypot import alterar_retencao, aplicar_retencao, importar_eventos, revisar_evento, salvar_sensor
from inventario.models import Alerta, EventoHoneypot, PoliticaRetencaoHoneypot, RegistroAuditoria, RevisaoEventoHoneypot, SensorHoneypot
from .base import BancoTeste
from .test_honeypot import arquivo, evento


class RetencaoHoneypot(BancoTeste):
    def setUp(self):
        super().setUp()
        self.sensor = salvar_sensor(SensorHoneypot(nome="Sensor teste retenção", responsavel="SOC", ativo=self.a), self.usuario)
        importar_eventos(self.sensor.pk, arquivo(evento()), self.usuario)
        self.evento = EventoHoneypot.objects.get(sensor=self.sensor)
        EventoHoneypot.objects.filter(pk=self.evento.pk).update(recebido_em=timezone.now()-timedelta(days=100))

    def test_padrao_anonimiza_ip_preserva_revisao_recente_e_alerta(self):
        revisao = revisar_evento(self.evento.pk, "INCONCLUSIVO", "SEM_CONTEXTO", self.usuario)
        r = aplicar_retencao()
        self.assertEqual((r["dias"], r["ips_eliminados"], r["revisoes_eliminadas"], r["eventos_eliminados"]), (90, 1, 0, 0))
        self.evento.refresh_from_db()
        self.assertIsNone(self.evento.origem_ip)
        self.assertTrue(RevisaoEventoHoneypot.objects.filter(pk=revisao.pk).exists())
        self.assertTrue(Alerta.objects.filter(tipo="HONEYPOT").exists())
        pagina = self.client.get("/honeypot/")
        self.assertContains(pagina, "IP eliminado pela retenção")
        self.assertEqual(aplicar_retencao()["ips_eliminados"], 0)
        RevisaoEventoHoneypot.objects.filter(pk=revisao.pk).update(criado_em=timezone.now()-timedelta(days=91))
        r = aplicar_retencao()
        self.assertEqual((r["revisoes_eliminadas"], r["eventos_eliminados"]), (1, 1))
        self.assertTrue(Alerta.objects.filter(tipo="HONEYPOT").exists())
        registro = RegistroAuditoria.objects.filter(acao="APLICAR_RETENCAO").latest("id")
        self.assertNotIn("192.0.2.10", str(registro.detalhes))

    def test_prazo_gerencial_e_papeis(self):
        sem = get_user_model().objects.create_user("sem-retencao")
        with self.assertRaises(PermissionDenied):
            alterar_retencao(30, sem)
        for valor in (29, 181):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                alterar_retencao(valor, self.usuario)
        self.assertFalse(PoliticaRetencaoHoneypot.objects.exists())
        alterar_retencao(180, self.usuario)
        self.assertEqual(aplicar_retencao()["eventos_eliminados"], 0)
        alterar_retencao(30, self.usuario)
        self.assertEqual(aplicar_retencao()["eventos_eliminados"], 1)
        self.assertEqual(PoliticaRetencaoHoneypot.objects.get(pk=1).atualizado_por_id, self.usuario.pk)
        call_command("configurar_grupos", verbosity=0)
        for nome in ("Operadores", "Auditores"):
            self.assertFalse(Group.objects.get(name=nome).permissions.filter(content_type__model="politicaretencaohoneypot").exists())
        self.assertTrue(Group.objects.get(name="Gerentes").permissions.filter(codename="change_politicaretencaohoneypot").exists())

    def test_banco_recusa_prazo_ou_identificador_fora_da_politica(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PoliticaRetencaoHoneypot.objects.create(pk=1, dias=29)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PoliticaRetencaoHoneypot.objects.create(pk=2, dias=90)
        self.assertFalse(PoliticaRetencaoHoneypot.objects.exists())

    def test_lotes_nao_ficam_bloqueados_por_evento_anonimo_com_revisao_recente(self):
        revisar_evento(self.evento.pk, "SUSPEITO", "ANALISAR", self.usuario)
        importar_eventos(self.sensor.pk, arquivo(evento("segundo")), self.usuario)
        outro = EventoHoneypot.objects.get(identificador="segundo")
        EventoHoneypot.objects.filter(pk=outro.pk).update(recebido_em=timezone.now()-timedelta(days=100))
        self.assertEqual(aplicar_retencao(limite=1)["ips_eliminados"], 1)
        r = aplicar_retencao(limite=1)
        self.assertEqual(r["eventos_eliminados"], 1)
        self.assertFalse(EventoHoneypot.objects.filter(pk=outro.pk).exists())

    def test_rotina_chama_retencao_e_registra_resultado(self):
        from inventario.aplicacao.rotinas import executar_rotinas
        with ExitStack() as pilha:
            for nome in ("expirar_aceites", "enriquecer_kev", "atualizar_prazos", "alertas_inventario", "alertar_tendencia", "executar_ciclo"):
                pilha.enter_context(patch("inventario.aplicacao.rotinas." + nome, return_value=0))
            pilha.enter_context(patch("inventario.aplicacao.rotinas.sugerir_cves", return_value={"avisos": []}))
            pilha.enter_context(patch("inventario.aplicacao.rotinas.gravar_snapshot_risco", return_value=SimpleNamespace(pk=1)))
            pilha.enter_context(patch("inventario.aplicacao.rotinas.CisaKevClient"))
            pilha.enter_context(patch("inventario.infraestrutura.ancoras.ancorar", return_value=None))
            resultado = executar_rotinas(sem_rede=True)
        self.assertNotIn("retencao_isca", resultado["erros"])
        self.assertEqual(resultado["etapas"]["retencao_isca"]["eventos_eliminados"], 1)
        self.assertFalse(EventoHoneypot.objects.filter(pk=self.evento.pk).exists())

    def test_falha_na_auditoria_reverte_retencao(self):
        with patch("inventario.aplicacao.honeypot.registrar_evento", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                aplicar_retencao()
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.origem_ip, "192.0.2.10")

    def test_formulario_negacao_mfa_e_validacao(self):
        url = "/honeypot/retencao/"
        self.assertContains(self.client.get(url), "90 dias")
        self.assertEqual(self.client.post(url, {"dias": 31}).status_code, 302)
        self.assertEqual(PoliticaRetencaoHoneypot.objects.get(pk=1).dias, 31)
        self.assertEqual(self.client.post(url, {"dias": 10}).status_code, 200)
        self.assertEqual(PoliticaRetencaoHoneypot.objects.get(pk=1).dias, 31)
        sem = get_user_model().objects.create_user("leitor-sem-retencao")
        self.autenticar(sem)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url).url, "/mfa/")

    def test_pendencias_na_tela_respeitam_permissoes_e_prazo(self):
        from django.contrib.auth.models import Permission
        revisao = revisar_evento(self.evento.pk, "INCONCLUSIVO", "SEM_CONTEXTO", self.usuario)
        RevisaoEventoHoneypot.objects.filter(pk=revisao.pk).update(criado_em=timezone.now()-timedelta(days=100))
        resposta = self.client.get('/honeypot/retencao/')
        self.assertEqual(resposta.context['pendencias'], {'ips': 1, 'revisoes': 1})
        alterar_retencao(180, self.usuario)
        self.assertEqual(self.client.get('/honeypot/retencao/').context['pendencias'], {'ips': 0, 'revisoes': 0})
        gerente = get_user_model().objects.create_user('politica-sem-eventos')
        gerente.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventario', codename__in=(
            'view_ativo', 'view_sensorhoneypot', 'view_politicaretencaohoneypot', 'change_politicaretencaohoneypot')))
        self.autenticar(gerente)
        self.assertIsNone(self.client.get('/honeypot/retencao/').context['pendencias'])
