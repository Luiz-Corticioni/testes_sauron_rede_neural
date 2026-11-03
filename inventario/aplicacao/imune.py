"""Recomendador auditável: nenhum vínculo é criado pelo ciclo automático."""

from datetime import timedelta
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from inventario.infraestrutura.auditoria import travar_escrita, usar_usuario
from inventario.dominio.sistema_imune import avaliar_sinais
from inventario.aplicacao.imune_padroes import aprender, afinidade, clonar, base_correspondente
from inventario.models import (
    Alerta,
    Anticorpo,
    Ativo,
    Dependencia,
    Incidencia,
    Incidente,
    SugestaoImune,
    Tolerancia,
)
from inventario.aplicacao.operacao import emitir_alerta, exigir
from inventario.aplicacao.risco import calcular_risco_banco

ABERTAS = ["PENDENTE", "OBSERVACAO"]


def forca_atual(memoria):
    dias = max(0, (timezone.now() - memoria.reforcado_em).total_seconds() / 86400)
    return memoria.para_dominio().decaimento(dias, settings.IMUNE_MEIA_VIDA_DIAS)


def sinais_perigo(ativo, vulnerabilidade, riscos, fornecedores, incidentes=None):
    sinais = []
    if vulnerabilidade.kev:
        sinais.append("KEV")
    if ativo.exposto_internet:
        sinais.append("INTERNET")
    if (
        ativo.pk in incidentes
        if incidentes is not None
        else Incidente.objects.filter(ativo=ativo, encerrado_em__isnull=True).exists()
    ):
        sinais.append("INCIDENTE_ABERTO")
    if riscos.get(ativo.pk, 0) >= settings.IMUNE_LIMIAR_RISCO:
        sinais.append("RISCO_EFETIVO")
    if any(
        riscos.get(pk, 0) >= settings.IMUNE_LIMIAR_RISCO for pk in fornecedores.get(ativo.pk, [])
    ):
        sinais.append("VIZINHO_DE_RISCO")
    return sinais


def retirar(sugestao, estado="EXPIRADA"):
    sugestao.estado = estado
    sugestao.save(update_fields=["estado", "decidido_por", "decidido_em"])
    for alerta in Alerta.objects.filter(
        tipo="IMUNE", chave=str(sugestao.pk), reconhecido_em__isnull=True
    ):
        alerta.reconhecido_em = timezone.now()
        alerta.save(update_fields=["reconhecido_em"])


def atualizar_sugestao(ativo, memoria, valor, sinais, estado):
    sugestao = SugestaoImune.objects.filter(
        ativo=ativo, vulnerabilidade=memoria.vulnerabilidade, estado__in=ABERTAS
    ).first()
    from inventario.aplicacao.imune_padroes import vinculo_deterministico, antigenos
    tipo = "DETERMINISTICO" if vinculo_deterministico(ativo, memoria.vulnerabilidade) is True else "HIPOTESE"
    origem = memoria.prototipo
    eixos = sorted({k for a in antigenos(ativo, memoria.vulnerabilidade)
                    for k,v in a.to_dict().items() if v != "" and origem.get(k)==v
                    and k not in ("categoria","vetor_ataque")})
    campos = dict(
        tipo_vinculo=tipo,
        explicacao=eixos,
        anticorpo=memoria,
        codigo_anticorpo=str(memoria.pk),
        afinidade=valor,
        prioridade=valor * forca_atual(memoria),
        sinal2=bool(sinais),
        sinais=sinais,
        estado=estado,
    )
    if sugestao is None:
        sugestao = SugestaoImune.objects.create(
            ativo=ativo, vulnerabilidade=memoria.vulnerabilidade, **campos
        )
    elif any(getattr(sugestao, k) != v for k, v in campos.items()):
        for k, v in campos.items():
            setattr(sugestao, k, v)
        sugestao.save()
    if estado == "PENDENTE":
        emitir_alerta(
            "IMUNE",
            ativo,
            str(sugestao.pk),
            f"Possivelmente afetado por {memoria.vulnerabilidade_id}; "
            f'afinidade {valor:.1%}; sinais: {", ".join(sinais)}. Revise antes de confirmar.',
        )
    else:
        for a in Alerta.objects.filter(
            tipo="IMUNE", chave=str(sugestao.pk), reconhecido_em__isnull=True
        ):
            a.reconhecido_em = timezone.now()
            a.save(update_fields=["reconhecido_em"])
    return sugestao.pk


def executar_ciclo():
    from django.core.cache import cache
    from inventario.models import RegistroAuditoria
    from inventario.aplicacao.risco import namespace_risco
    from inventario.infraestrutura.auditoria import registrar_evento

    # Aprendizagem limitada; nenhum cálculo de risco ocorre sob esta trava.
    with transaction.atomic():
        travar_escrita()
        saudaveis_aprendizado=list(Ativo.objects.filter(linha_base_saudavel=True).prefetch_related("softwares"))
        aprendidos=aprender(saudaveis_aprendizado)
    cabeca=lambda: RegistroAuditoria.objects.order_by("-id").values_list("hash",flat=True).first()
    versao=cabeca()
    ativos=list(Ativo.objects.exclude(status="BAIXADO").prefetch_related("softwares").order_by("pk"))
    saudaveis=[a for a in ativos if a.linha_base_saudavel]
    memorias=list(Anticorpo.objects.filter(estado="ATIVO").select_related("vulnerabilidade","origem"))
    chave_cursor="imune:cursor:"+namespace_risco()
    cursor=cache.get(chave_cursor,0)
    limite=max(1,settings.IMUNE_MAX_ATIVOS_CICLO)
    inicio=cursor % max(1,len(ativos))
    lote=(ativos[inicio:]+ativos[:inicio])[:limite]
    manutencao=[]
    for memoria in memorias:
        base=base_correspondente(memoria,saudaveis,memoria.vulnerabilidade)
        if base:
            manutencao.append((memoria,"DESCARTADO",base))
        elif (forca_atual(memoria)<settings.IMUNE_PISO and
              not (memoria.origem and memoria.origem.status in ("ABERTA","TRATAMENTO","ACEITA"))):
            manutencao.append((memoria,"ARQUIVADO",None))
    removidas={m.pk for m,_,_ in manutencao}
    risco=calcular_risco_banco()
    riscos=dict(zip(risco["ids_ativos"],risco["risco_efetivo"]))
    fornecedores={}
    for i,j in Dependencia.objects.filter(peso__gt=0).values_list("dependente_id","fornecedor_id"):
        fornecedores.setdefault(i,[]).append(j)
    incidentes=set(Incidente.objects.filter(encerrado_em__isnull=True).values_list("ativo_id",flat=True))
    tolerados=set(Tolerancia.objects.filter(valida_ate__gte=timezone.localdate()).values_list("linhagem","ativo_id"))
    conhecidos=set(Incidencia.objects.exclude(status="SUGERIDA").values_list("ativo_id","vulnerabilidade_id"))
    melhores={}
    for memoria in memorias:
        if memoria.pk in removidas:
            continue
        for ativo in lote:
            par=(ativo.pk,memoria.vulnerabilidade_id)
            if ativo.linha_base_saudavel or par in conhecidos or (memoria.linhagem,ativo.pk) in tolerados:
                continue
            valor=afinidade(memoria,ativo,memoria.vulnerabilidade)
            if valor<settings.IMUNE_LIMIAR-1e-9:
                continue
            sinais=sinais_perigo(ativo,memoria.vulnerabilidade,riscos,fornecedores,incidentes)
            estado=avaliar_sinais(valor,sinais,settings.IMUNE_LIMIAR)
            if estado and (par not in melhores or valor>melhores[par][2]):
                melhores[par]=(ativo,memoria,valor,sinais,estado)
    resultado={"aprendidos":aprendidos,"removidos":0,"pendentes":0,"observacoes":0}
    # A cabeça auditada cobre também tolerâncias, software e autoria. Alteração
    # concorrente adia o lote inteiro, sem aplicar decisões calculadas de snapshot velho.
    with transaction.atomic():
        travar_escrita()
        if cabeca()!=versao:
            resultado["adiado_por_concorrencia"]=True
            return resultado
        for memoria,estado,base in manutencao:
            memoria.estado,memoria.descartado_por_ativo=estado,base
            memoria.save(update_fields=["estado","descartado_por_ativo"])
            resultado["removidos"]+=estado=="ARQUIVADO"
        vistos=set()
        for dados in melhores.values():
            vistos.add(atualizar_sugestao(*dados))
            resultado["pendentes" if dados[-1]=="PENDENTE" else "observacoes"]+=1
        for sugestao in SugestaoImune.objects.filter(ativo_id__in=[a.pk for a in lote],estado__in=ABERTAS).exclude(pk__in=vistos):
            retirar(sugestao)
        registrar_evento("CICLO_IMUNE","Imune","ciclo",resultado)
        transaction.on_commit(lambda: cache.set(chave_cursor,inicio+len(lote),timeout=None))
    return resultado


@transaction.atomic
def decidir_sugestao(pk, confirmar, usuario, motivo="", valida_ate=None):
    travar_escrita()
    usuario = exigir(usuario, "inventario.decidir_sugestao_imune")
    s = SugestaoImune.objects.select_related("anticorpo", "ativo", "vulnerabilidade").get(pk=pk)
    a = s.anticorpo
    if s.estado not in ABERTAS or not a or a.estado != "ATIVO":
        raise ValidationError(
            "Sugestão já decidida ou memória indisponível. Execute o ciclo novamente."
        )
    if confirmar and (
        s.ativo.status == "BAIXADO"
        or s.ativo.linha_base_saudavel
        or afinidade(a, s.ativo, s.vulnerabilidade)
        < settings.IMUNE_LIMIAR - 1e-9
    ):
        raise ValidationError("Perfil do ativo ou afinidade mudou. Execute o ciclo novamente.")
    with usar_usuario(usuario):
        if confirmar:
            incidencia = Incidencia.objects.filter(
                ativo=s.ativo, vulnerabilidade=s.vulnerabilidade
            ).first()
            if incidencia and incidencia.status != "SUGERIDA":
                raise ValidationError(
                    "Este vínculo já possui decisão; revise no menu de incidências."
                )
            if incidencia is None:
                incidencia = Incidencia(
                    id="INC-I-" + uuid.uuid4().hex[:12].upper(),
                    ativo=s.ativo,
                    vulnerabilidade=s.vulnerabilidade,
                )
            incidencia.status = "ABERTA"
            incidencia.observacoes = f"Confirmação humana da sugestão imune {s.pk}."
            incidencia.save()
        else:
            validade = valida_ate or timezone.localdate() + timedelta(
                days=settings.IMUNE_TOLERANCIA_DIAS
            )
            if not motivo.strip() or validade < timezone.localdate():
                raise ValidationError("Rejeição exige motivo e validade presente ou futura.")
            t, _ = Tolerancia.objects.get_or_create(
                anticorpo=a,
                ativo=s.ativo,
                defaults=dict(linhagem=a.linhagem, motivo=motivo, valida_ate=validade, por=usuario),
            )
            t.motivo, t.valida_ate, t.por = motivo, validade, usuario
            t.save()
        dominio = a.para_dominio()
        dominio.forca = forca_atual(a)
        dominio.reforcar(confirmar)
        a.forca, a.confirmacoes, a.rejeicoes = (
            dominio.forca,
            dominio.confirmacoes,
            dominio.rejeicoes,
        )
        a.reforcado_em = timezone.now()
        if dominio.deve_suspender(settings.IMUNE_TAXA_REJEICAO, settings.IMUNE_MIN_REJEICOES):
            a.estado = "SUSPENSO"
        a.save()
        s.decidido_por, s.decidido_em = usuario, timezone.now()
        retirar(s, "CONFIRMADA" if confirmar else "REJEITADA")
        if confirmar:
            clonar(a, list(Ativo.objects.filter(linha_base_saudavel=True)))
        if a.estado == "SUSPENSO":
            for outra in SugestaoImune.objects.filter(anticorpo=a, estado__in=ABERTAS):
                retirar(outra)
    return s
