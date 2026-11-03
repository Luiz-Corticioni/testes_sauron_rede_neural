from __future__ import annotations

from datetime import datetime
import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Count, Max
from django.utils import timezone

from inventario.aplicacao.cache_consultas import lembrar
from inventario.matematica.series import SerieRisco
from inventario.infraestrutura.cve_client import CisaKevClient, IntegracaoCVEError
from inventario.matematica.risco import ModeloRisco
from inventario.models import Ativo, Dependencia, Incidencia, SnapshotRisco, Vulnerabilidade


def caminho_cache_kev():
    return settings.DATA_DIR / "cache_kev.json"


def parametros_risco(perfil):
    if perfil not in {"puro", "operacional"}:
        raise ValueError("Escolha o perfil puro ou operacional.")
    return {"perfil": perfil, "kappa": settings.RISCO_KAPPA, "tau": settings.RISCO_TAU}


def namespace_risco():
    origem = f"{connection.settings_dict['NAME']}|{settings.DATA_DIR}"
    return hashlib.sha256(origem.encode()).hexdigest()[:20]


def versao_dados(perfil="puro"):
    # Inclui o formato do resultado: arquivos de cache antigos não contêm resíduos.
    versao = [("modelo", 4)]
    for modelo in (Ativo, Vulnerabilidade, Incidencia, Dependencia):
        estado = modelo.objects.aggregate(total=Count("pk"), ultima=Max("atualizado_em"))
        ultima = estado["ultima"].isoformat() if estado["ultima"] else ""
        versao.append((modelo.__name__, estado["total"], ultima))
    if perfil == "operacional":
        caminho = caminho_cache_kev()
        stat = caminho.stat() if caminho.exists() else None
        versao.append(("KEV", stat.st_mtime_ns if stat else 0, stat.st_size if stat else 0))
    versao.append(parametros_risco(perfil))
    versao.append(("exposicao_configurada",settings.RISCO_FATORES_EXPOSICAO,
                   settings.RISCO_MULTIPLICADOR_INTERNET,settings.RISCO_MULTIPLICADOR_ADMIN_REMOTA,
                   settings.RISCO_POLITICA))
    return hashlib.sha256(json.dumps(versao, sort_keys=True).encode()).hexdigest()


def invalidar_cache_risco():
    for perfil in ("puro", "operacional"):
        ponteiro = f"risco:ultimo:{namespace_risco()}:{perfil}"
        chave = cache.get(ponteiro)
        if chave:
            cache.delete(chave)
        cache.delete(ponteiro)


def peso_relatorio(ativo):
    # A migração traz os valores legados do JSON para campos validados e explícitos.
    if not isinstance(ativo.atributos, dict):
        raise ValueError("Atributos do ativo devem ser um objeto JSON.")
    valores = [ativo.criticidade]
    for campo in ("confidencialidade", "integridade", "disponibilidade"):
        valor = getattr(ativo, campo)
        if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= 4:
            raise ValueError(f"{campo} precisa ser inteiro entre 1 e 4.")
        valores.append(valor)
    return max(valores)


def carregar_modelo_risco(perfil="puro"):
    parametros_risco(perfil)
    # .only inclui todos os campos da conversão: nunca há SELECT por atributo adiado.
    ativos = list(
        Ativo.objects.only(
            *Ativo.CAMPOS_DOMINIO,
            *Ativo.CAMPOS_ESTADO,
            "tipo",
            "ip",
            "atributos",
            "fim_suporte",
        )
    )
    vuls = list(
        Vulnerabilidade.objects.only(
            *Vulnerabilidade.CAMPOS_DOMINIO,
            *Vulnerabilidade.DATAS_DOMINIO,
        )
    )
    vulnerabilidades = [v.para_dominio() for v in vuls]
    incidencias = [
        i.para_dominio()
        for i in Incidencia.objects.only(
            *Incidencia.CAMPOS_DOMINIO,
            *Incidencia.DATAS_DOMINIO,
            "ativo_id",
        )
    ]
    dependencias = [
        d.para_dominio()
        for d in Dependencia.objects.only(
            "dependente_id",
            "fornecedor_id",
            "peso",
            "descricao",
        )
    ]
    def fator_configurado(a):
        import math
        obj=a.para_dominio()
        fator=settings.RISCO_FATORES_EXPOSICAO.get(a.tipo,obj.FATOR_BASE)
        if a.tipo in ("5","7") and a.exposto_internet:
            fator*=settings.RISCO_MULTIPLICADOR_INTERNET
        if a.tipo=="5" and obj.administracao_remota():
            fator*=settings.RISCO_MULTIPLICADOR_ADMIN_REMOTA
        if not math.isfinite(fator) or fator<0:
            raise ValueError("Fator de exposição inválido.")
        return fator
    fatores = {a.id: fator_configurado(a) for a in ativos}
    kev_ids = {v.id for v in vuls if v.kev} if perfil == "operacional" else set()
    origem = "KEV não utilizado no perfil puro."
    if perfil == "operacional":
        try:
            dados, origem = CisaKevClient(caminho_cache_kev()).carregar()
            cves = {i["cveID"] for i in dados["vulnerabilities"]}
            kev_ids |= {v.id for v in vuls if v.cve_id in cves}
        except IntegracaoCVEError as erro:
            origem = (
                f"Cache KEV indisponível; usando {len(kev_ids)} marcações persistidas. " f"{erro}"
            )
    from inventario.matematica.cvss import score_ambiental_ativo
    mapa_ativos={a.pk:a for a in ativos}
    mapa_vuls={v.pk:v for v in vuls}
    ambientais={}
    for incidencia in incidencias:
        if incidencia.status in ("ABERTA","TRATAMENTO","ACEITA"):
            vid=incidencia.vulnerabilidade_id
            score=score_ambiental_ativo(mapa_vuls[vid],mapa_ativos[incidencia.equipamento_id])
            ambientais[vid]=max(ambientais.get(vid,0),score)
    return (
        ModeloRisco(
            [a.id for a in ativos],
            vulnerabilidades,
            incidencias,
            dependencias,
            fatores,
            kev_ids=kev_ids,
            pesos_relatorio={a.id: peso_relatorio(a) for a in ativos},
            scores_ambientais=ambientais,
        ),
        origem,
    )


def calcular_risco_banco(usar_exposicao=False, perfil=None):
    if settings.RISCO_POLITICA != "leontief":
        raise ValueError("Noisy-OR é módulo de laboratório e não está integrado à produção.")
    perfil = perfil or ("operacional" if usar_exposicao else "puro")
    with transaction.atomic():
        versao = versao_dados(perfil)
        chave = f"risco:v2:{namespace_risco()}:{perfil}:{versao}"
        def construir():
            modelo, origem = carregar_modelo_risco(perfil)
            resultado = modelo.calcular(**parametros_risco(perfil)).to_dict()
            resultado.update(versao_dados=versao, origem_kev=origem)
            # Chave versionada: um cálculo atrasado não sobrescreve a versão seguinte.
            cache.set(f"risco:ultimo:{namespace_risco()}:{perfil}", chave, timeout=3600)
            return resultado
        return lembrar(chave, construir)


def simular_correcao(incidencias_corrigidas, perfil="puro"):
    with transaction.atomic():
        modelo, origem = carregar_modelo_risco(perfil)
        resultado = modelo.simular(incidencias_corrigidas, **parametros_risco(perfil))
        resultado["origem_kev"] = origem
        return resultado


def gravar_snapshot_risco():
    from inventario.infraestrutura.auditoria import travar_escrita

    with transaction.atomic():
        # Serializar antes da leitura evita upgrade concorrente de leitor para escritor.
        travar_escrita()
        resultado = calcular_risco_banco(perfil="puro")
        chave = f"{resultado['versao_dados']}:{timezone.now().isoformat()}"
        por_ativo = dict(zip(resultado["ids_ativos"], resultado["risco_efetivo"]))
        snapshot, _ = SnapshotRisco.objects.get_or_create(
            chave=chave,
            defaults={
                "risco_total": sum(resultado["risco_efetivo"]),
                "por_ativo": por_ativo,
                "perfil": "puro",
            },
        )
        return snapshot


def registrar_mudanca_risco():
    """Compatibilidade: alteração apenas invalida; rotina persiste snapshots."""
    invalidar_cache_risco()


def analisar_historico_risco(inicio=None, fim=None):
    snapshots = list(SnapshotRisco.objects.filter(perfil="puro").order_by("ts", "id"))
    pontos = {s.ts: s.risco_total for s in snapshots}
    instantes = list(pontos)
    if len(instantes) < 3:
        return SerieRisco([], []).analisar()
    origem = instantes[0]
    dias = [(t - origem).total_seconds() / 86400 for t in instantes]

    def converter(texto):
        if texto is None:
            return None
        try:
            data = datetime.fromisoformat(texto)
        except (TypeError, ValueError) as erro:
            raise ValueError("Use data ISO, por exemplo 2026-10-06T12:00:00-03:00.") from erro
        if timezone.is_naive(data):
            raise ValueError("Informe o fuso horário da data.")
        return (data - origem).total_seconds() / 86400

    resultado = SerieRisco(dias, list(pontos.values())).analisar(
        inicio=converter(inicio),
        fim=converter(fim),
        limiar=settings.RISCO_LIMIAR_TENDENCIA,
        janela_minima_dias=settings.RISCO_JANELA_MINIMA_HORAS/24,
    )
    resultado.update(
        origem=origem.isoformat(),
        snapshots=len(instantes),
        perfil="puro",
        contem_simulacao=any(s.chave.startswith("DEMO-") for s in snapshots),
    )
    return resultado
