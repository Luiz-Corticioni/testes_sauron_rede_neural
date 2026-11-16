"""Conversão offline de JSONL Cowrie; nunca preserva credenciais ou comandos."""
import json
import uuid

from django.core.exceptions import ValidationError
from inventario.aplicacao.honeypot import LIMITE_BYTES, LIMITE_EVENTOS, validar_lote

TIPOS = {"cowrie.session.connect": "CONEXAO", "cowrie.login.failed": "LOGIN_FALHOU",
         "cowrie.login.success": "LOGIN_ACEITO"}


def converter(conteudo, lote):
    try:
        lote = str(uuid.UUID(str(lote)))
    except (ValueError, TypeError, AttributeError) as erro:
        raise ValidationError("Informe um identificador UUID para o lote.") from erro
    if not isinstance(conteudo, bytes) or len(conteudo) > LIMITE_BYTES:
        raise ValidationError("Arquivo inválido ou maior que 1 MB.")
    try:
        linhas = conteudo.decode("utf-8").splitlines()
        if not 1 <= len(linhas) <= LIMITE_EVENTOS:
            raise ValidationError("O arquivo deve conter de 1 a 500 linhas.")
        eventos = []
        ignorados = 0
        for numero, linha in enumerate(linhas, 1):
            item = json.loads(linha)
            if not isinstance(item, dict):
                raise ValidationError("Cada linha deve conter um objeto JSON.")
            tipo = TIPOS.get(item.get("eventid"))
            if tipo is None:
                ignorados += 1
                continue
            eventos.append({"id": f"cowrie:{lote}:{numero}", "observado_em": item.get("timestamp"),
                            "origem_ip": item.get("src_ip"), "tipo": tipo})
        if not eventos:
            raise ValidationError("Nenhum evento de conexão ou login suportado foi encontrado.")
        reduzido = json.dumps(eventos, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
        validar_lote(reduzido)
        return reduzido, ignorados
    except (UnicodeDecodeError, ValueError, RecursionError, TypeError) as erro:
        raise ValidationError("JSONL inválido; confira as linhas e os campos obrigatórios.") from erro
