from __future__ import annotations

import json
import logging
import time

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from inventario.web.forms import SoftwareForm, ImportarCSVForm
from inventario.models import Alerta, Incidencia, Software


INICIO_PROCESSO = time.monotonic()
LOGGER = logging.getLogger(__name__)


@require_http_methods(["POST"])
def alterar_status_incidencia(request, pk):
    get_object_or_404(Incidencia, pk=pk)
    status = request.POST.get("status", "")
    if status not in dict(Incidencia.STATUS):
        return JsonResponse({"erro": "Status inválido."}, status=400)
    from inventario.aplicacao.servicos import alterar_status

    try:
        incidencia = alterar_status(
            pk,
            status,
            request.user,
            request.POST.get("justificativa", ""),
            request.POST.get("aceita_ate"),
            evidencia=request.POST.get("evidencia", ""),
        )
    except ValidationError as erro:
        return JsonResponse({"erro": "; ".join(erro.messages)}, status=400)
    return JsonResponse({"id": incidencia.pk, "status": incidencia.status})


@require_GET
def alertas(request):
    from inventario.aplicacao.servicos import calcular_mttr
    from inventario.models import SnapshotRisco

    registros = Alerta.objects.select_related("ativo", "reconhecido_por")
    if request.GET.get("todos") != "1":
        registros = registros.filter(reconhecido_em__isnull=True)
    marcador = {}
    try:
        marcador = json.loads((settings.DATA_DIR / "ultima_rotina.json").read_text())
    except (OSError, ValueError):
        pass
    from django.core.paginator import Paginator
    incidencias = Incidencia.objects.select_related("ativo", "vulnerabilidade", "solicitada_por", "aprovada_por")
    if request.GET.get("pendentes") == "1":
        incidencias = incidencias.exclude(decisao_pendente="")
    pagina_decisoes = Paginator(incidencias.order_by("detectada_em", "pk"), 50).get_page(request.GET.get("pagina_decisoes"))
    return render(
        request,
        "inventario/alertas.html",
        {
            "alertas": registros[:200],
            "mttr": calcular_mttr(),
            "rotina": marcador,
            "contem_simulacao": SnapshotRisco.objects.filter(chave__startswith="DEMO-").exists(),
            "incidencias": pagina_decisoes,
            "pagina_decisoes": pagina_decisoes,
            "somente_pendentes": request.GET.get("pendentes") == "1",
        },
    )


@require_http_methods(["POST"])
def reconhecer_alerta_web(request, pk):
    from inventario.aplicacao.servicos import reconhecer_alerta

    get_object_or_404(Alerta, pk=pk)
    reconhecer_alerta(pk, request.user)
    messages.success(request, "Alerta reconhecido. Reconhecer não corrige a causa.")
    return redirect("alertas")


@require_http_methods(["GET", "POST"])
def software(request):
    if request.method == "POST" and not request.user.has_perm("inventario.add_software"):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    form = SoftwareForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        from inventario.aplicacao.servicos import salvar_cadastro

        from django.db import IntegrityError
        try:
            salvar_cadastro(form.save(commit=False), request.user)
        except (ValidationError, ValueError, IntegrityError):
            form.add_error(None, "Não foi possível cadastrar. Confira os vínculos e se o software já existe.")
        else:
            messages.success(request, "Software cadastrado; a rotina fará sugestões por CPE.")
            return redirect("software")
    from inventario.web.paginacao import buscar, paginar

    contexto = paginar(
        buscar(
            Software.objects.select_related("ativo"),
            request.GET,
            ("nome", "versao", "fornecedor", "ativo__hostname"),
        ),
        request,
    )
    return render(
        request,
        "inventario/software.html",
        contexto
        | {
            "form": form,
            "softwares": contexto["pagina"],
        },
    )


@require_http_methods(["GET", "POST"])
def importar_ativos(request):
    from inventario.infraestrutura.importacao import importar_csv

    resultado = None
    form = ImportarCSVForm(request.POST if request.method == "POST" else None, request.FILES if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            texto = form.cleaned_data["arquivo"].read().decode("utf-8-sig")
            resultado = importar_csv(texto, request.user, dry_run=not form.cleaned_data["aplicar"])
        except UnicodeDecodeError:
            form.add_error("arquivo", "Salve o CSV em UTF-8.")
    return render(request, "inventario/importar.html", {"form": form, "resultado": resultado})


@require_http_methods(["POST"])
def status_incidencia_web(request, pk):
    resposta = alterar_status_incidencia(request, pk)
    if resposta.status_code == 400:
        messages.error(request, json.loads(resposta.content)["erro"])
    else:
        messages.success(request, "Status atualizado com auditoria.")
    return redirect("alertas")

@require_http_methods(["POST"])
def decidir_pendencia_web(request, pk):
    from inventario.aplicacao.operacao import decidir_pendencia
    get_object_or_404(Incidencia, pk=pk)
    acao = request.POST.get("acao")
    try:
        if acao not in ("aprovar", "devolver"):
            raise ValidationError("Ação de revisão inválida.")
        decidir_pendencia(pk, acao == "aprovar", request.user, request.POST.get("motivo", ""))
    except ValidationError as erro:
        messages.error(request, "; ".join(erro.messages))
    else:
        messages.success(request, "Revisão registrada com autoria e auditoria.")
    return redirect("alertas")
