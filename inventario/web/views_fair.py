"""Cenários FAIR por janela de 30 dias, sem obtenção automática de premissas."""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from inventario.aplicacao.fair import calcular, criar
from inventario.infraestrutura.limite_simulacoes import LimiteSimulacoes
from inventario.matematica.fair import validar
from inventario.models import Ativo, CenarioFAIR
from inventario.web.paginacao import paginar

MODOS = [('LEF', 'Frequência de perda informada (LEF)'), ('TEF', 'Ameaças e suscetibilidade (TEF)'),
         ('DECOMPOSTO', 'Contatos, ação, capacidade e resistência')]
CATEGORIAS = [('PRODUTIVIDADE', 'Produtividade'), ('RESPOSTA', 'Resposta'), ('SUBSTITUICAO', 'Substituição'),
              ('VANTAGEM', 'Vantagem competitiva'), ('MULTAS', 'Multas ou decisões'), ('REPUTACAO', 'Reputação')]


class CenarioForm(forms.Form):
    nome = forms.CharField(max_length=120)
    ativo = forms.ModelChoiceField(queryset=Ativo.objects.none())
    evento = forms.CharField(label='Evento de perda descrito', max_length=500)
    ameaca = forms.CharField(label='Agente ou causa da ameaça', max_length=200)
    efeito = forms.ChoiceField(choices=CenarioFAIR.EFEITOS)
    escopo = forms.CharField(max_length=300)
    origem_frequencia = forms.CharField(label='Fonte da frequência', max_length=300)
    origem_suscetibilidade = forms.CharField(label='Fonte da suscetibilidade ou capacidade e resistência', max_length=300, required=False)
    origem_perdas = forms.CharField(label='Fonte das magnitudes de perda', max_length=300)
    qualidade = forms.ChoiceField(choices=CenarioFAIR.QUALIDADE)
    data_referencia = forms.DateField(label='Data de referência das premissas', widget=forms.DateInput(attrs={'type': 'date'}))
    modo = forms.ChoiceField(choices=MODOS, label='Forma de estimar a frequência')
    sem_sobreposicao = forms.BooleanField(label='Confirmo que as parcelas de perda são distintas e cabem nos 30 dias.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ativo'].queryset = Ativo.objects.exclude(status__in=['INATIVO', 'BAIXADO'])
        nomes = {'frequencia': 'Frequência média de contatos, ameaças ou perdas por 30 dias',
                 'acao': 'Probabilidade de ação por contato (0 a 1)', 'suscetibilidade': 'Suscetibilidade por ameaça (0 a 1)',
                 'capacidade': 'Capacidade da ameaça (0 a 1)', 'resistencia': 'Resistência dos controles (0 a 1)'}
        for chave, label in nomes.items():
            for sufixo, nome in [('min', 'mínimo'), ('moda', 'mais provável'), ('max', 'máximo')]:
                self.fields[f'{chave}_{sufixo}'] = forms.DecimalField(label=f'{label} — {nome}', required=False,
                    min_value=0, max_value=20 if chave == 'frequencia' else 1)

    def parametros(self):
        dados = self.cleaned_data
        modo = dados['modo']
        necessarios = {'frequencia'} | ({'suscetibilidade'} if modo == 'TEF' else set()) | (
            {'acao', 'capacidade', 'resistencia'} if modo == 'DECOMPOSTO' else set())
        saida = {'modo': modo}
        for chave in ('frequencia', 'acao', 'suscetibilidade', 'capacidade', 'resistencia'):
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
    chance_min = forms.DecimalField(label='Chance secundária mínima (0 a 1)', min_value=0, max_value=1, required=False)
    chance_moda = forms.DecimalField(label='Chance secundária mais provável (0 a 1)', min_value=0, max_value=1, required=False)
    chance_max = forms.DecimalField(label='Chance secundária máxima (0 a 1)', min_value=0, max_value=1, required=False)

    def clean(self):
        dados = super().clean()
        if not self.has_changed():
            return dados
        if not dados.get('tipo') or not dados.get('categoria') or any(dados.get(c) is None for c in ('minimo', 'moda', 'maximo')):
            raise ValidationError('Informe tipo, categoria e três valores da parcela.')
        chances = [dados.get(c) for c in ('chance_min', 'chance_moda', 'chance_max')]
        if dados['tipo'] == 'PRIMARIA':
            if any(v is not None for v in chances):
                raise ValidationError('Para parcela primária deixe as chances secundárias em branco.')
            chances = [1, 1, 1]
        elif any(v is None for v in chances):
            raise ValidationError('Para parcela secundária informe as três chances condicionais.')
        dados['item'] = {'tipo': dados['tipo'], 'categoria': dados['categoria'],
                         'valor': [float(dados[c]) for c in ('minimo', 'moda', 'maximo')],
                         'probabilidade': [float(v) for v in chances]}
        return dados


PerdasFormSet = forms.formset_factory(PerdaForm, extra=12, max_num=12, absolute_max=12, validate_max=True)


class SimularForm(forms.Form):
    n = forms.IntegerField(label='Quantidade de simulações', min_value=100, max_value=20000, initial=10000)
    seed = forms.IntegerField(label='Semente para reprodução', min_value=0, max_value=2**32 - 1, initial=42)


@require_GET
def lista(request):
    return render(request, 'inventario/fair_lista.html', paginar(CenarioFAIR.objects.select_related('ativo', 'criado_por'), request))


@require_http_methods(['GET', 'POST'])
def novo(request):
    form = CenarioForm(request.POST or None)
    perdas = PerdasFormSet(request.POST or None, prefix='perdas')
    if request.method == 'POST' and form.is_valid() and perdas.is_valid():
        try:
            dados = form.parametros()
            dados['perdas'] = [linha['item'] for linha in perdas.cleaned_data if linha.get('item')]
            dados = validar(dados)
            campos = ('nome', 'ativo', 'evento', 'ameaca', 'efeito', 'escopo', 'origem_frequencia',
                      'origem_suscetibilidade', 'origem_perdas', 'qualidade', 'data_referencia')
            cenario = CenarioFAIR(**{campo: form.cleaned_data[campo] for campo in campos}, premissas=dados)
            criar(cenario, request.user, form.cleaned_data['sem_sobreposicao'])
        except (ValueError, ValidationError) as erro:
            form.add_error(None, '; '.join(erro.messages) if isinstance(erro, ValidationError) else str(erro))
        else:
            messages.success(request, 'Cenário registrado; hipóteses não são dados verificados automaticamente.')
            return redirect('fair_detalhe', pk=cenario.pk)
    return render(request, 'inventario/fair_form.html', {'form': form, 'perdas': perdas})


@require_http_methods(['GET', 'POST'])
def detalhe(request, pk):
    cenario = get_object_or_404(CenarioFAIR.objects.select_related('ativo', 'criado_por'), pk=pk)
    form = SimularForm(request.POST or None)
    resultado = None
    status = 200
    if request.method == 'POST' and form.is_valid():
        try:
            resultado = calcular(cenario, request.user, **form.cleaned_data)
            resultado['percentual_evento'] = resultado['probabilidade_evento'] * 100
            resultado['percentual_perda'] = resultado['perda']['probabilidade_perda'] * 100
        except LimiteSimulacoes:
            form.add_error(None, 'Há muitas simulações em andamento. Tente novamente em alguns segundos.')
            status = 429
        except (ValueError, ValidationError) as erro:
            form.add_error(None, '; '.join(erro.messages) if isinstance(erro, ValidationError) else str(erro))
    return render(request, 'inventario/fair_detalhe.html', {'cenario': cenario, 'form': form,
        'resultado': resultado, 'modos': dict(MODOS), 'categorias': dict(CATEGORIAS)}, status=status)
