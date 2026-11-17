from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.utils import timezone

from inventario.aplicacao.fair import calcular, comparar, criar
from inventario.models import CenarioFAIR, RegistroAuditoria
from .base import BancoTeste
from .test_fair_matematica import exemplo


class FluxoFAIR(BancoTeste):
    def modelo(self, **alteracoes):
        return CenarioFAIR(**({'nome': 'Serviço fictício', 'ativo': self.a, 'evento': 'Interrupção do serviço',
            'ameaca': 'Falha fictícia', 'efeito': 'A', 'escopo': 'Unidade fictícia', 'origem_frequencia': 'Hipótese documentada',
            'origem_suscetibilidade': '', 'origem_perdas': 'Estimativa demonstrativa', 'qualidade': 'SIMULADO',
            'data_referencia': timezone.localdate(), 'premissas': exemplo()} | alteracoes))

    def dados(self):
        return {'nome': 'Serviço fictício', 'ativo': self.a.pk, 'evento': 'Interrupção', 'ameaca': 'Falha fictícia',
                'efeito': 'A', 'escopo': 'Empresa fictícia', 'origem_frequencia': 'Estimativa fictícia',
                'origem_perdas': 'Estimativa fictícia', 'qualidade': 'SIMULADO', 'data_referencia': timezone.localdate().isoformat(),
                'modo': 'LEF', 'sem_sobreposicao': 'on', 'frequencia_min': '4', 'frequencia_moda': '4', 'frequencia_max': '4',
                'perdas-TOTAL_FORMS': '12', 'perdas-INITIAL_FORMS': '0', 'perdas-MIN_NUM_FORMS': '0', 'perdas-MAX_NUM_FORMS': '12',
                'perdas-0-tipo': 'PRIMARIA', 'perdas-0-categoria': 'RESPOSTA',
                'perdas-0-minimo': '100', 'perdas-0-moda': '100', 'perdas-0-maximo': '100'}

    def test_criacao_auditada_e_sem_registrar_valores(self):
        cenario = criar(self.modelo(), self.usuario, True)
        registro = RegistroAuditoria.objects.filter(acao='CRIAR', entidade='CenarioFAIR').latest('id')
        self.assertEqual(registro.usuario_id, self.usuario.pk)
        self.assertNotIn('100', str(registro.detalhes))
        self.assertTrue(registro.detalhes['custos_distintos_declarados'])
        self.assertEqual(calcular(cenario, self.usuario, n=100, seed=7)['versao_modelo'], 'sauron.fair/30d-v1')
        with self.assertRaises(ValueError):
            criar(self.modelo(), self.usuario, False)
        with self.assertRaises(ValidationError):
            criar(self.modelo(data_referencia=timezone.localdate() + timedelta(days=1)), self.usuario, True)

    def test_interface_cria_simula_e_exibe_fatores(self):
        resposta = self.client.post('/fair/novo/', self.dados())
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        cenario = CenarioFAIR.objects.get()
        resposta = self.client.get(f'/fair/{cenario.pk}/')
        self.assertContains(resposta, 'Frequência de perda informada')
        resposta = self.client.post(f'/fair/{cenario.pk}/', {'n': 100, 'seed': 42})
        self.assertContains(resposta, 'Resultado simulado')
        self.assertContains(resposta, 'Simulações que ultrapassam cada valor')
        self.assertEqual(resposta.context['resultado']['horizonte_dias'], 30)
        self.assertEqual(self.client.get('/fair/').status_code, 200)

    def test_recusa_formulario_incompleto_ou_inconsistente(self):
        dados = self.dados()
        dados['modo'] = 'DECOMPOSTO'
        resposta = self.client.post('/fair/novo/', dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Preencha os três valores')
        self.assertFalse(CenarioFAIR.objects.exists())
        dados = self.dados() | {'perdas-0-tipo': 'SECUNDARIA'}
        self.assertContains(self.client.post('/fair/novo/', dados), 'informe as três chances')
        dados = self.dados() | {'acao_min': '0'}
        self.assertContains(self.client.post('/fair/novo/', dados), 'Não preencha acao')

    def test_vias_tef_e_decomposta_com_perda_secundaria(self):
        tef = self.dados() | {'modo': 'TEF', 'origem_suscetibilidade': 'Evidência fictícia',
                              'suscetibilidade_min': '0.5', 'suscetibilidade_moda': '0.5', 'suscetibilidade_max': '0.5'}
        resposta = self.client.post('/fair/novo/', tef)
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        cenario = CenarioFAIR.objects.get()
        self.assertEqual(cenario.premissas['suscetibilidade'], [.5, .5, .5])
        self.assertEqual(self.client.post(f'/fair/{cenario.pk}/', {'n': 100, 'seed': 1}).status_code, 200)
        dados = self.dados() | {'nome': 'Decomposto', 'modo': 'DECOMPOSTO', 'origem_suscetibilidade': 'Hipótese de controles',
            'acao_min': '1', 'acao_moda': '1', 'acao_max': '1', 'capacidade_min': '0.8', 'capacidade_moda': '0.8',
            'capacidade_max': '0.8', 'resistencia_min': '0.2', 'resistencia_moda': '0.2', 'resistencia_max': '0.2',
            'perdas-1-tipo': 'SECUNDARIA', 'perdas-1-categoria': 'MULTAS', 'perdas-1-minimo': '50',
            'perdas-1-moda': '50', 'perdas-1-maximo': '50', 'perdas-1-chance_min': '1',
            'perdas-1-chance_moda': '1', 'perdas-1-chance_max': '1'}
        resposta = self.client.post('/fair/novo/', dados)
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        cenario = CenarioFAIR.objects.get(nome='Decomposto')
        r = self.client.post(f'/fair/{cenario.pk}/', {'n': 100, 'seed': 7})
        self.assertEqual(r.context['resultado']['media_por_evento'], 150)

    def test_permissoes_mfa_e_csrf(self):
        cenario = criar(self.modelo(), self.usuario, True)
        sem = get_user_model().objects.create_user('sem-fair')
        with self.assertRaises(PermissionDenied):
            calcular(cenario, sem, n=100)
        self.autenticar(sem)
        self.assertEqual(self.client.get(f'/fair/{cenario.pk}/').status_code, 403)
        permissoes = Permission.objects.filter(content_type__app_label='inventario', codename__in=['view_ativo', 'view_cenariofinanceiro'])
        sem.user_permissions.add(*permissoes)
        sem = get_user_model().objects.get(pk=sem.pk)
        self.autenticar(sem)
        self.assertEqual(self.client.get('/fair/').status_code, 200)
        self.assertEqual(self.client.post('/fair/novo/', self.dados()).status_code, 403)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get('/fair/').url, '/mfa/')
        cliente = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, cliente)
        self.assertEqual(cliente.post(f'/fair/{cenario.pk}/', {'n': 100, 'seed': 42}).status_code, 403)

    def test_backup_e_restauracao_preservam_analise_e_suas_premissas(self):
        import json
        import sqlite3
        from contextlib import closing
        from cryptography.fernet import Fernet
        from django.conf import settings
        from django.test import override_settings
        from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
        cenario = criar(self.modelo(), self.usuario, True)
        destino = settings.DATA_DIR / 'fair-restaurado.sqlite3'
        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode(), SAURON_BACKUP_DESTINO_ADICIONAL=''):
            backup = backup_sqlite()
            restaurar_backup(backup, destino)
        with closing(sqlite3.connect(destino)) as banco:
            nome, premissas = banco.execute('SELECT nome, premissas FROM inventario_cenariofair WHERE id = ?', [cenario.pk]).fetchone()
        self.assertEqual(nome, cenario.nome)
        self.assertEqual(json.loads(premissas), cenario.premissas)

    def test_comparacao_exige_mesmo_contexto_e_nao_inventa_eficacia(self):
        base = criar(self.modelo(), self.usuario, True)
        parametros = exemplo() | {'frequencia': [0., 0., 0.]}
        alternativa = criar(self.modelo(nome='Alternativa hipotética', premissas=parametros), self.usuario, True)
        resultado = comparar(base, alternativa, self.usuario, n=1000, seed=4)
        self.assertEqual(resultado, comparar(base, alternativa, self.usuario, n=1000, seed=4))
        self.assertEqual(resultado['alternativa']['perda']['media'], 0)
        self.assertGreater(resultado['diferenca_media'], 0)
        self.assertNotEqual(resultado['semente_atual'], resultado['semente_alternativa'])
        resposta = self.client.post(f'/fair/{base.pk}/comparar/', {'alternativa': alternativa.pk, 'n': 100, 'seed': 4})
        self.assertContains(resposta, 'Não é economia comprovada')
        outra = criar(self.modelo(nome='Outro escopo', escopo='Unidade diferente'), self.usuario, True)
        with self.assertRaises(ValueError):
            comparar(base, outra, self.usuario, n=100)
        self.assertNotContains(self.client.get(f'/fair/{base.pk}/comparar/'), 'Outro escopo')
        with self.assertRaises(ValueError):
            comparar(base, base, self.usuario, n=100)
        sem = get_user_model().objects.create_user('sem-comparacao-fair')
        with self.assertRaises(PermissionDenied):
            comparar(base, alternativa, sem, n=100)
