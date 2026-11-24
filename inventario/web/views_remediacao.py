from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inventario.aplicacao.remediacao import sugerir_correcao
from inventario.aplicacao.vex_emissao import emitir_vex
from inventario.aplicacao.tickets import criar_ticket
from inventario.dominio.observacoes import LIMITE_BYTES
from inventario.models import Incidencia, ObservacaoImportada, SugestaoCorrecao, TicketRemediacao


class ComparacaoForm(forms.Form):
    observacao = forms.IntegerField(min_value=1, label="Número da observação Trivy revisada")
    observado_em = forms.CharField(max_length=40, label="Data do novo scan com fuso", help_text="Exemplo: 2026-11-20T14:30:00-03:00")
    fonte = forms.CharField(max_length=120, label="Identidade declarada da fonte")
    versao = forms.CharField(max_length=120, label="Versão declarada da fonte")
    declaracao = forms.CharField(max_length=500, label="Vínculo e cobertura", help_text="Explique por que o alvo pertence ao ativo e o que foi coberto pelo scan.")
    confirmar = forms.BooleanField(label="Confirmei que o alvo e o escopo do novo scan são comparáveis à observação anterior.")
    arquivo = forms.FileField(label="Novo relatório Trivy JSON (até 2 MiB)")

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if arquivo.size > LIMITE_BYTES:
            raise forms.ValidationError("Arquivo excede 2 MiB.")
        return arquivo


class EmissaoVEXForm(forms.Form):
    autor = forms.CharField(max_length=200, label="Autor da declaração (pessoa ou organização)")
    confirmar = forms.BooleanField(label="Revisei a identidade do produto e a evidência, e autorizo incluí-la no arquivo.")


class TicketForm(forms.Form):
    provedor = forms.ChoiceField(choices=[("jira", "Jira"), ("glpi", "GLPI")], label="Sistema de chamados")
    confirmar = forms.BooleanField(label="Autorizo enviar a identificação da incidência, CVE e prazo para o sistema escolhido.")


@require_http_methods(["GET", "POST"])
def ticket_web(request, pk):
    incidencia = get_object_or_404(Incidencia.objects.select_related("ativo", "vulnerabilidade"), pk=pk)
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            ticket = criar_ticket(pk, form.cleaned_data["provedor"], request.user)
            messages.info(request, f"Chamado #{ticket.pk}: {ticket.get_estado_display()}.")
            return redirect("ticket_remediacao", pk=pk)
        except ValidationError as erro:
            form.add_error(None, erro)
    tickets = TicketRemediacao.objects.filter(incidencia=incidencia).select_related("solicitado_por")
    resposta = render(request, "inventario/remediacao_ticket.html", {"inc": incidencia, "form": form, "tickets": tickets})
    resposta["Cache-Control"] = "no-store"
    return resposta


@require_http_methods(["GET", "POST"])
def exportar_vex(request, pk):
    incidencia = get_object_or_404(Incidencia.objects.select_related("ativo", "vulnerabilidade", "software"), pk=pk)
    form = EmissaoVEXForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            conteudo = emitir_vex(pk, form.cleaned_data["autor"], request.user)
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            resposta = HttpResponse(conteudo, content_type="application/json; charset=utf-8")
            resposta["Content-Disposition"] = f'attachment; filename="openvex-{incidencia.pk}.json"'
            resposta["Cache-Control"] = "no-store"
            return resposta
    resposta = render(request, "inventario/remediacao_vex.html", {"inc": incidencia, "form": form})
    resposta["Cache-Control"] = "no-store"
    return resposta


@require_http_methods(["GET", "POST"])
def comparar(request, pk):
    incidencia = get_object_or_404(Incidencia.objects.select_related("ativo", "vulnerabilidade"), pk=pk)
    form = ComparacaoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            sugestao = sugerir_correcao(pk, d["observacao"], d["arquivo"].read(LIMITE_BYTES + 1),
                                       d["observado_em"], d["declaracao"], d["fonte"], d["versao"], request.user)
            messages.success(request, f"Sugestão #{sugestao.pk} registrada. A incidência não foi alterada.")
            return redirect("comparar_correcao", pk=pk)
        except ValidationError as erro:
            form.add_error(None, erro)
        except Incidencia.DoesNotExist:
            form.add_error(None, "Incidência não encontrada.")
        except ObservacaoImportada.DoesNotExist:
            form.add_error("observacao", "Observação não encontrada.")
    from inventario.aplicacao.retencao_observacoes import corte_retencao
    sugestoes = SugestaoCorrecao.objects.filter(incidencia=incidencia, criado_em__gt=corte_retencao(),
        dados_eliminados=False).select_related("observacao", "criado_por").order_by("-criado_em")[:50]
    resposta = render(request, "inventario/remediacao_comparar.html", {"inc": incidencia, "form": form, "sugestoes": sugestoes})
    resposta["Cache-Control"] = "no-store"
    return resposta
