"""Prévia, ingestão idempotente e revisão humana de observações externas."""
from datetime import UTC, timedelta
import hashlib
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from inventario.aplicacao.autorizacao import exigir
from inventario.aplicacao.relacoes import salvar_relacao
from inventario.dominio.observacoes import FORMATOS, extrair, texto
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import ObservacaoImportada, RevisaoObservacao

LEITURA = ("inventario.view_observacaoimportada", "inventario.view_revisaoobservacao")
IMPORTAR = (*LEITURA, "inventario.add_observacaoimportada")
REVISAR = (*LEITURA, "inventario.add_revisaoobservacao")
PROMOVER = (*REVISAR, "inventario.view_ativo", "inventario.view_relacaoativos", "inventario.add_relacaoativos")


def canonico(objeto):
    return json.dumps(objeto, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


@transaction.atomic
def registrar_falha(formato, usuario):
    """Registra apenas categoria genérica; não transforma erro em observação válida."""
    if not settings.SAURON_IMPORTACAO_OBSERVACOES_ENABLED:
        return
    travar_escrita()
    usuario = exigir(usuario, *IMPORTAR)
    if not settings.SAURON_IMPORTACAO_OBSERVACOES_ENABLED:
        return
    with usar_usuario(usuario):
        registrar_evento("FALHA_OBSERVACOES", "ImportacaoObservacoes", "lote",
                         {"formato": formato if formato in FORMATOS else "DESCONHECIDO", "erro": "ARQUIVO_OU_CONTEXTO_INVALIDO"})


def preparar(formato, conteudo, fonte, versao, observado_em, confianca, usuario):
    exigir(usuario, *IMPORTAR)
    if not settings.SAURON_IMPORTACAO_OBSERVACOES_ENABLED:
        raise ValidationError("Importação de observações está desativada na configuração do servidor.")
    try:
        fonte, versao = texto(fonte, "Identidade da fonte", 120), texto(versao, "Versão da fonte", 120)
        if any(c in campo for campo in (fonte, versao) for c in ("@", "?", "://")):
            raise ValueError("Use fonte e versão sem URL, credenciais ou e-mail.")
        if confianca not in dict(ObservacaoImportada.CONFIANCAS):
            raise ValueError("Confiança declarada inválida.")
        instante = parse_datetime(observado_em) if isinstance(observado_em, str) else None
        if instante is None or timezone.is_naive(instante) or instante > timezone.now():
            raise ValueError("Informe data observada não futura com fuso horário.")
        instante = instante.astimezone(UTC)
        itens, ignorados = extrair(formato, conteudo)
        preparados = []
        for item in itens:
            identificador = hashlib.sha256(canonico([item["chave"], instante.isoformat()])).hexdigest()
            envelope = {"versao_contrato": ObservacaoImportada.VERSAO, "formato": formato,
                "tipo": item["tipo"], "identidade_fonte": fonte, "versao_fonte": versao,
                "identificador": identificador, "observado_em": instante.isoformat(),
                "confianca": confianca, "erro": None, "dados": item["dados"]}
            preparados.append({**envelope, "conteudo_sha256": hashlib.sha256(canonico(envelope)).hexdigest()})
        return {"itens": preparados, "ignorados": ignorados, "arquivo_sha256": hashlib.sha256(conteudo).hexdigest()}
    except (ValueError, TypeError, RecursionError) as erro:
        raise ValidationError(str(erro)) from erro


def importar(formato, conteudo, fonte, versao, observado_em, confianca, usuario):
    try:
        return _importar(formato, conteudo, fonte, versao, observado_em, confianca, usuario)
    except (ValidationError, IntegrityError):
        registrar_falha(formato, usuario)
        raise


@transaction.atomic
def _importar(formato, conteudo, fonte, versao, observado_em, confianca, usuario):
    previa = preparar(formato, conteudo, fonte, versao, observado_em, confianca, usuario)
    travar_escrita()
    usuario = exigir(usuario, *IMPORTAR)
    if not settings.SAURON_IMPORTACAO_OBSERVACOES_ENABLED:
        raise ValidationError("Importação de observações foi desativada antes da gravação.")
    novos, repetidos = [], 0
    with usar_usuario(usuario):
        ids = [item["identificador"] for item in previa["itens"]]
        existentes = {}
        for inicio in range(0, len(ids), 500):
            existentes.update(ObservacaoImportada.objects.filter(formato=formato, identidade_fonte=fonte.strip(),
                identificador__in=ids[inicio:inicio+500]).values_list("identificador", "conteudo_sha256"))
        for item in previa["itens"]:
            campos = {k: item[k] for k in ("formato", "identidade_fonte", "identificador")}
            existente = existentes.get(item["identificador"])
            if existente is not None:
                if existente != item["conteudo_sha256"]:
                    raise ValidationError("Identificador existente com conteúdo diferente; lote não importado.")
                repetidos += 1
                continue
            novos.append(ObservacaoImportada(**campos, versao_contrato=item["versao_contrato"], tipo=item["tipo"], versao_fonte=item["versao_fonte"],
                conteudo_sha256=item["conteudo_sha256"], observado_em=item["observado_em"],
                confianca=item["confianca"], erro="", dados=item["dados"], recebido_por=usuario))
        ObservacaoImportada.objects.bulk_create(novos, batch_size=200)
        registrar_evento("IMPORTAR_OBSERVACOES", "ObservacaoImportada", "lote",
                         {"formato": formato, "arquivo_sha256": previa["arquivo_sha256"],
                          "novos": len(novos), "repetidos": repetidos, "ignorados": previa["ignorados"]})
    return {"novos": len(novos), "repetidos": repetidos, "ignorados": previa["ignorados"]}


@transaction.atomic
def revisar(pk, classificacao, justificativa, usuario, revisar_em=None):
    travar_escrita()
    usuario = exigir(usuario, *(PROMOVER if classificacao == "RELACAO_CRIADA" else REVISAR))
    observacao = ObservacaoImportada.objects.get(pk=pk)
    if classificacao not in dict(RevisaoObservacao.CLASSIFICACOES):
        raise ValidationError("Classificação inválida.")
    justificativa = texto(justificativa, "Justificativa", 500)
    relacao = None
    criacao = observacao.revisoes.filter(classificacao="RELACAO_CRIADA").select_related("relacao").first()
    if classificacao in {"INCORRETA", "INCONCLUSIVA"} and criacao and criacao.relacao and criacao.relacao.vigente:
        raise ValidationError("Revogue a relação vinculada antes de marcar a observação como incorreta ou inconclusiva.")
    if classificacao == "RELACAO_CRIADA":
        if observacao.tipo != "RELACAO" or criacao:
            raise ValidationError("A observação não é uma relação pendente ou já foi convertida.")
        hoje = timezone.localdate()
        data_observada = timezone.localtime(observacao.observado_em).date()
        if data_observada < hoje - timedelta(days=90):
            raise ValidationError("Observação com mais de 90 dias; importe uma evidência atual antes de criar a relação.")
        if revisar_em is None or not hoje < revisar_em <= hoje + timedelta(days=90):
            raise ValidationError("A revisão da relação deve ocorrer em até 90 dias.")
        d = observacao.dados
        relacao = salvar_relacao({"origem_id": d["origem_ativo"], "destino_id": d["destino_ativo"],
            "tipo": "REDE", "escopo": d["escopo"], "protocolo": d["protocolo"], "porta": d["porta"],
            "principal": "", "privilegio": "", "fonte": f"{observacao.formato}: {observacao.identidade_fonte}",
            "evidencia": f"Observação #{observacao.pk}; regra {d['id_regra']}. {justificativa}",
            "observada_em": data_observada, "revisar_em": revisar_em,
            "vigente": True}, usuario)
    revisao = RevisaoObservacao(observacao=observacao, classificacao=classificacao,
        justificativa=justificativa, relacao=relacao, autor=usuario)
    revisao.full_clean()
    with usar_usuario(usuario):
        revisao.save()
        registrar_evento("REVISAR_OBSERVACAO", "ObservacaoImportada", observacao.pk,
                         {"classificacao": classificacao, "revisao": revisao.pk, "relacao": relacao.pk if relacao else None})
    return revisao
