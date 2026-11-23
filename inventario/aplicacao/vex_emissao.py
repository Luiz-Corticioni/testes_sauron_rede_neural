"""Emissão de OpenVEX limitado a decisões de correção com evidência registrada."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from jsonschema import Draft202012Validator

from inventario.aplicacao.autorizacao import exigir
from inventario.dominio.documentos import purl_exata, vex
from inventario.dominio.observacoes import texto
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import Incidencia

PERMISSOES_VEX = ("inventario.view_incidencia", "inventario.view_ativo", "inventario.view_vulnerabilidade",
                  "inventario.view_software", "inventario.change_incidencia")
SCHEMA = Path(__file__).resolve().parents[2] / "docs" / "exemplos" / "openvex-schema-v0.2.0.json"


@transaction.atomic
def emitir_vex(incidencia_id, autor, usuario):
    travar_escrita()
    usuario = exigir(usuario, *PERMISSOES_VEX)
    inc = Incidencia.objects.select_related("vulnerabilidade", "software").get(pk=incidencia_id)
    if inc.status != "CORRIGIDA" or inc.decisao_pendente or not inc.evidencia.strip():
        raise ValidationError("A emissão exige decisão de correção concluída e evidência.")
    if not inc.software or not inc.software.purl or not inc.vulnerabilidade.cve_id:
        raise ValidationError("A emissão exige componente com PURL e CVE identificada.")
    try:
        autor = texto(autor, "Autor da declaração", 200)
        purl = purl_exata(inc.software.purl, inc.software.versao)
        doc = {"@context": "https://openvex.dev/ns/v0.2.0", "@id": f"urn:uuid:{uuid4()}",
               "author": autor, "timestamp": timezone.now().isoformat(), "version": 1,
               "statements": [{"vulnerability": {"name": inc.vulnerabilidade.cve_id},
                   "products": [{"@id": purl}], "status": "fixed", "status_notes": inc.evidencia}]}
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        erros = list(Draft202012Validator(schema).iter_errors(doc))
        if erros:
            raise ValueError("Documento não satisfaz o esquema OpenVEX local.")
        vex(doc)
    except (ValueError, KeyError, TypeError, OSError) as erro:
        raise ValidationError(str(erro)) from erro
    conteudo = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with usar_usuario(usuario):
        registrar_evento("EMITIR_VEX", "Incidencia", inc.pk,
                         {"documento": doc["@id"], "sha256": hashlib.sha256(conteudo.encode()).hexdigest()})
    return conteudo
