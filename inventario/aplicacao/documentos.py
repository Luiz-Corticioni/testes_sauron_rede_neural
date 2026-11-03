"""Importação local e atômica. Declarações externas nunca encerram incidências."""
import uuid
from django.core.exceptions import ValidationError
from inventario.aplicacao.autorizacao import exigir as exigir_permissoes
from django.db import transaction
from inventario.dominio.documentos import carregar, texto, exigir, serializar
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import (Ativo, Software, Vulnerabilidade, Incidencia, DocumentoInventario,
                               ItemSBOM, AchadoComponente, DeclaracaoVEX)

LEITURA = ("inventario.view_ativo", "inventario.view_software", "inventario.view_vulnerabilidade", "inventario.view_incidencia")
ESCRITA = (*LEITURA, "inventario.add_software", "inventario.add_incidencia")


def autorizar(usuario):
    return exigir_permissoes(usuario, *ESCRITA)


def reconciliar(documento, usuario):
    usuario = autorizar(usuario)
    with transaction.atomic(), usar_usuario(usuario):
        travar_escrita()
        ativo = Ativo.objects.get(pk=documento.ativo_id)
        if ativo.status in ("INATIVO", "BAIXADO"):
            raise ValidationError("Reconciliação operacional exige ativo ativo/em manutenção.")
        for declaracao in documento.declaracoes.filter(status="affected"):
            s = Software.objects.filter(ativo=ativo, purl=declaracao.purl).first()
            if s:
                achado, _ = AchadoComponente.objects.get_or_create(software=s, cve_id=declaracao.cve_id)
                achado.fontes.add(documento)
        achados = list(documento.achados.select_related("software"))
        catalogo = {v.cve_id: v for v in Vulnerabilidade.objects.filter(cve_id__in=[a.cve_id for a in achados])}
        vinculados = 0
        for achado in achados:
            if achado.cve_id not in catalogo or achado.incidencia_id:
                continue
            s, v = achado.software, catalogo[achado.cve_id]
            inc, _ = Incidencia.objects.get_or_create(ativo_id=s.ativo_id, vulnerabilidade=v,
                defaults={"id": "INC-"+uuid.uuid4().hex[:24].upper(), "software": s, "status": "SUGERIDA",
                          "versao_afetada": s.versao, "observacoes": "Declaração de documento SBOM/VEX; validar aplicabilidade de todos os componentes antes de confirmar."})
            achado.incidencia = inc
            achado.save(update_fields=["incidencia"])
            vinculados += 1
        registrar_evento("DOCUMENTO_RECONCILIADO", "DocumentoInventario", documento.pk, {"achados_vinculados": vinculados})
        return vinculados


def importar(ativo_id, conteudo, usuario, escopo, origem, aplicar=False):
    usuario = autorizar(usuario)
    bruto, assinatura, dados = carregar(conteudo)
    escopo, origem = texto(escopo, 200), texto(origem, 200)
    identificador = dados["id"]
    exigir(isinstance(identificador, str) and len(identificador) <= 512, "Identificador do documento inválido.")
    exigir(type(dados["versao"]) is int and 1 <= dados["versao"] <= 2**31-1, "Versão do documento deve ser inteiro positivo.")
    # A prévia também é somente leitura: gravações apenas após validar todo o lote.
    with transaction.atomic(), usar_usuario(usuario):
        if aplicar:
            travar_escrita()
            usuario = autorizar(usuario)
        try:
            ativo = Ativo.objects.get(pk=ativo_id)
        except Ativo.DoesNotExist as erro:
            raise ValidationError("Ativo não encontrado; recarregue a seleção.") from erro
        exigir(ativo.status not in ("INATIVO", "BAIXADO"), "Importação operacional exige ativo ativo/em manutenção.")
        if identificador and DocumentoInventario.objects.filter(ativo=ativo, tipo=dados["tipo"], identificador=identificador, versao=dados["versao"]).exclude(sha256=assinatura).exists():
            raise ValidationError("Mesmo identificador/versão com conteúdo diferente; corrija a revisão do documento.")
        componentes = {}
        for item in dados.get("itens", []):
            s = componentes.get(item["purl"]) or Software.objects.filter(ativo=ativo, purl=item["purl"]).first()
            if s is None:
                s = Software(ativo=ativo, **{k:item[k] for k in ("nome", "versao", "fornecedor", "purl", "cpe23")})
                s.full_clean()
            exigir(s.versao == item["versao"] and not (s.cpe23 and item["cpe23"] and s.cpe23 != item["cpe23"]), "Identidade/CPE diverge do componente já cadastrado.")
            componentes[item["purl"]] = s
        resumo = {"tipo": dados["tipo"], "sha256": assinatura, "previa": not aplicar,
                  "componentes": len(dados.get("itens", [])), "identidades_unicas": len(componentes), "achados": len(dados.get("achados", [])), "declaracoes": len(dados.get("declaracoes", []))}
        if not aplicar:
            return resumo
        documento, novo = DocumentoInventario.objects.get_or_create(ativo=ativo, tipo=dados["tipo"], sha256=assinatura, origem=origem, escopo=escopo,
            defaults={"identificador": identificador, "versao": dados["versao"], "conteudo": serializar(bruto), "importado_por": usuario})
        if novo:
            refs = {}
            for item in dados.get("itens", []):
                s = componentes[item["purl"]]
                if s.pk is None:
                    s.save()
                refs[item["ref"]] = s
                ItemSBOM.objects.create(documento=documento, referencia=item["ref"], software=s, depende_de=dados["dependencias"].get(item["ref"], []))
            if dados.get("raiz"):
                ItemSBOM.objects.create(documento=documento, referencia=dados["raiz"], depende_de=dados["dependencias"].get(dados["raiz"], []))
            for ref, codigo in dados.get("achados", []):
                achado, _ = AchadoComponente.objects.get_or_create(software=refs[ref], cve_id=codigo)
                achado.fontes.add(documento)
            for item in dados.get("declaracoes", []):
                DeclaracaoVEX.objects.create(documento=documento, **item)
                s = Software.objects.filter(ativo=ativo, purl=item["purl"]).first()
                if s and item["status"] == "affected":
                    achado, _ = AchadoComponente.objects.get_or_create(software=s, cve_id=item["cve_id"])
                    achado.fontes.add(documento)
        resumo.update(documento=documento.pk, novo=novo, vinculados=reconciliar(documento, usuario), achados_deduplicados=documento.achados.count())
        registrar_evento("DOCUMENTO_IMPORTADO" if novo else "DOCUMENTO_REIMPORTADO", "DocumentoInventario", documento.pk,
            {**resumo, "ativo": ativo.pk, "origem": origem, "escopo": escopo, "identificador": identificador, "versao": dados["versao"]})
        return resumo
