"""Construção dos perfis e aprendizagem; não consulta fontes externas."""

import hashlib
import json
import re
from django.conf import settings
from django.utils import timezone
from inventario.dominio.sistema_imune import Antigeno, separar_versao
from inventario.models import Anticorpo, Incidencia

CONFIRMADOS = ["ABERTA", "TRATAMENTO", "ACEITA"]


def antigenos(ativo, vulnerabilidade, software=None, somente_sistema=False):
    vetor = re.search(r"/AV:([NALP])", vulnerabilidade.cvss_vetor.upper())
    componentes = [software] if software else ([] if somente_sistema else list(ativo.softwares.all()))
    dados = [(s.nome, s.versao, s.cpe23) for s in componentes]
    if not dados:
        dados = [(ativo.sistema_operacional, ativo.versao, "")]
    resultado = []
    for familia, versao, cpe in dados:
        maior, menor = separar_versao(versao)
        resultado.append(
            Antigeno(
                vulnerabilidade.categoria,
                ativo.tipo,
                ativo.fabricante,
                familia,
                maior,
                menor,
                ativo.exposto_internet,
                vetor.group(1) if vetor else "",
                cpe,
            )
        )
    return resultado


def vinculo_deterministico(ativo, vulnerabilidade):
    from inventario.dominio.matching import avaliar_componente
    resultados = [avaliar_componente(s.cpe23, s.versao, vulnerabilidade.faixas_afetadas,
                                    vulnerabilidade.vex) for s in ativo.softwares.all() if s.cpe23]
    if True in resultados:
        return True
    return False if resultados and all(r is False for r in resultados) else None


def afinidade(memoria, ativo, vulnerabilidade):
    deterministico = vinculo_deterministico(ativo, vulnerabilidade)
    if deterministico is not None:
        return float(deterministico)
    return max(
        memoria.para_dominio().avaliar(a, memoria.ignorados)
        for a in antigenos(ativo, vulnerabilidade)
    )


def chave(dados):
    texto = json.dumps(dados, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texto.encode()).hexdigest()


def base_correspondente(memoria, saudaveis, vulnerabilidade):
    return next((a for a in saudaveis if afinidade(memoria, a, vulnerabilidade) >= settings.IMUNE_LIMIAR - 1e-9), None)


def cruza_linha_base(memoria, saudaveis, vulnerabilidade):
    return base_correspondente(memoria, saudaveis, vulnerabilidade) is not None


def reservar_vaga():
    from inventario.aplicacao.operacao import emitir_alerta
    ativos = Anticorpo.objects.filter(estado="ATIVO")
    if ativos.count() >= settings.IMUNE_MAX_POPULACAO:
        menor = min(ativos, key=lambda m: (
            m.para_dominio().decaimento(max(0, (timezone.now()-m.reforcado_em).total_seconds()/86400),
                                      settings.IMUNE_MEIA_VIDA_DIAS), m.pk))
        menor.estado = "ARQUIVADO"
        menor.save(update_fields=["estado"])
    if ativos.count() + 1 >= settings.IMUNE_MAX_POPULACAO * .8:
        emitir_alerta("IMUNE", None, "capacidade-imune",
                      "População imune atingiu 80% da capacidade; reveja o dimensionamento.", 3)


def aprender(saudaveis):
    total = 0
    casos = Incidencia.objects.filter(status__in=CONFIRMADOS, imune_aprendida=False).select_related(
        "ativo", "vulnerabilidade"
    )
    for i in casos[:settings.IMUNE_MAX_APRENDIZADOS_CICLO]:
        componente = i.software
        if componente is None:
            componentes = list(i.ativo.softwares.all())
            texto = (i.observacoes + " " + i.vulnerabilidade.descricao).casefold()
            candidatos = [s for s in componentes if s.nome.casefold() in texto
                          or (s.cpe23 and s.cpe23.casefold() in texto)]
            if len(candidatos) == 1:
                componente = candidatos[0]
            elif len(componentes) == 1:
                componente = componentes[0]
        perfil = antigenos(i.ativo, i.vulnerabilidade, componente, somente_sistema=True)[0].to_dict()
        codigo = chave([i.pk, perfil])
        existente = Anticorpo.objects.filter(chave=codigo).first()
        if existente:
            if existente.estado == "ARQUIVADO":
                reservar_vaga()
                existente.estado, existente.reforcado_em = "ATIVO", timezone.now()
                existente.save(update_fields=["estado", "reforcado_em"])
                total += 1
            i.imune_aprendida = True
            i.save(update_fields=["imune_aprendida"])
            continue
        reservar_vaga()
        memoria = Anticorpo(
            vulnerabilidade=i.vulnerabilidade,
            origem=i,
            prototipo=perfil,
            chave=codigo,
            linhagem=codigo,
        )
        if cruza_linha_base(memoria, saudaveis, i.vulnerabilidade):
            memoria.estado = "DESCARTADO"
            memoria.descartado_por_ativo = base_correspondente(memoria, saudaveis, i.vulnerabilidade)
        memoria.save()
        i.imune_aprendida = True
        i.save(update_fields=["imune_aprendida"])
        total += 1
    return total


def clonar(memoria, saudaveis):
    """Relaxa um eixo; só sobrevive se todos os casos confirmados ainda casarem."""
    if memoria.ignorados or Anticorpo.objects.filter(estado="ATIVO").count() >= settings.IMUNE_MAX_POPULACAO:
        return None
    campo = "versao_menor" if memoria.prototipo["versao_menor"] else "fabricante"
    codigo = chave([memoria.linhagem, campo])
    if Anticorpo.objects.filter(chave=codigo).exists():
        return None
    clone = Anticorpo(
        vulnerabilidade=memoria.vulnerabilidade,
        origem=memoria.origem,
        prototipo=memoria.prototipo,
        ignorados=[campo],
        forca=memoria.forca,
        chave=codigo,
        linhagem=memoria.linhagem,
        reforcado_em=timezone.now(),
    )
    casos = Incidencia.objects.filter(
        vulnerabilidade=memoria.vulnerabilidade, status__in=CONFIRMADOS
    ).select_related("ativo")
    if not casos.exists() or any(
        afinidade(clone, i.ativo, i.vulnerabilidade) < settings.IMUNE_LIMIAR - 1e-9 for i in casos
    ):
        return None
    if cruza_linha_base(clone, saudaveis, memoria.vulnerabilidade):
        return None
    clone.save()
    return clone
