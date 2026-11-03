"""CSV compartilhado, com proteção contra fórmulas ao abrir em planilhas."""

import csv
import io

from inventario.models import Alerta, Ativo, Vulnerabilidade
from inventario.aplicacao.operacao import exigir
from inventario.aplicacao.risco import calcular_risco_banco


def celula_segura(valor):
    texto = "" if valor is None else str(valor)
    if texto.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + texto
    return texto


def relatorio_csv(colecao, usuario):
    permissoes = {
        "ativos": ["view_ativo"],
        "vulnerabilidades": ["view_vulnerabilidade"],
        "alertas": ["view_alerta"],
        "risco": ["view_ativo", "view_vulnerabilidade", "view_incidencia", "view_dependencia"],
    }
    if colecao not in permissoes:
        raise ValueError("Relatório desconhecido.")
    for permissao in permissoes[colecao]:
        exigir(usuario, f"inventario.{permissao}")
    if colecao == "ativos":
        campos = [
            "id",
            "id_numerico",
            "hostname",
            "tipo",
            "nome",
            "fabricante",
            "ip",
            "sala_id",
            "responsavel",
            "contato",
            "criticidade",
            "confidencialidade",
            "integridade",
            "disponibilidade",
            "exposto_internet",
            "zona_rede",
            "status",
        ]
        linhas = Ativo.objects.values_list(*campos)
    elif colecao == "vulnerabilidades":
        campos = [
            "id",
            "cve_id",
            "descricao",
            "cvss",
            "kev",
            "kev_adicionada_em",
            "kev_prazo",
            "uso_ransomware",
        ]
        linhas = Vulnerabilidade.objects.values_list(*campos)
    elif colecao == "alertas":
        campos = [
            "id",
            "tipo",
            "severidade",
            "ativo_id",
            "mensagem",
            "criado_em",
            "reconhecido_por_id",
            "reconhecido_em",
        ]
        linhas = Alerta.objects.values_list(*campos)
    else:
        r = calcular_risco_banco(perfil="puro")
        campos = ["ativo_id", "risco_proprio", "risco_efetivo", "risco_relatorio", "indice"]
        linhas = zip(
            *(
                r[chave]
                for chave in [
                    "ids_ativos",
                    "risco_proprio",
                    "risco_efetivo",
                    "risco_relatorio",
                    "indices",
                ]
            )
        )
    arquivo = io.StringIO()
    escritor = csv.writer(arquivo)
    escritor.writerow(campos)
    for linha in linhas:
        escritor.writerow([celula_segura(c) for c in linha])
    return "\ufeff" + arquivo.getvalue()
