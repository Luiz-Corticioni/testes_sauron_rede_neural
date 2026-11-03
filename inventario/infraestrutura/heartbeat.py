"""Heartbeat de conclusão da rotina, independente de HTTP e ORM."""
from datetime import datetime, timezone
import json
from pathlib import Path


def verificar_heartbeat(caminho, intervalo, agora=None):
    agora=agora or datetime.now(timezone.utc)
    try:
        registro=json.loads(Path(caminho).read_text(encoding="utf-8"))
        instante=datetime.fromisoformat(registro["finalizada_em"])
        idade=(agora-instante).total_seconds()
        return 0<=idade<=2*intervalo
    except (ValueError,KeyError,TypeError,OSError):
        return False

