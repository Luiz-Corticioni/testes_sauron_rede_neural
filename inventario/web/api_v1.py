"""Consultas versionadas do inventário, com autorização por sessão e MFA."""

from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from heapq import nlargest, nsmallest
from inventario.models import Ativo, Incidencia, Vulnerabilidade


def problema(status, titulo, detalhe):
    resposta = JsonResponse({"type": "about:blank", "title": titulo, "status": status,
                             "detail": detalhe}, status=status,
                            content_type="application/problem+json")
    resposta["Cache-Control"] = "no-store"
    return resposta


def verificar(request, permissoes, escopo=None):
    if request.method != "GET":
        resposta = problema(405, "Método não permitido", "Use GET nesta rota.")
        resposta["Allow"] = "GET"
        return resposta
    autorizacao = request.headers.get("Authorization", "")
    if escopo and autorizacao.startswith("Bearer "):
        from django.core.exceptions import PermissionDenied
        from inventario.aplicacao.credenciais_api import autenticar, limitar_origem, CredencialInvalida, LimiteCredencial
        from inventario.seguranca import ip_cliente
        try:
            if not limitar_origem(ip_cliente(request)):
                raise LimiteCredencial
            request.user = autenticar(autorizacao[7:], escopo)
        except CredencialInvalida:
            from inventario.infraestrutura.auditoria import registrar_evento
            registrar_evento("CREDENCIAL_API_NEGADA", "HTTP", request.path, {"motivo": "invalida"})
            return problema(401, "Credencial inválida", "A credencial é inválida, expirou ou foi revogada.")
        except PermissionDenied:
            return problema(403, "Acesso negado", "A credencial não permite esta consulta.")
        except LimiteCredencial:
            resposta = problema(429, "Limite excedido", "Aguarde antes de repetir a consulta.")
            resposta["Retry-After"] = "60"
            return resposta
    if not request.user.is_authenticated:
        return problema(401, "Autenticação necessária", "Entre e conclua o segundo fator.")
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


def ativos_por_risco(qs, campos, inicio, fim, total):
    """Seleciona IDs incrementalmente e carrega os campos apenas da página."""
    from inventario.aplicacao.risco import calcular_risco_banco

    resultado = calcular_risco_banco(perfil="puro")
    riscos = dict(zip(resultado["ids_ativos"], resultado["risco_efetivo"], strict=True))
    chave = lambda pk: (-riscos[pk], pk)
    candidatos = qs.order_by().values_list("id", flat=True).iterator()
    if fim <= total - inicio:
        ids = nsmallest(fim, candidatos, key=chave)[inicio:fim]
    else:
        ids = sorted(nlargest(total - inicio, candidatos, key=chave), key=chave)[:fim - inicio]
    registros = {item["id"]: item for item in qs.filter(id__in=ids).values(*campos)}
    return [{**registros[pk], "risco_efetivo": riscos[pk]} for pk in ids]


def paginar_risco(request, qs, campos):
    try:
        pagina = int(request.GET.get("pagina", "1"))
        tamanho = int(request.GET.get("tamanho", "25"))
        if pagina < 1 or not 1 <= tamanho <= 100:
            raise ValueError
    except ValueError:
        return problema(422, "Parâmetro inválido", "Use página positiva e tamanho entre 1 e 100.")
    paginador = Paginator(qs.order_by("id"), tamanho)
    if pagina > paginador.num_pages:
        return problema(404, "Página não encontrada", "A página solicitada não existe.")
    inicio = (pagina - 1) * tamanho
    try:
        registros = ativos_por_risco(qs, campos, inicio, inicio + tamanho, paginador.count)
    except KeyError:
        return problema(503, "Risco indisponível", "O inventário mudou durante o cálculo. Tente novamente.")
    return JsonResponse({"pagina": pagina, "tamanho": tamanho, "total": paginador.count,
                         "paginas": paginador.num_pages, "resultados": registros})


def ativos(request):
    escopo = "risco" if request.GET.get("ordenar") == "-risco" else "ativos"
    erro = verificar(request, ("inventario.view_ativo",), escopo)
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
        return paginar_risco(request, qs, campos)
    else:
        registros = qs.order_by(ordem, "id").values(*campos) if ordem != "id" else qs.order_by("id").values(*campos)
    return paginar(request, registros)


def ativos_afetados(request, pk):
    erro = verificar(request, ("inventario.view_ativo", "inventario.view_vulnerabilidade",
                               "inventario.view_incidencia"), "incidencias")
    if erro:
        return erro
    if not Vulnerabilidade.objects.filter(pk=pk).exists():
        return problema(404, "Não encontrado", "Vulnerabilidade não encontrada.")
    registros = Incidencia.objects.filter(vulnerabilidade_id=pk).order_by("ativo_id", "id").values(
        "id", "status", "ativo_id", "ativo__nome", "ativo__hostname")
    return paginar(request, registros)


def qualidade(request, pk, entidade):
    from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
    from inventario.aplicacao.qualidade_dados import PERMISSOES, qualidade_ativo, qualidade_servico

    permissoes = PERMISSOES + (("inventario.view_serviconegocio",) if entidade == "servico" else ())
    erro = verificar(request, permissoes)
    if erro:
        return erro
    try:
        if entidade == "servico":
            resultado = qualidade_servico(request.user, pk)
        else:
            valor = request.GET.get("perimetro", "")
            perimetro = int(valor) if valor else None
            tipo = request.GET.get("tipo", "REDE")
            principal = request.GET.get("principal", "").strip()
            if (perimetro is not None and perimetro < 1) or tipo not in {"REDE", "NEGOCIO", "IDENTIDADE"} or len(principal) > 200:
                raise ValueError
            resultado = qualidade_ativo(request.user, pk, perimetro, tipo, principal)
        resposta = JsonResponse(resultado)
        resposta["Cache-Control"] = "no-store"
        return resposta
    except (ValueError, ValidationError):
        return problema(422, "Parâmetro inválido", "Confira o perímetro, a camada e o principal informados.")
    except ObjectDoesNotExist:
        return problema(404, "Não encontrado", "Ativo, serviço ou perímetro não encontrado.")
    except PermissionDenied:
        return problema(403, "Acesso negado", "A conta não possui as permissões necessárias.")


def qualidade_fontes(request):
    erro = verificar(request, ("inventario.view_vulnerabilidade",))
    if erro:
        return erro
    from inventario.aplicacao.documentos import LEITURA as LEITURA_DOCUMENTOS
    from inventario.aplicacao.estado_fontes import resumo_fontes

    resposta = JsonResponse(resumo_fontes(
        ver_isca=request.user.has_perms(("inventario.view_ativo", "inventario.view_sensorhoneypot", "inventario.view_eventohoneypot")),
        ver_importacoes=request.user.has_perms(LEITURA_DOCUMENTOS)))
    resposta["Cache-Control"] = "no-store"
    return resposta


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
