"""Decisões do recomendador compartilham as mesmas regras do terminal."""

from datetime import date
import sys
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from inventario.aplicacao.imune import decidir_sugestao, executar_ciclo
from inventario.models import Anticorpo, SugestaoImune, Tolerancia


@require_GET
def painel(request):
    anticorpos = list(Anticorpo.objects.order_by("id")[:100])
    meia_vida = settings.IMUNE_MEIA_VIDA_DIAS
    curvas = []
    agora = timezone.now()
    horizonte = meia_vida * 3 if meia_vida <= sys.float_info.max / 3 else meia_vida
    for a in anticorpos:
        memoria = a.para_dominio()
        idade = max(0, (agora - a.reforcado_em).total_seconds() / 86400)
        a.forca_atual = memoria.decaimento(idade, meia_vida)
        curvas.append(
            {
                "id": a.pk,
                "vulnerabilidade": a.vulnerabilidade_id,
                "idade": idade,
                "forca_atual": a.forca_atual,
                "pontos": [
                    [horizonte * (p / 36), memoria.decaimento(horizonte * (p / 36), meia_vida)]
                    for p in range(37)
                ],
            }
        )
    return render(
        request,
        "inventario/imune.html",
        {
            "sugestoes": SugestaoImune.objects.filter(estado__in=["PENDENTE", "OBSERVACAO"])
            .select_related("ativo", "vulnerabilidade")
            .order_by("-afinidade")[:100],
            "anticorpos": anticorpos,
            "curvas": curvas,
            "tolerancias": Tolerancia.objects.filter(valida_ate__gte=timezone.localdate())
            .select_related("ativo", "por")
            .order_by("-valida_ate")[:100],
            "limiar": settings.IMUNE_LIMIAR,
            "meia_vida": settings.IMUNE_MEIA_VIDA_DIAS,
        },
    )


@require_POST
def ciclo(request):
    messages.success(request, f"Ciclo local: {executar_ciclo()}")
    return redirect("imune")


@require_POST
def decidir(request, pk):
    acao = request.POST.get("acao")
    if acao not in {"confirmar", "rejeitar"}:
        return HttpResponseBadRequest("Escolha confirmar ou rejeitar.")
    try:
        validade = request.POST.get("valida_ate")
        decidir_sugestao(
            pk,
            acao == "confirmar",
            request.user,
            request.POST.get("motivo", ""),
            date.fromisoformat(validade) if validade else None,
        )
    except (ValidationError, ValueError, ObjectDoesNotExist) as erro:
        return HttpResponseBadRequest(str(erro))
    messages.success(request, "Decisão humana e autoria registradas.")
    return redirect("imune")
