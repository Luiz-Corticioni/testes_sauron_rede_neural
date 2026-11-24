"""Comparação limitada de evidências; nunca encerra uma incidência."""
import hashlib
from datetime import UTC

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from inventario.aplicacao.autorizacao import exigir
from inventario.dominio.observacoes import LIMITE_BYTES, extrair, json_local, texto
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import Incidencia, ObservacaoImportada, SugestaoCorrecao

PERMISSOES = ("inventario.view_incidencia", "inventario.view_vulnerabilidade", "inventario.view_ativo",
              "inventario.view_observacaoimportada", "inventario.view_revisaoobservacao",
              "inventario.view_sugestaocorrecao", "inventario.add_sugestaocorrecao")


@transaction.atomic
def sugerir_correcao(incidencia_id, observacao_id, conteudo, observado_em, declaracao, fonte, versao, usuario):
    """Compara a CVE com um novo Trivy do mesmo alvo declarado e fonte original.

    A associação entre alvo e ativo e a cobertura são afirmações do operador, não
    verificações automáticas. O relatório pode ter limitações de detecção.
    """
    travar_escrita()
    usuario = exigir(usuario, *PERMISSOES)
    if not settings.SAURON_IMPORTACAO_OBSERVACOES_ENABLED:
        raise ValidationError("Importação de observações desativada.")
    inc = Incidencia.objects.select_related("vulnerabilidade", "ativo").get(pk=incidencia_id)
    obs = ObservacaoImportada.objects.get(pk=observacao_id)
    from inventario.aplicacao.retencao_observacoes import corte_retencao, EXPIRADA
    if obs.erro == EXPIRADA or obs.recebido_em <= corte_retencao():
        raise ValidationError("Observação fora do prazo de retenção; importe evidência atual.")
    if inc.status not in {"ABERTA", "TRATAMENTO", "ACEITA", "MITIGADA"}:
        raise ValidationError("A incidência deve estar confirmada e ainda não corrigida.")
    ultima = obs.revisoes.order_by("-criada_em", "-pk").first()
    if obs.formato != "trivy" or obs.tipo != "ACHADO" or not ultima or ultima.classificacao != "VALIDA":
        raise ValidationError("Selecione uma observação Trivy revisada como válida.")
    if fonte != obs.identidade_fonte or versao != obs.versao_fonte:
        raise ValidationError("Fonte e versão declaradas devem coincidir com a observação anterior.")
    cve = inc.vulnerabilidade.cve_id
    alvo = obs.dados.get("alvo_sha256")
    if not cve or obs.dados.get("cve") != cve.upper() or not alvo or alvo == hashlib.sha256(b"").hexdigest():
        raise ValidationError("A CVE ou o alvo da observação não permite comparação.")
    try:
        declaracao = texto(declaracao, "Declaração de vínculo e cobertura", 500)
        instante = parse_datetime(observado_em) if isinstance(observado_em, str) else None
        if instante is None or timezone.is_naive(instante) or instante <= obs.observado_em or instante > timezone.now():
            raise ValueError("Informe data com fuso, posterior à observação e não futura.")
        if not isinstance(conteudo, bytes) or not 0 < len(conteudo) <= LIMITE_BYTES:
            raise ValueError("Arquivo vazio ou acima de 2 MiB.")
        itens, _ = extrair("trivy", conteudo)
        doc = json_local(conteudo)
        grupos = [g for g in doc["Results"] if isinstance(g.get("Target"), str)
                  and hashlib.sha256(g["Target"].encode()).hexdigest() == alvo]
        if not grupos or any("Vulnerabilities" not in g for g in grupos):
            raise ValueError("O relatório deve conter o mesmo alvo e lista explícita de vulnerabilidades.")
        if any(i["dados"].get("alvo_sha256") == alvo and i["dados"].get("cve") == cve.upper() for i in itens):
            raise ValueError("A CVE ainda consta no relatório para esse alvo.")
    except (ValueError, TypeError, RecursionError) as erro:
        raise ValidationError(str(erro)) from erro
    digest = hashlib.sha256(conteudo).hexdigest()
    existente = SugestaoCorrecao.objects.filter(incidencia=inc, observacao=obs, scan_sha256=digest).first()
    if existente:
        if existente.observado_em != instante.astimezone(UTC) or existente.declaracao != declaracao:
            raise ValidationError("O mesmo relatório já foi registrado com outros termos.")
        return existente
    with usar_usuario(usuario):
        sugestao = SugestaoCorrecao.objects.create(incidencia=inc, observacao=obs, scan_sha256=digest,
            observado_em=instante, declaracao=declaracao, criado_por=usuario)
        registrar_evento("SUGERIR_CORRECAO", "SugestaoCorrecao", sugestao.pk,
            {"incidencia": inc.pk, "observacao": obs.pk, "scan_sha256": digest})
    return sugestao
