"""Demonstração manual de sensores: nenhum serviço de isca é instalado."""
from django import forms
import hashlib
from django.core import signing
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from inventario.aplicacao.honeypot import LIMITE_BYTES, salvar_sensor, importar_eventos, revisar_evento, alterar_retencao
from inventario.aplicacao.cowrie import converter
from inventario.models import EventoHoneypot, SensorHoneypot, RevisaoEventoHoneypot, PoliticaRetencaoHoneypot
from inventario.web.paginacao import paginar


class SensorForm(forms.ModelForm):
    class Meta:
        model = SensorHoneypot
        fields = ["nome", "localizacao", "responsavel", "ativo", "ambiente", "habilitado"]


class ImportarForm(forms.Form):
    arquivo = forms.FileField(label="Eventos JSON (UTF-8, até 1 MB)")

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if arquivo.size > LIMITE_BYTES:
            raise forms.ValidationError("Arquivo excede 1 MB.")
        return arquivo


class CowrieForm(ImportarForm):
    lote = forms.UUIDField(label="UUID do lote", help_text="Use o mesmo UUID ao reimportar o mesmo arquivo.")
    confirmacao = forms.CharField(required=False, widget=forms.HiddenInput)


class RevisaoForm(forms.Form):
    classificacao = forms.ChoiceField(label="Classificação", choices=RevisaoEventoHoneypot.CLASSIFICACOES)
    observacao = forms.ChoiceField(label="Observação", choices=RevisaoEventoHoneypot.OBSERVACOES)


class RetencaoForm(forms.Form):
    dias = forms.IntegerField(label="Prazo de retenção em dias", min_value=30, max_value=180, initial=90)


@require_GET
def painel(request):
    sensores = SensorHoneypot.objects.select_related("ativo").order_by("nome", "pk")
    eventos = EventoHoneypot.objects.select_related("sensor").order_by("-observado_em", "-pk")
    contexto = paginar(eventos, request)
    contexto["sensores"] = sensores[:200]
    return render(request, "inventario/honeypot.html", contexto)


@require_http_methods(["GET", "POST"])
def cadastrar(request, pk=None):
    sensor = get_object_or_404(SensorHoneypot, pk=pk) if pk is not None else SensorHoneypot()
    form = SensorForm(request.POST or None, instance=sensor)
    if request.method == "POST" and form.is_valid():
        try:
            salvar_sensor(form.save(commit=False), request.user)
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(request, "Sensor salvo. Nenhuma porta ou serviço de isca foi iniciado.")
            return redirect("honeypot")
    return render(request, "inventario/honeypot_form.html", {"form": form, "titulo": "Editar sensor" if pk is not None else "Cadastrar sensor"})


@require_http_methods(["GET", "POST"])
def importar(request, pk):
    sensor = get_object_or_404(SensorHoneypot, pk=pk)
    form = ImportarForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            resultado = importar_eventos(sensor.pk, form.cleaned_data["arquivo"].read(LIMITE_BYTES + 1), request.user)
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(request, f"Importados: {resultado['novos']}; repetidos: {resultado['duplicados']}.")
            return redirect("honeypot")
    return render(request, "inventario/honeypot_form.html",
                  {"form": form, "titulo": "Importar eventos", "sensor": sensor})


@require_http_methods(["GET", "POST"])
def importar_cowrie(request, pk):
    sensor = get_object_or_404(SensorHoneypot, pk=pk)
    form = CowrieForm(request.POST or None, request.FILES or None)
    previa = None
    if request.method == "POST" and form.is_valid():
        try:
            conteudo, ignorados = converter(form.cleaned_data["arquivo"].read(LIMITE_BYTES + 1), form.cleaned_data["lote"])
            vinculo = {"sensor": sensor.pk, "usuario": request.user.pk,
                       "sha256": hashlib.sha256(conteudo).hexdigest(), "ignorados": ignorados}
            token = form.cleaned_data["confirmacao"]
            if token:
                try:
                    validado = signing.loads(token, salt="cowrie-previa", max_age=600)
                except signing.BadSignature as erro:
                    raise ValidationError("Prévia inválida ou expirada; gere outra.") from erro
                if validado != vinculo:
                    raise ValidationError("O arquivo ou sensor mudou; gere outra prévia.")
                resultado = importar_eventos(sensor.pk, conteudo, request.user)
                messages.success(request, f"Importados: {resultado['novos']}; repetidos: {resultado['duplicados']}.")
                return redirect("honeypot")
            import json
            previa = {"eventos": json.loads(conteudo), "ignorados": ignorados}
            form.fields["confirmacao"].initial = signing.dumps(vinculo, salt="cowrie-previa")
            form = CowrieForm(initial={"lote": form.cleaned_data["lote"], "confirmacao": form.fields["confirmacao"].initial})
        except ValidationError as erro:
            form.add_error(None, erro)
    return render(request, "inventario/honeypot_cowrie.html", {"form": form, "sensor": sensor, "previa": previa})


@require_http_methods(["GET", "POST"])
def revisar(request, pk):
    evento = get_object_or_404(EventoHoneypot.objects.select_related("sensor"), pk=pk)
    form = RevisaoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        revisar_evento(evento.pk, form.cleaned_data["classificacao"], form.cleaned_data["observacao"], request.user)
        messages.success(request, "Revisão registrada. Uma classificação não comprova um ataque.")
        return redirect("honeypot_revisar", pk=evento.pk)
    return render(request, "inventario/honeypot_revisar.html", {"evento": evento, "form": form,
        "revisoes": evento.revisoes.select_related("autor")[:100]})


@require_http_methods(["GET", "POST"])
def retencao(request):
    politica = PoliticaRetencaoHoneypot.objects.filter(pk=1).select_related("atualizado_por").first()
    form = RetencaoForm(request.POST or None, initial={"dias": politica.dias if politica else 90})
    if request.method == "POST" and form.is_valid():
        alterar_retencao(form.cleaned_data["dias"], request.user)
        messages.success(request, "Política salva; os dados vencidos serão tratados pela próxima rotina.")
        return redirect("honeypot_retencao")
    return render(request, "inventario/honeypot_retencao.html", {"form": form, "politica": politica})
