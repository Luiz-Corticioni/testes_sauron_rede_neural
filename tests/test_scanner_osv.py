import json
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from inventario.aplicacao.scanner_osv import extrair_osv
from inventario.models import Incidencia, RelatorioScanner
from .base import BancoTeste


class ScannerOSV(BancoTeste):
    def setUp(self):
        super().setUp()
        self.documento = {'results': [{'source': {'path': '/privado/repo/lock', 'type': 'lockfile'},
            'packages': [{'package': {'name': 'pacote', 'version': '1.2', 'ecosystem': 'PyPI'},
                'vulnerabilities': [
                    {'id': 'GHSA-exemplo', 'aliases': ['CVE-2024-12345'], 'details': 'dados ignorados'},
                    {'id': 'CVE-2024-12345', 'aliases': []},
                    {'id': 'GHSA-sem-cve', 'aliases': []}]}]}]}
        self.data = '2026-11-18T10:30:00-03:00'
        self.dados = {'ativo': self.a.pk, 'escopo': 'teste', 'origem': 'auditoria local',
                      'formato': 'osv', 'observado_em': self.data}

    def arquivo(self):
        return SimpleUploadedFile('osv.json', json.dumps(self.documento).encode())

    def test_previa_confirmacao_revisao_e_deduplicacao(self):
        antes = Incidencia.objects.count()
        resposta = self.client.post('/scanner/', self.dados | {'arquivo': self.arquivo()})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['previa']['ignorados'], 1)
        self.assertEqual(resposta.context['previa']['achados'], [{'cve': 'CVE-2024-12345', 'pacote': 'PyPI:pacote', 'versao': '1.2'}])
        self.assertContains(resposta, 'data declarada')
        self.assertFalse(RelatorioScanner.objects.exists())
        token = resposta.context['form'].initial['confirmacao']
        alterada = self.client.post('/scanner/', self.dados | {'arquivo': self.arquivo(), 'confirmacao': token,
                                  'observado_em': '2026-11-17T10:30:00-03:00'})
        self.assertContains(alterada, 'contexto mudou')
        self.assertFalse(RelatorioScanner.objects.exists())
        confirmada = self.client.post('/scanner/', self.dados | {'arquivo': self.arquivo(), 'confirmacao': token})
        self.assertEqual(confirmada.status_code, 302)
        relatorio = RelatorioScanner.objects.get()
        self.assertEqual(relatorio.origem, 'OSV-Scanner: auditoria local')
        self.assertNotIn('/privado/', str(relatorio.achados))
        self.assertEqual(Incidencia.objects.count(), antes)
        revisao = self.client.post(f'/scanner/{relatorio.pk}/achados/0/revisar/',
            {'classificacao': 'INCONCLUSIVO', 'justificativa': 'Analisar versão implantada'})
        self.assertEqual(revisao.status_code, 302)
        self.assertEqual(Incidencia.objects.count(), antes)

    def test_data_e_formatos_invalidos(self):
        conteudo = json.dumps(self.documento).encode()
        for data in ('', '2026-11-18T10:30:00', '2026-99-99T10:30:00Z'):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                extrair_osv(conteudo, data)
        with self.assertRaises(ValidationError):
            extrair_osv(b'{}', self.data)
        self.documento['results'][0]['packages'][0]['vulnerabilities'][0]['aliases'] = 'CVE-2024-12345'
        with self.assertRaises(ValidationError):
            extrair_osv(json.dumps(self.documento).encode(), self.data)

    def test_alerta_data_futura_e_limites(self):
        from datetime import timedelta
        from django.utils import timezone
        dados = self.dados | {'observado_em': (timezone.now() + timedelta(days=1)).isoformat()}
        resposta = self.client.post('/scanner/', dados | {'arquivo': self.arquivo()})
        self.assertContains(resposta, 'data informada está no futuro')
        self.assertFalse(RelatorioScanner.objects.exists())
        self.documento['results'][0]['packages'][0]['vulnerabilities'][0]['aliases'] = ['CVE-2024-12345'] * 1001
        with self.assertRaises(ValidationError):
            extrair_osv(json.dumps(self.documento).encode(), self.data)

    def test_usuario_sem_permissao_de_escrita_nao_importa(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        from inventario.aplicacao.documentos import LEITURA
        leitor = get_user_model().objects.create_user('leitor-osv', password='senha-teste-123')
        nomes = [permissao.split('.')[1] for permissao in LEITURA]
        leitor.user_permissions.set(Permission.objects.filter(content_type__app_label='inventario', codename__in=nomes))
        self.autenticar(leitor)
        self.assertEqual(self.client.post('/scanner/', self.dados | {'arquivo': self.arquivo()}).status_code, 403)
        self.assertFalse(RelatorioScanner.objects.exists())
