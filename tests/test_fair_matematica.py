from copy import deepcopy
from django.test import SimpleTestCase
from inventario.matematica.fair import simular, validar


def exemplo(modo='LEF'):
    return {'modo': modo, 'frequencia': [4., 4., 4.], 'acao': None, 'suscetibilidade': None,
            'capacidade': None, 'resistencia': None,
            'perdas': [{'tipo': 'PRIMARIA', 'categoria': 'RESPOSTA', 'valor': [100., 100., 100.],
                        'probabilidade': [1., 1., 1.]},
                       {'tipo': 'SECUNDARIA', 'categoria': 'MULTAS', 'valor': [50., 50., 50.],
                        'probabilidade': [1., 1., 1.]}]}


class MatematicaFAIR(SimpleTestCase):
    def test_frequencia_e_multiplos_eventos_contra_esperanca_analitica(self):
        dados = exemplo()
        r = simular(dados, n=20000, seed=7)
        self.assertEqual(r, simular(dados, n=20000, seed=7))
        self.assertAlmostEqual(r['eventos_medios'], 4, delta=.08)
        self.assertAlmostEqual(r['perda']['media'], 600, delta=12)
        self.assertAlmostEqual(r['media_primaria'] + r['media_secundaria'], r['perda']['media'])
        self.assertEqual(r['media_por_evento'], 150)
        self.assertEqual(r['excedencia'][-1]['percentual'], 0)
        self.assertTrue(all(a['percentual'] >= b['percentual'] for a, b in zip(r['excedencia'], r['excedencia'][1:])))

    def test_ameaca_condicional_e_decomposicao_sao_distintas(self):
        tef = exemplo('TEF') | {'suscetibilidade': [0., 0., 0.]}
        self.assertEqual(simular(tef, n=100)['eventos_medios'], 0)
        tef['suscetibilidade'] = [1., 1., 1.]
        self.assertAlmostEqual(simular(tef, n=10000)['eventos_medios'], 4, delta=.1)
        dados = exemplo('DECOMPOSTO') | {'acao': [1., 1., 1.], 'capacidade': [.9, .9, .9], 'resistencia': [.1, .1, .1]}
        r = simular(dados, n=10000)
        self.assertEqual(r['eventos_medios'], r['ameacas_medias'])
        dados['resistencia'] = [.9, .9, .9]  # Empate não é tratado como superação.
        self.assertEqual(simular(dados, n=100)['eventos_medios'], 0)
        dados['acao'] = [0., 0., 0.]
        self.assertEqual(simular(dados, n=100)['ameacas_medias'], 0)
        tef_cap = exemplo('TEF_CAPACIDADE') | {'capacidade': [.9, .9, .9], 'resistencia': [.1, .1, .1]}
        self.assertEqual(simular(tef_cap, n=100)['eventos_medios'], simular(tef_cap, n=100)['ameacas_medias'])
        contato_susc = exemplo('CONTATO_SUSC') | {'acao': [0., 0., 0.], 'suscetibilidade': [1., 1., 1.]}
        self.assertEqual(simular(contato_susc, n=100)['eventos_medios'], 0)

    def test_perdas_secundarias_e_ausencia_de_eventos(self):
        dados = exemplo()
        dados['perdas'][1]['probabilidade'] = [0., 0., 0.]
        self.assertEqual(simular(dados, n=100)['media_secundaria'], 0)
        dados['frequencia'] = [0., 0., 0.]
        r = simular(dados, n=100)
        self.assertEqual(r['perda']['media'], 0)
        self.assertEqual(r['probabilidade_evento'], 0)
        self.assertIsNone(r['media_por_evento'])
        dados = exemplo()
        dados['perdas'][0]['probabilidade'] = [0., 0., 0.]
        self.assertEqual(simular(dados, n=100)['media_primaria'], 0)

    def test_slef_controla_reacao_comum_e_preserva_versao_anterior(self):
        legado = exemplo()
        self.assertEqual(simular(legado, n=100)['versao_modelo'], 'sauron.fair/30d-v1')
        dados = exemplo() | {'slef': [0., 0., 0.]}
        self.assertEqual(simular(dados, n=100)['media_secundaria'], 0)
        dados['slef'] = [1., 1., 1.]
        resultado = simular(dados, n=1000)
        self.assertEqual(resultado['versao_modelo'], 'sauron.fair/30d-v2')
        self.assertEqual(resultado['efeitos_secundarios_medios'], resultado['eventos_medios'])
        self.assertEqual(resultado['proporcao_efeito_secundario'], 1)
        dados['slef'] = [.5, .5, .5]
        dados['perdas'].append({'tipo': 'SECUNDARIA', 'categoria': 'REPUTACAO',
                                'valor': [50., 50., 50.], 'probabilidade': [1., 1., 1.]})
        resultado = simular(dados, n=10000, seed=1)
        self.assertEqual(resultado['parcelas'][1]['media'], resultado['parcelas'][2]['media'])
        self.assertAlmostEqual(resultado['proporcao_efeito_secundario'], .5, delta=.02)
        with self.assertRaises(ValueError):
            validar(dados | {'slef': None})

    def test_entradas_invalidas_nao_sao_silenciosamente_convertidas(self):
        base = exemplo()
        ruins = [base | {'frequencia': [0, 3, 2]}, base | {'frequencia': [0, 0, float('nan')]},
                 base | {'frequencia': [False, 0, 1]}, base | {'modo': []}, base | {'acao': [0, 0, 0]},
                 base | {'perdas': [base['perdas'][0]] * 2},
                 base | {'perdas': [base['perdas'][1]]}]
        for dados in ruins:
            with self.subTest(dados=dados), self.assertRaises(ValueError):
                validar(deepcopy(dados))
        for n in (True, 99, 20001):
            with self.subTest(n=n), self.assertRaises(ValueError):
                simular(base, n=n)
