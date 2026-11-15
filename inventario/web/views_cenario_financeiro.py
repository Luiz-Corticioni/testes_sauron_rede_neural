"""Interface independente para cenários financeiros com premissas explícitas."""
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from inventario.aplicacao.cenario_financeiro import calcular_cenario, criar_cenario
from inventario.infraestrutura.limite_simulacoes import LimiteSimulacoes
from inventario.models import CenarioFinanceiro
from inventario.web.paginacao import paginar


class CenarioForm(forms.ModelForm):
    class Meta:
        model = CenarioFinanceiro
        exclude = ("criado_por", "criado_em")
        widgets = {"data_referencia": forms.DateInput(attrs={"type": "date"})}
        labels = {"probabilidade": "Probabilidade hipotética em 30 dias (0 a 1)",
                  "probabilidade_apos": "Hipótese após controle (0 a 1, opcional)",
                  "horas_min": "Duração mínima (horas)", "horas_moda": "Duração mais provável (horas)",
                  "horas_max": "Duração máxima (horas)", "custo_hora": "Perda incremental por hora (R$)",
                  "custo_adicional": "Custo adicional por incidente (R$)"}


class SimulacaoForm(forms.Form):
    n = forms.IntegerField(label="Quantidade de simulações", min_value=100, max_value=100000, initial=20000)
    seed = forms.IntegerField(label="Semente", min_value=0, max_value=2**32 - 1, initial=42)
    limite = forms.DecimalField(label="Limiar de perda em R$ (opcional)", min_value=0, max_value=10**15, required=False)


@require_GET
def lista(request):
    return render(request, "inventario/cenarios_financeiros.html",
                  paginar(CenarioFinanceiro.objects.select_related("ativo", "criado_por"), request))


@require_http_methods(["GET", "POST"])
def novo(request):
    form = CenarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cenario = criar_cenario(form.save(commit=False), request.user)
        messages.success(request, "Cenário registrado. Suas premissas não são previsão de perda.")
        return redirect("cenario_financeiro_detalhe", pk=cenario.pk)
    return render(request, "inventario/cenario_financeiro_form.html", {"form": form})


@require_http_methods(["GET", "POST"])
def detalhe(request, pk):
    cenario = get_object_or_404(CenarioFinanceiro.objects.select_related("ativo", "criado_por"), pk=pk)
    form = SimulacaoForm(request.POST or None)
    resultado = None
    status = 200
    if request.method == "POST" and form.is_valid():
        dados = form.cleaned_data
        try:
            resultado = calcular_cenario(cenario, request.user, n=dados["n"], seed=dados["seed"],
                                          limite=float(dados["limite"]) if dados["limite"] is not None else None)
        except LimiteSimulacoes:
            form.add_error(None, "Há muitas simulações em andamento. Tente novamente em alguns segundos.")
            status = 429
        except ValueError as erro:
            form.add_error(None, str(erro))
        if resultado:
            resultado["frequencia_percentual"] = 100 * resultado["atual"]["probabilidade_perda"]
            if resultado["excedencia"] is not None:
                resultado["excedencia_percentual"] = 100 * resultado["excedencia"]
    return render(request, "inventario/cenario_financeiro_detalhe.html",
                  {"cenario": cenario, "form": form, "resultado": resultado}, status=status)
