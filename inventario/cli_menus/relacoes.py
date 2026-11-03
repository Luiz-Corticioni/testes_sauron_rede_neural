"""Terminal usa a mesma autorização, validação e análise da web."""
from datetime import date
import json
from inventario.aplicacao.relacoes import LEITURA, analisar_relacoes, salvar_relacao
from inventario.models import RelacaoAtivos


def relacoes(cli):
    if not all(cli._exigir(p) for p in LEITURA):
        return
    acao = cli._texto("1 Listar | 2 Analisar | 3 Cadastrar | 4 Editar/revogar | 5 Qualidade/cobertura | 0 Voltar")
    if acao == "0":
        return
    if acao == "5":
        from inventario.cli_menus.cobertura import cobertura
        cobertura(cli)
        return
    if acao == "1":
        for r in RelacaoAtivos.objects.all()[:25]:
            cli.saida(f"#{r.pk} {r} · revisar {r.revisar_em} · vigente={r.vigente}")
        cli.saida("Até 25 relações exibidas; a lista web possui paginação e evidências completas.")
        return
    if acao == "2":
        analisar(cli)
        return
    if acao not in ("3", "4"):
        raise ValueError("Opção inválida.")
    permissao = f"inventario.{'add' if acao == '3' else 'change'}_relacaoativos"
    if not cli._exigir(permissao):
        return
    r = RelacaoAtivos.objects.get(pk=cli._inteiro("ID da relação")) if acao == "4" else None
    versao = r.atualizado_em.isoformat() if r else None
    def texto(campo, rotulo, opcional=False):
        return cli._texto(rotulo, permitir_vazio=opcional, padrao=str(getattr(r, campo)) if r and getattr(r, campo) else None)
    cli.saida("Origem → destino. Rede: emissor → receptor. Identidade: ponto de uso → recurso. Negócio: fornecedor → consumidor.")
    dados = {"origem_id": cli._ativo(padrao=r.origem_id if r else None).pk,
             "destino_id": cli._ativo(padrao=r.destino_id if r else None).pk,
             "tipo": texto("tipo", "REDE, IDENTIDADE ou NEGOCIO").upper(),
             "escopo": texto("escopo", "Escopo exato"), "protocolo": "", "porta": 0, "principal": "", "privilegio": ""}
    if dados["tipo"] == "REDE":
        dados["protocolo"] = texto("protocolo", "tcp, udp ou icmp").lower()
        if dados["protocolo"] in ("tcp", "udp"):
            dados["porta"] = cli._inteiro("Porta destino", 1, 65535, padrao=r.porta if r else None)
    elif dados["tipo"] == "IDENTIDADE":
        dados["principal"] = texto("principal", "Identidade externa (sem credenciais)")
        dados["privilegio"] = texto("privilegio", "LEITURA, EXECUCAO ou ADMIN").upper()
    dados.update(fonte=texto("fonte", "Fonte"), evidencia=texto("evidencia", "Evidência ou referência verificável"),
                 observada_em=date.fromisoformat(texto("observada_em", "Data observada AAAA-MM-DD")),
                 revisar_em=date.fromisoformat(texto("revisar_em", "Revisar em AAAA-MM-DD")),
                 vigente=cli._confirmar("Relação vigente? Não para revogar preservando o cadastro."))
    if cli._confirmar("Salvar relação com auditoria?"):
        if all(cli._exigir(p) for p in (*LEITURA, permissao)):
            cli.saida(f"Relação #{salvar_relacao(dados, cli.usuario, r.pk if r else None, versao).pk} salva.")


def analisar(cli):
    if not all(cli._exigir(p) for p in LEITURA):
        return
    tipo = cli._texto("REDE, IDENTIDADE ou NEGOCIO").upper()
    escopo = cli._texto("Escopo exato")
    principal = cli._texto("Identidade exata") if tipo == "IDENTIDADE" else ""
    origem = cli._ativo().pk
    destino = cli._texto("Código do destino (Enter: todos)", permitir_vazio=True) or None
    retirada = cli._texto("ID da relação a retirar na simulação (Enter: nenhuma)", permitir_vazio=True)
    ativo = cli._texto("Código do ativo a retirar na simulação (Enter: nenhum)", permitir_vazio=True) or None
    if all(cli._exigir(p) for p in LEITURA):
        resultado = analisar_relacoes(cli.usuario, tipo, escopo, origem, destino, principal,
                                     int(retirada) if retirada else None, ativo)
        cli.saida(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
