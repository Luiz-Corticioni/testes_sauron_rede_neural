"""Consulta local durante a digitação; rede somente em ação explícita com CSRF."""

import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from inventario.aplicacao.catalogo_cves import autocomplete_cves, consultar_internet
from inventario.infraestrutura.cve_client import CVENaoEncontrada, IntegracaoCVEError

LOGGER = logging.getLogger(__name__)


@require_GET
def api_sugestoes_cves(request):
    try:
        return JsonResponse(autocomplete_cves(request.GET.get('q', '')))
    except ValueError as erro:
        return JsonResponse({'erro': str(erro)}, status=400)


@require_POST
def api_consultar_cves(request):
    try:
        if len(request.body) > 4096:
            raise ValueError('Consulta grande demais.')
        dados = json.loads(request.body)
        if not isinstance(dados, dict) or type(dados.get('forcar', False)) is not bool:
            raise ValueError('Envie um objeto JSON com termo e forcar booleano.')
        return JsonResponse(consultar_internet(dados.get('termo', ''), dados.get('forcar', False)))
    except (ValueError, UnicodeError) as erro:
        return JsonResponse({'erro': str(erro)}, status=400)
    except CVENaoEncontrada as erro:
        return JsonResponse({'erro': str(erro)}, status=404)
    except IntegracaoCVEError as erro:
        return JsonResponse({'erro': str(erro)}, status=503)
    except OSError:
        LOGGER.exception('Não foi possível gravar o cache NVD.')
        return JsonResponse({'erro': 'Consulta indisponível: verifique as permissões do diretório de dados.'}, status=503)
