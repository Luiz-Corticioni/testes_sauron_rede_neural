# Manifesto oficial multi-arquitetura consultado em 15/11/2026.
FROM python:3.12-alpine@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89

# Atualiza correções disponíveis no Alpine no momento da construção. A imagem
# continua sujeita à varredura Trivy e pode conter CVEs ainda sem correção.
RUN apk update && apk upgrade --no-cache

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SAURON_DB_PATH=/app/dados/sauron.sqlite3 \
    SAURON_DATA_DIR=/app/dados

WORKDIR /app
RUN addgroup -g 10001 -S sauron \
    && adduser -S -D -H -u 10001 -G sauron sauron
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
