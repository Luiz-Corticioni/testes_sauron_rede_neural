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
from django.views.decorators.http import require_POST, require_http_methods
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


@require_POST
def api_montecarlo_v2(request):
    import json
    from django.core.exceptions import PermissionDenied
    from inventario.aplicacao.montecarlo_v2 import calcular
    from inventario.infraestrutura.limite_simulacoes import LimiteSimulacoes
    try:
        if request.content_type != "application/json" or len(request.body) > 256_000:
            raise ValueError("Envie JSON de até 256 KB.")
        dados = json.loads(request.body)
        resposta = JsonResponse(calcular(request.user, dados), json_dumps_params={"allow_nan": False})
        resposta["Cache-Control"] = "no-store"
        return resposta
    except LimiteSimulacoes as erro:
        resposta = JsonResponse({"erro": str(erro)}, status=429)
        resposta["Retry-After"] = "3"
        return resposta
    except PermissionDenied:
        return JsonResponse({"erro": "Acesso não autorizado."}, status=403)
    except (ValueError, TypeError, UnicodeDecodeError, RecursionError):
        return JsonResponse({"erro": "Cenário inválido. Confira os parâmetros, faixas e identificadores."}, status=400)


@require_http_methods(["GET", "POST"])
def montecarlo_v2(request):
    from inventario.aplicacao.montecarlo_v2 import calcular
    from inventario.aplicacao.perdas_financeiras import LEITURA as LEITURA_PERDAS
    from inventario.infraestrutura.limite_simulacoes import LimiteSimulacoes
    from inventario.matematica.montecarlo_v2 import FATORES
    from inventario.models import Ativo, PerimetroRelacoes
    from inventario.web.forms_montecarlo_v2 import CenarioV2Form

    form = CenarioV2Form(request.POST or None,
        perimetros=PerimetroRelacoes.objects.order_by("nome")[:100],
        ativos=Ativo.objects.exclude(status__in=["BAIXADO", "INATIVO"]).order_by("nome", "pk")[:1000],
        incidencias=incidencias_elegiveis().order_by("pk")[:1000],
        pode_calibrar=request.user.has_perms(LEITURA_PERDAS))
    resultado, status = None, 200
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        fatores = {nome: {"faixa": [d[f"{nome}_{x}"] for x in ("min", "moda", "max")],
                           "origem": d[f"{nome}_origem"]} for nome in FATORES}
        dados = {"escopo": d["escopo"], "origem_ativo": d["origem_ativo"], "incidencias": d["incidencias"],
                 "fatores": {i: fatores for i in d["incidencias"]}, "n": d["n"], "seed": d["seed"],
                 "correlacao": d["correlacao"], "custos": {"C": d["custo_c"], "I": d["custo_i"], "A": d["custo_a"]},
                 "sensibilidade": d["sensibilidade"], "calibrar": d.get("calibrar", False)}
        if d["limite"] is not None:
            dados["apetite"] = {"limite": d["limite"], "probabilidade_tolerada": d["tolerada"]}
        if d["comparar"]:
            dados["intervencoes"] = [{"nome": "Correção selecionada", "incidencias": d["incidencias"], "custo": d["custo_intervencao"]}]
        try:
            resultado = calcular(request.user, dados)
        except LimiteSimulacoes:
            form.add_error(None, "Simulações ocupadas. Tente novamente em alguns segundos.")
            status = 429
        except (ValueError, TypeError) as erro:
            form.add_error(None, str(erro))
    resposta = render(request, "inventario/montecarlo_v2.html", {"form": form, "resultado": resultado}, status=status)
    resposta["Cache-Control"] = "no-store"
    return resposta


@require_GET
def montecarlo(request):
    grupos = {}
    for i in incidencias_elegiveis():
        codigo = i.vulnerabilidade.cve_id or i.vulnerabilidade_id
        grupo = grupos.setdefault(codigo, {"cve": codigo, "incidencias": [], "ativos": 0})
        grupo["incidencias"].append(i.id)
        grupo["ativos"] += 1
    return render(request, "inventario/montecarlo.html", {"cves": sorted(grupos.values(), key=lambda g: g["cve"])})
