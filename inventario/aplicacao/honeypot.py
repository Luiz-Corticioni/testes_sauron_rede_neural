"""Importação manual e minimizada; não abre portas nem executa telemetria."""
import ipaddress
import json
import re
from datetime import UTC

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from inventario.aplicacao.autorizacao import exigir
from inventario.aplicacao.operacao import emitir_alerta
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import EventoHoneypot, SensorHoneypot

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
