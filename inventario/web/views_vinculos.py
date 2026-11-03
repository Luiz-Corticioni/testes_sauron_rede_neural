"""Operações da ficha: o ativo vem da URL, nunca de um campo POST alterável."""

from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from inventario.aplicacao.catalogo_cves import preparar_importacao
from inventario.aplicacao.cadastros import salvar_cadastro
from inventario.aplicacao.vinculos import cadastrar_e_vincular, vincular_existente
from inventario.dominio.autocomplete import normalizar_cve
from inventario.infraestrutura.cve_client import IntegracaoCVEError
from inventario.models import Ativo, Dependencia, Incidencia, Vulnerabilidade
from inventario.web.forms import DependenciaForm, IncidenciaForm, VulnerabilidadeForm


def _erro_formulario(form, erro):
    texto = "; ".join(erro.messages) if isinstance(erro, ValidationError) else str(erro)
    form.add_error(None, texto)


def _renderizar(request, ativo, form, titulo, orientacao):
    return render(request, "inventario/formulario.html", {
        "form": form, "titulo": titulo, "orientacao": orientacao,
        "cancelar_url": reverse("detalhe_ativo", args=[ativo.pk]),
    })


@require_http_methods(["GET", "POST"])
def vincular(request, pk):
    ativo = get_object_or_404(Ativo, pk=pk)
    initial = {"status": Incidencia.Status.SUGERIDA}
    if request.GET.get("vulnerabilidade"):
        initial["vulnerabilidade"] = get_object_or_404(
            Vulnerabilidade, pk=request.GET["vulnerabilidade"]
        ).pk
    form = IncidenciaForm(
        request.POST if request.method == "POST" else None,
        instance=Incidencia(ativo=ativo), initial=initial, usuario=request.user, ativo_fixo=ativo,
    )
    if request.method == "POST" and form.is_valid():
        try:
            incidencia, criada = vincular_existente(form.save(commit=False), request.user)
        except (ValidationError, IntegrityError, ValueError) as erro:
            _erro_formulario(form, erro)
        else:
            messages.success(request, f"Vínculo {incidencia.pk} {'criado' if criada else 'já existente'}; estado preservado.")
            return redirect("detalhe_ativo", pk=ativo.pk)
    return _renderizar(request, ativo, form, "Vincular vulnerabilidade existente", 
        f"Ativo #{ativo.id_numerico} · {ativo.hostname}. O padrão é Aguardando confirmação; "
        "a pesquisa pública de uma CVE não demonstra que este ativo esteja vulnerável.")


@require_http_methods(["GET", "POST"])
def cadastrar(request, pk):
    ativo = get_object_or_404(Ativo, pk=pk)
    initial = {}
    if request.method == "GET" and request.GET.get("cve"):
        try:
            cve = normalizar_cve(request.GET["cve"])
            existente = Vulnerabilidade.objects.filter(cve_id=cve).first()
            if existente:
                messages.info(request, f"CVE já cadastrada; os dados existentes serão preservados. Fonte: {existente.fonte}.")
                if existente.fonte == "Cenário demonstrativo":
                    messages.warning(request, "Este é um cadastro didático antigo. Revise os dados pela NVD antes de confirmar uma incidência real.")
                url = reverse("vincular_vulnerabilidade_ativo", args=[ativo.pk])
                return redirect(f"{url}?{urlencode({'vulnerabilidade': existente.pk})}")
            initial, aviso = preparar_importacao(cve)
            messages.info(request, "Revise os dados da NVD, escolha a categoria e confira o ID antes de salvar.")
            if aviso:
                messages.warning(request, aviso)
        except (ValueError, IntegracaoCVEError):
            messages.warning(request, "Sem consulta em cache. Consulte a NVD ou preencha o cadastro manualmente.")
    form = VulnerabilidadeForm(request.POST if request.method == "POST" else None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            incidencia = cadastrar_e_vincular(form.save(commit=False), ativo, request.user)
        except (ValidationError, IntegrityError, ValueError) as erro:
            _erro_formulario(form, erro)
        else:
            messages.success(request, f"Vulnerabilidade e vínculo {incidencia.pk} salvos juntos, aguardando confirmação.")
            return redirect("detalhe_ativo", pk=ativo.pk)
    return _renderizar(request, ativo, form, "Cadastrar e vincular vulnerabilidade",
        f"Ativo #{ativo.id_numerico} · {ativo.hostname}. Salvar cria o cadastro e um vínculo "
        "Aguardando confirmação na mesma transação. Confira produto/versão antes de marcar como Aberta.")


@require_http_methods(["GET", "POST"])
def dependencia(request, pk):
    ativo = get_object_or_404(Ativo, pk=pk)
    form = DependenciaForm(request.POST if request.method == "POST" else None,
                          instance=Dependencia(dependente=ativo))
    form.fields["dependente"].disabled = True
    form.initial["dependente"] = ativo.pk
    if request.method == "POST" and form.is_valid():
        try:
            salvar_cadastro(form.save(commit=False), request.user)
        except (ValidationError, IntegrityError, ValueError) as erro:
            _erro_formulario(form, erro)
        else:
            messages.success(request, "Dependência salva com peso validado e auditoria.")
            return redirect("detalhe_ativo", pk=ativo.pk)
    return _renderizar(request, ativo, form, "Adicionar fornecedor de risco",
        f"{ativo.hostname} é o dependente i. Escolha o fornecedor j e a fração A[i,j] "
        "do risco transmitida por ele. Um cabo de rede, por si só, não determina esse peso.")
