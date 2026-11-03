from datetime import timedelta
from io import StringIO
import os
from unittest.mock import patch
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command, CommandError
from django.test import override_settings
from django.utils import timezone
from inventario.aplicacao.epss import sincronizar_epss, situacao_epss
from inventario.infraestrutura.cve_client import EpssClient, IntegracaoCVEError
from inventario.models import ObservacaoEPSS
from .base import BancoTeste


@patch.dict(os.environ, {'SAURON_ROTINAS_SEM_REDE': '0'})
class EPSSIntegrado(BancoTeste):
    def resposta(self, valor='0.2', percentil='0.9', dias=0):
        return {'data': [{'cve': self.v.cve_id, 'epss': valor, 'percentile': percentil,
                          'date': (timezone.now().date()-timedelta(days=dias)).isoformat()}]}

    def sincronizar(self, resposta=None):
        with patch('inventario.infraestrutura.cve_client._baixar_json', return_value=resposta or self.resposta()):
            return sincronizar_epss()

    def test_historico_idempotente_e_origem_sem_inventar_versao(self):
        self.assertEqual(self.sincronizar()['observacoes_novas'], 1)
        self.assertEqual(self.sincronizar()['observacoes_novas'], 0)
        self.assertEqual(ObservacaoEPSS.objects.count(), 1)
        self.v.refresh_from_db()
        o = self.v.epss_observacao
        self.assertEqual((self.v.epss, o.percentil), (.2, .9))
        self.assertEqual(o.modelo, '')
        self.assertEqual(len(o.assinatura), 64)
        self.assertEqual(o.fonte, 'https://api.first.org/data/v1/epss')

    def test_revisao_mesmo_dia_preserva_evidencias(self):
        self.sincronizar()
        self.sincronizar(self.resposta(valor='0.4'))
        self.assertEqual(ObservacaoEPSS.objects.count(), 2)
        self.v.refresh_from_db()
        self.assertEqual(self.v.epss, .4)
        self.assertEqual(self.v.epss_observacao.epss, .4)

    def test_historico_antigo_nao_substitui_atual(self):
        self.sincronizar()
        self.sincronizar(self.resposta(valor='0.8', dias=10))
        self.v.refresh_from_db()
        self.assertEqual(self.v.epss, .2)
        self.assertEqual(ObservacaoEPSS.objects.count(), 2)

    def test_falha_e_cve_ausente_preservam_dados(self):
        self.sincronizar()
        self.assertTrue(self.sincronizar({'data': []})['avisos'])
        with patch('inventario.infraestrutura.cve_client._baixar_json', side_effect=IntegracaoCVEError('rede indisponível')):
            self.assertTrue(sincronizar_epss()['avisos'])
        self.v.refresh_from_db()
        self.assertEqual(self.v.epss, .2)
        self.assertEqual(ObservacaoEPSS.objects.count(), 1)

    def test_payloads_invalidos_nao_gravam(self):
        for valor, percentil in [('nan', '.9'), (10**400, '.9'), (True, '.9'), ('.2', 'inf'), ('.2', True), ('.2', '1.1')]:
            with self.subTest(valor=valor, percentil=percentil):
                self.assertTrue(self.sincronizar(self.resposta(valor, percentil))['avisos'])
        self.assertTrue(self.sincronizar(self.resposta(dias=-1))['avisos'])
        self.assertEqual(ObservacaoEPSS.objects.count(), 0)

    def test_lote_invalido_nao_grava_parcialmente(self):
        dados = self.resposta()
        dados['data'].append(dict(dados['data'][0]))
        self.assertTrue(self.sincronizar(dados)['avisos'])
        self.assertEqual(ObservacaoEPSS.objects.count(), 0)

    def test_troca_cve_limpa_cache_mas_mantem_historico(self):
        self.sincronizar()
        self.v.refresh_from_db()
        self.v.cve_id = 'CVE-2024-12345'
        self.v.save(update_fields=['cve_id'])
        self.v.refresh_from_db()
        self.assertIsNone(self.v.epss)
        self.assertIsNone(self.v.epss_observacao_id)
        self.assertEqual(ObservacaoEPSS.objects.count(), 1)

    def test_tela_historico_percentil_zero_e_get_sem_rede(self):
        self.sincronizar(self.resposta(valor='0', percentil='0'))
        with patch('inventario.infraestrutura.cve_client._baixar_json', side_effect=AssertionError('GET não acessa rede')):
            self.assertContains(self.client.get('/vulnerabilidades/'), 'EPSS: 0,00%')
            r = self.client.get(f'/vulnerabilidades/{self.v.pk}/epss/')
            self.assertContains(r, '0,00%')
            self.assertContains(r, 'Não informado pela fonte')
            self.assertEqual(self.client.post(f'/vulnerabilidades/{self.v.pk}/epss/').status_code, 405)

    def test_permissoes_e_mfa_no_historico(self):
        u = get_user_model().objects.create_user('leitor-epss')
        self.client.force_login(u)
        url = f'/vulnerabilidades/{self.v.pk}/epss/'
        self.assertEqual(self.client.get(url).url, '/mfa/')
        self.autenticar(u)
        self.assertEqual(self.client.get(url).status_code, 403)
        u.user_permissions.add(Permission.objects.get(codename='view_vulnerabilidade'))
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_filtros_e_dado_ausente_nao_sao_zero(self):
        self.assertContains(self.client.get('/vulnerabilidades/'), 'EPSS: desconhecido')
        self.sincronizar(self.resposta(dias=5))
        self.v.refresh_from_db()
        self.assertEqual(situacao_epss(self.v), 'Desatualizado')
        self.assertContains(self.client.get('/vulnerabilidades/?epss=vencido&ordem=epss'), self.v.cve_id)
        self.assertNotContains(self.client.get('/vulnerabilidades/?epss=atualizado'), self.v.cve_id)

    def test_atualizacao_chega_ao_montecarlo_e_invalida_cache(self):
        from inventario.aplicacao.montecarlo import calcular_montecarlo
        from inventario.models import Incidencia
        # Este cenário cobre uma CVE; a segunda vulnerabilidade da fixture não tem CVE/EPSS.
        Incidencia.objects.filter(vulnerabilidade=self.w).update(status='CORRIGIDA')
        antes = calcular_montecarlo({'n': 100})
        self.assertFalse(antes['disponivel'])
        self.sincronizar()
        depois = calcular_montecarlo({'n': 100})
        self.assertTrue(depois['disponivel'])
        self.assertNotEqual(antes['versao_dados'], depois['versao_dados'])
        entrada = next(e for e in depois['entradas'] if e['cve']==self.v.cve_id)
        self.assertEqual(entrada['epss'], .2)
        self.assertEqual(entrada['observacao_epss_id'], ObservacaoEPSS.objects.get().pk)

    def test_comando_retorna_erro_quando_fonte_falha(self):
        with patch('inventario.infraestrutura.cve_client._baixar_json', side_effect=IntegracaoCVEError('rede indisponível')):
            with self.assertRaises(CommandError):
                call_command('sync_epss', stdout=StringIO())

    def test_backup_e_exportacao_preservam_historico(self):
        import sqlite3
        from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
        from inventario.infraestrutura.exportacao import inventario_completo
        self.sincronizar()
        self.assertEqual(len(inventario_completo()['colecoes']['observacaoepss']), 1)
        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode()):
            destino = settings.DATA_DIR/'epss-restaurado.sqlite3'
            restaurar_backup(backup_sqlite(), destino)
        with sqlite3.connect(destino) as db:
            self.assertEqual(db.execute('select count(*) from inventario_observacaoepss').fetchone()[0], 1)
            self.assertEqual(db.execute('select epss from inventario_vulnerabilidade where id=?', [self.v.pk]).fetchone()[0], .2)

    def test_cliente_limita_tamanho_da_consulta(self):
        with self.assertRaises(IntegracaoCVEError):
            EpssClient().buscar(['CVE-2024-'+'1'*25]*70)

    def test_valor_nao_pode_apontar_para_evidencia_divergente(self):
        from django.core.exceptions import ValidationError
        self.sincronizar()
        self.v.refresh_from_db()
        self.v.epss = .99
        with self.assertRaises(ValidationError):
            self.v.save()

    def test_probabilidade_pequena_nao_e_exibida_como_zero(self):
        self.sincronizar(self.resposta(valor='0.0000001'))
        self.assertContains(self.client.get('/vulnerabilidades/'), 'EPSS: &lt;0,01%')
        self.assertContains(self.client.get(f'/vulnerabilidades/{self.v.pk}/epss/'), '&lt;0,01%')
