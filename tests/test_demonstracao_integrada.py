"""Fluxo sintético com senha, CSRF e TOTP; nenhum serviço externo é contatado."""
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from inventario.models import CenarioFinanceiro, EventoHoneypot, RelacaoAtivos, RelatorioScanner, SensorHoneypot
from .base import BancoTeste


class DemonstracaoIntegrada(BancoTeste):
    def entrar(self, usuario):
        cliente = Client(enforce_csrf_checks=True)
        dispositivo = TOTPDevice.objects.get(user=usuario)
        cliente.get('/entrar/')
        resposta = self.post(cliente, '/entrar/', {'username': usuario.username, 'password': 'senha-teste-123'})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(cliente.get('/ativos/').url, '/mfa/')
        codigo = str(totp(dispositivo.bin_key, step=dispositivo.step, t0=dispositivo.t0,
                          digits=dispositivo.digits, drift=dispositivo.drift)).zfill(dispositivo.digits)
        resposta = self.post(cliente, '/mfa/', {'acao': 'totp', 'dispositivo': dispositivo.pk,
                                               'password': 'senha-teste-123', 'token': codigo})
        self.assertEqual(resposta.status_code, 302)
        return cliente

    def post(self, cliente, url, dados):
        return cliente.post(url, dados | {'csrfmiddlewaretoken': cliente.cookies['csrftoken'].value})

    def test_fluxo_completo_e_nega_administracao_ao_usuario_comum(self):
        cliente = self.entrar(self.usuario)
        hoje = timezone.localdate()
        relacao = {'origem': self.a.pk, 'destino': self.b.pk, 'tipo': 'NEGOCIO', 'escopo': 'Demo', 'porta': '0',
                   'fonte': 'Equipe fictícia', 'evidencia': 'Relação fictícia conferida',
                   'observada_em': hoje.isoformat(), 'revisar_em': (hoje + timedelta(days=30)).isoformat(), 'vigente': 'on'}
        resposta = self.post(cliente, '/relacoes/nova/', relacao)
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        self.assertEqual(RelacaoAtivos.objects.filter(tipo='NEGOCIO').count(), 1)
        cenario = {'nome': 'Demonstração', 'ativo': self.a.pk, 'descricao': 'Empresa fictícia',
                   'probabilidade': '0.1', 'horas_min': '4', 'horas_moda': '8', 'horas_max': '24',
                   'custo_hora': '1000', 'custo_adicional': '2000', 'origem': 'Exemplo fictício',
                   'qualidade': 'SIMULADO', 'data_referencia': hoje.isoformat()}
        resposta = self.post(cliente, '/cenarios-financeiros/novo/', cenario)
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        cenario = CenarioFinanceiro.objects.get(nome='Demonstração')
        resposta = self.post(cliente, f'/cenarios-financeiros/{cenario.pk}/', {'n': '100', 'seed': '42'})
        self.assertContains(resposta, 'Resultado simulado')
        exemplos = Path(__file__).resolve().parent.parent / 'docs/exemplos'
        trivy = (exemplos / 'trivy-demo.json').read_bytes()
        contexto = {'ativo': self.a.pk, 'escopo': 'Demo', 'origem': 'Trivy fictício'}
        resposta = self.post(cliente, '/scanner/', contexto | {'arquivo': SimpleUploadedFile('trivy.json', trivy)})
        self.assertFalse(RelatorioScanner.objects.exists())
        token = resposta.context['form'].initial['confirmacao']
        resposta = self.post(cliente, '/scanner/', contexto | {'arquivo': SimpleUploadedFile('trivy.json', trivy), 'confirmacao': token})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(RelatorioScanner.objects.count(), 1)
        resposta = self.post(cliente, '/honeypot/novo/', {'nome': 'Demo', 'responsavel': 'Equipe',
                             'ativo': self.a.pk, 'ambiente': 'DEMONSTRACAO', 'habilitado': 'on'})
        self.assertEqual(resposta.status_code, 302)
        sensor = SensorHoneypot.objects.get(nome='Demo')
        cowrie = (exemplos / 'cowrie-demo.jsonl').read_bytes()
        url = f'/honeypot/{sensor.pk}/cowrie/'
        dados = {'lote': 'a47ac10b-58cc-4372-a567-0e02b2c3d479'}
        resposta = self.post(cliente, url, dados | {'arquivo': SimpleUploadedFile('cowrie.jsonl', cowrie)})
        self.assertFalse(EventoHoneypot.objects.exists())
        token = resposta.context['form'].initial['confirmacao']
        resposta = self.post(cliente, url, dados | {'arquivo': SimpleUploadedFile('cowrie.jsonl', cowrie), 'confirmacao': token})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(EventoHoneypot.objects.count(), 2)
        comum = get_user_model().objects.create_user('comum-demo', password='senha-teste-123')
        TOTPDevice.objects.create(user=comum, name='demo', confirmed=True)
        leitor = self.entrar(comum)
        self.assertEqual(leitor.get('/admin/').status_code, 403)
        self.assertEqual(leitor.get('/scanner/').status_code, 403)
        self.assertEqual(leitor.get('/honeypot/').status_code, 403)
