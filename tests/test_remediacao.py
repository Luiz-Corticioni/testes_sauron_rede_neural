import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings
from django.utils import timezone

from inventario.aplicacao.observacoes import importar, revisar
from inventario.aplicacao.remediacao import sugerir_correcao
from inventario.aplicacao.vex_emissao import emitir_vex
from inventario.models import ObservacaoImportada, Software, SugestaoCorrecao
from .base import BancoTeste


@override_settings(SAURON_IMPORTACAO_OBSERVACOES_ENABLED=True)
class ComparacaoScan(BancoTeste):
    def setUp(self):
        super().setUp()
        self.anterior = timezone.now() - timedelta(days=2)
        self.atual = (timezone.now() - timedelta(days=1)).isoformat()
        self.meta = {"fonte": "trivy-demo", "versao": "1", "observado_em": self.anterior.isoformat(),
                     "confianca": "MEDIA", "usuario": self.usuario}
        importar("trivy", self.scan([{"VulnerabilityID": self.v.cve_id, "PkgName": "lib", "InstalledVersion": "1"}]), **self.meta)
        self.obs = ObservacaoImportada.objects.get()
        revisar(self.obs.pk, "VALIDA", "Revisão inicial", self.usuario)

    def scan(self, achados, alvo="alvo-1"):
        return json.dumps({"SchemaVersion": 2, "Results": [{"Target": alvo, "Vulnerabilities": achados}]}).encode()

    def comparar(self, arquivo=None, **kwargs):
        return sugerir_correcao(self.i.pk, self.obs.pk, arquivo if arquivo is not None else self.scan([]),
            kwargs.get("data", self.atual), kwargs.get("declaracao", "Alvo corresponde ao ativo; escopo revisado."),
            kwargs.get("fonte", "trivy-demo"), kwargs.get("versao", "1"),
            kwargs.get("usuario", self.usuario))

    def test_sugere_sem_alterar_incidencia_e_e_idempotente(self):
        resultado = self.comparar()
        self.assertEqual(self.comparar().pk, resultado.pk)
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, "ABERTA")
        self.assertEqual(SugestaoCorrecao.objects.count(), 1)
        with self.assertRaises(ValidationError):
            self.comparar(declaracao="Outra declaração")
        with self.assertRaises(ValidationError):
            self.comparar(fonte="outra-fonte")

    def test_recusa_alvo_errado_cve_presente_arquivo_incompleto_e_data(self):
        cve = {"VulnerabilityID": self.v.cve_id, "PkgName": "lib", "InstalledVersion": "2"}
        for arquivo, data in ((self.scan([], "outro"), self.atual), (self.scan([cve]), self.atual),
                              (b'{"SchemaVersion":2', self.atual), (self.scan([]), self.anterior.isoformat()),
                              (b'{"SchemaVersion":2,"Results":[{"Target":"alvo-1"}]}', self.atual)):
            with self.subTest(arquivo=arquivo, data=data), self.assertRaises(ValidationError):
                self.comparar(arquivo, data=data)
        self.assertFalse(SugestaoCorrecao.objects.exists())

    def test_exige_revisao_valida_e_autorizacao(self):
        revisar(self.obs.pk, "INCONCLUSIVA", "Evidência insuficiente", self.usuario)
        with self.assertRaises(ValidationError):
            self.comparar()
        usuario = get_user_model().objects.create_user("sem-permissao")
        with self.assertRaises(PermissionDenied):
            self.comparar(usuario=usuario)
        self.autenticar(usuario)
        self.assertEqual(self.client.get(f"/incidencias/{self.i.pk}/comparar-scan/").status_code, 403)

    def test_falha_auditoria_desfaz_sugestao(self):
        with patch("inventario.aplicacao.remediacao.registrar_evento", side_effect=RuntimeError("falha")):
            with self.assertRaises(RuntimeError):
                self.comparar()
        self.assertFalse(SugestaoCorrecao.objects.exists())

    @override_settings(SAURON_IMPORTACAO_OBSERVACOES_ENABLED=False)
    def test_feature_flag_e_obrigatoria(self):
        with self.assertRaises(ValidationError):
            self.comparar()

    def test_interface_e_csrf(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import Client
        caminho = f"/incidencias/{self.i.pk}/comparar-scan/"
        self.assertContains(self.client.get(caminho), "não prova correção")
        cliente_csrf = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, cliente_csrf)
        self.assertEqual(cliente_csrf.post(caminho, {}).status_code, 403)
        resposta = self.client.post(caminho, {"observacao": self.obs.pk, "observado_em": self.atual,
            "fonte": "trivy-demo", "versao": "1",
            "declaracao": "O mesmo alvo, cobertura revisada", "confirmar": "on",
            "arquivo": SimpleUploadedFile("scan.json", self.scan([]))})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(SugestaoCorrecao.objects.count(), 1)


class EmissaoVEX(BancoTeste):
    def setUp(self):
        super().setUp()
        from inventario.aplicacao.operacao import alterar_status
        componente = Software.objects.create(ativo=self.a, nome="lib", versao="1.0", fornecedor="Exemplo", purl="pkg:pypi/lib@1.0")
        self.i.software = componente
        self.i.save()
        outro = get_user_model().objects.create_superuser("aprovador", "outro@example.org", "senha-teste-123")
        alterar_status(self.i.pk, "CORRIGIDA", self.usuario, evidencia="Atualização 1.0 revisada")
        alterar_status(self.i.pk, "CORRIGIDA", outro)

    def test_exporta_decisao_e_valida_schema(self):
        from jsonschema import Draft202012Validator
        from inventario.aplicacao.vex_emissao import SCHEMA
        doc = json.loads(emitir_vex(self.i.pk, "Equipe de segurança", self.usuario))
        Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(doc)
        self.assertEqual(doc["statements"][0]["status"], "fixed")
        self.assertEqual(doc["statements"][0]["products"][0]["@id"], "pkg:pypi/lib@1.0")
        self.assertIn("Atualização", doc["statements"][0]["status_notes"])

    def test_recusa_sem_permissao_e_decisao_inadequada(self):
        usuario = get_user_model().objects.create_user("sem-permissao")
        with self.assertRaises(PermissionDenied):
            emitir_vex(self.i.pk, "Equipe", usuario)
        with self.assertRaises(ValidationError):
            emitir_vex("INC-0002", "Equipe", self.usuario)

    def test_interface_exporta_somente_post(self):
        caminho = f"/incidencias/{self.i.pk}/openvex/"
        self.assertContains(self.client.get(caminho), "texto da evidência")
        resposta = self.client.post(caminho, {"autor": "Equipe", "confirmar": "on"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(json.loads(resposta.content)["statements"][0]["status"], "fixed")
        self.assertEqual(resposta["Cache-Control"], "no-store")
