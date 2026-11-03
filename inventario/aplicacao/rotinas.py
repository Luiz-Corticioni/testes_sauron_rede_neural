"""Orquestra tarefas idempotentes; falha em uma fonte não interrompe as demais."""

import logging

from django.conf import settings
from django.utils import timezone

from inventario.infraestrutura.arquivos import salvar_json_atomico, trava_arquivo
from inventario.infraestrutura.cve_client import CisaKevClient
from inventario.aplicacao.operacao import (
    alertar_tendencia,
    alertas_inventario,
    atualizar_prazos,
    enriquecer_kev,
    expirar_aceites,
    sugerir_cves,
)
from inventario.aplicacao.imune import executar_ciclo
from inventario.aplicacao.risco import caminho_cache_kev, gravar_snapshot_risco

LOGGER = logging.getLogger(__name__)


def executar_rotinas(sem_rede=False):
    resultado = {
        "ultima_rotina_em": timezone.now().isoformat(),
        "sem_rede": sem_rede,
        "etapas": {},
        "erros": {},
    }

    def kev():
        cliente = CisaKevClient(caminho_cache_kev())
        dados = cliente.carregar()[0] if sem_rede else cliente.atualizar()
        return {"enriquecidas": enriquecer_kev(dados)}

    from inventario.infraestrutura.ancoras import ancorar
    etapas = {
        "aceites": expirar_aceites,
        "kev": kev,
        "software": lambda: sugerir_cves(sem_rede=sem_rede),
        "prazos": atualizar_prazos,
        "alertas": alertas_inventario,
        "snapshot": lambda: gravar_snapshot_risco().pk,
        "tendencia": alertar_tendencia,
        "imune": executar_ciclo,
        "ancora": ancorar,
    }
    # Também serializa chamadas simultâneas de cron, Docker e terminal.
    with trava_arquivo(settings.DATA_DIR / "cache" / "rotinas.lock"):
        for nome, rotina in etapas.items():
            try:
                resultado["etapas"][nome] = rotina()
            except Exception as erro:
                # Cada etapa registra a própria falha; nunca informa sucesso fictício.
                LOGGER.exception("Rotina %s falhou", nome)
                resultado["erros"][nome] = str(erro)
        avisos = resultado["etapas"].get("software", {}).get("avisos", [])
        resultado["status"] = "parcial" if resultado["erros"] or avisos else "ok"
        resultado["finalizada_em"] = timezone.now().isoformat()
        salvar_json_atomico(settings.DATA_DIR / "ultima_rotina.json", resultado)
    return resultado
