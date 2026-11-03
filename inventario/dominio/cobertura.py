"""Medidas com denominadores explícitos, sem nota composta de segurança."""
from collections import Counter
import hashlib
import json

MOTIVOS = ("ELEGIVEL", "REVOGADA", "OBSERVACAO_FUTURA", "VENCIDA", "ATIVO_INATIVO", "FORA_PERIMETRO")
ESTADOS = ("SEM_REVISAO", "CONTEXTO_ALTERADO", "REVISAO_VENCIDA", "LACUNAS", "REVISADO", "SEM_RELACOES")
ROTULOS = {"SEM_REVISAO": "Sem revisão registrada", "CONTEXTO_ALTERADO": "Contexto mudou: revisar novamente",
           "REVISAO_VENCIDA": "Prazo de revisão vencido", "LACUNAS": "Revisão com lacunas conhecidas",
           "REVISADO": "Relações revisadas no prazo", "SEM_RELACOES": "Ausência de vínculos declarada",
           "ELEGIVEL": "No prazo e dentro do recorte", "REVOGADA": "Vínculo revogado",
           "OBSERVACAO_FUTURA": "Data de observação futura", "VENCIDA": "Revisão do vínculo vencida",
           "ATIVO_INATIVO": "Ativo inativo ou baixado", "FORA_PERIMETRO": "Endpoint fora do perímetro"}


def motivo(r, ids, hoje):
    if not r["vigente"]:
        return "REVOGADA"
    if r["observada_em"] > hoje:
        return "OBSERVACAO_FUTURA"
    if r["revisar_em"] <= hoje:
        return "VENCIDA"
    if any(r.get(c) in ("INATIVO", "BAIXADO") for c in ("origem__status", "destino__status")):
        return "ATIVO_INATIVO"
    if r["origem_id"] not in ids or r["destino_id"] not in ids:
        return "FORA_PERIMETRO"
    return "ELEGIVEL"


def contextos(ativos, linhas, perimetro_id, hoje, tipo, principal, definicao=None):
    ids = {a["id"] for a in ativos}
    resumos = {a["id"]: {"ativo": a["id"], "contagens": dict.fromkeys(MOTIVOS, 0), "vigentes": 0,
                         "hash": hashlib.sha256(json.dumps({"perimetro": perimetro_id, "definicao": definicao, "ativo": a, "tipo": tipo, "principal": principal}, sort_keys=True).encode())} for a in ativos}
    motivos = Counter(dict.fromkeys(MOTIVOS, 0))
    for r in linhas:
        razao = motivo(r, ids, hoje)
        motivos[razao] += 1
        canonico = json.dumps({"relacao": r, "motivo": razao}, sort_keys=True, ensure_ascii=False, default=str).encode()+b"\n"
        for ativo in (r["origem_id"], r["destino_id"]):
            if ativo in resumos:
                resumo = resumos[ativo]
                resumo["hash"].update(canonico)
                resumo["contagens"][razao] += 1
                resumo["vigentes"] += int(r["vigente"])
    for resumo in resumos.values():
        resumo["sha256"] = resumo.pop("hash").hexdigest()
        resumo["pendentes"] = resumo["vigentes"] - resumo["contagens"]["ELEGIVEL"]
    return resumos, dict(motivos)


def estado(revisao, contexto, hoje):
    if revisao is None:
        return "SEM_REVISAO"
    if revisao["contexto_sha256"] != contexto["sha256"]:
        return "CONTEXTO_ALTERADO"
    if revisao["revisar_em"] <= hoje:
        return "REVISAO_VENCIDA"
    return revisao["resultado"]


def percentual(parte, total):
    return round(100*parte/total, 2) if total else None
