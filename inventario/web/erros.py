"""Erros HTML/JSON sem dependência de CSS, JS, banco ou manifesto de estáticos."""

import logging
import uuid
from django.db import OperationalError
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

LOGGER = logging.getLogger(__name__)


class FiltroLogRequisicao(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(getattr(record, 'request', None), 'sauron_request_id', '-')
        return True


def resposta_erro(request, status, mensagem):
    id_ = getattr(request, 'sauron_request_id', '')
    dados = {'erro': mensagem, 'request_id': id_, 'status': status}
    if request.path.startswith('/api/'):
        return JsonResponse(dados, status=status)
    return render(request, 'inventario/erro.html', dados, status=status)


class IdentificadorRequisicaoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.sauron_request_id = uuid.uuid4().hex[:16]
        resposta = self.get_response(request)
        resposta['X-Request-ID'] = request.sauron_request_id
        return resposta


class FalhasOperacionaisMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, OperationalError):
            LOGGER.error('Banco indisponível · requisição %s', request.sauron_request_id, exc_info=True)
            return resposta_erro(request, 503, 'Banco temporariamente indisponível. Consulte o diagnóstico e tente novamente.')
        if isinstance(exception, ValueError) and 'Missing staticfiles manifest entry' in str(exception):
            LOGGER.error('Estáticos não preparados · requisição %s', request.sauron_request_id, exc_info=True)
            return resposta_erro(request, 503, 'Arquivos da interface não preparados. Execute python manage.py preparar_servidor.')
        if isinstance(exception, OSError):
            LOGGER.error('Falha de armazenamento · requisição %s', request.sauron_request_id, exc_info=True)
            return resposta_erro(request, 503, 'Falha de armazenamento. Confira o diagnóstico e se a alteração foi concluída antes de repetir.')


def erro_400(request, exception):
    return resposta_erro(request, 400, 'Requisição inválida.')


def erro_403(request, exception):
    return resposta_erro(request, 403, 'Você não tem permissão para esta operação.')


def erro_404(request, exception):
    return resposta_erro(request, 404, 'Página ou registro não encontrado.')


def erro_500(request):
    return resposta_erro(request, 500, 'Não foi possível concluir a operação. Informe o código da requisição ao administrador.')


def erro_csrf(request, reason=''):
    return resposta_erro(request, 403, 'A sessão ou o token de segurança expirou. Recarregue a página e entre novamente.')
