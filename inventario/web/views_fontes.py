from django.shortcuts import render
from django.views.decorators.http import require_GET

from inventario.aplicacao.estado_fontes import resumo_fontes


@require_GET
def painel(request):
    from inventario.aplicacao.documentos import LEITURA as LEITURA_DOCUMENTOS
    ver_isca = request.user.has_perms(("inventario.view_ativo", "inventario.view_sensorhoneypot",
                                       "inventario.view_eventohoneypot"))
    return render(request, "inventario/fontes.html", resumo_fontes(ver_isca=ver_isca,
                  ver_importacoes=request.user.has_perms(LEITURA_DOCUMENTOS)))
