"""Demonstração manual de sensores: nenhum serviço de isca é instalado."""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from inventario.aplicacao.honeypot import LIMITE_BYTES, salvar_sensor, importar_eventos
from inventario.models import EventoHoneypot, SensorHoneypot
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
