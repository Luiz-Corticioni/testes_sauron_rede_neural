"""Resumo de até 15s, separado por permissões; gravações invalidam após commit."""
from datetime import timedelta
from uuid import uuid4
from django.core.cache import cache
from django.db import connection
from django.db.models import Count
from django.utils import timezone
from inventario.aplicacao.cache_consultas import lembrar
from inventario.aplicacao.risco import calcular_risco_banco, namespace_risco, parametros_risco
from inventario.models import Ativo, Vulnerabilidade, Incidencia, Sala, Alerta, CertificadoDigital

VALIDADE = 15


def invalidar_cache_painel():
    cache.set(f'painel:geracao:{namespace_risco()}', uuid4().hex, timeout=None)


def contexto_painel(perfil='puro', ver_alertas=False, ver_certificados=False):
    parametros_risco(perfil)  # Não reutiliza um resultado para parâmetros inválidos.
    hoje = timezone.localdate()
    def construir():
        risco, erro = None, None
        if Ativo.objects.exists():
            try:
                risco = calcular_risco_banco(perfil=perfil)
            except ValueError as exc:
                erro = str(exc)
        return {
            'total_ativos': Ativo.objects.count(), 'total_vulnerabilidades': Vulnerabilidade.objects.count(),
            'incidencias_abertas': Incidencia.objects.pendentes_sla().count(), 'salas': Sala.objects.count(),
            'alertas_pendentes': Alerta.objects.filter(reconhecido_em__isnull=True).count() if ver_alertas else None,
            'alertas_recentes': list(Alerta.objects.filter(reconhecido_em__isnull=True).order_by('-criado_em').values('tipo', 'severidade', 'mensagem', 'criado_em')[:5]) if ver_alertas else [],
            'top_vulnerabilidades': list(Vulnerabilidade.objects.annotate(total_ativos=Count('ativos')).order_by('-total_ativos', '-cvss').values('id', 'cve_id', 'total_ativos')[:8]),
            'eol_proximos': list(Ativo.objects.filter(fim_suporte__isnull=False, fim_suporte__lte=hoje+timedelta(days=90)).order_by('fim_suporte').values('hostname', 'fim_suporte')[:8]),
            'certificados_proximos': list(CertificadoDigital.objects.filter(expira_em__lte=hoje+timedelta(days=45)).order_by('expira_em').values('dominio', 'expira_em')[:8]) if ver_certificados else [],
            'risco': risco, 'risco_json': risco or {}, 'erro_risco': erro, 'perfil': perfil,
            'indicadores': list(zip(risco['ids_ativos'], risco['indices'], risco['risco_relatorio'])) if risco else [],
            'indice_medio': sum(risco['indices'])/len(risco['indices']) if risco and risco['indices'] else 0,
            'painel_gerado_em': timezone.now(), 'painel_validade': VALIDADE,
        }
    # Não publica dados ainda não confirmados ou reutiliza um resumo anterior à edição.
    if any(getattr(cb, '_sauron_invalidacao', False) for _, cb, _ in connection.run_on_commit):
        return construir()
    chave_geracao = f'painel:geracao:{namespace_risco()}'
    geracao = lembrar(chave_geracao, lambda: uuid4().hex, segundos=None)
    chave = f'painel:v1:{namespace_risco()}:{geracao}:{hoje}:{perfil}:{int(ver_alertas)}:{int(ver_certificados)}'
    return lembrar(chave, construir, segundos=VALIDADE)
