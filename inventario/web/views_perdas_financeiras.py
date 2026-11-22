from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, time

from inventario.aplicacao.perdas_financeiras import ESCRITA, registrar
from inventario.models import Ativo, Incidente, PerdaFinanceira


class IncidenteChoice(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"#{obj.pk} — {obj.titulo} — {obj.ativo.nome}"


class PerdaForm(forms.Form):
    incidente = IncidenteChoice(queryset=Incidente.objects.none(), label="Incidente encerrado")
    categoria = forms.ChoiceField(choices=PerdaFinanceira.CATEGORIAS, label="Categoria")
    natureza = forms.ChoiceField(choices=[("", "Selecione"), *PerdaFinanceira.NATUREZAS], label="Natureza do incidente")
    valor = forms.DecimalField(min_value=0, max_value=10**15, max_digits=18, decimal_places=2, label="Perda declarada em reais")
    data = forms.DateField(label="Data da perda", widget=forms.DateInput(attrs={"type": "date"}))
    origem = forms.CharField(max_length=200, label="Origem ou documento da estimativa")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ids = Incidente.objects.filter(encerrado_em__isnull=False).order_by("-encerrado_em").values_list("pk", flat=True)[:1000]
        self.fields["incidente"].queryset = Incidente.objects.filter(pk__in=ids).select_related("ativo")


class IncidenteHistoricoForm(forms.Form):
    ativo = forms.ModelChoiceField(queryset=Ativo.objects.none(), label="Ativo afetado")
    titulo = forms.CharField(max_length=160, label="Título")
    descricao = forms.CharField(label="Descrição", widget=forms.Textarea)
    gravidade = forms.IntegerField(label="Gravidade (1 a 4)", min_value=1, max_value=4)
    abertura = forms.DateField(label="Data de abertura", widget=forms.DateInput(attrs={"type": "date"}))
    encerramento = forms.DateField(label="Data de encerramento", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ids = Ativo.objects.order_by("pk").values_list("pk", flat=True)[:1000]
        self.fields["ativo"].queryset = Ativo.objects.filter(pk__in=ids)

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get("abertura"), dados.get("encerramento")
        if inicio and fim and (inicio > fim or fim > timezone.localdate()):
            raise forms.ValidationError("As datas devem estar em ordem e não podem ser futuras.")
        return dados


@require_http_methods(["GET", "POST"])
def perdas(request):
    form = PerdaForm(request.POST or None)
    if request.method == "POST":
        if not request.user.has_perms(ESCRITA):
            return HttpResponseForbidden("Acesso não autorizado.")
        if form.is_valid():
            try:
                registrar(request.user, **form.cleaned_data)
            except (ValidationError, IntegrityError, PermissionDenied):
                form.add_error(None, "Não foi possível registrar. Confira as datas, permissões e se já existe registro nesta categoria.")
            else:
                return redirect("perdas_financeiras")
    resposta = render(request, "inventario/perdas_financeiras.html", {"form": form,
        "pode_registrar": request.user.has_perms(ESCRITA),
        "perdas": PerdaFinanceira.objects.select_related("incidente", "registrado_por").order_by("-data", "-pk")[:50]})
    resposta["Cache-Control"] = "no-store"
    return resposta


@require_http_methods(["GET", "POST"])
def incidente_historico(request):
    from inventario.aplicacao.cadastros import salvar_cadastro
    form = IncidenteHistoricoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        dados = form.cleaned_data
        objeto = Incidente(ativo=dados["ativo"], titulo=dados["titulo"], descricao=dados["descricao"], gravidade=dados["gravidade"],
            aberto_em=timezone.make_aware(datetime.combine(dados["abertura"], time.min)),
            encerrado_em=timezone.make_aware(datetime.combine(dados["encerramento"], time.min)))
        try:
            salvar_cadastro(objeto, request.user)
        except (ValidationError, PermissionDenied):
            form.add_error(None, "Não foi possível registrar; confira os dados e as permissões.")
        else:
            return redirect("perdas_financeiras")
    resposta = render(request, "inventario/incidente_historico.html", {"form": form})
    resposta["Cache-Control"] = "no-store"
    return resposta
