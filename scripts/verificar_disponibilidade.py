"""Confere critérios do JSONL coletado por prova_24h.py; não gera evidência de execução."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


def instante(texto):
    try:
        valor = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError("Data sem fuso horário.")
        return valor
    except (AttributeError, TypeError, ValueError) as erro:
        raise ValueError("A evidência exige datas ISO com fuso horário.") from erro


def validar_registros(registros):
    # Aceita registros antigos sem alterar datas, identidade ou estado observado.
    nomes_antigos = {'data': 'ts', 'container_id': 'id', 'iniciado_em': 'started_at',
                    'estado': 'status', 'healthcheck': 'health', 'reinicios': 'restart_count'}
    registros = [dict(r, **{novo: r[antigo] for antigo,novo in nomes_antigos.items()
                            if antigo in r and novo not in r}) for r in registros]
    if len(registros) < 2:
        raise ValueError("São necessárias amostras durante pelo menos 24 horas.")
    primeiro = registros[0]
    identidade = tuple(primeiro.get(k) for k in ("id", "started_at", "restart_count"))
    if not identidade[0] or type(identidade[2]) is not int or identidade[2] < 0:
        raise ValueError("Identidade ou contador de reinícios ausente/inválido.")
    boot = instante(identidade[1])
    tempos = []
    for n, r in enumerate(registros, 1):
        if r.get("erro_coleta") or r.get("status") != "running" or r.get("health") != "healthy":
            raise ValueError(f"Amostra {n}: coleta falhou ou container não estava saudável.")
        if tuple(r.get(k) for k in ("id", "started_at", "restart_count")) != identidade:
            raise ValueError(f"Amostra {n}: houve reinício ou troca do container.")
        ts = instante(r.get("ts"))
        if ts < boot:
            raise ValueError(f"Amostra {n}: coleta anterior à inicialização do container.")
        if tempos and not 0 < (ts - tempos[-1]).total_seconds() <= 90:
            raise ValueError(f"Amostra {n}: data fora de ordem ou lacuna maior que 90 segundos.")
        tempos.append(ts)
    duracao = (tempos[-1] - tempos[0]).total_seconds()
    if duracao < 86400:
        raise ValueError(f"Duração insuficiente: {duracao / 3600:.4f} horas; exigidas 24.")
    return dict(
        amostras=len(registros),
        horas_observadas=duracao / 3600,
        inicio=tempos[0].isoformat(),
        fim=tempos[-1].isoformat(),
        criterio="Mesma execução, healthy/running, sem reinício, lacunas ≤90s.",
    )


def validar_arquivo(caminho):
    if caminho.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Arquivo excede 10 MB; separe as janelas de observação.")
    registros = []
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8-sig").splitlines(), 1):
        try:
            registro = json.loads(linha)
            if not isinstance(registro, dict):
                raise ValueError("Cada linha deve conter um objeto JSON.")
            registros.append(registro)
        except ValueError as erro:
            raise ValueError(f"Linha {numero}: JSON inválido ou incompleto.") from erro
    return validar_registros(registros)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arquivo", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validar_arquivo(args.arquivo), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as erro:
        print(f"Evidência reprovada: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
