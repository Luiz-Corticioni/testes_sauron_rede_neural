"""Escritas autenticadas: o terminal e a web usam os mesmos contratos."""

import re
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings
from inventario.infraestrutura.auditoria import travar_escrita, usar_usuario
from inventario.models import Ativo, Dependencia, HistoricoIncidencia, Incidencia, Sala, Vulnerabilidade
from inventario.aplicacao.operacao import exigir


def sala_exige_autorizacao(sala, tipo):
    return sala.restrita or bool(sala.tipos_permitidos and tipo not in sala.tipos_permitidos)


def sugerir_id(modelo, prefixo, largura):
    """Propõe ID; a reserva efetiva acontece na gravação sob transação."""
    usados = set(modelo.objects.filter(pk__startswith=prefixo).values_list("pk", flat=True))
    n = 1
    while f"{prefixo}{n:0{largura}d}" in usados:
        n += 1
    return f"{prefixo}{n:0{largura}d}"


def proximo_id_vulnerabilidade(categoria):
    if categoria not in dict(Vulnerabilidade.CATEGORIAS):
        raise ValidationError("Categoria de vulnerabilidade inválida.")
    from django.db.models import Max, BigIntegerField
    from django.db.models.functions import Cast, Substr
    prefixo = f"VUL-{categoria}-"
    ultimo = Vulnerabilidade.objects.filter(pk__regex=rf"^{prefixo}[0-9]+$").aggregate(
        ultimo=Max(Cast(Substr("id", len(prefixo)+1), BigIntegerField())))["ultimo"] or 0
    return f"{prefixo}{ultimo+1:04d}"


def proximo_id_sala(codigo):
    if not re.fullmatch(r"[A-Z0-9]{1,6}", codigo):
        raise ValidationError("Código da sala: 1 a 6 letras/números, ex. TI ou LAB.")
    return sugerir_id(Sala, f"SALA-{codigo}-", 3)


def proximo_id_incidencia():
    # Não reutilizar códigos de vínculos excluídos: o histórico conserva suas referências.
    usados = set(Incidencia.objects.values_list("id", flat=True))
    usados.update(HistoricoIncidencia.objects.values_list("incidencia_codigo", flat=True))
    n = 1
    while f"INC-{n:04d}" in usados:
        n += 1
    return f"INC-{n:04d}"


def validar_alocacao(objeto, anterior, usuario):
    mudou = anterior is None or any(
        getattr(objeto, campo) != getattr(anterior, campo)
        for campo in ("sala_id", "alocacao_excepcional_autorizada", "justificativa_excecao")
    )
    if mudou and objeto.alocacao_excepcional_autorizada:
        exigir(usuario, "inventario.autorizar_alocacao_excepcional")
        if not objeto.justificativa_excecao.strip():
            raise ValidationError("Explique o motivo da autorização excepcional.")
        objeto.autorizado_por = usuario
    elif anterior is not None:
        objeto.autorizado_por_id = anterior.autorizado_por_id
    if not objeto.alocacao_excepcional_autorizada:
        objeto.autorizado_por = None
        objeto.justificativa_excecao = ""


def validar_identidade(objeto, anterior):
    if anterior is None:
        return
    campos = {
        Ativo: ("tipo",),
        Incidencia: ("ativo_id", "vulnerabilidade_id"),
        Dependencia: ("dependente_id", "fornecedor_id"),
    }.get(type(objeto), ())
    if any(getattr(objeto, c) != getattr(anterior, c) for c in campos):
        raise ValidationError("Identidade e vínculos não podem mudar. Crie um novo cadastro.")


@transaction.atomic
def salvar_cadastro(objeto, usuario):
    """Valida permissão, trava escritores, valida invariantes e audita uma única gravação."""
    acao = "add" if objeto._state.adding else "change"
    travar_escrita()
    usuario = exigir(usuario, f"inventario.{acao}_{objeto._meta.model_name}")
    anterior = None
    if not objeto._state.adding:
        anterior = type(objeto).objects.get(pk=objeto.pk)
    elif objeto.pk and type(objeto).objects.filter(pk=objeto.pk).exists():
        raise ValidationError("O ID já existe. Use a operação de edição.")
    validar_identidade(objeto, anterior)
    if (
        isinstance(objeto, Incidencia)
        and anterior
        and not usuario.has_perm("inventario.add_incidencia")
    ):
        protegidos = (
            "detectada_em",
            "versao_afetada",
            "software_id",
            "observacoes",
            "prazo_correcao",
            "imune_aprendida",
            "aceita_por_id",
            "justificativa",
            "aceita_ate",
        )
        if any(getattr(objeto, c) != getattr(anterior, c) for c in protegidos):
            raise ValidationError("Este perfil pode alterar apenas o status da incidência.")
    if isinstance(objeto, Sala):
        politica = ("parent_id", "tipos_permitidos", "restrita")
        mudou = anterior is None or any(
            getattr(objeto, c) != getattr(anterior, c) for c in politica
        )
        if mudou:
            exigir(usuario, "inventario.autorizar_alocacao_excepcional")
    if isinstance(objeto, Ativo):
        validar_alocacao(objeto, anterior, usuario)
    if isinstance(objeto, Vulnerabilidade):
        objeto.id = objeto.id.upper()
        if objeto.cvss_versao == "4.0":
            objeto.cvss_v4 = {"baseScore": objeto.cvss, "vectorString": objeto.cvss_vetor, "fonte": objeto.fonte}

        if objeto.cvss_vetor and objeto.cvss_versao == "3.1":
            from inventario.matematica.cvss import CalculadoraCVSS31

            try:
                resultado = CalculadoraCVSS31.calcular(objeto.cvss_vetor)
            except ValueError as erro:
                raise ValidationError({"cvss_vetor": str(erro)}) from erro
            objeto.cvss = resultado.score
            objeto.cvss_vetor = resultado.vetor
            objeto.cvss_versao = "3.1"
        if not re.fullmatch(r"VUL-" + re.escape(objeto.categoria) + r"-\d{4,}", objeto.id):
            raise ValidationError("ID: VUL-CATEGORIA-0001, por exemplo VUL-RCE-0001.")
        try:
            objeto.para_dominio()
        except ValueError as erro:
            raise ValidationError(str(erro)) from erro
    if isinstance(objeto, Incidencia):
        if not objeto.pk:
            objeto.pk = proximo_id_incidencia()
        from inventario.aplicacao.decisoes import mudanca_material
        mudou_decisao = (anterior is None or objeto.status != anterior.status or
                         (objeto.status in ("ACEITA", "CORRIGIDA", "MITIGADA") and
                          mudanca_material(objeto, anterior, objeto.status)))
        if mudou_decisao and (objeto.decisao_pendente or objeto.status) == "ACEITA":
            exigir(usuario, "inventario.aprovar_aceite_risco" if objeto.aprovada_por_id == usuario.pk else "inventario.aceitar_risco")
        if not getattr(objeto, "_decisao_preparada", False) and mudou_decisao:
            from inventario.aplicacao.decisoes import preparar_decisao
            preparar_decisao(objeto, objeto.status, usuario)
    if isinstance(objeto, Dependencia):
        pesos = Dependencia.objects.filter(dependente_id=objeto.dependente_id)
        if anterior:
            pesos = pesos.exclude(pk=anterior.pk)
        soma = sum(pesos.values_list("peso", flat=True)) + objeto.peso
        if soma >= 1 and settings.RISCO_POLITICA == "leontief":
            raise ValidationError(f"Soma da linha seria {soma:.3f}; no cadastro deve ser < 1.")
    with usar_usuario(usuario):
        # Ativo.save gera o ID antes de full_clean; outros models validam campos e vínculos.
        if not isinstance(objeto, Ativo):
            objeto.full_clean()
        objeto.save(force_insert=objeto._state.adding)
    return objeto


@transaction.atomic
def remover_cadastro(objeto, usuario):
    travar_escrita()
    usuario = exigir(usuario, f"inventario.delete_{objeto._meta.model_name}")
    with usar_usuario(usuario):
        return objeto.delete()
