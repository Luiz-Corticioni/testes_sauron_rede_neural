#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
RAIZ="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$RAIZ"
PYTHON="$RAIZ/.venv-linux/bin/python"
[[ -x "$PYTHON" ]] || { echo 'Execute primeiro: bash instalar_linux.sh' >&2; exit 1; }
case "${1:---web}" in
    --web) exec "$PYTHON" manage.py runserver 127.0.0.1:8000 --noreload ;;
    --terminal) exec "$PYTHON" sauron.py ;;
    --agendador) exec "$PYTHON" scripts/agendador.py ;;
    --servidor) exec "$PYTHON" -m gunicorn sauron_web.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 90 --access-logfile - ;;
    *) echo 'Uso: bash iniciar_linux.sh [--web|--terminal|--agendador|--servidor]' >&2; exit 2 ;;
esac
