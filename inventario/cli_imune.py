"""Revisão humana e curva de memória pelo terminal."""

from __future__ import annotations
from inventario.aplicacao.servicos import salvar_cadastro

from django.conf import settings
from inventario.cli_menus.comum import menu_seguro
from inventario.aplicacao.imune import decidir_sugestao, executar_ciclo
from inventario.models import Anticorpo, SugestaoImune, Tolerancia


def listar(cli):
    cli._tabela(
        ["ID", "Ativo", "Falha", "Afinidade", "Estado", "Sinais"],
        [
            [
                s.pk,
                s.ativo_id,
                s.vulnerabilidade_id,
                f"{s.afinidade:.1%}",
                s.estado,
                ",".join(s.sinais) or "sem sinal 2",
            ]
            for s in SugestaoImune.objects.filter(estado__in=["PENDENTE", "OBSERVACAO"])
        ],
    )
    cli.saida(
        f"Limiar de afinidade: {settings.IMUNE_LIMIAR:.0%}; "
        f"risco alto: {settings.IMUNE_LIMIAR_RISCO:g} pontos do perfil puro."
    )


def decidir(cli, confirmar):
    if not cli._exigir("inventario.decidir_sugestao_imune"):
        return
    listar(cli)
    pk = cli._inteiro("ID da sugestão", 1)
    motivo, validade = "", None
    if confirmar:
        if not cli._confirmar("Verificou a aplicabilidade? Confirmar vínculo real?"):
            return
    else:
        motivo = cli._texto("Motivo da rejeição")
        validade = cli._data("Tolerância válida até", False)
    decidir_sugestao(pk, confirmar, cli.usuario, motivo, validade)
    cli._ok("Decisão e autoria registradas.")


def memoria(cli):
    cli._tabela(
        ["ID", "Vulnerabilidade", "Força inicial", "Estado", "Conf.", "Rej."],
        list(
            Anticorpo.objects.values_list(
                "id", "vulnerabilidade_id", "forca", "estado", "confirmacoes", "rejeicoes"
            )
        ),
    )
    pk = cli._texto("ID para curva de decaimento (Enter para voltar)", permitir_vazio=True)
    if pk:
        a = Anticorpo.objects.get(pk=int(pk))
        dias = cli._decimal("Dias desde o último reforço", 0)
        cli.saida(str(a.para_dominio().curva(dias, settings.IMUNE_MEIA_VIDA_DIAS)))
        cli.saida("F(t)=F0*exp(-ln(2)*t/meia_vida); derivada central do Modo Euler.")
    cli._tabela(
        ["Ativo", "Até", "Motivo"],
        list(Tolerancia.objects.values_list("ativo_id", "valida_ate", "motivo")),
    )


def linha_base(cli):
    if not cli._exigir("inventario.declarar_linha_base_saudavel"):
        return
    a = cli._ativo()
    cli.saida("Esta declaração exige verificação humana; ausência de falha não prova saúde.")
    a.linha_base_saudavel = cli._confirmar("Declarar como linha de base saudável?")
    if a.linha_base_saudavel:
        a.evidencia_scan = cli._texto("Evidência/ID do scan")
    salvar_cadastro(a, cli.usuario)
    cli._ok("Declaração registrada; execute o ciclo para reavaliar as recomendações.")


@menu_seguro("view_sugestaoimune")
def menu_imune(cli):
    acoes = {
        "1": lambda: listar(cli),
        "2": lambda: cli.saida(str(executar_ciclo())),
        "3": lambda: decidir(cli, True),
        "4": lambda: decidir(cli, False),
        "5": lambda: memoria(cli),
        "6": lambda: linha_base(cli),
    }
    itens = [
        ("1", "Sugestões e observações"),
        ("2", "Executar ciclo local"),
        ("3", "Confirmar sugestão"),
        ("4", "Rejeitar com validade"),
        ("5", "Memória, tolerâncias e decaimento Euler"),
        ("6", "Declarar linha de base"),
    ]
    while True:
        op = cli._submenu("SISTEMA IMUNE DE VULNERABILIDADES", itens)
        if op == "0":
            return
        if op == "2" and not cli._exigir("inventario.change_incidencia"):
            continue
        acoes.get(op, lambda: cli._falha("Opção inválida."))()
        cli._pausa()
