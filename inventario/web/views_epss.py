from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from inventario.models import ObservacaoEPSS, Vulnerabilidade
from inventario.web.paginacao import paginar
from inventario.aplicacao.epss import situacao_epss


@require_GET
def historico(request, pk):
    v = get_object_or_404(Vulnerabilidade.objects.select_related("epss_observacao"), pk=pk)
    registros = ObservacaoEPSS.objects.filter(cve_id=v.cve_id) if v.cve_id else ObservacaoEPSS.objects.none()
    contexto = paginar(registros, request)
    for item in contexto["pagina"]:
        item.probabilidade_pct, item.percentil_pct = item.epss * 100, item.percentil * 100
    return render(request, "inventario/epss.html", {**contexto, "v": v, "situacao": situacao_epss(v)})
