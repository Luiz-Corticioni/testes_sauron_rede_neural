from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from inventario.aplicacao.visao_executiva import DESTINOS, exportar, montar


class Selecao(forms.Form):
    execucao = forms.IntegerField(min_value=1, required=False, label="Execução FAIR")


class Exportacao(Selecao):
    destino = forms.ChoiceField(choices=list(DESTINOS.items()), label="Destino pretendido")


@require_GET
def painel(request):
    form = Selecao(request.GET)
    if not form.is_valid():
        return HttpResponse("Seleção inválida.", status=400)
    try:
        dados = montar(request.user, form.cleaned_data.get("execucao"))
    except ValidationError:
        return HttpResponse("Execução financeira não encontrada.", status=404)
    resposta = render(request, "inventario/executivo.html", dados)
    resposta["Cache-Control"] = "no-store"
    return resposta


@require_POST
def baixar(request):
    form = Exportacao(request.POST)
    if not form.is_valid():
        return HttpResponse("Informe destino e execução válidos.", status=400)
    try:
        conteudo = exportar(request.user, form.cleaned_data["destino"], form.cleaned_data.get("execucao"))
    except ValidationError:
        return HttpResponse("Não foi possível gerar o relatório com a seleção informada.", status=400)
    resposta = HttpResponse(conteudo, content_type="text/html; charset=utf-8")
    resposta["Content-Disposition"] = 'attachment; filename="sauron-diretoria.html"'
    resposta["Cache-Control"] = "no-store"
    resposta["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
    return resposta
