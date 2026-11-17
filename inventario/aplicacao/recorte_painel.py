"""Recorte explícito do painel; não altera os cálculos nem o inventário."""
from django.db.models import Exists, OuterRef, Q

from inventario.models import Ativo, Incidencia, Vulnerabilidade
from inventario.models.ativos import TIPOS


def recorte_painel(parametros, risco):
    filtros = {chave: parametros.get(chave, '').strip() for chave in
               ('tipo', 'severidade', 'responsavel', 'ambiente', 'pendencias')}
    if any(len(valor) > 120 for valor in filtros.values()):
        raise ValueError('Filtro muito longo.')
    faixas = {
        'critica': Q(vulnerabilidade__cvss__gte=9),
        'alta': Q(vulnerabilidade__cvss__gte=7, vulnerabilidade__cvss__lt=9),
        'media': Q(vulnerabilidade__cvss__gte=4, vulnerabilidade__cvss__lt=7),
        'baixa': Q(vulnerabilidade__cvss__gt=0, vulnerabilidade__cvss__lt=4),
        'nenhuma': Q(vulnerabilidade__cvss=0),
    }
    if filtros['tipo'] and filtros['tipo'] not in dict(TIPOS):
        raise ValueError('Tipo de ativo inválido.')
    if filtros['severidade'] and filtros['severidade'] not in faixas:
        raise ValueError('Severidade inválida.')
    if filtros['pendencias'] not in ('', '1'):
        raise ValueError('Filtro de pendências inválido.')
    opcoes = {
        'filtros': filtros, 'ativo': any(filtros.values()), 'tipos': TIPOS,
        'responsaveis': list(Ativo.objects.exclude(responsavel='').order_by('responsavel').values_list('responsavel', flat=True).distinct()[:200]),
        'ambientes': list(Ativo.objects.exclude(zona_rede='').order_by('zona_rede').values_list('zona_rede', flat=True).distinct()[:200]),
    }
    if not opcoes['ativo']:
        return opcoes
    ativos = Ativo.objects.all()
    for chave, campo in [('tipo', 'tipo'), ('responsavel', 'responsavel'), ('ambiente', 'zona_rede')]:
        if filtros[chave]:
            ativos = ativos.filter(**{campo: filtros[chave]})
    pendentes = Incidencia.objects.pendentes_sla().filter(ativo_id=OuterRef('pk'))
    if filtros['pendencias']:
        ativos = ativos.filter(Exists(pendentes))
    if filtros['severidade']:
        consideradas = Incidencia.objects.filter(ativo_id=OuterRef('pk'), status__in=['ABERTA', 'TRATAMENTO', 'ACEITA'])
        ativos = ativos.filter(Exists(consideradas.filter(faixas[filtros['severidade']])))
    ids = list(ativos.values_list('pk', flat=True))
    incidencias = Incidencia.objects.filter(ativo_id__in=ativos.values('pk'))
    vulnerabilidades = Vulnerabilidade.objects.filter(pk__in=incidencias.values('vulnerabilidade_id'))
    ids_selecionados = set(ids)
    posicoes = [i for i, identificador in enumerate((risco or {}).get('ids_ativos', [])) if identificador in ids_selecionados]
    grafico = {chave: [risco[chave][i] for i in posicoes] for chave in
               ('ids_ativos', 'risco_proprio', 'risco_efetivo')} if risco else {}
    nomes = dict(ativos.values_list('pk', 'hostname'))
    prioridades = sorted(({'id': identificador, 'nome': nomes[identificador], 'risco': valor}
                           for identificador, valor in zip(grafico.get('ids_ativos', []), grafico.get('risco_efetivo', []))),
                          key=lambda item: (-item['risco'], item['id']))[:6]
    matriz = []
    if any(filtros.values()):
        ativos_visiveis = list(ativos.order_by('pk').values('pk', 'hostname')[:20])
        acumulado = {a['pk']: [0, 0, 0, 0, 0] for a in ativos_visiveis}
        for incidencia in incidencias.filter(ativo_id__in=acumulado, status__in=['ABERTA', 'TRATAMENTO', 'ACEITA']).values('ativo_id', 'vulnerabilidade__cvss'):
            cvss = incidencia['vulnerabilidade__cvss']
            coluna = 0 if cvss >= 9 else 1 if cvss >= 7 else 2 if cvss >= 4 else 3 if cvss > 0 else 4
            acumulado[incidencia['ativo_id']][coluna] += 1
        matriz = [{'id': a['pk'], 'nome': a['hostname'], 'valores': acumulado[a['pk']]} for a in ativos_visiveis]
    return {
        **opcoes,
        'total_ativos': len(ids), 'total_vulnerabilidades': vulnerabilidades.count(),
        'pendencias': incidencias.pendentes_sla().count(),
        'ativos_com_pendencias': incidencias.pendentes_sla().values('ativo_id').distinct().count(),
        'grafico': grafico, 'matriz': matriz, 'prioridades': prioridades, '_ativos': ativos,
    }
