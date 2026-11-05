"""APIs de consulta: não recebem matrizes arbitrárias nem alteram cadastros."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from inventario.aplicacao.analise_linear import explicar_modelo
from inventario.aplicacao.impacto import analisar_impacto
from inventario.models import Ativo


@require_GET
def api_impacto(request):
    try:
        return JsonResponse(analisar_impacto(
            request.GET.get("ativo", ""), request.user, int(request.GET.get("limite", "50"))
        ))
    except Ativo.DoesNotExist:
        return JsonResponse({"erro": "Ativo não encontrado."}, status=404)
    except ValueError as erro:
        return JsonResponse({"erro": str(erro)}, status=400)


@require_GET
def api_diagnostico(request):
    try:
        return JsonResponse(explicar_modelo(
            request.user, request.GET.get("ativo") or None, request.GET.get("perfil", "puro")
        ))
    except Ativo.DoesNotExist:
        return JsonResponse({"erro": "Ativo não encontrado."}, status=404)
    except ValueError as erro:
        return JsonResponse({"erro": str(erro)}, status=422)


from django.shortcuts import render
from django.views.decorators.http import require_POST
from inventario.aplicacao.montecarlo import calcular_montecarlo, incidencias_elegiveis


@require_POST
def atualizar_epss(request):
    from django.contrib import messages
    from django.shortcuts import redirect
    from inventario.aplicacao.epss import sincronizar_epss
    r = sincronizar_epss(usuario=request.user, limite=50)
    messages.info(request, f"EPSS: {r['atualizadas']} cadastro(s) atualizado(s). "+" ".join(r["avisos"]))
    return redirect("montecarlo")


@require_POST
def api_montecarlo(request):
    import json
    from inventario.infraestrutura.limite_simulacoes import LimiteSimulacoes
    try:
        if request.content_type != "application/json":
            raise ValueError("Envie o corpo como application/json.")
        if len(request.body) > 256_000:
            raise ValueError("JSON excede 256 KB.")
        try:
            dados = json.loads(request.body)
        except (ValueError, UnicodeDecodeError) as erro:
            raise ValueError("JSON inválido; envie um objeto com parâmetros da simulação.") from erro
        if not isinstance(dados, dict):
            raise ValueError("Envie um objeto JSON.")
        return JsonResponse(calcular_montecarlo(dados), json_dumps_params={"allow_nan": False})
    except LimiteSimulacoes as erro:
        resposta = JsonResponse({"erro": str(erro)}, status=429)
        resposta["Retry-After"] = "3"
        return resposta
    except (ValueError, TypeError, UnicodeDecodeError) as erro:
        return JsonResponse({"erro": str(erro)}, status=400)


@require_GET
def montecarlo(request):
    grupos = {}
    for i in incidencias_elegiveis():
        codigo = i.vulnerabilidade.cve_id or i.vulnerabilidade_id
        grupo = grupos.setdefault(codigo, {"cve": codigo, "incidencias": [], "ativos": 0})
        grupo["incidencias"].append(i.id)
        grupo["ativos"] += 1
    return render(request, "inventario/montecarlo.html", {"cves": sorted(grupos.values(), key=lambda g: g["cve"])})
