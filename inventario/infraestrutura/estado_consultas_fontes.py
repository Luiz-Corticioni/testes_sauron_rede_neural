"""Últimas tentativas sanitizadas; não registra URL, consulta ou credenciais."""
import json
import logging
from datetime import datetime, timezone

from django.conf import settings

from inventario.infraestrutura.arquivos import salvar_json_atomico, trava_arquivo

LOGGER = logging.getLogger(__name__)
ESTADOS = {"resposta", "falha", "limitada", "desativada", "parcial"}


def ler_estado(fonte):
    if fonte not in {"nvd", "epss", "kev"}:
        raise ValueError("Fonte desconhecida.")
    caminho = settings.DATA_DIR / "estado_fontes" / f"{fonte}.json"
    try:
        if caminho.stat().st_size > 4096:
            return None
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(dados, dict):
            return None
        for valor in dados.values():
            if not isinstance(valor, dict) or set(valor) != {"estado", "data"} or valor["estado"] not in ESTADOS:
                return None
            data = datetime.fromisoformat(valor["data"])
            if data.tzinfo is None:
                return None
        return {k: v for k, v in dados.items() if k in {"ultima", "ultima_falha", "ultimo_sucesso"}}
    except (OSError, ValueError, TypeError):
        return None


def registrar_estado(fonte, estado):
    if fonte not in {"nvd", "epss", "kev"} or estado not in ESTADOS:
        raise ValueError("Fonte ou estado desconhecido.")
    caminho = settings.DATA_DIR / "estado_fontes" / f"{fonte}.json"
    try:
        with trava_arquivo(caminho.with_suffix(".lock")):
            dados = ler_estado(fonte) or {}
            atual = {"estado": estado, "data": datetime.now(timezone.utc).isoformat()}
            dados["ultima"] = atual
            dados["ultimo_sucesso" if estado == "resposta" else "ultima_falha"] = atual
            salvar_json_atomico(caminho, dados)
    except OSError:
        # Falha de telemetria não deve mudar o resultado da consulta externa.
        LOGGER.warning("Não foi possível registrar o estado da fonte %s.", fonte)
