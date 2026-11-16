import json
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from inventario.aplicacao.scanner import extrair
from inventario.models import Incidencia, RelatorioScanner, RevisaoAchadoScanner
from .base import BancoTeste


class ScannerTeste(BancoTeste):
    def setUp(self):
        super().setUp()
        self.doc = {"SchemaVersion": 2, "CreatedAt": "2026-11-13T12:00:00Z", "Results": [{"Vulnerabilities": [
            {"VulnerabilityID": "CVE-2026-12345", "PkgName": "libteste", "InstalledVersion": "1.0", "Description": "não arquivar"},
            {"VulnerabilityID": "GHSA-exemplo", "PkgName": "libteste", "InstalledVersion": "1.0"}]}]}

    def upload(self):
        return SimpleUploadedFile("trivy.json", json.dumps(self.doc).encode())

    def test_importacao_exige_previa_e_nao_cria_incidencias(self):
        dados = {"ativo": self.a.pk, "escopo": "imagem", "origem": "Trivy local"}
        antes = Incidencia.objects.count()
        resposta = self.client.post("/scanner/", dados | {"arquivo": self.upload()})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["previa"]["ignorados"], 1)
        self.assertFalse(RelatorioScanner.objects.exists())
        token = resposta.context["form"].initial["confirmacao"]
        resposta = self.client.post("/scanner/", dados | {"arquivo": self.upload(), "confirmacao": token})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Incidencia.objects.count(), antes)
        self.assertNotIn("não arquivar", str(RelatorioScanner.objects.get().achados))
        self.client.post("/scanner/", dados | {"arquivo": self.upload(), "confirmacao": token})
        self.assertEqual(RelatorioScanner.objects.count(), 1)

    def test_alteracao_apos_previa_e_formato_invalido(self):
        dados = {"ativo": self.a.pk, "escopo": "imagem", "origem": "Trivy local"}
        resposta = self.client.post("/scanner/", dados | {"arquivo": self.upload()})
        token = resposta.context["form"].initial["confirmacao"]
        self.doc["Results"][0]["Vulnerabilities"][0]["InstalledVersion"] = "2.0"
        resposta = self.client.post("/scanner/", dados | {"arquivo": self.upload(), "confirmacao": token})
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(RelatorioScanner.objects.exists())
        with self.assertRaises(ValidationError):
            extrair(b"{}")

    def test_revisao_registra_historico_sem_alterar_incidencias(self):
        dados = {"ativo": self.a.pk, "escopo": "imagem", "origem": "Trivy local"}
        resposta = self.client.post("/scanner/", dados | {"arquivo": self.upload()})
        token = resposta.context["form"].initial["confirmacao"]
        self.client.post("/scanner/", dados | {"arquivo": self.upload(), "confirmacao": token})
        relatorio = RelatorioScanner.objects.get()
        url = f"/scanner/{relatorio.pk}/achados/0/revisar/"
        antes = Incidencia.objects.count()
        resposta = self.client.post(url, {"classificacao": "INCONCLUSIVO", "justificativa": "Verificar versão em produção"})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(RevisaoAchadoScanner.objects.count(), 1)
        self.assertEqual(Incidencia.objects.count(), antes)
        self.assertEqual(self.client.get(f"/scanner/{relatorio.pk}/achados/99/revisar/").status_code, 404)
