"""Perímetro, registro histórico e consulta de cobertura com autorização comum."""
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from inventario.aplicacao.cobertura import salvar_perimetro, preparar_revisao, registrar_revisao, analisar_cobertura
from inventario.dominio.cobertura import ESTADOS
from inventario.models import Ativo, RelacaoAtivos, PerimetroRelacoes, RevisaoCobertura


class PerimetroForm(forms.ModelForm):
    ativos = forms.ModelMultipleChoiceField(queryset=Ativo.objects.all(), required=False)
    versao = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = PerimetroRelacoes
        fields = ["nome", "descricao", "ativos"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["nome"].disabled = True
            self.initial["versao"] = self.instance.atualizado_em.isoformat()


class ConsultaForm(forms.Form):
    perimetro = forms.ModelChoiceField(queryset=PerimetroRelacoes.objects.all())
    tipo = forms.ChoiceField(choices=RelacaoAtivos.TIPOS)
    principal = forms.CharField(required=False, max_length=200)
    filtro = forms.ChoiceField(required=False, choices=[("", "Todos os estados"), *[(e, e.replace("_", " ")) for e in ESTADOS]])
    limite = forms.IntegerField(required=False, min_value=1, max_value=100, initial=50)

    def parametros(self):
        d = self.cleaned_data.copy()
        d["perimetro"] = d["perimetro"].pk
        d["limite"] = d["limite"] or 50
        return d


class RevisaoForm(forms.ModelForm):
    contexto_sha256 = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = RevisaoCobertura
        fields = ["perimetro", "ativo", "tipo", "principal", "resultado", "evidencia", "observada_em", "revisar_em"]
        widgets = {c: forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}) for c in ("observada_em", "revisar_em")}


def texto_erro(erro):
    return "; ".join(erro.messages) if isinstance(erro, ValidationError) else str(erro)


@require_http_methods(["GET", "POST"])
def perimetro_form(request, pk=None):
    if not request.user.has_perm(f"inventario.{'change' if pk else 'add'}_perimetrorelacoes"):
        raise PermissionDenied
    p = get_object_or_404(PerimetroRelacoes, pk=pk) if pk else PerimetroRelacoes()
    form = PerimetroForm(request.POST if request.method == "POST" else None, instance=p)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            salvar_perimetro(request.user, d["nome"], d["descricao"], [a.pk for a in d["ativos"]], p.pk, d["versao"])
        except (ValueError, ValidationError, IntegrityError) as erro:
            form.add_error(None, texto_erro(erro) if not isinstance(erro, IntegrityError) else "Perímetro já existente ou conflito no cadastro.")
        else:
            messages.success(request, "Perímetro salvo. Os grafos deste escopo passam a usar seus ativos operacionais.")
            return redirect("qualidade_relacoes")
    return render(request, "inventario/formulario.html", {"form": form, "titulo": "Editar perímetro" if pk else "Declarar perímetro do grafo", "cancelar_url": reverse("qualidade_relacoes")})


@require_GET
def painel(request):
    form = ConsultaForm(request.GET if request.GET else None)
    resultado = None
    if form.is_bound and form.is_valid():
        try:
            resultado = analisar_cobertura(request.user, **form.parametros())
        except (ValueError, ValidationError) as erro:
            form.add_error(None, texto_erro(erro))
    return render(request, "inventario/qualidade_relacoes.html", {"form": form, "resultado": resultado, "perimetros": PerimetroRelacoes.objects.all()[:100]})


@require_GET
def api(request):
    form = ConsultaForm(request.GET)
    if not form.is_valid():
        return JsonResponse({"erro": form.errors.get_json_data()}, status=400)
    try:
        return JsonResponse(analisar_cobertura(request.user, **form.parametros()))
    except (ValueError, ValidationError) as erro:
        return JsonResponse({"erro": texto_erro(erro)}, status=400)


@require_http_methods(["GET", "POST"])
def revisar(request):
    if not request.user.has_perm("inventario.add_revisaocobertura"):
        raise PermissionDenied
    dados = request.POST if request.method == "POST" else request.GET
    resumo = None
    erro = None
    form = RevisaoForm(request.POST if request.method == "POST" else None, initial={k: dados.get(k, "") for k in ("perimetro", "tipo", "principal", "ativo")})
    # Prévia por GET valida a identidade do recorte antes de preencher o hash oculto.
    if request.method == "GET" and all(dados.get(k) for k in ("perimetro", "tipo", "ativo")):
        selecao = ConsultaForm({"perimetro": dados["perimetro"], "tipo": dados["tipo"], "principal": dados.get("principal", "")})
        if selecao.is_valid():
            try:
                _, resumo = preparar_revisao(request.user, selecao.cleaned_data["perimetro"].pk, dados["tipo"], dados["ativo"], dados.get("principal", ""))
                form.initial["contexto_sha256"] = resumo["sha256"]
            except (ValueError, ValidationError) as exc:
                erro = texto_erro(exc)
        else:
            erro = "Seleção de perímetro/camada inválida."
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data.copy()
        d["perimetro"], d["ativo"] = d["perimetro"].pk, d["ativo"].pk
        try:
            r = registrar_revisao(request.user, **d)
        except (ValueError, ValidationError) as exc:
            form.add_error(None, texto_erro(exc))
        else:
            messages.success(request, "Revisão registrada. Alterações futuras exigem nova avaliação.")
            return redirect("revisao_cobertura", pk=r.pk)
    return render(request, "inventario/revisar_cobertura.html", {"form": form, "resumo": resumo, "erro": erro})


@require_GET
def detalhe(request, pk):
    r = get_object_or_404(RevisaoCobertura.objects.select_related("ativo", "perimetro", "por"), pk=pk)
    return render(request, "inventario/revisao_cobertura.html", {"r": r})
