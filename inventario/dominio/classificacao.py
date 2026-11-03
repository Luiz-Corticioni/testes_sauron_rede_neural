"""Validações pequenas e puras dos metadados de inventário."""

import re


def validar_cpe(texto):
    # Aceita a forma básica e escapes CPE. Não substitui validação no dicionário NVD.
    partes = re.split(r"(?<!\\):", texto)
    if len(partes) != 13 or partes[:2] != ["cpe", "2.3"] or partes[2] not in {"a", "h", "o"}:
        raise ValueError("Use CPE 2.3, ex.: cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*")
    if any(not p or re.search(r"[\s\x00-\x1f]", p) for p in partes):
        raise ValueError("Componentes CPE não podem estar vazios ou conter espaços.")
    if any(p in {"*", "-"} or "*" in p or "?" in p for p in partes[3:6]):
        raise ValueError("Informe fabricante, produto e versão exatos no CPE.")


def validar_portas(itens):
    if not isinstance(itens, list) or len(itens) > 256:
        raise ValueError("Portas/serviços devem ser uma lista com até 256 objetos.")
    for item in itens:
        if not isinstance(item, dict) or set(item) - {"porta", "protocolo", "servico"}:
            raise ValueError('Use objetos: {"porta":443,"protocolo":"tcp","servico":"https"}.')
        porta = item.get("porta")
        if type(porta) is not int or not 1 <= porta <= 65535:
            raise ValueError("Porta deve ser um inteiro de 1 a 65535.")
        if item.get("protocolo") not in {"tcp", "udp"}:
            raise ValueError("Protocolo deve ser tcp ou udp.")
        if not isinstance(item.get("servico", ""), str) or len(item.get("servico", "")) > 80:
            raise ValueError("Serviço deve ser texto de até 80 caracteres.")
