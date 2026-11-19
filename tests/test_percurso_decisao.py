"""Percurso sintético entre serviços, evidências e decisão financeira."""
import json
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from inventario.aplicacao.fair import criar
from inventario.models import CenarioFAIR, Incidencia, MembroPerimetro, PerimetroRelacoes, RelatorioScanner, ServicoNegocio
from .base import BancoTeste
from .test_fair_matematica import exemplo


class PercursoDecisao(BancoTeste):
    def test_percurso_nao_promove_achado_nem_confunde_hipoteses_com_fatos(self):
        perimetro = PerimetroRelacoes.objects.create(nome='faturamento-demo', descricao='Escopo fictício',
            criada_por=self.usuario, atualizada_por=self.usuario)
        MembroPerimetro.objects.create(perimetro=perimetro, ativo=self.a)
        servico = {'nome': 'Faturamento fictício', 'descricao': 'Pedidos', 'responsavel': 'Equipe fictícia',
                   'impacto_interrupcao': 'Operação parada', 'criticidade': 4, 'perimetro': perimetro.pk}
        self.assertEqual(self.client.post(reverse('servico_negocio_novo'), servico).status_code, 302)
        registrado = ServicoNegocio.objects.get(nome=servico['nome'])

        documento = {'results': [{'packages': [{'package': {'name': 'biblioteca', 'version': '1.0', 'ecosystem': 'PyPI'},
            'vulnerabilities': [{'id': 'GHSA-ficticio', 'aliases': ['CVE-2024-12345']}]}]}]}
        def arquivo():
            return SimpleUploadedFile('resultado.json', json.dumps(documento).encode())
        dados = {'ativo': self.a.pk, 'escopo': 'imagem fictícia', 'origem': 'Teste sintético', 'formato': 'osv',
                 'observado_em': timezone.now().isoformat()}
        anteriores = set(Incidencia.objects.values_list('pk', flat=True))
        previa = self.client.post(reverse('scanner_importar'), dados | {'arquivo': arquivo()})
        token = previa.context['form'].initial['confirmacao']
        self.assertEqual(self.client.post(reverse('scanner_importar'),
            dados | {'arquivo': arquivo(), 'confirmacao': token}).status_code, 302)
        relatorio = RelatorioScanner.objects.get()
        self.assertEqual(self.client.post(reverse('scanner_revisao', args=[relatorio.pk, 0]),
            {'classificacao': 'INCONCLUSIVO', 'justificativa': 'Sem confirmação de instalação'}).status_code, 302)
        self.assertEqual(set(Incidencia.objects.values_list('pk', flat=True)), anteriores)
        self.assertContains(self.client.get(reverse('detalhe_ativo', args=[self.a.pk])), 'OSV-Scanner: Teste sintético')
        pagina = self.client.get(reverse('servico_negocio', args=[registrado.pk]))
        self.assertContains(pagina, self.a.hostname)
        self.assertNotContains(pagina, 'CVE-2024-12345')

        campos = {'ativo': self.a, 'evento': 'Interrupção fictícia', 'ameaca': 'Falha fictícia', 'efeito': 'A',
                  'escopo': 'Faturamento fictício', 'origem_frequencia': 'Hipótese', 'origem_perdas': 'Hipótese',
                  'qualidade': 'SIMULADO', 'data_referencia': timezone.localdate(),
                  'premissas': exemplo() | {'frequencia': [0., 1., 2.], 'slef': [1., 1., 1.]}}
        base = criar(CenarioFAIR(nome='Base fictícia', **campos), self.usuario, True)
        alternativa = criar(CenarioFAIR(nome='Alternativa fictícia', **campos), self.usuario, True)
        comparacao = self.client.post(reverse('fair_comparar', args=[base.pk]), {'alternativa': alternativa.pk,
            'n': 100, 'seed': 42, 'intervencao': 'Segmentação proposta', 'custo_30_dias': '100.00',
            'fonte_custo': 'Orçamento fictício', 'custo_distinto': 'on'})
        self.assertContains(comparacao, 'Não é lucro, benefício comprovado')
        sensibilidade = self.client.post(reverse('fair_sensibilidade', args=[base.pk]),
            {'premissa': 'frequencia', 'n': 100, 'seed': 42})
        self.assertContains(sensibilidade, 'não mede causalidade')
        self.assertEqual(sensibilidade.context['resultado']['media_min'], 0)
