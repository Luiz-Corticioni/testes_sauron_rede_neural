"""Tabela Deployer explícita: sem pesos inventados ou consulta externa."""
from functools import lru_cache
from itertools import product
import hashlib
import json
from pathlib import Path

PONTOS = {"exploitation": ("none", "public poc", "active"), "exposure": ("small", "controlled", "open"),
          "automatable": ("no", "yes"), "human_impact": ("low", "medium", "high", "very high")}
ACOES = {"pending": "Pendente de contexto", "defer": "Adiar com revisão", "scheduled": "Programar",
         "out-of-cycle": "Antecipar manutenção", "immediate": "Agir imediatamente"}


@lru_cache(maxsize=1)
def politica():
    conteudo = Path(__file__).with_name("ssvc_deployer.json").read_bytes()
    dados = json.loads(conteudo)
    tabela = {tuple(r[k] for k in PONTOS): r for r in dados["rows"]}
    if len(dados["rows"]) != 72 or set(tabela) != set(product(*PONTOS.values())) or any(r["decision"] not in ACOES or r["decision"] == "pending" for r in tabela.values()):
        raise ValueError("Tabela SSVC incompleta ou inválida.")
    return dados, tabela, hashlib.sha256(conteudo).hexdigest()


def avaliar(entradas, versao=None):
    dados, tabela, assinatura = politica()
    if versao is not None and versao != dados["id"]:
        raise ValueError("Versão SSVC não suportada.")
    if not isinstance(entradas, dict) or set(entradas) != set(PONTOS):
        raise ValueError("Informe exatamente os quatro pontos de decisão SSVC.")
    if any(v not in ("", None, *PONTOS[k]) for k, v in entradas.items()):
        raise ValueError("Resposta SSVC inválida.")
    faltantes = [k for k, v in entradas.items() if v in ("", None)]
    linha = tabela[tuple(entradas[k] for k in PONTOS)] if not faltantes else None
    acao = linha["decision"] if linha else "pending"
    return {"acao": acao, "rotulo": ACOES[acao], "faltantes": faltantes, "linha": linha["row"] if linha else None,
            "politica": dados["id"], "politica_sha256": assinatura, "fonte": dados["source"],
            "pontos_versoes": dados["decision_points"], "resultado_versao": dados["outcome"]}
