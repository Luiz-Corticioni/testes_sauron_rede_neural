"""Relacionamentos e indicadores da ficha, respeitando permissões individuais."""

from inventario.models import Dependencia
from inventario.aplicacao.servicos import calcular_risco_banco
from inventario.web.visualizacao import indicadores

PERMISSOES = tuple(
    f"inventario.view_{nome}" for nome in ("ativo", "vulnerabilidade", "incidencia", "dependencia")
)


def barras_ativos(ativos, usuario):
    dados, erro = {}, None
    if usuario.has_perms(PERMISSOES):
        try:
            dados = indicadores(calcular_risco_banco(perfil="puro"))
        except ValueError as exc:
            erro = str(exc)
    for ativo in ativos:
        ativo.indicador = dados.get(ativo.pk)
    return erro


def ficha_ativo(ativo, usuario):
    contexto = {"ativo": ativo}
    from inventario.aplicacao.procedencia import evidencias_ativo
    contexto['procedencia'] = evidencias_ativo(ativo, usuario)
    from inventario.aplicacao.qualidade_dados import PERMISSOES as PERMISSOES_QUALIDADE, qualidade_ativo
    if usuario.has_perms(PERMISSOES_QUALIDADE):
        contexto["qualidade"] = qualidade_ativo(usuario, ativo.pk)
        contexto["perimetros_qualidade"] = ativo.perimetros_declarados.select_related("perimetro").order_by("perimetro__nome")[:100]
    if usuario.has_perm("inventario.view_incidencia") and usuario.has_perm(
        "inventario.view_vulnerabilidade"
    ):
        contexto["incidencias"] = ativo.incidencia_set.select_related("vulnerabilidade")
    for permissao, relacao, destino in (
        ("software", "softwares", "softwares"),
        ("certificadodigital", "certificados", "certificados"),
        ("incidente", "incidentes", "incidentes"),
    ):
        if usuario.has_perm(f"inventario.view_{permissao}"):
            contexto[destino] = (
                getattr(ativo, relacao)
                .all()
                .order_by("-aberto_em" if destino == "incidentes" else "-pk")
            )
    if usuario.has_perm("inventario.view_dependencia"):
        contexto["entradas"] = Dependencia.objects.filter(dependente=ativo).select_related(
            "fornecedor"
        )
        contexto["saidas"] = Dependencia.objects.filter(fornecedor=ativo).select_related(
            "dependente"
        )
    contexto["erro_risco"] = barras_ativos([ativo], usuario)
    return contexto
