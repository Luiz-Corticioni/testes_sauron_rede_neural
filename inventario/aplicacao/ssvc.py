"""Avaliações são registros novos; não modificam aceites, correções ou SLA."""
from datetime import timedelta
import hashlib
import json
from django.core.exceptions import ValidationError
from inventario.aplicacao.autorizacao import exigir
from django.db import transaction
from django.utils import timezone
from inventario.dominio.ssvc import avaliar, politica
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario, dados_objeto
from inventario.models import AvaliacaoSSVC, Incidencia

PERMISSOES_LEITURA = ("inventario.view_incidencia", "inventario.view_ativo", "inventario.view_vulnerabilidade")


def contexto_atual(inc):
    # Somente campos relevantes: sem copiar contatos, senhas ou dados pessoais.
    v, a, s = inc.vulnerabilidade, inc.ativo, inc.software
    contexto = {"politica_sha256": politica()[2], "incidencia": {k: getattr(inc, k) for k in ("id", "ativo_id", "vulnerabilidade_id", "software_id", "status", "versao_afetada")},
                "ativo": {k: getattr(a, k) for k in ("id", "status", "criticidade", "exposto_internet", "zona_rede")},
                "vulnerabilidade": {k: getattr(v, k) for k in ("id", "cve_id", "cvss", "kev", "epss", "epss_observacao_id")},
                "componente": {k: getattr(s, k) for k in ("id", "nome", "versao", "cpe23")} if s else None,
                "epss_data": v.epss_data.isoformat() if v.epss_data else None}
    from inventario.models import AchadoComponente, DeclaracaoVEX
    componentes = list(AchadoComponente.objects.filter(incidencia=inc).order_by("pk", "fontes__pk").values(
        "software_id", "software__purl", "software__versao", "cve_id", "fontes__id", "fontes__sha256", "fontes__escopo"))
    if componentes:
        contexto["componentes_declarados"] = componentes
    purls = [c["software__purl"] for c in componentes]
    if s and s.purl:
        contexto["componente"]["purl"] = s.purl
        purls.append(s.purl)
    declaracoes = list(DeclaracaoVEX.objects.filter(documento__ativo_id=a.pk, cve_id=v.cve_id, purl__in=purls).order_by("pk").values(
        "documento_id", "documento__escopo", "documento__sha256", "purl", "status"))
    if declaracoes:
        contexto["declaracoes_vex"] = declaracoes
    from django.db.models import Q
    from inventario.models import RelacaoAtivos
    relacoes = RelacaoAtivos.objects.filter(Q(origem=a) | Q(destino=a)).order_by("pk").values(
        "id", "tipo", "escopo", "principal", "privilegio", "protocolo", "porta", "fonte", "evidencia",
        "observada_em", "revisar_em", "vigente", "origem_id", "destino_id", "origem__status", "destino__status")
    hoje, resumo, possui_relacoes = timezone.localdate(), hashlib.sha256(), False
    for relacao in relacoes.iterator(chunk_size=200):
        relacao["no_prazo"] = relacao["observada_em"] <= hoje < relacao["revisar_em"]
        resumo.update(json.dumps(relacao, sort_keys=True, ensure_ascii=False, default=str).encode()+b"\n")
        possui_relacoes = True
    if possui_relacoes:
        # A decisão percebe mudanças sem expor contas/evidências a quem só lê SSVC.
        contexto["relacoes_do_ativo_sha256"] = resumo.hexdigest()
    from inventario.models import MembroPerimetro, RevisaoCobertura
    from django.db.models import F, Window
    from django.db.models.functions import RowNumber
    membros = list(MembroPerimetro.objects.filter(ativo=a).order_by("perimetro_id").values("perimetro_id", "perimetro__atualizado_em"))
    revisoes = RevisaoCobertura.objects.filter(ativo=a).annotate(posicao=Window(RowNumber(),
        partition_by=[F("perimetro_id"), F("tipo"), F("principal")], order_by=F("pk").desc())).filter(posicao=1).order_by("pk")
    cobertura_hash, possui_revisao = hashlib.sha256(json.dumps(membros, default=str).encode()), False
    for revisao in revisoes.values("id", "perimetro_id", "tipo", "principal", "resultado", "contexto_sha256", "revisar_em").iterator(chunk_size=200):
        revisao["no_prazo"] = revisao["revisar_em"] > hoje
        cobertura_hash.update(json.dumps(revisao, sort_keys=True, default=str).encode()+b"\n")
        possui_revisao = True
    if membros or possui_revisao:
        contexto["cobertura_declarada_sha256"] = cobertura_hash.hexdigest()
    assinatura = hashlib.sha256(json.dumps(contexto, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    return contexto, assinatura


def elegivel(inc):
    return inc.status not in ("SUGERIDA", "CORRIGIDA") and inc.ativo.status not in ("BAIXADO", "INATIVO")


def registrar_avaliacao(pk, usuario, entradas, evidencia, revisar_em, contexto_hash, remediacao):
    usuario = exigir(usuario, *PERMISSOES_LEITURA, "inventario.change_incidencia")
    hoje = timezone.localdate()
    if not remediacao.strip() or len(remediacao) > 1000:
        raise ValidationError("Informe a remediação/mitigação avaliada (até 1000 caracteres).")
    if not evidencia.strip() or len(evidencia) > 8000:
        raise ValidationError("Informe evidências para as respostas (até 8000 caracteres).")
    if not hoje < revisar_em <= hoje + timedelta(days=90):
        raise ValidationError("A revisão deve ocorrer entre amanhã e 90 dias.")
    with transaction.atomic(), usar_usuario(usuario):
        travar_escrita()
        usuario = exigir(usuario, *PERMISSOES_LEITURA, "inventario.change_incidencia")
        inc = Incidencia.objects.select_for_update().get(pk=pk)
        contexto, assinatura = contexto_atual(inc)
        if assinatura != contexto_hash:
            raise ValidationError("O contexto mudou; recarregue a página antes de avaliar.")
        if not elegivel(inc):
            raise ValidationError("SSVC exige ocorrência confirmada e ainda não corrigida em ativo ativo/em manutenção.")
        if inc.vulnerabilidade.kev and entradas.get("exploitation") != "active":
            raise ValidationError("KEV exige registrar exploração ativa; EPSS não revoga essa evidência.")
        try:
            resultado = avaliar(entradas)
        except ValueError as erro:
            raise ValidationError(str(erro)) from erro
        registro = AvaliacaoSSVC.objects.create(incidencia=inc, incidencia_codigo=inc.pk, entradas=entradas,
            resultado=resultado, contexto=contexto, contexto_sha256=assinatura, evidencia=evidencia.strip(), remediacao=remediacao.strip(), revisar_em=revisar_em, por=usuario)
        registrar_evento("SSVC_AVALIADO", "AvaliacaoSSVC", registro.pk, dados_objeto(registro))
        return registro


def situacao(registro, assinatura):
    if registro.contexto_sha256 != assinatura:
        return "Reavaliar: contexto alterado"
    if registro.revisar_em <= timezone.localdate():
        return "Reavaliar: prazo de revisão vencido"
    return "Pendente de contexto" if registro.resultado["acao"] == "pending" else "Contexto registrado; revisão no prazo"
