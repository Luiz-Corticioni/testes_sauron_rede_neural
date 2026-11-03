FROM python:3.15.0-slim-bookworm

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
