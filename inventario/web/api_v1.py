"""Consultas versionadas do inventário, com autorização por sessão e MFA."""

from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from inventario.models import Ativo, Incidencia, Vulnerabilidade


def problema(status, titulo, detalhe):
    resposta = JsonResponse({"type": "about:blank", "title": titulo, "status": status,
                             "detail": detalhe}, status=status,
                            content_type="application/problem+json")
    resposta["Cache-Control"] = "no-store"
    return resposta


def verificar(request, permissoes):
    if not request.user.is_authenticated:
        return problema(401, "Autenticação necessária", "Entre e conclua o segundo fator.")
    if request.method != "GET":
        resposta = problema(405, "Método não permitido", "Use GET nesta rota.")
        resposta["Allow"] = "GET"
        return resposta
    if not request.user.has_perms(permissoes):
        return problema(403, "Acesso negado", "A conta não possui as permissões necessárias.")
    return None


def paginar(request, registros):
    try:
        pagina = int(request.GET.get("pagina", "1"))
        tamanho = int(request.GET.get("tamanho", "25"))
        if pagina < 1 or not 1 <= tamanho <= 100:
            raise ValueError
    except ValueError:
        return problema(422, "Parâmetro inválido", "Use página positiva e tamanho entre 1 e 100.")
    paginador = Paginator(registros, tamanho)
    if pagina > paginador.num_pages:
        return problema(404, "Página não encontrada", "A página solicitada não existe.")
    parte = paginador.page(pagina)
    return JsonResponse({"pagina": pagina, "tamanho": tamanho, "total": paginador.count,
                         "paginas": paginador.num_pages, "resultados": list(parte.object_list)})


def ativos_por_risco(qs, campos):
    """Reutiliza o cálculo de risco existente sem alterar o significado do score."""
    from inventario.aplicacao.risco import calcular_risco_banco

    resultado = calcular_risco_banco(perfil="puro")
    riscos = dict(zip(resultado["ids_ativos"], resultado["risco_efetivo"], strict=True))
    registros = list(qs.order_by("id").values(*campos))
    for item in registros:
        item["risco_efetivo"] = riscos.get(item["id"], 0.0)
    registros.sort(key=lambda item: (-item["risco_efetivo"], item["id"]))
    return registros


def ativos(request):
    erro = verificar(request, ("inventario.view_ativo",))
    if erro:
        return erro
    ordem = request.GET.get("ordenar", "id")
    if ordem not in ("id", "nome", "-risco"):
        return problema(422, "Parâmetro inválido", "Ordene por id, nome ou -risco.")
    qs = Ativo.objects.all()
    termo = request.GET.get("busca", "").strip()
    if len(termo) > 100:
        return problema(422, "Parâmetro inválido", "A busca aceita até 100 caracteres.")
    if termo:
        qs = qs.filter(Q(nome__icontains=termo) | Q(hostname__icontains=termo) | Q(id__icontains=termo))
    campos = ("id", "nome", "hostname", "tipo", "criticidade", "status")
    if ordem == "-risco":
        permissoes = ("inventario.view_vulnerabilidade", "inventario.view_incidencia",
                      "inventario.view_dependencia")
        if not request.user.has_perms(permissoes):
            return problema(403, "Acesso negado", "A ordenação por risco exige acesso ao modelo de risco.")
        registros = ativos_por_risco(qs, campos)
    else:
        registros = qs.order_by(ordem, "id").values(*campos) if ordem != "id" else qs.order_by("id").values(*campos)
    return paginar(request, registros)


def ativos_afetados(request, pk):
    erro = verificar(request, ("inventario.view_ativo", "inventario.view_vulnerabilidade",
                               "inventario.view_incidencia"))
    if erro:
        return erro
    if not Vulnerabilidade.objects.filter(pk=pk).exists():
        return problema(404, "Não encontrado", "Vulnerabilidade não encontrada.")
    registros = Incidencia.objects.filter(vulnerabilidade_id=pk).order_by("ativo_id", "id").values(
        "id", "status", "ativo_id", "ativo__nome", "ativo__hostname")
    return paginar(request, registros)


def especificacao(request):
    erro = verificar(request, ())
    if erro:
        return erro
    import json
    from django.conf import settings

    caminho = settings.BASE_DIR / "docs" / "openapi-v1.json"
    with caminho.open(encoding="utf-8") as arquivo:
        return JsonResponse(json.load(arquivo))


def documentacao(request):
    erro = verificar(request, ("inventario.view_ativo",))
    if erro:
        return erro
    from django.shortcuts import render

    return render(request, "inventario/api_v1.html")
