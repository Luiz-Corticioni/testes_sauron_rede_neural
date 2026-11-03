"""Comparador de scores com POST protegido; GET nunca consulta a internet."""

from django import forms
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_GET
from inventario.dominio.autocomplete import normalizar_cve
from inventario.infraestrutura.cve_client import CVE_RE
from inventario.matematica.cvss import CalculadoraCVSS31
from inventario.models import Vulnerabilidade
from inventario.aplicacao.comparacao_cvss import comparar


class ComparacaoForm(forms.Form):
    vulnerabilidade = forms.CharField(max_length=30, required=False, widget=forms.HiddenInput)
    cve = forms.CharField(
        label="CVE",
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "CVE-2024-7450", "data-autocomplete-cve": ""}),
    )
    vetor = forms.CharField(
        label="Vetor base CVSS 3.1 (opcional)",
        required=False,
        max_length=2048,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Se vazio, usa o vetor 3.1 da NVD. Cole somente as oito métricas base; o cálculo é feito pelo Sauron.",
    )
    atualizar = forms.BooleanField(
        label="Atualizar pela internet",
        required=False,
        initial=True,
        help_text="Desmarque para usar apenas o cache local, sem acesso à internet.",
    )

    def clean_cve(self):
        cve = normalizar_cve(self.cleaned_data["cve"])
        if cve and not CVE_RE.fullmatch(cve):
            raise forms.ValidationError("Informe uma CVE completa, como CVE-2024-7450.")
        return cve

    def clean_vetor(self):
        vetor = self.cleaned_data["vetor"].strip()
        if vetor:
            try:
                return CalculadoraCVSS31.calcular(vetor).vetor
            except ValueError as erro:
                raise forms.ValidationError(str(erro)) from erro
        return vetor

    def clean(self):
        dados = super().clean()
        if not self.errors and not (dados.get("cve") or dados.get("vetor")):
            raise forms.ValidationError("Informe uma CVE ou um vetor base 3.1.")
        return dados


@require_http_methods(["GET", "POST"])
def comparacao(request):
    codigo = (
        request.POST.get("vulnerabilidade")
        if request.method == "POST"
        else request.GET.get("vulnerabilidade")
    )
    cadastro = get_object_or_404(Vulnerabilidade, pk=codigo) if codigo else None
    vetor_cadastro = cadastro.cvss_vetor if cadastro and cadastro.cvss_versao == "3.1" else ""
    initial = {
        "cve": cadastro.cve_id if cadastro else request.GET.get("cve", ""),
        "vetor": vetor_cadastro,
        "vulnerabilidade": codigo or "",
    }
    form = ComparacaoForm(request.POST if request.method == "POST" else None, initial=initial)
    resultado = None
    if request.method == "POST" and form.is_valid():
        dados = form.cleaned_data
        if cadastro and (cadastro.cve_id or "") != dados["cve"]:
            form.add_error(
                "cve",
                "A CVE difere do cadastro selecionado. Abra uma nova comparação para consultar outra CVE.",
            )
        else:
            origem = (
                "vetor do cadastro"
                if cadastro and dados["vetor"] == vetor_cadastro
                else "vetor informado"
            )
            resultado = comparar(
                dados["cve"], dados["vetor"], dados["atualizar"], origem if dados["vetor"] else None
            )
            if (
                cadastro
                and resultado["local31"]["nota"] is not None
                and cadastro.cvss_versao == "3.1"
                and cadastro.cvss != resultado["local31"]["nota"]
            ):
                resultado["avisos"].append(
                    "A nota cadastrada difere do vetor calculado nesta tela; revise o cadastro. A comparação não altera seus dados."
                )
    return render(
        request,
        "inventario/comparacao_cvss.html",
        {"form": form, "resultado": resultado, "cadastro": cadastro},
    )


@require_GET
def guia(request):
    from inventario.web.orientacao import GLOSSARIO

    return render(request, "inventario/guia.html", {"glossario": GLOSSARIO})
