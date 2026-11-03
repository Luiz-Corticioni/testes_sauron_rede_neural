"""Importação de novos ativos: validar o lote inteiro antes de qualquer gravação."""

import csv
import io
import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from inventario.infraestrutura.auditoria import travar_escrita, usar_usuario
from inventario.models import Ativo, Sala
from inventario.aplicacao.operacao import exigir

OBRIGATORIOS = {"tipo", "nome", "fabricante", "sala", "responsavel"}
OPCIONAIS = {
    "ip",
    "contato",
    "criticidade",
    "confidencialidade",
    "integridade",
    "disponibilidade",
    "exposto_internet",
    "zona_rede",
    "portas_servicos",
}
INTEIROS = {"criticidade", "confidencialidade", "integridade", "disponibilidade"}
MAX_BYTES = 1024 * 1024
MAX_LINHAS = 500


def ler_linhas(texto):
    if len(texto.encode("utf-8")) > MAX_BYTES:
        raise ValueError("CSV excede 1 MB.")
    leitor = csv.DictReader(io.StringIO(texto.lstrip("\ufeff")))
    campos = leitor.fieldnames or []
    if len(campos) != len(set(campos)) or not OBRIGATORIOS.issubset(campos):
        raise ValueError("Cabeçalho exige: tipo,nome,fabricante,sala,responsavel.")
    if set(campos) - OBRIGATORIOS - OPCIONAIS:
        raise ValueError("Colunas não permitidas no CSV. Consulte o modelo fornecido.")
    linhas = []
    for row in leitor:
        if len(linhas) >= MAX_LINHAS:
            raise ValueError("Importe no máximo 500 linhas por lote.")
        linhas.append((leitor.line_num, row))
    if not linhas:
        raise ValueError("CSV sem registros.")
    return linhas


def preparar_ativo(row):
    if None in row or any(valor is None for valor in row.values()):
        raise ValueError("Quantidade de colunas diferente do cabeçalho.")
    dados = {campo: valor.strip() for campo, valor in row.items() if valor.strip()}
    sala_id = dados.pop("sala", "")
    try:
        dados["sala"] = Sala.objects.get(pk=sala_id)
    except Sala.DoesNotExist as erro:
        raise ValueError(f"Sala inexistente: {sala_id}.") from erro
    for campo in INTEIROS & dados.keys():
        dados[campo] = int(dados[campo])
    if "exposto_internet" in dados:
        if dados["exposto_internet"].lower() not in {"true", "false", "1", "0"}:
            raise ValueError("exposto_internet: use true/false ou 1/0.")
        dados["exposto_internet"] = dados["exposto_internet"].lower() in {"true", "1"}
    if "portas_servicos" in dados:
        dados["portas_servicos"] = json.loads(dados["portas_servicos"])
    obj = Ativo(**dados)
    obj.full_clean(exclude=["id", "hostname"])
    return obj


def validar_lote(linhas):
    objetos, erros, ips = [], [], set()
    for numero, row in linhas:
        try:
            obj = preparar_ativo(row)
            if obj.ip and obj.ip in ips:
                raise ValueError("IP repetido dentro do lote.")
            ips.add(obj.ip)
            objetos.append((numero, obj))
        except (ValueError, TypeError, ValidationError) as erro:
            mensagem = "; ".join(erro.messages) if isinstance(erro, ValidationError) else str(erro)
            erros.append({"linha": numero, "mensagem": mensagem})
    return objetos, erros


def importar_csv(texto, usuario, dry_run=True):
    usuario = exigir(usuario, "inventario.add_ativo")
    resultado = {"dry_run": dry_run, "validos": 0, "gravados": 0, "erros": []}
    try:
        linhas = ler_linhas(texto)
        objetos, resultado["erros"] = validar_lote(linhas)
        resultado["validos"] = len(objetos)
        if dry_run or resultado["erros"]:
            return resultado
        with transaction.atomic(), usar_usuario(usuario):
            travar_escrita()
            usuario = exigir(usuario, "inventario.add_ativo")
            # Revalida sob lock: o banco pode ter mudado depois da prévia.
            objetos, erros = validar_lote(linhas)
            if erros:
                resultado["erros"] = erros
                return resultado
            for numero, obj in objetos:
                obj.save()
        resultado["gravados"] = len(objetos)
    except (ValueError, csv.Error, ValidationError, IntegrityError) as erro:
        resultado["erros"].append({"linha": locals().get("numero", 1), "mensagem": str(erro)})
    return resultado
