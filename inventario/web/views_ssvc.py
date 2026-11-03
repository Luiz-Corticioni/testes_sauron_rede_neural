from datetime import timedelta
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from inventario.aplicacao.ssvc import contexto_atual, registrar_avaliacao, situacao, elegivel
from inventario.dominio.ssvc import PONTOS, politica
from inventario.models import Incidencia
from inventario.web.paginacao import paginar

ROTULOS = {"exploitation": "Exploração: evidências globais", "exposure": "Exposição neste ambiente",
           "automatable": "Exploração automatizável", "human_impact": "Impacto humano e na missão"}
VALORES = {"none": "Sem evidência após pesquisa", "public poc": "PoC público", "active": "Exploração ativa",
           "small": "Pequena (local ou altamente restrita)", "controlled": "Controlada (controles comprovados)", "open": "Aberta",
           "no": "Não", "yes": "Sim", "low": "Baixo", "medium": "Médio", "high": "Alto", "very high": "Muito alto"}


class FormSSVC(forms.Form):
    remediacao = forms.CharField(label="Remediação ou mitigação avaliada (patch, versão ou ação)", max_length=1000)
    contexto_hash = forms.CharField(widget=forms.HiddenInput, max_length=64)
    evidencia = forms.CharField(label="Evidências e justificativa de cada resposta", max_length=8000, widget=forms.Textarea)
    revisar_em = forms.DateField(label="Revisar em", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, valores in PONTOS.items():
            self.fields[nome] = forms.ChoiceField(label=ROTULOS[nome], required=False,
                choices=[("", "Desconhecido / pendente"), *((v, VALORES[v]) for v in valores)])
        self.order_fields(["remediacao", *PONTOS, "evidencia", "revisar_em", "contexto_hash"])


@require_http_methods(["GET", "POST"])
def painel(request, pk):
    inc = get_object_or_404(Incidencia.objects.select_related("ativo", "vulnerabilidade", "software"), pk=pk)
    _, assinatura = contexto_atual(inc)
    pode = request.user.has_perm("inventario.change_incidencia")
    if request.method == "POST" and not pode:
        raise PermissionDenied
    form = FormSSVC(request.POST if request.method == "POST" else None, initial={"contexto_hash": assinatura,
        "revisar_em": timezone.localdate()+timedelta(days=30), "exploitation": "active" if inc.vulnerabilidade.kev else ""})
    if request.method == "POST" and form.is_valid():
        try:
            registrar_avaliacao(inc.pk, request.user, {k: form.cleaned_data[k] for k in PONTOS},
                form.cleaned_data["evidencia"], form.cleaned_data["revisar_em"], form.cleaned_data["contexto_hash"], form.cleaned_data["remediacao"])
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            return redirect("ssvc_incidencia", pk=inc.pk)
    registros = inc.avaliacoes_ssvc.select_related("por")
    contexto = paginar(registros, request)
    for registro in contexto["pagina"]:
        registro.situacao_atual = situacao(registro, assinatura)
    return render(request, "inventario/ssvc.html", {**contexto, "inc": inc, "form": form, "pode_avaliar": pode and elegivel(inc), "elegivel": elegivel(inc), "politica": politica()[0]})
