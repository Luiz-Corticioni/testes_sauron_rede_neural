"""Cache de dados calculados; uma reconstrução por vez no mesmo host.

Até 64 travas por família limitam uso de disco/memória. Não guarda
autorização, sessão ou HTML. Um host adicional requer cache/trava compartilhados.
"""
import hashlib
from threading import Lock
from django.conf import settings
from django.core.cache import cache
from inventario.infraestrutura.arquivos import trava_arquivo

TRAVAS = {grupo: tuple(Lock() for _ in range(64)) for grupo in ('painel', 'risco', 'montecarlo', 'outros')}


def lembrar(chave, construir, segundos=3600):
    pronto = cache.get(chave)
    if pronto is not None:
        return pronto
    grupo = chave.split(':', 1)[0]
    grupo = grupo if grupo in TRAVAS else 'outros'
    faixa = int(hashlib.sha256(chave.encode()).hexdigest()[:8], 16) % len(TRAVAS[grupo])
    # Painel pode chamar risco: famílias distintas evitam travas aninhadas iguais.
    with TRAVAS[grupo][faixa], trava_arquivo(settings.DATA_DIR/'cache'/'calculos'/f'{grupo}-{faixa}.lock'):
        pronto = cache.get(chave)
        if pronto is None:
            pronto = construir()
            cache.set(chave, pronto, timeout=segundos)
        return pronto
