"""Comparação de registros persistidos; não reconstitui informações ausentes."""
from inventario.models import SnapshotRisco

PERMISSOES = ("inventario.view_ativo", "inventario.view_vulnerabilidade", "inventario.view_incidencia",
              "inventario.view_dependencia", "inventario.view_snapshotrisco", "inventario.view_historicoincidencia")


def mudancas():
    registros = list(SnapshotRisco.objects.filter(perfil="puro").order_by("-ts", "-pk")[:2])
    if len(registros) < 2:
        return {"disponivel": False, "motivo": "São necessários dois snapshots do perfil puro."}
    atual, anterior = registros
    resultado = {"disponivel": True, "perfil": "puro", "anterior": anterior.ts.isoformat(),
                 "atual": atual.ts.isoformat(), "risco_anterior": anterior.risco_total,
                 "risco_atual": atual.risco_total, "variacao_risco": atual.risco_total - anterior.risco_total,
                 "contem_simulacao": anterior.chave.startswith("DEMO-") or atual.chave.startswith("DEMO-"),
                 "top": None, "backlog": None, "mttr": None}
    a, b = anterior.detalhes, atual.detalhes
    def valido(item):
        return (isinstance(item, dict) and item.get("versao") == 1
                and isinstance(item.get("top_vulnerabilidades"), list)
                and all(isinstance(x, str) for x in item["top_vulnerabilidades"])
                and type(item.get("backlog_vencido")) is int and item["backlog_vencido"] >= 0
                and isinstance(item.get("mttr"), dict)
                and {"dias", "correcoes"} <= item["mttr"].keys())
    if valido(a) and valido(b):
        velhos, novos = a["top_vulnerabilidades"], b["top_vulnerabilidades"]
        resultado["top"] = {"limite": 10, "entraram": [x for x in novos if x not in velhos],
                            "sairam": [x for x in velhos if x not in novos]}
        resultado["backlog"] = {"anterior": a["backlog_vencido"], "atual": b["backlog_vencido"]}
        resultado["mttr"] = {"anterior": a["mttr"], "atual": b["mttr"]}
    return resultado
