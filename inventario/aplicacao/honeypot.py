"""Importação manual e minimizada; não abre portas nem executa telemetria."""
import ipaddress
import json
import re
from datetime import UTC, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from inventario.aplicacao.autorizacao import exigir
from inventario.aplicacao.operacao import emitir_alerta
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import EventoHoneypot, SensorHoneypot, RevisaoEventoHoneypot, PoliticaRetencaoHoneypot

LIMITE_BYTES = 1024 * 1024
LIMITE_EVENTOS = 500
CAMPOS = {"id", "observado_em", "origem_ip", "tipo"}


def validar_lote(conteudo):
    if not isinstance(conteudo, bytes) or len(conteudo) > LIMITE_BYTES:
        raise ValidationError("Arquivo inválido ou maior que 1 MB.")
    try:
        lote = json.loads(conteudo.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as erro:
        raise ValidationError("Arquivo deve conter JSON UTF-8 válido.") from erro
    if not isinstance(lote, list) or not 1 <= len(lote) <= LIMITE_EVENTOS:
        raise ValidationError("Envie uma lista com 1 a 500 eventos.")
    eventos = {}
    for item in lote:
        if not isinstance(item, dict) or set(item) != CAMPOS or any(not isinstance(item[c], str) for c in CAMPOS):
            raise ValidationError("Cada evento deve ter apenas id, observado_em, origem_ip e tipo como texto.")
        identificador = item["id"]
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", identificador):
            raise ValidationError("Identificador de evento inválido.")
        try:
            endereco = ipaddress.ip_address(item["origem_ip"])
            if getattr(endereco, "scope_id", None):
                raise ValueError("Endereço IP com zona não suportado.")
            origem = str(endereco)
            observado = parse_datetime(item["observado_em"])
        except ValueError as erro:
            raise ValidationError("Data ou endereço IP inválido.") from erro
        if observado is None or timezone.is_naive(observado):
            raise ValidationError("Informe data e hora ISO 8601 com fuso horário.")
        if item["tipo"] not in dict(EventoHoneypot.TIPOS):
            raise ValidationError("Tipo de evento inválido.")
        valor = (observado.astimezone(UTC), origem, item["tipo"])
        if identificador in eventos and eventos[identificador] != valor:
            raise ValidationError("Um identificador foi associado a dados diferentes no lote.")
        eventos[identificador] = valor
    return eventos, len(lote)


@transaction.atomic
def salvar_sensor(sensor, usuario):
    travar_escrita()
    acao = "add" if sensor._state.adding else "change"
    usuario = exigir(usuario, "inventario.view_ativo", f"inventario.{acao}_sensorhoneypot")
    if not sensor._state.adding:
        anterior = SensorHoneypot.objects.get(pk=sensor.pk)
        if (anterior.ambiente, anterior.ativo_id) != (sensor.ambiente, sensor.ativo_id) and EventoHoneypot.objects.filter(sensor=anterior).exists():
            raise ValidationError("Ambiente e ativo vinculado não podem mudar após importar eventos. Cadastre outro sensor.")
    sensor.full_clean()
    with usar_usuario(usuario):
        sensor.save()
    return sensor


@transaction.atomic
def importar_eventos(sensor_id, conteudo, usuario):
    eventos, total = validar_lote(conteudo)
    travar_escrita()
    usuario = exigir(usuario, "inventario.view_sensorhoneypot", "inventario.add_eventohoneypot")
    sensor = SensorHoneypot.objects.get(pk=sensor_id)
    if not sensor.habilitado:
        raise ValidationError("O sensor está desabilitado.")
    existentes = {e.identificador: e for e in EventoHoneypot.objects.filter(
        sensor=sensor, identificador__in=eventos)}
    novos = []
    dias = set()
    for identificador, (quando, origem, tipo) in eventos.items():
        antigo = existentes.get(identificador)
        if antigo:
            if (antigo.observado_em, antigo.origem_ip, antigo.tipo) != (quando, origem, tipo):
                raise ValidationError("Identificador já importado com outros dados; nenhum evento foi gravado.")
            continue
        novos.append(EventoHoneypot(sensor=sensor, identificador=identificador,
                                   observado_em=quando, origem_ip=origem, tipo=tipo))
        dias.add(quando.date().isoformat())
    with usar_usuario(usuario):
        EventoHoneypot.objects.bulk_create(novos)
        for dia in sorted(dias):
            emitir_alerta("HONEYPOT", sensor.ativo, f"sensor:{sensor.pk}:{dia}",
                          f"{sensor.get_ambiente_display()}: interação no sensor {sensor.nome} em {dia} (UTC). Verifique o contexto.", 2)
        registrar_evento("IMPORTAR", "SensorHoneypot", sensor.pk,
                         {"recebidos": total, "novos": len(novos), "duplicados": total - len(novos)})
    return {"recebidos": total, "novos": len(novos), "duplicados": total - len(novos)}


@transaction.atomic
def revisar_evento(evento_id, classificacao, observacao, usuario):
    usuario = exigir(usuario, "inventario.view_ativo", "inventario.view_sensorhoneypot",
                     "inventario.view_eventohoneypot", "inventario.view_revisaoeventohoneypot",
                     "inventario.add_revisaoeventohoneypot")
    travar_escrita()
    revisao = RevisaoEventoHoneypot(evento=EventoHoneypot.objects.get(pk=evento_id), autor=usuario,
                                    classificacao=classificacao, observacao=observacao)
    revisao.full_clean()
    with usar_usuario(usuario):
        revisao.save()
        registrar_evento("REVISAR", "EventoHoneypot", evento_id,
                         {"revisao": revisao.pk, "classificacao": classificacao, "observacao": observacao})
    return revisao


@transaction.atomic
def alterar_retencao(dias, usuario):
    travar_escrita()
    usuario = exigir(usuario, "inventario.view_ativo", "inventario.view_sensorhoneypot",
                     "inventario.view_politicaretencaohoneypot", "inventario.change_politicaretencaohoneypot")
    politica = PoliticaRetencaoHoneypot.objects.filter(pk=1).first() or PoliticaRetencaoHoneypot(pk=1)
    politica.dias = dias
    politica.atualizado_por = usuario
    politica.full_clean()
    with usar_usuario(usuario):
        politica.save()
        registrar_evento("CONFIGURAR_RETENCAO", "Honeypot", "politica", {"dias": politica.dias})
    return politica


@transaction.atomic
def aplicar_retencao(limite=1000):
    """Remove IPs e revisões expirados em lotes, sem alterar alertas nem backups."""
    if type(limite) is not int or not 1 <= limite <= 1000:
        raise ValueError("O limite deve estar entre 1 e 1000 registros.")
    travar_escrita()
    politica = PoliticaRetencaoHoneypot.objects.filter(pk=1).first()
    dias = politica.dias if politica else 90
    corte = timezone.now() - timedelta(days=dias)
    ids_revisoes = list(RevisaoEventoHoneypot.objects.filter(criado_em__lte=corte).order_by("pk").values_list("pk", flat=True)[:limite])
    revisoes = RevisaoEventoHoneypot.objects.filter(pk__in=ids_revisoes).delete()[0]
    candidatos = EventoHoneypot.objects.filter(recebido_em__lte=corte).filter(Q(origem_ip__isnull=False) | Q(revisoes__isnull=True))
    ids_eventos = list(candidatos.order_by("pk").values_list("pk", flat=True).distinct()[:limite])
    eventos = EventoHoneypot.objects.filter(pk__in=ids_eventos)
    ips = eventos.filter(origem_ip__isnull=False).update(origem_ip=None)
    removidos = eventos.filter(revisoes__isnull=True).delete()[0]
    resultado = {"dias": dias, "ips_eliminados": ips, "revisoes_eliminadas": revisoes, "eventos_eliminados": removidos}
    if ips or revisoes or removidos:
        registrar_evento("APLICAR_RETENCAO", "Honeypot", "politica", resultado)
    return resultado
