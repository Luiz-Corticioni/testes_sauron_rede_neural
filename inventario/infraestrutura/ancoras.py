"""Âncoras HMAC append-only por aplicação; coletor externo deve preservar cópias."""
import hashlib
import hmac
import json
import logging
import logging.handlers
import os
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from inventario.infraestrutura.arquivos import trava_arquivo


def assinar(dados):
    canonico=json.dumps(dados,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return hmac.new(settings.SAURON_AUDIT_HMAC_KEY.encode(),canonico.encode(),hashlib.sha256).hexdigest()


def ancorar(ate_id=None):
    from inventario.models import RegistroAuditoria
    from inventario.infraestrutura.auditoria import verificar_cadeia
    caminho=Path(settings.SAURON_AUDIT_ANCHOR_PATH)
    with trava_arquivo(caminho.with_suffix(".lock")), transaction.atomic():
        if not verificar_cadeia(verificar_ancora=False)["integra"]:
            raise ValueError("Cadeia inválida: âncora recusada.")
        registros=RegistroAuditoria.objects.order_by("id")
        if ate_id is not None:
            registros=registros.filter(pk__lte=ate_id)
        cabeca=registros.last()
        dados={"id_cabeca":cabeca.pk if cabeca else 0, "contagem":registros.count(),
               "hash":cabeca.hash if cabeca else "", "timestamp":timezone.now().isoformat()}
        envelope={**dados,"assinatura":assinar(dados)}
        caminho.parent.mkdir(parents=True,exist_ok=True)
        with caminho.open("a",encoding="utf-8") as f:
            f.write(json.dumps(envelope,ensure_ascii=False)+"\n")
            f.flush()
            os.fsync(f.fileno())
        if settings.SAURON_AUDIT_SYSLOG:
            host,porta=settings.SAURON_AUDIT_SYSLOG.rsplit(":",1)
            handler=logging.handlers.SysLogHandler(address=(host,int(porta)))
            try:
                registro=logging.LogRecord("sauron.ancora",logging.INFO,"",0,json.dumps(envelope),(),None)
                handler.emit(registro)
            finally:
                handler.close()
        return envelope


def verificar_ancoras():
    from inventario.models import RegistroAuditoria
    caminho=Path(settings.SAURON_AUDIT_ANCHOR_PATH)
    if not caminho.exists():
        return not settings.SAURON_EXIGIR_ANCORA, "ausente"
    try:
        quantidade = 0
        with caminho.open(encoding="utf-8") as f:
            for linha in f:
                quantidade += 1
                envelope=json.loads(linha)
                if not isinstance(envelope, dict) or set(envelope) != {"id_cabeca", "contagem", "hash", "timestamp", "assinatura"}:
                    return False, "formato de âncora inválido"
                if (type(envelope["id_cabeca"]) is not int or type(envelope["contagem"]) is not int
                        or envelope["id_cabeca"] < 0 or envelope["contagem"] < 0
                        or not all(isinstance(envelope[c], str) for c in ("hash", "timestamp", "assinatura"))):
                    return False, "campos de âncora inválidos"
                assinatura=envelope.pop("assinatura")
                if not hmac.compare_digest(assinatura,assinar(envelope)):
                    return False, "assinatura de âncora inválida"
                registros=RegistroAuditoria.objects.filter(pk__lte=envelope["id_cabeca"])
                cabeca=registros.order_by("pk").last()
                if registros.count()!=envelope["contagem"] or (cabeca.hash if cabeca else "")!=envelope["hash"]:
                    return False, "truncamento ou divergência de âncora"
        return (True, "válida") if quantidade else (False, "arquivo de âncoras vazio")
    except (ValueError,KeyError,TypeError,OSError):
        return False, "âncora ilegível"

