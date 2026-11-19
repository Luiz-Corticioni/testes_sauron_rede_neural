"""Cenários FAIR por janela de 30 dias, sem obtenção automática de premissas."""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from django.utils import timezone

from inventario.aplicacao.fair import comparar, criar, executar
from inventario.infraestrutura.limite_simulacoes import LimiteSimulacoes
from inventario.matematica.fair import validar
from inventario.models import Ativo, CenarioFAIR, ExecucaoFAIR
from inventario.web.paginacao import paginar

MODOS = [('LEF', 'Frequência de perda informada (LEF)'), ('TEF', 'Ameaças e suscetibilidade (TEF)'),
         ('TEF_CAPACIDADE', 'Ameaças, capacidade e resistência'), ('CONTATO_SUSC', 'Contatos, ação e suscetibilidade'),
         ('DECOMPOSTO', 'Contatos, ação, capacidade e resistência')]
CATEGORIAS = [('PRODUTIVIDADE', 'Produtividade'), ('RESPOSTA', 'Resposta'), ('SUBSTITUICAO', 'Substituição'),
              ('VANTAGEM', 'Vantagem competitiva'), ('MULTAS', 'Multas ou decisões'), ('REPUTACAO', 'Reputação')]


class CenarioForm(forms.Form):
    nome = forms.CharField(max_length=120)
    ativo = forms.ModelChoiceField(queryset=Ativo.objects.none())
    evento = forms.CharField(label='Evento de perda descrito', max_length=500)
    ameaca = forms.CharField(label='Agente ou causa da ameaça', max_length=200)
    valor_para_ameaca = forms.CharField(label='Valor percebido pela ameaça (contexto opcional)', max_length=300, required=False)
    esforco_da_ameaca = forms.CharField(label='Esforço percebido pela ameaça (contexto opcional)', max_length=300, required=False)
    risco_para_ameaca = forms.CharField(label='Risco percebido pela ameaça (contexto opcional)', max_length=300, required=False)
    habilidades_ameaca = forms.CharField(label='Habilidades da ameaça (contexto opcional)', max_length=300, required=False)
    recursos_ameaca = forms.CharField(label='Recursos da ameaça (contexto opcional)', max_length=300, required=False)
    efeito = forms.ChoiceField(choices=CenarioFAIR.EFEITOS)
    escopo = forms.CharField(max_length=300)
    origem_frequencia = forms.CharField(label='Fonte da frequência', max_length=300)
    origem_suscetibilidade = forms.CharField(label='Fonte da suscetibilidade ou capacidade e resistência', max_length=300, required=False)
    origem_perdas = forms.CharField(label='Fonte das perdas e dos efeitos secundários', max_length=300)
    qualidade = forms.ChoiceField(choices=CenarioFAIR.QUALIDADE)
    data_referencia = forms.DateField(label='Data de referência das premissas', widget=forms.DateInput(attrs={'type': 'date'}))
    modo = forms.ChoiceField(choices=MODOS, label='Forma de estimar a frequência')
    sem_sobreposicao = forms.BooleanField(label='Confirmo que as parcelas de perda são distintas e cabem nos 30 dias.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ativo'].queryset = Ativo.objects.exclude(status__in=['INATIVO', 'BAIXADO'])
        nomes = {'frequencia': 'Frequência média de contatos, ameaças ou perdas por 30 dias',
                 'acao': 'Probabilidade de ação por contato (0 a 1)', 'suscetibilidade': 'Suscetibilidade por ameaça (0 a 1)',
                 'capacidade': 'Capacidade da ameaça (0 a 1)', 'resistencia': 'Resistência dos controles (0 a 1)',
                 'slef': 'Chance de efeito secundário por evento de perda (0 a 1)'}
        for chave, label in nomes.items():
            for sufixo, nome in [('min', 'mínimo'), ('moda', 'mais provável'), ('max', 'máximo')]:
                self.fields[f'{chave}_{sufixo}'] = forms.DecimalField(label=f'{label} — {nome}', required=False,
                    min_value=0, max_value=20 if chave == 'frequencia' else 1)

    def parametros(self, parcelas):
        dados = self.cleaned_data
        modo = dados['modo']
        necessarios = {'frequencia'} | {
            'LEF': set(), 'TEF': {'suscetibilidade'}, 'TEF_CAPACIDADE': {'capacidade', 'resistencia'},
            'CONTATO_SUSC': {'acao', 'suscetibilidade'}, 'DECOMPOSTO': {'acao', 'capacidade', 'resistencia'},
        }[modo]
        saida = {'modo': modo}
        if any(item['tipo'] == 'SECUNDARIA' for item in parcelas):
            necessarios.add('slef')
        for chave in ('frequencia', 'acao', 'suscetibilidade', 'capacidade', 'resistencia', 'slef'):
            valores = [dados.get(f'{chave}_{sufixo}') for sufixo in ('min', 'moda', 'max')]
            if chave in necessarios:
                if any(valor is None for valor in valores):
                    raise ValidationError(f'Preencha os três valores de {chave}.')
                saida[chave] = [float(valor) for valor in valores]
            else:
                if any(valor is not None for valor in valores):
                    raise ValidationError(f'Não preencha {chave} neste modo; isso não seria utilizado.')
                saida[chave] = None
        return saida


class PerdaForm(forms.Form):
    tipo = forms.ChoiceField(choices=[('', 'Selecione'), ('PRIMARIA', 'Primária'), ('SECUNDARIA', 'Secundária')], required=False)
    categoria = forms.ChoiceField(choices=[('', 'Selecione'), *CATEGORIAS], required=False)
    minimo = forms.DecimalField(label='Valor mínimo (R$)', min_value=0, max_value=10**12, required=False)
    moda = forms.DecimalField(label='Valor mais provável (R$)', min_value=0, max_value=10**12, required=False)
    maximo = forms.DecimalField(label='Valor máximo (R$)', min_value=0, max_value=10**12, required=False)
    chance_min = forms.DecimalField(label='Chance condicional mínima (0 a 1)', min_value=0, max_value=1, required=False)
    chance_moda = forms.DecimalField(label='Chance condicional mais provável (0 a 1)', min_value=0, max_value=1, required=False)
    chance_max = forms.DecimalField(label='Chance condicional máxima (0 a 1)', min_value=0, max_value=1, required=False)

    def clean(self):
        dados = super().clean()
        if not any(valor is not None and valor != '' for valor in dados.values()):
            return dados
        if not dados.get('tipo') or not dados.get('categoria') or any(dados.get(c) is None for c in ('minimo', 'moda', 'maximo')):
            raise ValidationError('Informe tipo, categoria e três valores da parcela.')
        chances = [dados.get(c) for c in ('chance_min', 'chance_moda', 'chance_max')]
        if dados['tipo'] == 'PRIMARIA' and all(v is None for v in chances):
            chances = [1, 1, 1]
        elif any(v is None for v in chances):
            raise ValidationError('Informe as três chances condicionais, ou deixe-as em branco somente para perda primária certa.')
        dados['item'] = {'tipo': dados['tipo'], 'categoria': dados['categoria'],
                         'valor': [float(dados[c]) for c in ('minimo', 'moda', 'maximo')],
                         'probabilidade': [float(v) for v in chances]}
        return dados


PerdasFormSet = forms.formset_factory(PerdaForm, extra=12, max_num=12, absolute_max=12, validate_max=True)


class SimularForm(forms.Form):
    n = forms.IntegerField(label='Quantidade de simulações', min_value=100, max_value=20000, initial=10000)
    seed = forms.IntegerField(label='Semente para reprodução', min_value=0, max_value=2**32 - 1, initial=42)


class SimularRegistroForm(SimularForm):
    guardar = forms.BooleanField(label='Guardar resultado e cópia das premissas para revisão', required=False)

    def __init__(self, *args, pode_guardar, **kwargs):
        super().__init__(*args, **kwargs)
        if not pode_guardar:
            self.fields['guardar'].widget = forms.HiddenInput()


class CompararForm(SimularForm):
    alternativa = forms.ModelChoiceField(queryset=CenarioFAIR.objects.none(), label='Análise alternativa')
    intervencao = forms.CharField(label='Intervenção proposta', max_length=200, required=False,
        help_text='Opcional: descreva a ação considerada, sem credenciais ou dados pessoais.')
    custo_30_dias = forms.DecimalField(label='Custo adicional estimado nos mesmos 30 dias (R$)',
        max_digits=14, decimal_places=2, min_value=0, required=False)
    fonte_custo = forms.CharField(label='Fonte e justificativa do custo', max_length=300, required=False)
    custo_distinto = forms.BooleanField(required=False,
        label='Confirmo que esse custo adicional não está incluído nas perdas de nenhum dos cenários.')

    def __init__(self, *args, atual, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alternativa'].queryset = CenarioFAIR.objects.filter(
            ativo_id=atual.ativo_id, evento=atual.evento, ameaca=atual.ameaca, efeito=atual.efeito,
            escopo=atual.escopo, versao_modelo=atual.versao_modelo).exclude(pk=atual.pk)
        self.fields['alternativa'].label_from_instance = lambda c: f'{c.nome} (#{c.pk}, {c.data_referencia})'

    def clean(self):
        dados = super().clean()
        if dados.get('custo_30_dias') is not None and not (
            dados.get('intervencao') and dados.get('fonte_custo') and dados.get('custo_distinto')):
            raise ValidationError('Para considerar o custo, informe a intervenção, a fonte e confirme que ele não está duplicado.')
        if dados.get('custo_30_dias') is None and (dados.get('fonte_custo') or dados.get('custo_distinto')):
            raise ValidationError('Informe o custo dos mesmos 30 dias ou deixe em branco a fonte e a confirmação.')
        return dados


class SensibilidadeFAIRForm(forms.Form):
    premissa = forms.ChoiceField(label='Premissa a examinar')
    n = forms.IntegerField(label='Simulações por alternativa', min_value=100, max_value=3000, initial=1000)
    seed = forms.IntegerField(label='Semente', min_value=0, max_value=2**32-1, initial=42)

    def __init__(self, *args, cenario, **kwargs):
        super().__init__(*args, **kwargs)
        nomes = {'frequencia': 'Frequência em 30 dias', 'acao': 'Chance de ação',
                 'suscetibilidade': 'Suscetibilidade', 'capacidade': 'Capacidade',
                 'resistencia': 'Resistência', 'slef': 'Chance de reação secundária'}
        opcoes = [(k, v) for k, v in nomes.items() if cenario.premissas.get(k) is not None]
        opcoes += [(f'perda:{i}', f"Valor: {p['tipo']} · {p['categoria']}")
                   for i, p in enumerate(cenario.premissas['perdas'])]
        self.fields['premissa'].choices = opcoes


@never_cache
@require_GET
def lista(request):
    return render(request, 'inventario/fair_lista.html', paginar(CenarioFAIR.objects.select_related('ativo', 'criado_por'), request))


def dados_iniciais(cenario):
    campos = ('nome', 'ativo', 'evento', 'ameaca', 'valor_para_ameaca', 'esforco_da_ameaca', 'risco_para_ameaca',
              'habilidades_ameaca', 'recursos_ameaca', 'efeito', 'escopo', 'origem_frequencia',
              'origem_suscetibilidade', 'origem_perdas', 'qualidade', 'data_referencia')
    dados = {campo: getattr(cenario, campo) for campo in campos}
    dados['nome'] = cenario.nome[:110] + ' - cópia'
    dados['modo'] = cenario.premissas['modo']
    for chave in ('frequencia', 'acao', 'suscetibilidade', 'capacidade', 'resistencia', 'slef'):
        valores = cenario.premissas.get(chave)
        if chave == 'slef' and 'slef' not in cenario.premissas and any(p['tipo'] == 'SECUNDARIA' for p in cenario.premissas['perdas']):
            valores = [1., 1., 1.]
        if valores is not None:
            for sufixo, valor in zip(('min', 'moda', 'max'), valores):
                dados[f'{chave}_{sufixo}'] = valor
    linhas = []
    for item in cenario.premissas['perdas']:
        linha = {'tipo': item['tipo'], 'categoria': item['categoria']}
        linha.update(zip(('minimo', 'moda', 'maximo'), item['valor']))
        if item['tipo'] == 'SECUNDARIA' or item['probabilidade'] != [1., 1., 1.]:
            linha.update(zip(('chance_min', 'chance_moda', 'chance_max'), item['probabilidade']))
        linhas.append(linha)
    return dados, linhas


@never_cache
@require_http_methods(['GET', 'POST'])
def novo(request, origem_pk=None):
    inicial, parcelas_iniciais = {}, []
    origem = None
    if origem_pk is not None:
        origem = get_object_or_404(CenarioFAIR.objects.select_related('ativo'), pk=origem_pk)
        inicial, parcelas_iniciais = dados_iniciais(origem)
    elif request.GET.get('exemplo') == '1':
        inicial = {'nome': 'Demonstração fictícia', 'evento': 'Interrupção fictícia de faturamento',
                   'ameaca': 'Falha operacional fictícia', 'efeito': 'A', 'escopo': 'Empresa fictícia',
                   'origem_frequencia': 'Hipótese para demonstração', 'origem_suscetibilidade': 'Hipótese para demonstração',
                   'origem_perdas': 'Valores fictícios para demonstração', 'qualidade': 'SIMULADO',
                   'data_referencia': timezone.localdate(), 'modo': 'TEF', 'frequencia_min': 0.1,
                   'frequencia_moda': 0.5, 'frequencia_max': 1, 'suscetibilidade_min': 0.1,
                   'suscetibilidade_moda': 0.3, 'suscetibilidade_max': 0.5}
        parcelas_iniciais = [{'tipo': 'PRIMARIA', 'categoria': 'PRODUTIVIDADE', 'minimo': 1000, 'moda': 5000, 'maximo': 10000}]
    form = CenarioForm(request.POST or None, initial=inicial)
    perdas = PerdasFormSet(request.POST or None, prefix='perdas', initial=parcelas_iniciais)
    if request.method == 'POST' and form.is_valid() and perdas.is_valid():
        try:
            parcelas = [linha['item'] for linha in perdas.cleaned_data if linha.get('item')]
            dados = form.parametros(parcelas)
            dados['perdas'] = parcelas
            dados = validar(dados)
            campos = ('nome', 'ativo', 'evento', 'ameaca', 'valor_para_ameaca', 'esforco_da_ameaca', 'risco_para_ameaca',
                      'habilidades_ameaca', 'recursos_ameaca', 'efeito', 'escopo', 'origem_frequencia',
                      'origem_suscetibilidade', 'origem_perdas', 'qualidade', 'data_referencia')
            cenario = CenarioFAIR(**{campo: form.cleaned_data[campo] for campo in campos}, premissas=dados)
            criar(cenario, request.user, form.cleaned_data['sem_sobreposicao'])
        except (ValueError, ValidationError) as erro:
            form.add_error(None, '; '.join(erro.messages) if isinstance(erro, ValidationError) else str(erro))
        else:
            messages.success(request, 'Cenário registrado; hipóteses não são dados verificados automaticamente.')
            return redirect('fair_detalhe', pk=cenario.pk)
    return render(request, 'inventario/fair_form.html', {'form': form, 'perdas': perdas, 'origem': origem,
                                                         'exemplo': request.GET.get('exemplo') == '1'})


@never_cache
@require_http_methods(['GET', 'POST'])
def detalhe(request, pk):
    cenario = get_object_or_404(CenarioFAIR.objects.select_related('ativo', 'criado_por'), pk=pk)
    pode_guardar = request.user.has_perms(('inventario.view_ativo', 'inventario.view_cenariofinanceiro', 'inventario.add_cenariofinanceiro'))
    form = SimularRegistroForm(request.POST or None, pode_guardar=pode_guardar)
    resultado = None
    execucao = None
    status = 200
    if request.method == 'POST' and form.is_valid():
        try:
            resultado, execucao = executar(cenario, request.user, **form.cleaned_data)
            resultado['percentual_evento'] = resultado['probabilidade_evento'] * 100
            resultado['percentual_perda'] = resultado['perda']['probabilidade_perda'] * 100
        except LimiteSimulacoes:
            form.add_error(None, 'Há muitas simulações em andamento. Tente novamente em alguns segundos.')
            status = 429
        except (ValueError, ValidationError) as erro:
            form.add_error(None, '; '.join(erro.messages) if isinstance(erro, ValidationError) else str(erro))
    execucoes = cenario.execucoes.select_related('criado_por').only('id', 'criado_em', 'criado_por__username', 'cenario_id')[:10]
    return render(request, 'inventario/fair_detalhe.html', {'cenario': cenario, 'form': form, 'execucao': execucao,
        'execucoes': execucoes, 'resultado': resultado, 'modos': dict(MODOS), 'categorias': dict(CATEGORIAS)}, status=status)


@never_cache
@require_GET
def execucao(request, pk, execucao_id):
    registro = get_object_or_404(ExecucaoFAIR.objects.select_related('criado_por'), pk=execucao_id, cenario_id=pk)
    return render(request, 'inventario/fair_execucao.html', {'registro': registro})


@never_cache
@require_GET
def exportar(request, pk, execucao_id):
    registro = get_object_or_404(ExecucaoFAIR, pk=execucao_id, cenario_id=pk)
    dados = {'versao_modelo': registro.versao_modelo, 'n': registro.n, 'seed': registro.seed,
             'versao_python': registro.versao_python, 'versao_numpy': registro.versao_numpy,
             'criado_em': registro.criado_em.isoformat(), 'premissas': registro.premissas_snapshot, 'resultado': registro.resultado}
    resposta = JsonResponse(dados, json_dumps_params={'allow_nan': False, 'ensure_ascii': False})
    resposta['Content-Disposition'] = f'attachment; filename="sauron-fair-{registro.pk}.json"'
    resposta['Cache-Control'] = 'no-store'
    return resposta


@never_cache
@require_http_methods(['GET', 'POST'])
def comparacao(request, pk):
    atual = get_object_or_404(CenarioFAIR.objects.select_related('ativo'), pk=pk)
    form = CompararForm(request.POST or None, atual=atual)
    resultado = None
    status = 200
    if request.method == 'POST' and form.is_valid():
        try:
            resultado = comparar(atual, form.cleaned_data['alternativa'], request.user,
                                 n=form.cleaned_data['n'], seed=form.cleaned_data['seed'])
            resultado['intervencao'] = form.cleaned_data['intervencao']
            if form.cleaned_data['custo_30_dias'] is not None:
                from decimal import Decimal
                resultado['fonte_custo'] = form.cleaned_data['fonte_custo']
                resultado['custo_30_dias'] = form.cleaned_data['custo_30_dias']
                resultado['diferenca_apos_custo'] = Decimal(str(resultado['diferenca_media'])) - resultado['custo_30_dias']
        except LimiteSimulacoes:
            form.add_error(None, 'Há muitas simulações em andamento. Tente novamente em alguns segundos.')
            status = 429
        except (ValueError, ValidationError) as erro:
            form.add_error(None, '; '.join(erro.messages) if isinstance(erro, ValidationError) else str(erro))
    return render(request, 'inventario/fair_comparacao.html', {'cenario': atual, 'form': form,
        'resultado': resultado}, status=status)


@never_cache
@require_http_methods(['GET', 'POST'])
def sensibilidade(request, pk):
    from inventario.aplicacao.sensibilidade_fair import analisar
    cenario = get_object_or_404(CenarioFAIR.objects.select_related('ativo'), pk=pk)
    form = SensibilidadeFAIRForm(request.POST or None, cenario=cenario)
    resultado = None
    status = 200
    if request.method == 'POST' and form.is_valid():
        escolhido = form.cleaned_data['premissa']
        fator, indice = ('valor_perda', int(escolhido.split(':')[1])) if escolhido.startswith('perda:') else (escolhido, None)
        try:
            resultado = analisar(cenario, request.user, fator, indice, form.cleaned_data['n'], form.cleaned_data['seed'])
            resultado['rotulo'] = dict(form.fields['premissa'].choices)[escolhido]
        except LimiteSimulacoes:
            form.add_error(None, 'Há muitas simulações em andamento. Tente novamente em alguns segundos.')
            status = 429
        except (ValueError, ValidationError) as erro:
            form.add_error(None, '; '.join(erro.messages) if isinstance(erro, ValidationError) else str(erro))
    return render(request, 'inventario/fair_sensibilidade.html', {'cenario': cenario, 'form': form,
        'resultado': resultado}, status=status)
