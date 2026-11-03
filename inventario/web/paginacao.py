"""Busca e navegação de listas sem perder os filtros na próxima página."""

from django.core.paginator import Paginator
from django.db.models import Q
from inventario.models import Ativo, Sala


def filtrar_ativos(qs, dados, prefixo=""):
    for nome in ("tipo", "sala", "criticidade", "status"):
        valor = dados.get(nome, "")
        if not valor:
            continue
        if nome in ("tipo", "criticidade") and valor not in (
            [str(n) for n in range(1, 10)] if nome == "tipo" else ["1", "2", "3", "4"]
        ):
            return qs.none()
        campo = "sala_id" if nome == "sala" else nome
        qs = qs.filter(**{prefixo + campo: valor})
    return qs


def buscar(qs, dados, campos, campo_numerico=None):
    termo = dados.get("q", "").strip()[:100]
    if campo_numerico and termo.isascii() and termo.isdigit():
        numero = int(termo)
        return qs.filter(**{campo_numerico: numero}) if 1 <= numero <= 2**63 - 1 else qs.none()
    if termo:
        condicao = Q()
        for campo in campos:
            condicao |= Q(**{campo + "__icontains": termo})
        qs = qs.filter(condicao)
    return qs


def paginar(qs, request):
    pagina = Paginator(qs, 25).get_page(request.GET.get("page"))
    parametros = request.GET.copy()
    parametros.pop("page", None)
    return {"pagina": pagina, "parametros": parametros.urlencode(), "filtros": request.GET}


def opcoes_ativos():
    return {
        "tipos": Ativo._meta.get_field("tipo").choices,
        "salas_filtro": Sala.objects.only("id", "nome"),
        "status_ativos": Ativo.Status.choices,
        "criticidades": range(1, 5),
    }
