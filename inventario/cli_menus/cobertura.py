"""Cobertura no terminal, pelos mesmos contratos da web."""
from datetime import date
import json
from inventario.aplicacao.cobertura import LEITURA, analisar_cobertura, salvar_perimetro, preparar_revisao, registrar_revisao
from inventario.models import PerimetroRelacoes


def cobertura(cli):
    if not all(cli._exigir(p) for p in LEITURA):
        return
    for p in PerimetroRelacoes.objects.all()[:25]:
        cli.saida(f"#{p.pk} {p.nome}")
    acao = cli._texto("1 Consultar | 2 Declarar perímetro | 3 Editar perímetro | 4 Revisar ativo | 0 Voltar")
    if acao == "0":
        return
    if acao in ("2", "3"):
        perm = f"inventario.{'add' if acao == '2' else 'change'}_perimetrorelacoes"
        if not cli._exigir(perm):
            return
        p = PerimetroRelacoes.objects.get(pk=cli._inteiro("ID do perímetro")) if acao == "3" else None
        versao = p.atualizado_em.isoformat() if p else None
        nome = p.nome if p else cli._texto("Nome exato do escopo")
        descricao = cli._texto("Descrição do perímetro", padrao=p.descricao if p else None)
        cli.saida("Membros atuais: "+", ".join(p.membros.values_list("ativo_id", flat=True)) if p else "Informe códigos reais do inventário.")
        texto = cli._texto("Códigos separados por vírgula (vazio: perímetro vazio)", permitir_vazio=True)
        ativos = [a.strip() for a in texto.split(",")] if texto.strip() else []
        if cli._confirmar("Salvar perímetro? Os grafos deste escopo usarão apenas seus membros operacionais."):
            if all(cli._exigir(v) for v in (*LEITURA, perm)):
                cli.saida(f"Perímetro #{salvar_perimetro(cli.usuario, nome, descricao, ativos, p.pk if p else None, versao).pk} salvo.")
        return
    if acao not in ("1", "4"):
        raise ValueError("Opção inválida.")
    perimetro = cli._inteiro("ID do perímetro")
    tipo = cli._texto("REDE, IDENTIDADE ou NEGOCIO").upper()
    principal = cli._texto("Identidade exata") if tipo == "IDENTIDADE" else ""
    if acao == "1":
        if all(cli._exigir(v) for v in LEITURA):
            cli.saida(json.dumps(analisar_cobertura(cli.usuario, perimetro, tipo, principal), ensure_ascii=False, indent=2, default=str))
        return
    perm = "inventario.add_revisaocobertura"
    if not cli._exigir(perm):
        return
    ativo = cli._ativo().pk
    _, resumo = preparar_revisao(cli.usuario, perimetro, tipo, ativo, principal)
    cli.saida(json.dumps(resumo, ensure_ascii=False))
    resultado = cli._texto("REVISADO, SEM_RELACOES ou LACUNAS").upper()
    evidencia = cli._texto("Verificação e limitações; sem credenciais")
    observada = date.fromisoformat(cli._texto("Observada em AAAA-MM-DD"))
    revisar = date.fromisoformat(cli._texto("Revisar em AAAA-MM-DD"))
    if cli._confirmar("Registrar revisão histórica?"):
        if all(cli._exigir(v) for v in (*LEITURA, perm)):
            r = registrar_revisao(cli.usuario, perimetro, tipo, ativo, principal, resultado, evidencia, observada, revisar, resumo["sha256"])
            cli.saida(f"Revisão #{r.pk} registrada.")
