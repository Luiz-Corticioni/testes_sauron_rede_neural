from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from inventario.infraestrutura.auditoria import verificar_cadeia
from inventario.models import Ativo, Incidencia, Sala, SnapshotRisco


class CenarioOperacional(TestCase):
    def setUp(self):
        pasta = TemporaryDirectory(prefix="sauron-demo-")
        self.addCleanup(pasta.cleanup)
        self.config = override_settings(DATA_DIR=Path(pasta.name), SAURON_EXIGIR_ANCORA=False,
            CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.ambiente = patch.dict("os.environ", {"SAURON_ADMIN_USER": "", "SAURON_ADMIN_PASSWORD": ""})
        self.ambiente.start()
        self.addCleanup(self.ambiente.stop)

    def test_seed_operacional_usa_aprovacao_segregada_e_repeticao_e_segura(self):
        saida = StringIO()
        call_command("seed_demo", operacional=True, stdout=saida)
        i = Incidencia.objects.get(pk="INC-0002")
        self.assertEqual(i.status, "ACEITA")
        self.assertNotEqual(i.aceita_por_id, i.aprovada_por_id)
        self.assertGreaterEqual(i.aceita_ate, timezone.localdate())
        self.assertIn("SIMULAÇÃO", i.justificativa)
        self.assertTrue(SnapshotRisco.objects.filter(chave__startswith="DEMO-").exists())
        self.assertTrue(verificar_cadeia(verificar_ancora=False)["integra"])
        self.assertFalse(get_user_model().objects.get(pk=i.aceita_por_id).has_usable_password())
        self.assertFalse(get_user_model().objects.get(pk=i.aprovada_por_id).has_usable_password())
        total = (Ativo.objects.count(), Incidencia.objects.count(), SnapshotRisco.objects.count())
        call_command("seed_demo", operacional=True, stdout=saida)
        self.assertEqual(total, (Ativo.objects.count(), Incidencia.objects.count(), SnapshotRisco.objects.count()))
        self.assertIn("ignorado", saida.getvalue())

    def test_falha_no_meio_do_seed_reverte_cenario_e_auditoria(self):
        antes = verificar_cadeia(verificar_ancora=False)
        with patch("inventario.aplicacao.operacao.emitir_alerta", side_effect=RuntimeError("falha simulada")):
            with self.assertRaisesMessage(RuntimeError, "falha simulada"):
                call_command("seed_demo", operacional=True, stdout=StringIO())
        self.assertFalse(Ativo.objects.exists())
        self.assertFalse(Incidencia.objects.exists())
        self.assertFalse(SnapshotRisco.objects.exists())
        self.assertEqual(verificar_cadeia(verificar_ancora=False), antes)

    def test_base_existente_nao_recebe_nem_altera_dados_de_demo(self):
        sala = Sala.objects.create(id="SALA-REAL-1", nome="Local existente")
        saida = StringIO()
        call_command("seed_demo", operacional=True, stdout=saida)
        sala.refresh_from_db()
        self.assertEqual(sala.nome, "Local existente")
        self.assertEqual(Sala.objects.count(), 1)
        self.assertFalse(Ativo.objects.exists())
        self.assertFalse(SnapshotRisco.objects.exists())
        self.assertIn("ignorado", saida.getvalue())

    def test_empresa_ficticia_tem_inventario_diverso_e_risco_calculavel(self):
        from inventario.aplicacao.servicos import calcular_risco_banco
        from inventario.models import Dependencia, Vulnerabilidade
        from inventario.web.visualizacao import grafo_dependencias

        call_command('seed_demo', empresa=True, stdout=StringIO())
        self.assertEqual(Ativo.objects.count(), 30)
        self.assertGreaterEqual(Ativo.objects.values('tipo').distinct().count(), 6)
        self.assertEqual(Vulnerabilidade.objects.count(), 8)
        self.assertEqual(Ativo.objects.filter(ip__isnull=False).count(), 30)
        self.assertGreater(Dependencia.objects.count(), 40)
        risco = calcular_risco_banco()
        grafo = grafo_dependencias(risco, {})
        self.assertEqual(len(grafo['nos']), 30)
        self.assertEqual(len(grafo['arestas']), Dependencia.objects.count())
        self.assertTrue(all(0 <= n['x'] <= grafo['largura'] and 0 <= n['y'] <= grafo['altura'] for n in grafo['nos']))
        self.assertGreater(len({n['x'] for n in grafo['nos']}), 5)
        call_command('seed_demo', empresa=True, stdout=StringIO())
        self.assertEqual(Ativo.objects.count(), 30)

    def test_empresa_exige_superusuario_mfa_e_post(self):
        from django.contrib.auth.models import Permission
        from django_otp.plugins.otp_totp.models import TOTPDevice
        admin = get_user_model().objects.create_superuser('admin', 'admin@example.org', 'teste')
        comum = get_user_model().objects.create_user('comum', password='teste')
        comum.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventario',
            codename__in=['view_ativo', 'view_vulnerabilidade', 'view_incidencia', 'view_dependencia']))
        def autenticar(usuario):
            self.client.force_login(usuario)
            dispositivo = TOTPDevice.objects.create(user=usuario, name='teste', confirmed=True)
            sessao = self.client.session
            sessao['otp_device_id'] = dispositivo.persistent_id
            sessao['sauron_reauth_em'] = timezone.now().timestamp()
            sessao.save()
        autenticar(comum)
        self.assertEqual(self.client.post('/demonstracao/empresa/').status_code, 403)
        self.client.force_login(admin)
        self.assertEqual(self.client.post('/demonstracao/empresa/').status_code, 302)
        self.assertFalse(Ativo.objects.exists())
        autenticar(admin)
        self.assertEqual(self.client.get('/demonstracao/empresa/').status_code, 405)
        self.assertEqual(self.client.post('/demonstracao/empresa/').status_code, 302)
        self.assertEqual(Ativo.objects.count(), 30)
        self.assertContains(self.client.get('/'), 'EMPRESA AURORA · DADOS FICTÍCIOS')

    def test_empresa_realista_mantem_fontes_e_associacoes_especificas(self):
        from inventario.aplicacao.demo_realista import AVISOS, FONTE
        from inventario.aplicacao.servicos import calcular_risco_banco
        from inventario.models import Vulnerabilidade
        call_command('seed_demo', empresa_realista=True, stdout=StringIO())
        self.assertEqual(Ativo.objects.count(), 30)
        self.assertEqual(Vulnerabilidade.objects.filter(fonte=FONTE).count(), 8)
        for cve, _, cvss, versao, _, _, fonte, _ in AVISOS:
            vulnerabilidade = Vulnerabilidade.objects.get(cve_id=cve)
            self.assertEqual((vulnerabilidade.cvss, vulnerabilidade.cvss_versao), (cvss, versao))
            self.assertEqual(vulnerabilidade.referencias, [fonte])
            ocorrencias = Incidencia.objects.filter(vulnerabilidade=vulnerabilidade)
            self.assertEqual(ocorrencias.count(), 4)
            self.assertTrue(all('SIMULAÇÃO' in i.observacoes for i in ocorrencias))
        self.assertEqual(set(Incidencia.objects.filter(vulnerabilidade__cve_id='CVE-2019-5285').values_list('ativo__modelo', flat=True)), {'S12700'})
        self.assertEqual(set(Incidencia.objects.filter(vulnerabilidade__cve_id='CVE-2024-3400').values_list('ativo__versao', flat=True)), {'10.2.8'})
        self.assertEqual(len(calcular_risco_banco()['ids_ativos']), 30)
        call_command('seed_demo', empresa_realista=True, stdout=StringIO())
        self.assertEqual(Ativo.objects.count(), 30)

    def test_opcao_realista_web_respeita_escolha_e_recusa_inventario_preenchido(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from inventario.aplicacao.demo_realista import FONTE
        from inventario.models import Vulnerabilidade
        usuario = get_user_model().objects.create_superuser('admin-demo', 'admin@example.org', 'senha-teste')
        self.client.force_login(usuario)
        dispositivo = TOTPDevice.objects.create(user=usuario, name='teste', confirmed=True)
        sessao = self.client.session
        sessao['otp_device_id'] = dispositivo.persistent_id
        sessao['sauron_reauth_em'] = timezone.now().timestamp()
        sessao.save()
        self.assertEqual(self.client.post('/demonstracao/empresa/', {'cenario': 'outro'}).status_code, 400)
        self.assertEqual(self.client.post('/demonstracao/empresa/', {'cenario': 'realista'}).status_code, 302)
        self.assertEqual(Ativo.objects.count(), 30)
        self.assertEqual(Vulnerabilidade.objects.filter(fonte=FONTE).count(), 8)
        self.assertContains(self.client.get('/'), 'Produtos e CVEs são reais')
        self.assertEqual(self.client.post('/demonstracao/empresa/', {'cenario': 'realista'}).status_code, 302)
        self.assertEqual(Ativo.objects.count(), 30)

    def test_aurora_epss_atualizavel_e_simulacao_disponivel(self):
        from inventario.aplicacao.epss import sincronizar_epss
        from inventario.aplicacao.montecarlo import calcular_montecarlo
        from inventario.models import ObservacaoEPSS, Vulnerabilidade
        call_command('seed_demo', empresa_realista=True, stdout=StringIO())
        cves = list(Vulnerabilidade.objects.values_list('cve_id', flat=True))
        hoje = timezone.now().date().isoformat()
        dados = {cve: {'epss': .2, 'percentil': .8, 'data': hoje, 'modelo': ''} for cve in cves}
        with patch('inventario.aplicacao.epss.EpssClient.buscar', return_value=dados):
            sincronizar_epss()
        self.assertEqual(Vulnerabilidade.objects.filter(epss_observacao__isnull=False).count(), 8)
        self.assertGreaterEqual(ObservacaoEPSS.objects.count(), 8)
        resultado = calcular_montecarlo({'n': 100})
        self.assertTrue(resultado['disponivel'])
        self.assertEqual(resultado['quantidade_incidencias'], 32)
        from django_otp.plugins.otp_totp.models import TOTPDevice
        usuario = get_user_model().objects.create_superuser('aurora', 'aurora@example.org', 'senha-teste')
        self.client.force_login(usuario)
        dispositivo = TOTPDevice.objects.create(user=usuario, name='teste', confirmed=True)
        sessao = self.client.session
        sessao['otp_device_id'] = dispositivo.persistent_id
        sessao['sauron_reauth_em'] = timezone.now().timestamp()
        sessao.save()
        pagina = self.client.get('/montecarlo/')
        self.assertContains(pagina, 'CVE-2024-3400')
        resposta = self.client.post('/api/montecarlo/', data='{"n":100}', content_type='application/json')
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['disponivel'])

    def test_fotografia_antiga_nao_e_tratada_como_epss_recente(self):
        from datetime import timedelta
        from inventario.aplicacao.montecarlo import calcular_montecarlo
        from inventario.models import Vulnerabilidade
        call_command('seed_demo', empresa_realista=True, stdout=StringIO())
        Vulnerabilidade.objects.update(epss_data=timezone.now().date() - timedelta(days=3))
        resultado = calcular_montecarlo({'n': 100})
        self.assertFalse(resultado['disponivel'])
        self.assertEqual(resultado['pendencias_total'], 32)
