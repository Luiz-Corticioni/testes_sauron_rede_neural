"""Gera um .env privado sem expor a chave e sem sobrescrever configuração existente."""

import argparse
import base64
import os
from pathlib import Path
import secrets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desenvolvimento", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--https", action="store_true")
    parser.add_argument("--saida", type=Path, help="Destino alternativo; nunca sobrescreve arquivos.")
    argumentos = parser.parse_args()
    if any(caractere in argumentos.host for caractere in "\n\r/,: "):
        parser.error("Informe apenas o nome DNS ou IPv4 do servidor, sem protocolo ou porta.")
    caminho = argumentos.saida or Path(__file__).resolve().parent.parent / ".env"
    if caminho.exists():
        print("O .env já existe e foi preservado. Edite-o se precisar alterar o host.")
        return
    https = argumentos.https or argumentos.host not in ("localhost","127.0.0.1")
    if not https:
        print("ATENÇÃO: HTTP SEM TLS — use apenas em desenvolvimento local; cookies sem transporte seguro.")
    origens = (f"https://{argumentos.host}" if https else
               ",".join(f"http://{host}:{porta}" for host in ("127.0.0.1", "localhost")
                        for porta in (8000, 2228)))
    conteudo = [
        f"SAURON_SECRET_KEY={secrets.token_urlsafe(64)}",
        f"SAURON_DEBUG={int(argumentos.desenvolvimento)}",
        f"SAURON_ALLOWED_HOSTS=localhost,127.0.0.1,{argumentos.host}",
        f"SAURON_CSRF_TRUSTED_ORIGINS={origens}",
        "SAURON_SEED=0",
        f"SAURON_SECURE_COOKIES={int(https)}",
        f"SAURON_SSL_REDIRECT={int(https)}",
        f"SAURON_HSTS_PRELOAD={int(https)}",
        f"SAURON_AUDIT_HMAC_KEY={secrets.token_urlsafe(64)}",
        "SAURON_ADMIN_USER=",
        "SAURON_ADMIN_PASSWORD=",
        f"SAURON_BACKUP_KEY={base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()}",
        "NVD_API_KEY=",
        "SAURON_EMAIL_ENABLED=0",
        "SAURON_EMAIL_HOST=",
        "SAURON_EMAIL_PORT=587",
        "SAURON_EMAIL_USER=",
        "SAURON_EMAIL_PASSWORD=",
        "SAURON_EMAIL_FROM=",
        "SAURON_EMAIL_USE_TLS=1",
        "SAURON_EMAIL_USE_SSL=0",
        "SAURON_RISCO_KAPPA=0.3",
        "SAURON_RISCO_TAU=25",
        "SAURON_LIMIAR_TENDENCIA=10",
    ]
    with os.fdopen(os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(conteudo) + "\n")
    caminho.chmod(0o600)
    print(".env criado com chave aleatória privada. Nenhuma chave foi exibida.")


if __name__ == "__main__":
    main()
