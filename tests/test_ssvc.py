import csv
from datetime import timedelta
import json
from pathlib import Path
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, SimpleTestCase, override_settings
from django.utils import timezone
from inventario.dominio.ssvc import avaliar, politica, PONTOS
from inventario.aplicacao.ssvc import contexto_atual, registrar_avaliacao, situacao
from inventario.models import AvaliacaoSSVC, RegistroAuditoria
from .base import BancoTeste


class TabelaSSVC(SimpleTestCase):
    def test_72_combinacoes_conferem_com_referencia_oficial_congelada(self):
        caminho = Path(__file__).parent/'fixtures/ssvc_deployer_referencia.csv'
        with caminho.open(encoding='utf-8-sig') as f:
            linhas = list(csv.DictReader(f))
        self.assertEqual(len(linhas), 72)
        for r in linhas:
            with self.subTest(linha=r['row']):
                resultado = avaliar({k: r[k] for k in PONTOS})
                self.assertEqual(resultado['acao'], r['decision'])
                self.assertEqual(resultado['linha'], int(r['row']))
                self.assertEqual(len(resultado['politica_sha256']), 64)

    def test_ausencia_e_invalidez_nao_viram_prioridade_baixa(self):
        entradas = dict.fromkeys(PONTOS, '')
        self.assertEqual(avaliar(entradas)['acao'], 'pending')
        self.assertEqual(set(avaliar(entradas)['faltantes']), set(PONTOS))
        for ruim in (None, {}, {**entradas, 'score': 9}, {**entradas, 'human_impact': 'critico'}):
            with self.assertRaises(ValueError):
                avaliar(ruim)
        with self.assertRaises(ValueError):
            avaliar(entradas, versao='versao-desconhecida')

    def test_tabela_incompleta_e_recusada(self):
        conteudo = json.loads(Path(__file__).parents[1].joinpath('inventario/dominio/ssvc_deployer.json').read_text(encoding='utf-8'))
        conteudo['rows'].pop()
        politica.cache_clear()
        try:
            with patch('inventario.dominio.ssvc.Path.read_bytes', return_value=json.dumps(conteudo).encode()), self.assertRaises(ValueError):
                politica()
        finally:
            politica.cache_clear()


class FluxoSSVC(BancoTeste):
    entradas = {'exploitation': 'active', 'exposure': 'open', 'automatable': 'yes', 'human_impact': 'high'}

    @property
    def url(self):
        return f'/incidencias/{self.i.pk}/ssvc/'

    def dados(self, **alteracoes):
        self.i.refresh_from_db()
        dados = {**self.entradas, 'evidencia': 'KEV consultado; regra FW-1; avaliação de missão BIA-4.',
                 'revisar_em': (timezone.localdate()+timedelta(days=30)).isoformat(),
                 'contexto_hash': contexto_atual(self.i)[1], 'remediacao': 'Atualizar componente para versão corrigida, ticket CHG-42'}
        return {**dados, **alteracoes}

    def registrar(self, **alteracoes):
        dados = self.dados(**alteracoes)
        return registrar_avaliacao(self.i.pk, self.usuario, {k:dados[k] for k in PONTOS}, dados['evidencia'],
            timezone.datetime.strptime(dados['revisar_em'], '%Y-%m-%d').date(), dados['contexto_hash'], dados['remediacao'])

    def test_fluxo_post_historia_autor_e_sem_alterar_decisoes_sla(self):
        antes = (self.i.status, self.i.prazo_correcao, self.i.aceita_por_id, self.i.decisao_pendente)
        with patch('inventario.infraestrutura.cve_client._baixar_json', side_effect=AssertionError('SSVC não usa rede')):
            self.assertContains(self.client.get(self.url), 'Registrar nova avaliação')
            self.assertEqual(self.client.post(self.url, self.dados(resultado='defer')).status_code, 302)
            r = self.client.get(self.url)
            self.assertContains(r, 'Agir imediatamente')
            self.assertContains(r, 'CHG-42')
        registro = AvaliacaoSSVC.objects.get()
        self.assertEqual(registro.por_id, self.usuario.pk)
        self.assertEqual(registro.resultado['linha'], 70)
        self.assertEqual(registro.resultado['acao'], 'immediate')
        self.assertContains(self.client.get('/incidencias/'), 'Agir imediatamente')
        self.i.refresh_from_db()
        self.assertEqual(antes, (self.i.status, self.i.prazo_correcao, self.i.aceita_por_id, self.i.decisao_pendente))
        self.assertEqual(RegistroAuditoria.objects.get(acao='SSVC_AVALIADO').usuario_id, self.usuario.pk)

    def test_pendente_nao_e_defer_e_historico_nao_e_sobrescrito(self):
        self.registrar()
        registro = self.registrar(human_impact='')
        self.assertEqual(registro.resultado['acao'], 'pending')
        self.assertEqual(AvaliacaoSSVC.objects.count(), 2)
        self.assertContains(self.client.get(self.url), 'Pendente de contexto')

    def test_contexto_alterado_rejeita_formulario_antigo(self):
        dados = self.dados()
        self.a.zona_rede = 'nova-zona'
        self.a.save()
        r = self.client.post(self.url, dados)
        self.assertContains(r, 'O contexto mudou')
        self.assertFalse(AvaliacaoSSVC.objects.exists())

    def test_contexto_novo_expiracao_e_versao_nao_reescrevem_historico(self):
        registro = self.registrar()
        original = registro.resultado.copy()
        self.assertIn('no prazo', situacao(registro, registro.contexto_sha256))
        with patch('inventario.aplicacao.ssvc.timezone.localdate', return_value=registro.revisar_em):
            self.assertIn('vencido', situacao(registro, registro.contexto_sha256))
        self.assertIn('alterado', situacao(registro, 'outra-assinatura'))
        registro.refresh_from_db()
        self.assertEqual(registro.resultado, original)

    def test_kev_nao_pode_ser_rebaixado_por_resposta_ou_epss(self):
        self.assertTrue(self.v.kev)
        r = self.client.post(self.url, self.dados(exploitation='none'))
        self.assertContains(r, 'KEV exige')
        self.assertFalse(AvaliacaoSSVC.objects.exists())

    def test_confirmacao_obrigatoria_antes_de_classificar_sugerida(self):
        self.i.status = 'SUGERIDA'
        self.i.save()
        self.assertNotContains(self.client.get(self.url), 'Registrar nova avaliação')
        with self.assertRaises(ValidationError):
            self.registrar()
        self.assertFalse(AvaliacaoSSVC.objects.exists())

    def test_ativo_baixado_nao_recebe_avaliacao_operacional(self):
        self.a.status = 'BAIXADO'
        self.a.save()
        with self.assertRaises(ValidationError):
            self.registrar()

    def test_evidencia_intervencao_e_prazo_obrigatorios(self):
        for alterar in ({'evidencia': '  '}, {'remediacao': '  '}, {'revisar_em': timezone.localdate().isoformat()},
                        {'revisar_em': (timezone.localdate()+timedelta(days=91)).isoformat()}, {'automatable': 'talvez'}):
            with self.subTest(alterar=alterar):
                r = self.client.post(self.url, self.dados(**alterar))
                self.assertEqual(r.status_code, 200)
                self.assertTrue(r.context['form'].errors)
        self.assertFalse(AvaliacaoSSVC.objects.exists())

    def test_leitor_consulta_mas_nao_escreve_e_servico_tambem_bloqueia(self):
        u = get_user_model().objects.create_user('leitor-ssvc')
        u.user_permissions.add(*Permission.objects.filter(codename__in=['view_ativo','view_vulnerabilidade','view_incidencia']))
        self.autenticar(u)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertNotContains(self.client.get(self.url), 'Registrar nova avaliação')
        self.assertEqual(self.client.post(self.url, self.dados()).status_code, 403)
        with self.assertRaises(PermissionDenied):
            registrar_avaliacao(self.i.pk, u, self.entradas, 'evidência', timezone.localdate()+timedelta(days=1), 'hash', 'patch')
        self.assertFalse(AvaliacaoSSVC.objects.exists())

    def test_mfa_csrf_e_permissoes_de_leitura_sao_exigidos(self):
        c = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, c)
        self.assertEqual(c.post(self.url, self.dados()).status_code, 403)
        self.client.logout()
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        u = get_user_model().objects.create_user('sem-contexto')
        self.autenticar(u)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_links_nas_listas_e_no_ativo(self):
        self.assertContains(self.client.get('/incidencias/'), self.url)
        self.assertContains(self.client.get(f'/ativos/{self.a.pk}/'), self.url)
        self.assertContains(self.client.get(f'/ativos/{self.a.pk}/'), f'/incidencias/{self.i.pk}/editar/')
        self.assertEqual(self.client.get(f'/incidencias/{self.i.pk}/editar/').status_code, 200)

    def test_exportacao_backup_e_restauracao_preservam_decisao_e_contexto(self):
        from cryptography.fernet import Fernet
        import sqlite3
        from django.conf import settings
        from inventario.infraestrutura.exportacao import inventario_completo
        from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
        registro = self.registrar()
        dados = inventario_completo()['colecoes']['avaliacaossvc']
        self.assertEqual(dados[0]['resultado']['politica_sha256'], registro.resultado['politica_sha256'])
        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode()):
            destino = settings.DATA_DIR/'ssvc-restaurado.sqlite3'
            restaurar_backup(backup_sqlite(), destino)
        with sqlite3.connect(destino) as db:
            resultado = json.loads(db.execute('select resultado from inventario_avaliacaossvc').fetchone()[0])
            self.assertEqual(resultado, registro.resultado)

    def test_terminal_usa_mesmo_servico_sem_regra_duplicada(self):
        from inventario.cli import SauronCLI
        saidas = []
        respostas = iter([self.i.pk, 'active', 'open', 'yes', 'high', 'Patch CHG-CLI', 'Evidências KEV, FW e BIA'])
        cli = SauronCLI(entrada=lambda _: next(respostas), saida=saidas.append)
        cli.usuario = self.usuario
        self.addCleanup(setattr, cli, 'usuario', None)
        with patch.object(cli, '_confirmar', return_value=True), patch.object(cli, '_data', return_value=timezone.localdate()+timedelta(days=30)):
            cli.ssvc_terminal()
        self.assertEqual(AvaliacaoSSVC.objects.get().resultado['acao'], 'immediate')
        self.assertTrue(any('Agir imediatamente' in str(s) for s in saidas))

    def test_ep_ss_novo_pede_reavaliacao_sem_reescrever_decisao(self):
        registro = self.registrar()
        self.v.epss = .7
        self.v.epss_data = timezone.localdate()
        self.v.save()
        self.i.refresh_from_db()
        self.assertIn('alterado', situacao(registro, contexto_atual(self.i)[1]))
        registro.refresh_from_db()
        self.assertEqual(registro.contexto['vulnerabilidade']['epss'], None)

    def test_sem_kev_o_mesmo_cve_pode_ter_contextos_e_acoes_diferentes(self):
        self.v.kev = False
        self.v.save()
        a = self.registrar(exploitation='none', exposure='small', automatable='no', human_impact='low')
        from inventario.models import Incidencia
        outra = Incidencia.objects.create(id='INC-SSVC-B', ativo=self.b, vulnerabilidade=self.v)
        b = registrar_avaliacao(outra.pk, self.usuario, self.entradas, 'Contexto de missão distinto, BIA-B',
            timezone.localdate()+timedelta(days=30), contexto_atual(outra)[1], 'Patch da implantação B')
        self.assertEqual(a.resultado['acao'], 'defer')
        self.assertEqual(b.resultado['acao'], 'immediate')
        self.assertEqual(AvaliacaoSSVC.objects.count(), 2)

    def test_evidencia_e_intervencao_sao_escapadas_e_snapshot_vai_para_auditoria(self):
        self.registrar(evidencia='<script>alert(1)</script>', remediacao='<img src=x onerror=alert(1)>')
        r = self.client.get(self.url)
        self.assertNotContains(r, '<script>alert(1)</script>')
        self.assertContains(r, '&lt;script&gt;')
        self.assertNotContains(r, '<img src=x')
        evento = RegistroAuditoria.objects.get(acao='SSVC_AVALIADO')
        self.assertEqual(evento.detalhes['entradas'], self.entradas)
        self.assertEqual(evento.detalhes['contexto']['incidencia']['id'], self.i.pk)
