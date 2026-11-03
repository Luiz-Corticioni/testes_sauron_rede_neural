#!/bin/sh
set -eu
papel="${1:-web}"
case "$papel" in
  preparar)
    mkdir -p /app/dados
    python manage.py preparar_servidor --sem-estaticos
    if [ "${SAURON_SEED:-0}" = "1" ]; then python manage.py seed_demo; fi
    ;;
  agendador)
    exec python -u scripts/agendador.py
    ;;
  web)
    exec python -m gunicorn sauron_web.wsgi:application --bind 0.0.0.0:8000 \
      --workers 1 --threads 2 --timeout 60 --worker-tmp-dir /dev/shm \
      --access-logfile - --error-logfile -
    ;;
  *)
    exec "$@"
    ;;
esac
