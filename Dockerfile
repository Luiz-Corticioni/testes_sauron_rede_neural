# Manifesto oficial multi-arquitetura consultado em 13/11/2026.
FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

# Atualiza correções disponíveis no Debian no momento da construção. A imagem
# continua sujeita à varredura Trivy e pode conter CVEs ainda sem correção.
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SAURON_DB_PATH=/app/dados/sauron.sqlite3 \
    SAURON_DATA_DIR=/app/dados

WORKDIR /app
RUN groupadd --system --gid 10001 sauron \
    && useradd --system --uid 10001 --gid sauron --home /app sauron
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Estáticos são construídos na imagem; o container pode usar raiz somente leitura.
# DEBUG vale só neste comando e não relaxa a validação da chave na execução.
RUN mkdir -p /app/dados /app/staticfiles \
    && SAURON_AUDIT_HMAC_KEY=build-only-audit-key SAURON_DEBUG=0 SAURON_SECRET_KEY=build-only-static-key-abcdefghijklmnopqrstuvwxyz-0123456789 python manage.py collectstatic --noinput \
    && chmod +x /app/entrypoint.sh \
    && chown -R sauron:sauron /app
USER sauron
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=330s --retries=3 \
  CMD python scripts/healthcheck.py || exit 1
ENTRYPOINT ["/app/entrypoint.sh"]
