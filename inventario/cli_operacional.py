"""Operações da Fase 4 sem inicializar um servidor web."""

from __future__ import annotations
from inventario.aplicacao.servicos import salvar_cadastro, remover_cadastro

import json
from pathlib import Path

from inventario.infraestrutura.backup import backup_sqlite
from inventario.infraestrutura.importacao import MAX_BYTES, importar_csv
from inventario.models import Alerta, Software
from inventario.aplicacao.servicos import calcular_mttr, reconhecer_alerta
from inventario.infraestrutura.relatorios import relatorio_csv
from inventario.aplicacao.rotinas import executar_rotinas


def software(cli):
    if not cli._exigir("inventario.view_software"):
        return
    cli._tabela(
        ["ID", "Ativo", "Nome", "Versão", "Fornecedor"],
        list(Software.objects.values_list("id", "ativo_id", "nome", "versao", "fornecedor")),
    )
    acao = cli._texto("1 Cadastrar | 2 Editar | 3 Remover | 0 Voltar")
    if acao == "0":
        return
    perm = {"1": "add", "2": "change", "3": "delete"}.get(acao)
    if not perm or not cli._exigir(f"inventario.{perm}_software"):
        return
    obj = Software() if acao == "1" else Software.objects.get(pk=cli._inteiro("ID do software"))
    if acao == "3":
        if cli._confirmar("Remover software? As incidências existentes ficam para revisão."):
            remover_cadastro(obj, cli.usuario)
        return
    obj.ativo = cli._ativo(padrao=obj.ativo_id)
    obj.nome = cli._texto("Nome", padrao=obj.nome or None)
    obj.versao = cli._texto("Versão", padrao=obj.versao or None)
    obj.fornecedor = cli._texto("Fornecedor", padrao=obj.fornecedor or None)
    cli.saida("CPE: cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*")
    obj.cpe23 = cli._texto("CPE 2.3 (opcional)", permitir_vazio=True, padrao=obj.cpe23 or None)
    salvar_cadastro(obj, cli.usuario)
    cli._ok("Software salvo; sugestões só entram no risco quando confirmadas.")


def classificacao(cli):
    if not cli._exigir("inventario.change_ativo"):
        return
    a = cli._ativo()
    cli.saida("Classificações: 1 baixo, 2 médio, 3 alto, 4 crítico.")
    for campo in ("confidencialidade", "integridade", "disponibilidade"):
        setattr(a, campo, cli._inteiro(campo, 1, 4, padrao=getattr(a, campo)))
    a.responsavel = cli._texto("Responsável", permitir_vazio=True, padrao=a.responsavel or None)
    a.contato = cli._texto("E-mail do custodiante", permitir_vazio=True, padrao=a.contato or None)
    a.exposto_internet = cli._confirmar("Exposto à internet?")
    a.zona_rede = cli._texto("Zona de rede", permitir_vazio=True, padrao=a.zona_rede or None)
    cli.saida('Portas: [{"porta":443,"protocolo":"tcp","servico":"https"}]')
    a.portas_servicos = json.loads(cli._texto("Lista JSON de portas", padrao="[]"))
    salvar_cadastro(a, cli.usuario)
    cli._ok("Classificação salva.")


def alertas(cli):
    if not cli._exigir("inventario.view_alerta"):
        return
    cli._tabela(
        ["ID", "Tipo", "Nível", "Ativo", "Mensagem"],
        list(
            Alerta.objects.filter(reconhecido_em__isnull=True).values_list(
                "id", "tipo", "severidade", "ativo_id", "mensagem"
            )
        ),
    )
    cli.saida(f"MTTR: {calcular_mttr()}")
    pk = cli._texto("ID para reconhecer (Enter para voltar)", permitir_vazio=True)
    if pk:
        reconhecer_alerta(int(pk), cli.usuario)
        cli._ok("Ciência registrada; a causa deve ser corrigida separadamente.")


def rotinas(cli):
    if not cli._exigir("auth.change_user") or not cli.usuario.is_superuser:
        cli._falha("Rotinas globais exigem superusuário.")
        return
    sem_rede = not cli._confirmar("Autorizar consultas CISA/NVD nesta execução?")
    if not cli._exigir("auth.change_user", interativo=False) or not cli.usuario.is_superuser:
        return
    cli.saida(json.dumps(executar_rotinas(sem_rede), ensure_ascii=False, indent=2))


def importar(cli):
    if not cli._exigir("inventario.add_ativo"):
        return
    caminho = Path(cli._texto("Caminho do CSV").strip('"'))
    if caminho.stat().st_size > MAX_BYTES:
        raise ValueError("CSV excede 1 MB.")
    texto = caminho.read_text(encoding="utf-8-sig")
    previa = importar_csv(texto, cli.usuario, dry_run=True)
    cli.saida(json.dumps(previa, ensure_ascii=False, indent=2))
    if not previa["erros"] and cli._confirmar("Gravar o lote validado?"):
        cli.saida(
            json.dumps(
                importar_csv(texto, cli.usuario, dry_run=False), ensure_ascii=False, indent=2
            )
        )


def backup(cli):
    if not cli._exigir("auth.change_user") or not cli.usuario.is_superuser:
        cli._falha("Backup completo exige superusuário.")
        return
    cli._ok(f"Backup criado: {backup_sqlite()}")


def exportar(cli):
    colecao = cli._texto("Coleção: ativos, vulnerabilidades, risco ou alertas").lower()
    permissao = {
        "ativos": "view_ativo",
        "vulnerabilidades": "view_vulnerabilidade",
        "risco": "view_ativo",
        "alertas": "view_alerta",
    }.get(colecao)
    if not permissao:
        raise ValueError("Relatório desconhecido.")
    if not cli._exigir(f"inventario.{permissao}"):
        return
    texto = relatorio_csv(colecao, cli.usuario)
    caminho = Path(cli._texto("Caminho de saída CSV").strip('"'))
    if caminho.exists() and not cli._confirmar("Sobrescrever o CSV existente?"):
        return
    if not cli._exigir(f"inventario.{permissao}", interativo=False):
        return
    caminho.write_text(texto, encoding="utf-8")
    cli._ok(f"Relatório salvo: {caminho}")


from inventario.cli_menus.comum import menu_seguro
from inventario.cli_menus.relacoes import relacoes


@menu_seguro()
def menu_operacional(cli):
    acoes = {
        "1": software,
        "2": classificacao,
        "3": alertas,
        "4": rotinas,
        "5": importar,
        "6": backup,
        "7": exportar,
        "8": documentos,
        "9": relacoes,
    }
    itens = [
        ("1", "Software: listar/cadastrar/editar/remover"),
        ("2", "Classificar ativo"),
        ("3", "Alertas, reconhecimento e MTTR"),
        ("4", "Executar rotinas"),
        ("5", "Importar CSV com prévia"),
        ("6", "Backup consistente"),
        ("7", "Exportar CSV por coleção"),
        ("8", "Documentos SBOM/VEX"),
        ("9", "Relações de rede, identidade e negócio"),
    ]
    while True:
        opcao = cli._submenu("INVENTÁRIO OPERACIONAL", itens)
        if opcao == "0":
            return
        acao = acoes.get(opcao)
        if acao:
            acao(cli)
            cli._pausa()
        else:
            cli._falha("Opção inválida.")


def documentos(cli):
    from inventario.aplicacao.documentos import LEITURA, ESCRITA, importar, reconciliar
    from inventario.dominio.documentos import MAX_BYTES
    from inventario.models import DocumentoInventario
    for permissao in LEITURA:
        if not cli._exigir(permissao):
            return
    ativo = cli._ativo()
    for doc in DocumentoInventario.objects.filter(ativo=ativo).defer("conteudo")[:10]:
        cli.saida(f"#{doc.pk} {doc.tipo} · {doc.escopo} · {doc.origem}")
    acao = cli._texto("1 Importar JSON | 2 Reconciliar documento | 0 Voltar")
    if acao == "0":
        return
    for permissao in ESCRITA:
        if not cli._exigir(permissao):
            return
    if acao == "2":
        doc = DocumentoInventario.objects.get(pk=cli._inteiro("ID do documento"), ativo=ativo)
        for permissao in ESCRITA:
            if not cli._exigir(permissao):
                return
        cli.saida(f"Achados vinculados: {reconciliar(doc, cli.usuario)}")
    elif acao == "1":
        caminho = Path(cli._texto("Arquivo JSON").strip('"'))
        if caminho.stat().st_size > MAX_BYTES:
            raise ValueError("Arquivo excede 2 MB.")
        with caminho.open("rb") as arquivo:
            conteudo = arquivo.read(MAX_BYTES+1)
        escopo, origem = cli._texto("Aplicação/implantação"), cli._texto("Origem declarada")
        cli.saida(json.dumps(importar(ativo.pk, conteudo, cli.usuario, escopo, origem), ensure_ascii=False))
        if cli._confirmar("Gravar documento validado?"):
            for permissao in ESCRITA:
                if not cli._exigir(permissao):
                    return
            cli.saida(json.dumps(importar(ativo.pk, conteudo, cli.usuario, escopo, origem, aplicar=True), ensure_ascii=False))
    else:
        cli._falha("Opção inválida.")
