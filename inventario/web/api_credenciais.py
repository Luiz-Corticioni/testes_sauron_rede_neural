"""Gerenciamento de credenciais por sessão humana com MFA e reautenticação."""
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse

from inventario.aplicacao.credenciais_api import CredencialInvalida, criar, listar, revogar, rotacionar
from inventario.web.api_v1 import problema


def _entrada(request):
    if len(request.body) > 4096:
        raise ValidationError("Corpo da requisição excede o limite.")
    try:
        dados = json.loads(request.body)
    except (ValueError, UnicodeDecodeError) as erro:
        raise ValidationError("Envie um objeto JSON válido.") from erro
    if not isinstance(dados, dict):
        raise ValidationError("Envie um objeto JSON.")
    return dados


def _resposta(credencial, segredo):
    resposta = JsonResponse({"id": str(credencial.pk), "escopos": credencial.escopos,
        "expira_em": credencial.expira_em.isoformat(), "segredo": segredo}, status=201)
    resposta["Cache-Control"] = "no-store"
    return resposta


def gerenciar(request, identificador=None, acao=None):
    if request.method == "GET" and identificador is None:
        try:
            resposta = JsonResponse(listar(request.user, request.GET.get("pagina", "1")))
        except PermissionDenied:
            return problema(403, "Acesso negado", "Somente administradores autorizados podem gerenciar credenciais.")
        except ValidationError as erro:
            return problema(422, "Parâmetro inválido", "; ".join(erro.messages))
        except CredencialInvalida:
            return problema(404, "Não encontrado", "Página não encontrada.")
        resposta["Cache-Control"] = "no-store"
        return resposta
    if request.method != "POST":
        resposta = problema(405, "Método não permitido", "Use GET ou POST." if identificador is None else "Use POST nesta rota.")
        resposta["Allow"] = "GET, POST" if identificador is None else "POST"
        return resposta
    try:
        dados = _entrada(request)
        if identificador is None and set(dados) == {"escopos", "dias"}:
            return _resposta(*criar(request.user, dados["escopos"], dados["dias"]))
        if acao == "rotacionar" and set(dados) == {"dias"}:
            return _resposta(*rotacionar(request.user, identificador, dados["dias"]))
        if acao == "revogar" and not dados:
            revogar(request.user, identificador)
            resposta = JsonResponse({"revogada": True})
            resposta["Cache-Control"] = "no-store"
            return resposta
        raise ValidationError("Parâmetros inesperados ou ausentes.")
    except ValidationError as erro:
        return problema(422, "Parâmetro inválido", "; ".join(erro.messages))
    except PermissionDenied:
        return problema(403, "Acesso negado", "Somente administradores autorizados podem gerenciar credenciais.")
    except CredencialInvalida:
        return problema(404, "Não encontrado", "Credencial não encontrada ou indisponível.")
