from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.utils import timezone

from inventario.aplicacao.fair import calcular, comparar, criar, executar
from inventario.models import CenarioFAIR, ExecucaoFAIR, RegistroAuditoria
from .base import BancoTeste
from .test_fair_matematica import exemplo


class FluxoFAIR(BancoTeste):
    def test_sensibilidade_fair_extremos_sem_alterar_cenario(self):
        from copy import deepcopy
        from inventario.aplicacao.sensibilidade_fair import analisar
        parametros = exemplo() | {'frequencia': [0., 1., 2.], 'slef': [1., 1., 1.]}
        cenario = criar(self.modelo(premissas=parametros), self.usuario, True)
        anterior = deepcopy(cenario.premissas)
        resultado = analisar(cenario, self.usuario, 'frequencia', n=1000, seed=42)
        self.assertEqual(resultado['media_min'], 0)
        self.assertGreater(resultado['media_max'], resultado['media_min'])
        self.assertEqual(resultado, analisar(cenario, self.usuario, 'frequencia', n=1000, seed=42))
        cenario.refresh_from_db()
        self.assertEqual(cenario.premissas, anterior)
        self.assertContains(self.client.get(f'/fair/{cenario.pk}/sensibilidade/'), 'não mede causalidade')
        resposta = self.client.post(f'/fair/{cenario.pk}/sensibilidade/', {'premissa': 'frequencia', 'n': '100', 'seed': '42'})
        self.assertContains(resposta, 'Premissa fixada no mínimo')
        sem = get_user_model().objects.create_user('sem-sensibilidade-fair')
        with self.assertRaises(PermissionDenied):
            analisar(cenario, sem, 'frequencia', n=100)
        with self.assertRaises(ValueError):
            analisar(cenario, self.usuario, 'valor_perda', indice=999, n=100)
        with self.assertRaises(ValueError):
            analisar(cenario, self.usuario, 'frequencia', n=3001)
        self.autenticar(sem)
        self.assertEqual(self.client.get(f'/fair/{cenario.pk}/sensibilidade/').status_code, 403)

    def test_sensibilidade_do_valor_de_perda(self):
        from copy import deepcopy
        from inventario.aplicacao.sensibilidade_fair import analisar
        parametros = deepcopy(exemplo()) | {'slef': [1., 1., 1.]}
        parametros['perdas'][0]['valor'] = [50., 100., 300.]
        cenario = criar(self.modelo(premissas=parametros), self.usuario, True)
        resultado = analisar(cenario, self.usuario, 'valor_perda', indice=0, n=1000, seed=4)
        self.assertLess(resultado['media_min'], resultado['media_base'])
        self.assertGreater(resultado['media_max'], resultado['media_base'])

    def test_comparacao_de_intervencao_exige_fonte_e_custo_nao_duplicado(self):
        base = criar(self.modelo(), self.usuario, True)
        alternativa = criar(self.modelo(nome='Alternativa'), self.usuario, True)
        dados = {'alternativa': alternativa.pk, 'n': 100, 'seed': 42, 'intervencao': 'Segmentar rede',
                 'custo_30_dias': '1200.00', 'fonte_custo': 'Orçamento fictício'}
        resposta = self.client.post(f'/fair/{base.pk}/comparar/', dados)
        self.assertContains(resposta, 'confirme que ele não está duplicado')
        self.assertIsNone(resposta.context['resultado'])
        resposta = self.client.post(f'/fair/{base.pk}/comparar/', dados | {'custo_distinto': 'on'})
        self.assertContains(resposta, 'Segmentar rede')
        self.assertContains(resposta, 'Não é lucro, benefício comprovado')
        self.assertEqual(resposta.context['resultado']['custo_30_dias'], 1200)
        self.assertLess(resposta.context['resultado']['diferenca_apos_custo'], 0)
        from decimal import Decimal
        self.assertEqual(resposta.context['resultado']['diferenca_apos_custo'],
            Decimal(str(resposta.context['resultado']['diferenca_media'])) - Decimal('1200.00'))
        sem_custo = {'alternativa': alternativa.pk, 'n': 100, 'seed': 42, 'intervencao': 'Segmentar rede'}
        resposta = self.client.post(f'/fair/{base.pk}/comparar/', sem_custo)
        self.assertContains(resposta, 'Custo não informado')
        zero = sem_custo | {'custo_30_dias': '0', 'fonte_custo': 'Estimativa', 'custo_distinto': 'on'}
        resposta = self.client.post(f'/fair/{base.pk}/comparar/', zero)
        self.assertContains(resposta, 'Diferença simulada entre médias menos o custo declarado')

    def test_backup_pre_migracao_omite_campos_novos_do_cenario(self):
        import json
        from unittest.mock import patch
        from cryptography.fernet import Fernet
        from django.db import connection
        from django.db.migrations.recorder import MigrationRecorder
        from django.test import override_settings
        from inventario.infraestrutura.backup import backup_sqlite

        criar(self.modelo(valor_para_ameaca='Contexto'), self.usuario, True)
        aplicadas = MigrationRecorder(connection).applied_migrations()
        antigas = {k: v for k, v in aplicadas.items() if k != ('inventario', '0038_cenariofair_esforco_da_ameaca_and_more')}
        chave = Fernet.generate_key()
        with override_settings(SAURON_BACKUP_KEY=chave.decode(), SAURON_BACKUP_DESTINO_ADICIONAL=''):
            with patch.object(MigrationRecorder, 'applied_migrations', return_value=antigas):
                arquivo = backup_sqlite()
            itens = json.loads(Fernet(chave).decrypt(arquivo.read_bytes()))
        campos = next(i['fields'] for i in itens if i['model'] == 'inventario.cenariofair')
        self.assertNotIn('valor_para_ameaca', campos)
        self.assertEqual(campos['nome'], 'Serviço fictício')

    def modelo(self, **alteracoes):
        return CenarioFAIR(**({'nome': 'Serviço fictício', 'ativo': self.a, 'evento': 'Interrupção do serviço',
            'ameaca': 'Falha fictícia', 'efeito': 'A', 'escopo': 'Unidade fictícia', 'origem_frequencia': 'Hipótese documentada',
            'origem_suscetibilidade': '', 'origem_perdas': 'Estimativa demonstrativa', 'qualidade': 'SIMULADO',
            'data_referencia': timezone.localdate(), 'premissas': exemplo() | {'slef': [1., 1., 1.]}} | alteracoes))

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
        self.assertEqual(calcular(cenario, self.usuario, n=100, seed=7)['versao_modelo'], 'sauron.fair/30d-v2')
        with self.assertRaises(ValueError):
            criar(self.modelo(), self.usuario, False)
        with self.assertRaises(ValidationError):
            criar(self.modelo(data_referencia=timezone.localdate() + timedelta(days=1)), self.usuario, True)

    def test_cenario_legado_continua_calculavel_sem_reclassificacao_silenciosa(self):
        legado = criar(self.modelo(versao_modelo='sauron.fair/30d-v1', premissas=exemplo()), self.usuario, True)
        self.assertNotIn('slef', legado.premissas)
        self.assertEqual(calcular(legado, self.usuario, n=100)['versao_modelo'], 'sauron.fair/30d-v1')
        copia = self.client.get(f'/fair/{legado.pk}/copiar/')
        self.assertContains(copia, 'Esta cópia usará a versão 2')
        self.assertEqual(copia.context['form'].initial['slef_min'], 1.)
        with self.assertRaises(ValidationError):
            criar(self.modelo(versao_modelo='sauron.fair/30d-v1'), self.usuario, True)

    def test_interface_cria_simula_e_exibe_fatores(self):
        resposta = self.client.post('/fair/novo/', self.dados() | {'valor_para_ameaca': 'Dados estratégicos', 'habilidades_ameaca': 'Especialista'})
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        cenario = CenarioFAIR.objects.get()
        self.assertEqual(cenario.valor_para_ameaca, 'Dados estratégicos')
        resposta = self.client.get(f'/fair/{cenario.pk}/')
        self.assertContains(resposta, 'Dados estratégicos')
        self.assertEqual(self.client.get(f'/fair/{cenario.pk}/copiar/').context['form'].initial['habilidades_ameaca'], 'Especialista')
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
        self.assertContains(self.client.post('/fair/novo/', dados), 'Informe as três chances')
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
            'perdas-1-chance_moda': '1', 'perdas-1-chance_max': '1', 'slef_min': '1', 'slef_moda': '1', 'slef_max': '1'}
        resposta = self.client.post('/fair/novo/', dados)
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        cenario = CenarioFAIR.objects.get(nome='Decomposto')
        r = self.client.post(f'/fair/{cenario.pk}/', {'n': 100, 'seed': 7})
        self.assertEqual(r.context['resultado']['media_por_evento'], 150)

    def test_vias_mistas_e_chance_primaria_opcional(self):
        comum = {'origem_suscetibilidade': 'Justificativa fictícia', 'acao_min': '1', 'acao_moda': '1', 'acao_max': '1',
                 'suscetibilidade_min': '1', 'suscetibilidade_moda': '1', 'suscetibilidade_max': '1'}
        dados = self.dados() | comum | {'modo': 'CONTATO_SUSC', 'perdas-0-chance_min': '0',
                                        'perdas-0-chance_moda': '0', 'perdas-0-chance_max': '0'}
        resposta = self.client.post('/fair/novo/', dados)
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        cenario = CenarioFAIR.objects.get()
        resultado = self.client.post(f'/fair/{cenario.pk}/', {'n': 100, 'seed': 7}).context['resultado']
        self.assertGreater(resultado['eventos_medios'], 0)
        self.assertEqual(resultado['perda']['media'], 0)
        dados = self.dados() | {'nome': 'TEF com controles', 'modo': 'TEF_CAPACIDADE', 'origem_suscetibilidade': 'Hipótese',
            'capacidade_min': '0.8', 'capacidade_moda': '0.8', 'capacidade_max': '0.8',
            'resistencia_min': '0.2', 'resistencia_moda': '0.2', 'resistencia_max': '0.2'}
        resposta = self.client.post('/fair/novo/', dados)
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        self.assertEqual(CenarioFAIR.objects.get(nome='TEF com controles').premissas['modo'], 'TEF_CAPACIDADE')

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
        _, execucao = executar(cenario, self.usuario, n=100, seed=42, guardar=True)
        destino = settings.DATA_DIR / 'fair-restaurado.sqlite3'
        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode(), SAURON_BACKUP_DESTINO_ADICIONAL=''):
            backup = backup_sqlite()
            restaurar_backup(backup, destino)
        with closing(sqlite3.connect(destino)) as banco:
            nome, premissas = banco.execute('SELECT nome, premissas FROM inventario_cenariofair WHERE id = ?', [cenario.pk]).fetchone()
            salvo = banco.execute('SELECT resultado FROM inventario_execucaofair WHERE id = ?', [execucao.pk]).fetchone()[0]
        self.assertEqual(nome, cenario.nome)
        self.assertEqual(json.loads(premissas), cenario.premissas)
        self.assertEqual(json.loads(salvo), execucao.resultado)

    def test_guardar_e_baixar_execucao_preserva_snapshot_e_permissoes(self):
        cenario = criar(self.modelo(), self.usuario, True)
        url = f'/fair/{cenario.pk}/'
        resposta = self.client.post(url, {'n': 100, 'seed': 7, 'guardar': 'on'})
        self.assertContains(resposta, 'Abrir simulação guardada')
        registro = ExecucaoFAIR.objects.get()
        self.assertEqual(registro.premissas_snapshot['premissas'], cenario.premissas)
        self.assertEqual(registro.resultado, calcular(cenario, self.usuario, n=100, seed=7))
        auditoria = RegistroAuditoria.objects.filter(acao='SIMULAR', entidade='CenarioFAIR').latest('id')
        self.assertNotIn('100', str(auditoria.detalhes))
        CenarioFAIR.objects.filter(pk=cenario.pk).update(nome='Nome alterado depois')
        detalhe = self.client.get(f'/fair/{cenario.pk}/execucoes/{registro.pk}/')
        self.assertContains(detalhe, 'Serviço fictício')
        self.assertIn('no-store', detalhe['Cache-Control'])
        self.assertNotContains(detalhe, 'Nome alterado depois')
        arquivo = self.client.get(f'/fair/{cenario.pk}/execucoes/{registro.pk}/baixar/')
        self.assertEqual(arquivo.status_code, 200)
        self.assertIn('no-store', arquivo['Cache-Control'])
        self.assertEqual(arquivo.json()['premissas']['nome'], 'Serviço fictício')
        self.assertEqual(self.client.get(f'/fair/999999/execucoes/{registro.pk}/').status_code, 404)
        sem = get_user_model().objects.create_user('sem-exportar-fair')
        self.autenticar(sem)
        self.assertEqual(self.client.get(f'/fair/{cenario.pk}/execucoes/{registro.pk}/baixar/').status_code, 403)

    def test_guardar_exige_escrita_e_recusa_mudanca_concorrente(self):
        from unittest.mock import patch
        cenario = criar(self.modelo(), self.usuario, True)
        leitor = get_user_model().objects.create_user('leitor-fair')
        leitor.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventario',
            codename__in=['view_ativo', 'view_cenariofinanceiro']))
        with self.assertRaises(PermissionDenied):
            executar(cenario, leitor, n=100, guardar=True)
        self.assertIsNone(executar(cenario, leitor, n=100, guardar=False)[1])
        self.autenticar(leitor)
        self.assertEqual(self.client.post(f'/fair/{cenario.pk}/', {'n': 100, 'seed': 42, 'guardar': 'on'}).status_code, 403)
        self.autenticar(self.usuario)
        resultado = calcular(cenario, self.usuario, n=100)
        def mudar(*args, **kwargs):
            CenarioFAIR.objects.filter(pk=cenario.pk).update(nome='Mudança concorrente')
            return resultado
        with patch('inventario.aplicacao.fair.calcular', side_effect=mudar):
            with self.assertRaisesMessage(ValueError, 'cenário mudou'):
                executar(cenario, self.usuario, n=100, guardar=True)
        self.assertFalse(ExecucaoFAIR.objects.exists())

    def test_comparacao_exige_mesmo_contexto_e_nao_inventa_eficacia(self):
        base = criar(self.modelo(), self.usuario, True)
        parametros = exemplo() | {'frequencia': [0., 0., 0.], 'slef': [1., 1., 1.]}
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

    def test_exemplo_e_copia_exigem_confirmacao_e_nao_gravam_por_get(self):
        resposta = self.client.get('/fair/novo/?exemplo=1')
        self.assertContains(resposta, 'Exemplo fictício')
        self.assertEqual(resposta.context['form'].initial['qualidade'], 'SIMULADO')
        self.assertNotIn('ativo', resposta.context['form'].initial)
        self.assertFalse(CenarioFAIR.objects.exists())
        original = criar(self.modelo(), self.usuario, True)
        resposta = self.client.get(f'/fair/{original.pk}/copiar/')
        self.assertContains(resposta, 'Pré-preenchido')
        self.assertEqual(len(resposta.context['perdas'].initial), 2)
        self.assertEqual(CenarioFAIR.objects.count(), 1)
        dados = self.dados() | {'nome': 'Cópia revisada', 'evento': original.evento, 'ameaca': original.ameaca,
            'escopo': original.escopo, 'perdas-INITIAL_FORMS': '2', 'perdas-1-tipo': 'SECUNDARIA',
            'perdas-1-categoria': 'MULTAS', 'perdas-1-minimo': '50', 'perdas-1-moda': '50', 'perdas-1-maximo': '50',
            'perdas-1-chance_min': '1', 'perdas-1-chance_moda': '1', 'perdas-1-chance_max': '1',
            'slef_min': '1', 'slef_moda': '1', 'slef_max': '1'}
        resposta = self.client.post(f'/fair/{original.pk}/copiar/', dados)
        self.assertEqual(resposta.status_code, 302, str(resposta.context['form'].errors) if resposta.status_code == 200 else '')
        copia = CenarioFAIR.objects.get(nome='Cópia revisada')
        self.assertEqual(len(copia.premissas['perdas']), 2)
        self.assertEqual(self.client.post(f'/fair/{original.pk}/comparar/', {'alternativa': copia.pk, 'n': 100, 'seed': 1}).status_code, 200)
