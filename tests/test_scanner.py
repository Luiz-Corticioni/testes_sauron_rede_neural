import json
from pathlib import Path
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

    def test_arquivo_de_demonstracao(self):
        exemplo = Path(__file__).resolve().parent.parent / "docs/exemplos/trivy-demo.json"
        _, achados, ignorados, _ = extrair(exemplo.read_bytes())
        self.assertEqual((len(achados), ignorados), (1, 0))

    def test_resultado_vazio_ou_ausente_nao_afirma_seguranca(self):
        dados = {'ativo': self.a.pk, 'escopo': 'imagem', 'origem': 'Trivy fictício'}
        for resultados in ([], None):
            with self.subTest(resultados=resultados):
                if resultados is None:
                    self.doc.pop('Results', None)
                else:
                    self.doc['Results'] = resultados
                resposta = self.client.post('/scanner/', dados | {'arquivo': self.upload()})
                self.assertEqual(resposta.context['previa']['achados'], [])
                self.assertContains(resposta, 'não comprova ausência de vulnerabilidades')
                token = resposta.context['form'].initial['confirmacao']
                self.assertEqual(self.client.post('/scanner/', dados | {'arquivo': self.upload(), 'confirmacao': token}).status_code, 302)
        self.assertEqual(RelatorioScanner.objects.count(), 1)

    def test_filtro_usa_revisao_mais_recente_e_indice_original(self):
        self.doc['Results'][0]['Vulnerabilities'].append(
            {'VulnerabilityID': 'CVE-2026-99999', 'PkgName': 'outro', 'InstalledVersion': '2.0'})
        dados = {'ativo': self.a.pk, 'escopo': 'imagem', 'origem': 'Trivy local'}
        previa = self.client.post('/scanner/', dados | {'arquivo': self.upload()})
        token = previa.context['form'].initial['confirmacao']
        self.client.post('/scanner/', dados | {'arquivo': self.upload(), 'confirmacao': token})
        relatorio = RelatorioScanner.objects.get()
        url = f'/scanner/{relatorio.pk}/achados/1/revisar/'
        self.client.post(url, {'classificacao': 'APLICAVEL', 'justificativa': 'Primeira avaliação'})
        self.client.post(url, {'classificacao': 'INCONCLUSIVO', 'justificativa': 'Evidência insuficiente'})
        resposta = self.client.get(f'/scanner/{relatorio.pk}/', {'estado': 'INCONCLUSIVO'})
        self.assertEqual(resposta.context['resumo']['PENDENTE'], 1)
        self.assertEqual(resposta.context['resumo']['INCONCLUSIVO'], 1)
        self.assertEqual(resposta.context['resumo']['APLICAVEL'], 0)
        self.assertEqual(resposta.context['pagina'][0]['indice'], 1)
        self.assertContains(resposta, url)
