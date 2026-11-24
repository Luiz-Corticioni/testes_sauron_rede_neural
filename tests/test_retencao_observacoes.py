from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, override_settings
from django.utils import timezone

from inventario.aplicacao.observacoes import importar, revisar
from inventario.aplicacao.retencao_observacoes import alterar_retencao, aplicar_retencao, prazo_dias
from inventario.models import ObservacaoImportada, PoliticaRetencaoObservacoes, RegistroAuditoria, RevisaoObservacao, SugestaoCorrecao
from .base import BancoTeste


@override_settings(SAURON_IMPORTACAO_OBSERVACOES_ENABLED=True)
class RetencaoObservacoes(BancoTeste):
    def setUp(self):
        super().setUp()
        conteudo = b'{"SchemaVersion":2,"Results":[{"Target":"alvo-ficticio","Vulnerabilities":[{"VulnerabilityID":"CVE-2021-44228","PkgName":"lib","InstalledVersion":"1"}]}]}'
        importar("trivy", conteudo, "fonte-sensivel", "1", timezone.now().isoformat(), "MEDIA", self.usuario)
        self.obs = ObservacaoImportada.objects.get()
        self.revisao = revisar(self.obs.pk, "VALIDA", "Descrição sensível fictícia", self.usuario)
        self.sugestao = SugestaoCorrecao.objects.create(incidencia=self.i, observacao=self.obs, scan_sha256="a" * 64,
            observado_em=timezone.now(), declaracao="Host fictício 192.0.2.1", criado_por=self.usuario)

    def envelhecer(self):
        data = timezone.now() - timedelta(days=91)
        ObservacaoImportada.objects.filter(pk=self.obs.pk).update(recebido_em=data)
        RevisaoObservacao.objects.filter(pk=self.revisao.pk).update(criada_em=data)
        SugestaoCorrecao.objects.filter(pk=self.sugestao.pk).update(criado_em=data)

    def test_padrao_limpeza_idempotente_e_ocultacao_antes_da_rotina(self):
        self.assertEqual(prazo_dias(), 90)
        self.envelhecer()
        self.assertEqual(self.client.get(f"/observacoes/{self.obs.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/observacoes/{self.obs.pk}/").status_code, 404)
        self.assertNotContains(self.client.get(f"/incidencias/{self.i.pk}/comparar-scan/"), "192.0.2.1")
        with self.assertRaises(ValidationError):
            revisar(self.obs.pk, "VALIDA", "nova", self.usuario)
        resultado = aplicar_retencao()
        self.assertEqual((resultado["observacoes_limpas"], resultado["revisoes_eliminadas"], resultado["sugestoes_limpas"]), (1, 1, 1))
        self.obs.refresh_from_db()
        self.sugestao.refresh_from_db()
        self.assertEqual(self.obs.dados, {})
        self.assertEqual(self.obs.identidade_fonte, "[EXPIRADA]")
        self.assertIsNone(self.obs.conteudo_sha256)
        self.assertIsNone(self.obs.identificador)
        self.assertTrue(self.sugestao.dados_eliminados)
        self.assertIsNone(self.sugestao.scan_sha256)
        self.assertNotIn("192.0.2.1", self.sugestao.declaracao)
        self.assertFalse(RevisaoObservacao.objects.filter(pk=self.revisao.pk).exists())
        self.assertEqual(aplicar_retencao()["observacoes_limpas"], 0)
        self.assertTrue(RegistroAuditoria.objects.filter(acao="APLICAR_RETENCAO", entidade="Observacoes").exists())

    def test_prazo_autorizacao_e_csrf(self):
        with self.assertRaises(ValidationError):
            alterar_retencao(29, self.usuario)
        with self.assertRaises(ValidationError):
            alterar_retencao(181, self.usuario)
        leitor = get_user_model().objects.create_user("sem-retencao")
        with self.assertRaises(PermissionDenied):
            alterar_retencao(30, leitor)
        csrf = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, csrf)
        self.assertEqual(csrf.post("/observacoes/retencao/", {"dias": 30}).status_code, 403)
        self.assertEqual(self.client.post("/observacoes/retencao/", {"dias": 30}).status_code, 302)
        self.assertEqual(PoliticaRetencaoObservacoes.objects.get(pk=1).dias, 30)
        self.assertEqual(self.client.post("/observacoes/retencao/", {"dias": 181}).status_code, 200)

    def test_falha_auditoria_reverte_todas_as_mudancas(self):
        self.envelhecer()
        with patch("inventario.aplicacao.retencao_observacoes.registrar_evento", side_effect=RuntimeError("falha")):
            with self.assertRaises(RuntimeError):
                aplicar_retencao()
        self.obs.refresh_from_db()
        self.sugestao.refresh_from_db()
        self.assertEqual(self.obs.identidade_fonte, "fonte-sensivel")
        self.assertFalse(self.sugestao.dados_eliminados)
        self.assertTrue(RevisaoObservacao.objects.filter(pk=self.revisao.pk).exists())

    def test_revogacao_de_permissao_apos_trava_impede_configuracao(self):
        from django.contrib.auth.models import Permission
        from inventario.aplicacao.retencao_observacoes import PERMISSOES
        usuario = get_user_model().objects.create_user("gerente-temporario")
        codenames = [p.split(".")[1] for p in PERMISSOES]
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario", codename__in=codenames))
        with patch("inventario.aplicacao.retencao_observacoes.travar_escrita", side_effect=usuario.user_permissions.clear):
            with self.assertRaises(PermissionDenied):
                alterar_retencao(60, usuario)
        self.assertFalse(PoliticaRetencaoObservacoes.objects.exists())

    def test_banco_rejeita_marcadores_incoerentes(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            ObservacaoImportada.objects.filter(pk=self.obs.pk).update(erro="RETENCAO_EXPIRADA")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SugestaoCorrecao.objects.filter(pk=self.sugestao.pk).update(dados_eliminados=True)

    def test_ampliacao_nao_reexpoe_dados_ja_vencidos(self):
        self.envelhecer()
        resposta = self.client.post("/observacoes/retencao/", {"dias": 180})
        self.assertContains(resposta, "Processe os dados já vencidos")
        self.assertEqual(prazo_dias(), 90)
        aplicar_retencao()
        self.assertEqual(self.client.post("/observacoes/retencao/", {"dias": 180}).status_code, 302)
        self.assertEqual(prazo_dias(), 180)
        self.assertEqual(self.client.get(f"/observacoes/{self.obs.pk}/").status_code, 404)

    def test_prazo_exato_e_limites(self):
        instante = timezone.now()
        ObservacaoImportada.objects.filter(pk=self.obs.pk).update(recebido_em=instante - timedelta(days=90))
        with patch("inventario.aplicacao.retencao_observacoes.timezone.now", return_value=instante):
            self.assertEqual(aplicar_retencao()["observacoes_limpas"], 1)
        for limite in (0, 1001, True):
            with self.assertRaises(ValueError):
                aplicar_retencao(limite)

    def test_relacao_criada_permanece_apos_expirar_evidencia(self):
        import json
        from inventario.models import RelacaoAtivos
        regra = {"rules": [{"id": "R1", "acao": "allow", "origem_ativo": self.a.pk, "destino_ativo": self.b.pk,
                             "escopo": "Rede fictícia", "protocolo": "tcp", "porta": 443}]}
        importar("firewall", json.dumps(regra).encode(), "firewall-demo", "1", timezone.now().isoformat(), "MEDIA", self.usuario)
        obs = ObservacaoImportada.objects.get(formato="firewall")
        revisao = revisar(obs.pk, "RELACAO_CRIADA", "Revisão fictícia", self.usuario, timezone.localdate() + timedelta(days=30))
        relacao_id = revisao.relacao_id
        vencimento = timezone.now() - timedelta(days=91)
        ObservacaoImportada.objects.filter(pk=obs.pk).update(recebido_em=vencimento)
        RevisaoObservacao.objects.filter(pk=revisao.pk).update(criada_em=vencimento)
        aplicar_retencao()
        self.assertTrue(RelacaoAtivos.objects.filter(pk=relacao_id, vigente=True).exists())
        self.assertFalse(RevisaoObservacao.objects.filter(pk=revisao.pk).exists())
        obs.refresh_from_db()
        self.assertEqual(obs.dados, {})

    def test_agendador_executa_retencao_em_banco_de_teste(self):
        from contextlib import ExitStack
        from types import SimpleNamespace
        from inventario.aplicacao.rotinas import executar_rotinas
        self.envelhecer()
        with ExitStack() as pilha:
            for nome in ("expirar_aceites", "enriquecer_kev", "atualizar_prazos", "alertas_inventario", "alertar_tendencia", "executar_ciclo"):
                pilha.enter_context(patch("inventario.aplicacao.rotinas." + nome, return_value=0))
            pilha.enter_context(patch("inventario.aplicacao.rotinas.sugerir_cves", return_value={"avisos": []}))
            pilha.enter_context(patch("inventario.aplicacao.rotinas.gravar_snapshot_risco", return_value=SimpleNamespace(pk=1)))
            pilha.enter_context(patch("inventario.aplicacao.rotinas.CisaKevClient"))
            pilha.enter_context(patch("inventario.infraestrutura.ancoras.ancorar", return_value=None))
            resultado = executar_rotinas(sem_rede=True)
        self.assertNotIn("retencao_observacoes", resultado["erros"])
        self.assertEqual(resultado["etapas"]["retencao_observacoes"]["observacoes_limpas"], 1)
