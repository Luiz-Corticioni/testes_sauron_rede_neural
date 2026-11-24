from __future__ import annotations

import logging
import time

from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from inventario.matematica.euler import Derivador, FuncaoMatematica, Integrador
from inventario.models import (
    Ativo,
    RegistroAuditoria,
)
from inventario.aplicacao.servicos import analisar_historico_risco


INICIO_PROCESSO = time.monotonic()
LOGGER = logging.getLogger(__name__)


def dashboard(request: HttpRequest):
    from inventario.aplicacao.painel import contexto_painel
    try:
        contexto = contexto_painel(request.GET.get("perfil", "puro"),
            ver_alertas=request.user.has_perm("inventario.view_alerta"),
            ver_certificados=request.user.has_perm("inventario.view_certificadodigital"))
        from inventario.aplicacao.recorte_painel import recorte_painel
        contexto = dict(contexto)  # Não modificar o resumo compartilhado em cache.
        contexto['recorte'] = recorte_painel(request.GET, contexto['risco'])
        if contexto['recorte']['ativo']:
            contexto['risco_json'] = contexto['recorte']['grafico']
        from inventario.aplicacao.qualidade_dados import qualidade_recorte_risco
        ativos_qualidade = contexto['recorte']['_ativos'].values('pk') if contexto['recorte']['ativo'] else None
        contexto['qualidade_recorte'] = qualidade_recorte_risco(request.user, ativos_qualidade)
    except ValueError as erro:
        return HttpResponseBadRequest(str(erro), content_type='text/plain; charset=utf-8')
    from inventario.models import Vulnerabilidade
    from inventario.aplicacao.demo_empresa import FONTE
    from inventario.aplicacao.demo_realista import FONTE as FONTE_REALISTA
    contexto['empresa_ficticia'] = Vulnerabilidade.objects.filter(fonte__in=[FONTE, FONTE_REALISTA]).exists()
    contexto['demo_realista'] = Vulnerabilidade.objects.filter(fonte=FONTE_REALISTA).exists()
    from inventario.aplicacao.mudancas_risco import PERMISSOES as PERMISSOES_MUDANCAS, mudancas
    if request.user.has_perms(PERMISSOES_MUDANCAS) and not contexto['recorte']['ativo'] and contexto['perfil'] == 'puro':
        contexto['mudancas_risco'] = mudancas()
    if request.user.has_perm('inventario.view_snapshotrisco') and not contexto['recorte']['ativo']:
        from inventario.models import SnapshotRisco
        amostras = list(SnapshotRisco.objects.filter(perfil=contexto['perfil'])
                        .order_by('-ts', '-pk').values('ts', 'risco_total', 'chave')[:30])
        contexto['amostras_risco'] = list(reversed(amostras))
    if request.user.has_perm('inventario.view_registroauditoria'):
        from django.core import signing
        ultimo = RegistroAuditoria.objects.order_by('-pk').values_list('pk', flat=True).first() or 0
        contexto['cursor_olho'] = signing.dumps(ultimo, salt='sauron.olho.eventos')
        # Resumo sem detalhes, limitado aos eventos de inventário permitidos ao painel.
        registros_painel = RegistroAuditoria.objects.filter(
            entidade__in=['Ativo', 'Vulnerabilidade', 'Incidencia'],
            acao__in=['CRIAR', 'ALTERAR'],
        )
        if contexto['recorte']['ativo']:
            from django.db.models import Q
            from inventario.models import Incidencia
            ativos = contexto['recorte']['_ativos']
            incidencias = Incidencia.objects.filter(ativo__in=ativos.values('pk'))
            registros_painel = registros_painel.filter(
                Q(entidade='Ativo', entidade_id__in=ativos.values('pk')) |
                Q(entidade='Incidencia', entidade_id__in=incidencias.values('pk')) |
                Q(entidade='Vulnerabilidade', entidade_id__in=incidencias.values('vulnerabilidade_id')))
        contexto['eventos_painel'] = list(registros_painel.values('acao', 'entidade', 'entidade_id', 'ocorrido_em').order_by('-ocorrido_em', '-pk')[:30])
        from inventario.models import HistoricoIncidencia
        transicoes = HistoricoIncidencia.objects.filter(para__in=['MITIGADA', 'CORRIGIDA'])
        if contexto['recorte']['ativo']:
            transicoes = transicoes.filter(incidencia__ativo__in=contexto['recorte']['_ativos'].values('pk'))
        contexto['mitigacoes_painel'] = list(transicoes.order_by('-em', '-pk').values('em', 'para', 'incidencia_codigo')[:10])
    return render(request, "inventario/dashboard.html", contexto)


@require_http_methods(['GET'])
def eventos_olho(request):
    from django.core import signing
    from django.http import JsonResponse
    from django.urls import reverse
    from inventario.models import Incidencia
    try:
        cursor = signing.loads(request.GET.get('cursor', ''), salt='sauron.olho.eventos', max_age=86400)
        if type(cursor) is not int or cursor < 0:
            raise ValueError
    except (signing.BadSignature, ValueError):
        return HttpResponseBadRequest('Cursor inválido ou expirado.')
    registros = list(RegistroAuditoria.objects.filter(pk__gt=cursor).order_by('pk')
                     .values('pk', 'acao', 'entidade', 'entidade_id')[:200])
    ids = [r['entidade_id'] for r in registros if r['acao'] == 'CRIAR' and r['entidade'] == 'Incidencia']
    incidencias = Incidencia.objects.filter(pk__in=ids, status__in=['ABERTA', 'TRATAMENTO'],
        vulnerabilidade__cvss__gte=9).select_related('ativo', 'vulnerabilidade').order_by('pk')
    itens = [{'ativo': i.ativo.hostname, 'cve': i.vulnerabilidade.cve_id or i.vulnerabilidade_id,
              'url': reverse('detalhe_ativo', args=[i.ativo_id])} for i in incidencias]
    resposta = JsonResponse({'eventos': itens, 'cursor': signing.dumps(registros[-1]['pk'] if registros else cursor,
                                                                      salt='sauron.olho.eventos')})
    resposta['Cache-Control'] = 'no-store'
    return resposta


@require_http_methods(['POST'])
def carregar_empresa_ficticia(request):
    from io import StringIO
    from django.contrib import messages
    from django.core.exceptions import PermissionDenied
    from django.core.management import call_command
    from django.shortcuts import redirect

    if not request.user.is_superuser:
        raise PermissionDenied
    saida = StringIO()
    cenario = request.POST.get('cenario', 'ficticio')
    if cenario not in ('ficticio', 'realista'):
        return HttpResponseBadRequest('Cenário desconhecido.')
    call_command('seed_demo', empresa=cenario == 'ficticio', empresa_realista=cenario == 'realista', stdout=saida)
    if 'Seed ignorado' in saida.getvalue():
        messages.warning(request, 'A empresa fictícia só pode ser carregada em um inventário vazio. Use uma base de demonstração separada.')
    else:
        messages.success(request, 'Empresa Aurora fictícia carregada. Todos os valores são demonstrativos.')
    return redirect('dashboard')


@require_http_methods(["GET", "POST"])
def modo_euler(request):
    resultado = erro = None
    dados = request.POST if request.method == "POST" else request.GET
    if dados.get("expressao"):
        try:
            funcao = FuncaoMatematica(dados["expressao"])
            operacao = dados.get("operacao", "derivada")
            if operacao not in {'derivada', 'segunda', 'integral'}:
                raise ValueError('Escolha derivada, segunda ou integral.')
            if operacao == "derivada":
                x = float(dados.get("x", 0))
                resultado = {
                    "operacao": "Derivada central",
                    "valor": Derivador.central(funcao.avaliar, x),
                    "em": x,
                }
            elif operacao == "segunda":
                x = float(dados.get("x", 0))
                resultado = {
                    "operacao": "Derivada segunda",
                    "valor": Derivador.segunda(funcao.avaliar, x),
                    "em": x,
                }
            else:
                a, b = float(dados.get("a", 0)), float(dados.get("b", 1))
                n = int(dados.get("n", 100))
                resultado = {
                    "operacao": "Integral de Simpson",
                    "valor": Integrador.simpson(funcao.avaliar, a, b, n),
                    "intervalo": [a, b],
                }
            resultado["tipo_funcao"] = funcao.identificar_tipo()
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as exc:
            erro = str(exc)
    try:
        historico = analisar_historico_risco(dados.get("inicio") or None, dados.get("fim") or None)
    except ValueError as exc:
        historico = {"disponivel": False, "mensagem": str(exc)}
    return render(
        request,
        "inventario/euler.html",
        {
            "resultado": resultado,
            "erro": erro,
            "dados": dados,
            "historico": historico,
        },
    )


def menu_cves(request):
    contexto = {}
    if request.GET.get("ativo"):
        from inventario.aplicacao.operacao import exigir

        exigir(request.user, "inventario.view_ativo")
        contexto["ativo_contexto"] = get_object_or_404(Ativo, pk=request.GET["ativo"])
    return render(request, "inventario/cves.html", contexto)


def auditoria(request):
    return render(
        request,
        "inventario/auditoria.html",
        {
            "registros": RegistroAuditoria.objects.select_related("usuario")[:100],
        },
    )


from inventario.web.views_operacionais import (
    alertas,
    alterar_status_incidencia,
    importar_ativos,
    reconhecer_alerta_web,
    software,
    status_incidencia_web,
)
