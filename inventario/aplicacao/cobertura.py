"""Cobertura declarada por perímetro; nenhum estado de risco é alterado."""
from django.core.exceptions import ValidationError
from inventario.aplicacao.autorizacao import exigir
from django.db import transaction
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.utils import timezone
from inventario.aplicacao.relacoes import LEITURA as LEITURA_RELACOES, carregar_recorte
from inventario.dominio.cobertura import contextos, estado, percentual, ESTADOS, ROTULOS
from inventario.dominio.grafo_relacoes import MAX_NOS
from inventario.infraestrutura.auditoria import usar_usuario, travar_escrita, registrar_evento, dados_objeto
from inventario.models import Ativo, PerimetroRelacoes, MembroPerimetro, RevisaoCobertura

LEITURA = (*LEITURA_RELACOES, "inventario.view_perimetrorelacoes", "inventario.view_revisaocobertura")


def autorizar(usuario, permissao=None):
    return exigir(usuario, *LEITURA, *([permissao] if permissao else []))


def salvar_perimetro(usuario, nome, descricao, ativos, pk=None, versao=None):
    if not isinstance(ativos, (list, tuple)) or len(ativos) > MAX_NOS or any(not isinstance(a, str) for a in ativos):
        raise ValidationError("Informe até 10.000 códigos de ativos.")
    ids = set(ativos)
    if len(ids) != len(ativos):
        raise ValidationError("A lista de ativos contém repetições.")
    with transaction.atomic():
        travar_escrita()
        usuario = autorizar(usuario, f"inventario.{'change' if pk else 'add'}_perimetrorelacoes")
        with usar_usuario(usuario):
            p = PerimetroRelacoes.objects.get(pk=pk) if pk else PerimetroRelacoes(criada_por=usuario)
            if pk and p.atualizado_em.isoformat() != versao:
                raise ValidationError("O perímetro mudou; recarregue antes de editar.")
            if set(Ativo.objects.filter(pk__in=ids).values_list("pk", flat=True)) != ids:
                raise ValidationError("Ativo não encontrado no inventário.")
            anteriores = set(p.membros.values_list("ativo_id", flat=True)) if p.pk else set()
            p.nome, p.descricao, p.atualizada_por = nome, descricao, usuario
            p.save()
            p.membros.exclude(ativo_id__in=ids).delete()
            MembroPerimetro.objects.bulk_create([MembroPerimetro(perimetro=p, ativo_id=a) for a in sorted(ids-anteriores)])
            registrar_evento("PERIMETRO_MEMBROS", "PerimetroRelacoes", p.pk,
                            {"adicionados": sorted(ids-anteriores), "retirados": sorted(anteriores-ids), "total": len(ids)})
            return p


def recorte(perimetro, tipo, principal=""):
    p = PerimetroRelacoes.objects.get(pk=perimetro)
    ativos, linhas, atual = carregar_recorte(tipo, p.nome, principal)
    if atual is None or atual.pk != p.pk:
        raise ValidationError("O perímetro mudou; recarregue a seleção.")
    resumos, motivos = contextos(ativos, linhas, atual.pk, timezone.localdate(), tipo, principal.strip(), {"nome": p.nome, "descricao": p.descricao})
    return p, ativos, linhas, resumos, motivos


@transaction.atomic
def preparar_revisao(usuario, perimetro, tipo, ativo, principal=""):
    autorizar(usuario)
    p, _, _, resumos, _ = recorte(perimetro, tipo, principal)
    if ativo not in resumos:
        raise ValidationError("A revisão exige ativo operacional pertencente ao perímetro.")
    return p, resumos[ativo]


def registrar_revisao(usuario, perimetro, tipo, ativo, principal, resultado, evidencia, observada_em, revisar_em, contexto_sha256):
    with transaction.atomic():
        travar_escrita()
        usuario = autorizar(usuario, "inventario.add_revisaocobertura")
        p, resumo = preparar_revisao(usuario, perimetro, tipo, ativo, principal)
        if contexto_sha256 != resumo["sha256"]:
            raise ValidationError("Relações ou perímetro mudaram; recarregue o contexto antes de revisar.")
        if resultado == "SEM_RELACOES" and resumo["vigentes"]:
            raise ValidationError("Há relações vigentes, inclusive pendências. Revise/revogue-as ou registre lacunas.")
        if resultado == "REVISADO" and (not resumo["contagens"]["ELEGIVEL"] or resumo["pendentes"]):
            raise ValidationError("Revisado exige relações elegíveis e nenhuma relação vigente pendente.")
        with usar_usuario(usuario):
            r = RevisaoCobertura.objects.create(perimetro=p, ativo_id=ativo, tipo=tipo, principal=principal.strip(), resultado=resultado,
                evidencia=evidencia, observada_em=observada_em, revisar_em=revisar_em, contexto_sha256=contexto_sha256, resumo=resumo, por=usuario)
            registrar_evento("COBERTURA_REVISADA", "RevisaoCobertura", r.pk, dados_objeto(r))
            return r


def ultimas_revisoes(perimetro, tipo, principal=""):
    # Uma linha por ativo; não carrega todo o histórico para escolher a última.
    return RevisaoCobertura.objects.filter(perimetro_id=perimetro, tipo=tipo, principal=principal.strip()).annotate(
        posicao=Window(RowNumber(), partition_by=[F("ativo_id")], order_by=F("pk").desc())).filter(posicao=1)


@transaction.atomic
def analisar_cobertura(usuario, perimetro, tipo, principal="", limite=50, filtro=""):
    autorizar(usuario)
    if type(limite) is not int or not 1 <= limite <= 100 or filtro not in (*ESTADOS, ""):
        raise ValueError("Limite deve ser inteiro de 1 a 100 e o estado deve ser conhecido.")
    hoje = timezone.localdate()
    p, ativos, linhas, resumos, motivos = recorte(perimetro, tipo, principal)
    revisoes = {r["ativo_id"]: r for r in ultimas_revisoes(p.pk, tipo, principal).filter(ativo__perimetros_declarados__perimetro=p).values(
        "id", "ativo_id", "resultado", "contexto_sha256", "revisar_em", "por_id")}
    contagens, itens = dict.fromkeys(ESTADOS, 0), []
    for a in ativos:
        resumo, revisao = resumos[a["id"]], revisoes.get(a["id"])
        situacao = estado(revisao, resumo, hoje)
        contagens[situacao] += 1
        if (not filtro or situacao == filtro) and len(itens) < limite:
            itens.append({**resumo, "estado": situacao, "estado_rotulo": ROTULOS[situacao], "revisao_id": revisao["id"] if revisao else None,
                          "revisar_em": revisao["revisar_em"] if revisao else None})
    total = len(ativos)
    revisados = contagens["REVISADO"]+contagens["SEM_RELACOES"]
    representados = sum(bool(r["contagens"]["ELEGIVEL"]) for r in resumos.values())
    membros_total = p.membros.count()
    return {"perimetro_id": p.pk, "escopo": p.nome, "tipo": tipo, "principal": principal.strip(), "data": hoje.isoformat(),
            "membros_total": membros_total, "ativos_operacionais": total, "ativos_excluidos": membros_total-total,
            "revisados_no_prazo": revisados, "cobertura_declarada_percentual": percentual(revisados, total),
            "com_relacoes_elegiveis": representados, "representacao_percentual": percentual(representados, total),
            "estados": contagens, "motivos_relacoes": motivos, "relacoes_total": len(linhas), "itens": itens,
            "estados_rotulados": [{"rotulo": ROTULOS[k], "total": v} for k, v in contagens.items()],
            "motivos_rotulados": [{"rotulo": ROTULOS[k], "total": v} for k, v in motivos.items()],
            "limitado": (contagens[filtro] if filtro else total) > len(itens), "limite": limite,
            "aviso": "Cobertura declarada das revisões neste perímetro, camada e principal. Não mede segurança, confiança na fonte ou cobertura real de descoberta. Nenhum estado de vulnerabilidade é alterado."}
