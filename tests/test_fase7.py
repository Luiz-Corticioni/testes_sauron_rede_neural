from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.db import connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from inventario.aplicacao.administrador_inicial import cadastrar_primeiro_administrador
from inventario.aplicacao.cache_consultas import lembrar
from inventario.aplicacao.painel import contexto_painel
from inventario.models import Alerta, Sala
from .base import BancoTeste


class CadastroInicial(TestCase):
    def setUp(self):
        pasta = TemporaryDirectory(prefix='sauron-bootstrap-')
        self.addCleanup(pasta.cleanup)
        configuracao = override_settings(DATA_DIR=Path(pasta.name), SAURON_EXIGIR_ANCORA=False,
            CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
        configuracao.enable()
        self.addCleanup(configuracao.disable)
        cache.clear()

    def test_aquecer_instalacao_vazia_nao_exige_ativos_ou_administrador(self):
        call_command('aquecer_cache', incluir_financeiro=True, stdout=StringIO())
        self.assertEqual(contexto_painel()['total_ativos'], 0)

    def test_comando_cria_primeiro_sem_mfa_ou_sessao_e_entrada_continua_protegida(self):
        with patch('inventario.management.commands.cadastrar_administrador.getpass', return_value='ForteProtótipo2026!'):
            call_command('cadastrar_administrador', usuario='primeiro', stdout=StringIO())
        u = get_user_model().objects.get(username='primeiro')
        self.assertTrue(u.is_superuser and u.is_staff and u.check_password('ForteProtótipo2026!'))
        self.assertFalse(TOTPDevice.objects.filter(user=u).exists())
        self.client.force_login(u)
        self.assertEqual(self.client.get('/').url, '/mfa/')

    def test_segundo_cadastro_inicial_bloqueia_antes_de_pedir_senha_mesmo_inativo(self):
        get_user_model().objects.create_superuser('existente', password='forte', is_active=False)
        with patch('inventario.management.commands.cadastrar_administrador.getpass') as senha, self.assertRaises(CommandError):
            call_command('cadastrar_administrador', usuario='segundo')
        senha.assert_not_called()
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_servico_impede_segundo_primeiro_administrador(self):
        cadastrar_primeiro_administrador('primeiro', 'ForteProtótipo2026!')
        with self.assertRaises(ValidationError):
            cadastrar_primeiro_administrador('outro', 'ForteProtótipo2026!')
        self.assertEqual(get_user_model().objects.filter(is_superuser=True).count(), 1)

    def test_senha_fraca_e_confirmacao_divergente_nao_criam_conta(self):
        with self.assertRaises(ValidationError):
            cadastrar_primeiro_administrador('primeiro', '123')
        with patch('inventario.management.commands.cadastrar_administrador.getpass', side_effect=['senha-A', 'senha-B']), self.assertRaises(CommandError):
            call_command('cadastrar_administrador', usuario='primeiro')
        self.assertFalse(get_user_model().objects.exists())

    def test_primeiro_pelo_menu_nao_exige_autenticacao_nem_deixa_usuario_logado(self):
        from inventario.cli import SauronCLI
        cli = SauronCLI(saida=lambda _: None)
        with patch.object(cli, '_texto', side_effect=['primeiro', '']), patch.object(cli, '_exigir', side_effect=AssertionError('Bootstrap não exige login')), patch('inventario.cli_menus.sistema.getpass', return_value='ForteProtótipo2026!'):
            cli.criar_admin()
        self.assertTrue(get_user_model().objects.get(username='primeiro').is_superuser)
        self.assertIsNone(cli.usuario)


class CacheESessao(BancoTeste):
    def setUp(self):
        super().setUp()
        # As fixtures deste TestCase ficam na transação externa; não estão em avaliação.
        connection.run_on_commit.clear()

    def test_resumo_aquecido_nao_consulta_orm_e_mantem_valores(self):
        esperado = contexto_painel()
        with self.assertNumQueries(0):
            self.assertEqual(contexto_painel(), esperado)
        self.assertEqual(esperado['total_ativos'], 2)

    def test_alertas_restritos_nao_vazam_para_variante_sem_permissao(self):
        Alerta.objects.create(tipo='SLA', chave='privado', mensagem='Somente responsáveis')
        connection.run_on_commit.clear()
        cache.clear()
        self.assertEqual(contexto_painel(ver_alertas=True)['alertas_pendentes'], 1)
        limitado = contexto_painel(ver_alertas=False)
        self.assertIsNone(limitado['alertas_pendentes'])
        self.assertEqual(limitado['alertas_recentes'], [])

    def test_cache_nao_preserva_permissao_de_alerta_revogada(self):
        u = get_user_model().objects.create_user('leitor')
        u.user_permissions.set(Permission.objects.filter(codename__in=['view_ativo', 'view_vulnerabilidade', 'view_incidencia', 'view_dependencia', 'view_alerta']))
        Alerta.objects.create(tipo='SLA', chave='privado', mensagem='Alerta reservado da fase 7')
        connection.run_on_commit.clear()
        self.autenticar(u)
        self.assertContains(self.client.get('/'), 'Alerta reservado da fase 7')
        u.user_permissions.remove(Permission.objects.get(codename='view_alerta'))
        self.assertNotContains(self.client.get('/'), 'Alerta reservado da fase 7')

    def test_cache_aquecido_nao_ignora_revogacao_totp(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        TOTPDevice.objects.filter(user=self.usuario).delete()
        self.assertEqual(self.client.get('/').url, '/mfa/')

    def test_leituras_proximas_nao_gravam_sessao_a_cada_get(self):
        self.client.get('/')
        with CaptureQueriesContext(connection) as consultas:
            self.client.get('/')
            self.client.get('/ativos/')
        self.assertFalse(any('UPDATE "django_session"' in q['sql'] for q in consultas))

    def test_batimento_atualiza_apos_30s_e_respeita_expiracao(self):
        agora = timezone.now()
        with patch('inventario.seguranca_mfa.timezone.now', return_value=agora):
            self.client.get('/')
        with patch('inventario.seguranca_mfa.timezone.now', return_value=agora+timedelta(seconds=31)):
            self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.session['sauron_ultima_atividade'], (agora+timedelta(seconds=31)).timestamp())
        with patch('inventario.seguranca_mfa.timezone.now', return_value=agora+timedelta(hours=9)):
            self.assertIn('/entrar/', self.client.get('/').url)

    def test_requisicoes_concorrentes_reconstroem_uma_vez(self):
        chamadas, trava = [], Lock()
        def construir():
            with trava:
                chamadas.append(1)
            time.sleep(.02)
            return {'valor': 42}
        with ThreadPoolExecutor(max_workers=20) as executor:
            valores = list(executor.map(lambda _: lembrar('risco:teste-concorrente', construir), range(40)))
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(valores, [{'valor': 42}]*40)

    def test_precarregamento_sem_rede_retorna_os_mesmos_valores(self):
        saida = StringIO()
        with patch('inventario.infraestrutura.cve_client._baixar_json', side_effect=AssertionError('Sem rede')):
            call_command('aquecer_cache', incluir_financeiro=True, stdout=saida)
        self.assertIn('Cache aquecido', saida.getvalue())
        self.assertIn('dados insuficientes', saida.getvalue())
        with self.assertNumQueries(0):
            self.assertEqual(contexto_painel()['total_ativos'], 2)

    def test_aquecimento_com_dado_invalido_avisa_sem_impedir_preparacao(self):
        erros = StringIO()
        with patch('inventario.aplicacao.risco.carregar_modelo_risco', side_effect=ValueError('Inventário incompatível')):
            call_command('aquecer_cache', stdout=StringIO(), stderr=erros)
        self.assertIn('Inventário incompatível', erros.getvalue())
        self.assertEqual(contexto_painel()['erro_risco'], 'Inventário incompatível')

    def test_perfil_invalido_retorna_400_em_vez_de_painel_de_outro_perfil(self):
        self.client.get('/')
        self.assertEqual(self.client.get('/?perfil=invalido').status_code, 400)

    def test_cache_arquivo_nao_copia_sobre_destino_e_repete_rename_transitorio(self):
        from inventario.infraestrutura.cache_arquivo import CacheArquivoAtomico
        import os
        with TemporaryDirectory(prefix='cache-atomico-') as pasta:
            c = CacheArquivoAtomico(pasta, {})
            c.set('chave', {'versao': 1})
            replace_original = os.replace
            def substituir(origem, destino):
                self.assertEqual(c.get('chave'), {'versao': 1})
                return replace_original(origem, destino)
            tentativas = []
            def repetir(origem, destino):
                tentativas.append(1)
                if len(tentativas) == 1:
                    raise PermissionError('Concorrência transitória')
                return replace_original(origem, destino)
            with patch('inventario.infraestrutura.cache_arquivo.os.replace', side_effect=repetir) as substituir_mock:
                c.set('teste-repeticao', 42)
                self.assertEqual(substituir_mock.call_count, 2)
                self.assertEqual(c.get('teste-repeticao'), 42)
            with patch('django.core.cache.backends.filebased.file_move_safe', side_effect=AssertionError('Não copiar sobre destino')), patch('inventario.infraestrutura.cache_arquivo.os.replace', side_effect=substituir):
                c.set('chave', {'versao': 2})
            self.assertEqual(c.get('chave'), {'versao': 2})

    def test_cache_arquivo_concorrente_nao_entrega_dado_parcial(self):
        from inventario.infraestrutura.cache_arquivo import CacheArquivoAtomico
        with TemporaryDirectory(prefix='cache-paralelo-') as pasta:
            c = CacheArquivoAtomico(pasta, {})
            c.set('alvo', {'conteudo': 'x'*10000})
            def usar(n):
                if n % 4 == 0:
                    c.set('alvo', {'conteudo': 'x'*10000})
                return c.get('alvo')
            with ThreadPoolExecutor(max_workers=20) as executor:
                valores = list(executor.map(usar, range(200)))
            self.assertEqual(valores, [{'conteudo': 'x'*10000}]*200)

    def test_cache_repete_leitura_transitoriamente_bloqueada_no_windows(self):
        from inventario.infraestrutura.cache_arquivo import CacheArquivoAtomico
        with TemporaryDirectory(prefix='cache-leitura-') as pasta:
            c = CacheArquivoAtomico(pasta, {})
            with patch('django.core.cache.backends.filebased.FileBasedCache.get', side_effect=[PermissionError('Handle transitório'), {'inteiro': True}]) as ler:
                self.assertEqual(c.get('teste'), {'inteiro': True})
                self.assertEqual(ler.call_count, 2)


class CacheConfirmado(BancoTeste):
    def setUp(self):
        super().setUp()
        connection.run_on_commit.clear()
        cache.clear()

    def test_commit_invalida_resumo_imediatamente(self):
        self.assertEqual(contexto_painel()['salas'], 1)
        with self.captureOnCommitCallbacks(execute=True):
            Sala.objects.create(id='SALA-NOVA', nome='Nova')
        connection.run_on_commit.clear()
        self.assertEqual(contexto_painel()['salas'], 2)
        with self.assertNumQueries(0):
            self.assertEqual(contexto_painel()['salas'], 2)

    def test_rollback_nao_publica_o_resumo_da_transacao(self):
        self.assertEqual(contexto_painel()['salas'], 1)
        try:
            with transaction.atomic():
                Sala.objects.create(id='SALA-ROLLBACK', nome='Não confirmada')
                self.assertEqual(contexto_painel()['salas'], 2)
                raise ValueError('Rollback intencional')
        except ValueError:
            pass
        with self.assertNumQueries(0):
            self.assertEqual(contexto_painel()['salas'], 1)
