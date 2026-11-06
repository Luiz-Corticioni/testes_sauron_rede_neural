"""Registra evidências reais por minuto. Não transforma amostras em aprovação automática."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time


def docker(*argumentos, entrada=None):
    resultado = subprocess.run(
        ["docker", *argumentos],
        input=entrada,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    return resultado.stdout.strip()


def coletar(container):
    estado = json.loads(docker("inspect", container))[0]
    memoria = json.loads(
        docker(
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
            container,
        )
    )
    processo = estado["State"]
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "id": estado["Id"],
        "started_at": processo.get("StartedAt"),
        "status": processo["Status"],
        "health": processo.get("Health", {}).get("Status", "ausente"),
        "restart_count": estado["RestartCount"],
        "memoria": memoria.get("MemUsage"),
        "memoria_percentual": memoria.get("MemPerc"),
    }


def gravar(container, caminho, registro):
    linha = json.dumps(registro, ensure_ascii=False) + "\n"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(linha)
    # Mantém a evidência também no volume do container, sem acesso privilegiado.
    codigo = (
        "import sys\n"
        "with open('/app/dados/prova_24h.log', 'a', encoding='utf-8') as arquivo:\n"
        "    arquivo.write(sys.stdin.read())\n"
    )
    docker("exec", "-i", container, "python", "-c", codigo, entrada=linha)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--horas", type=float, default=24)
    parser.add_argument("--intervalo", type=float, default=60)
    parser.add_argument("--container", help="ID ou nome; por padrão usa o serviço sauron do Compose.")
    parser.add_argument("--saida", type=Path, help="Arquivo novo para esta observação.")
    argumentos = parser.parse_args()
    if argumentos.horas <= 0 or argumentos.intervalo <= 0:
        parser.error("Duração e intervalo devem ser positivos.")
    caminho = argumentos.saida or Path(__file__).resolve().parent.parent / "dados" / "prova_24h.log"
    if caminho.exists():
        parser.error("O arquivo de evidências já existe; informe outro caminho em --saida.")
    if not argumentos.container:
        try:
            ids = docker("compose", "ps", "-q", "sauron").splitlines()
        except (OSError, subprocess.SubprocessError) as erro:
            parser.error(f"Não foi possível consultar o Compose: {erro}")
        if len(ids) != 1:
            parser.error("Inicie um único serviço sauron ou informe --container explicitamente.")
        argumentos.container = ids[0]
    inicio = time.monotonic()
    prazo = inicio + argumentos.horas * 3600
    proxima_amostra = inicio
    amostras = falhas = 0
    print(f"Registrando amostras em {caminho}. Mantenha este terminal aberto.")
    try:
        while True:
            try:
                registro = coletar(argumentos.container)
                falhas += int(registro["health"] != "healthy")
            except (OSError, subprocess.SubprocessError, ValueError, KeyError) as erro:
                falhas += 1
                registro = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "status": "erro_coleta",
                    "erro_coleta": True,
                    "erro": str(erro),
                }
            try:
                gravar(argumentos.container, caminho, registro)
            except (OSError, subprocess.SubprocessError) as erro:
                falhas += 1
                print(f"Falha de gravação da evidência: {erro}")
            amostras += 1
            print(f"{registro['ts']} {registro.get('health', registro['status'])}")
            agora = time.monotonic()
            if agora >= prazo:
                break
            proxima_amostra += argumentos.intervalo
            time.sleep(max(0, min(proxima_amostra, prazo) - agora))
    except KeyboardInterrupt:
        print("Coleta interrompida: não constitui evidência de 24 horas completas.")
    duracao = time.monotonic() - inicio
    print(f"Amostras: {amostras}; falhas: {falhas}; duração: {duracao:.0f}s.")
    print("Confira continuidade, healthcheck, ID, reinícios e início do processo no log.")


if __name__ == "__main__":
    main()
