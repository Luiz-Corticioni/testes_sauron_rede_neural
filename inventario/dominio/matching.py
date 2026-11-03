"""CPE + faixas determinísticas; None significa informação insuficiente."""
import re


def tokens(versao):
    if not isinstance(versao, str) or len(versao) > 200 or versao in ("", "*", "-"):
        raise ValueError("Versão desconhecida ou inválida.")
    partes = re.findall(r"[0-9]+|[a-z]+", re.sub(r"^v(?=\d)", "", versao.lower()))
    if not partes:
        raise ValueError("Versão sem tokens comparáveis.")
    return [int(p) if p.isdigit() else p for p in partes]


def comparar_versoes(a, b):
    x, y = tokens(a), tokens(b)
    for esquerdo, direito in zip(x,y):
        if esquerdo == direito:
            continue
        if type(esquerdo) is not type(direito):
            return 1 if isinstance(esquerdo,int) else -1
        return 1 if esquerdo > direito else -1
    resto = x[len(y):] if len(x)>len(y) else y[len(x):]
    if not resto or all(v==0 for v in resto):
        return 0
    while resto and resto[0] == 0:
        resto = resto[1:]
    sinal = -1 if isinstance(resto[0],str) else 1
    return sinal if len(x)>len(y) else -sinal


def identidade(cpe):
    partes = re.split(r"(?<!\\):", cpe.lower())
    if len(partes) != 13 or partes[:2] != ["cpe","2.3"]:
        raise ValueError("CPE 2.3 inválido.")
    return tuple(partes[2:5]), partes[5]


def extrair_faixas(cve):
    resultado = []
    def percorrer(no, complexo=False):
        if not isinstance(no,dict):
            return
        complexo = complexo or no.get("operator")=="AND" or bool(no.get("negate"))
        for item in no.get("cpeMatch",[]):
            if isinstance(item,dict):
                faixa = {k:v for k,v in item.items() if k in (
                    "criteria","vulnerable","versionStartIncluding","versionStartExcluding",
                    "versionEndIncluding","versionEndExcluding")}
                if complexo:
                    faixa["contexto_pendente"] = True
                resultado.append(faixa)
        for filho in no.get("nodes",[])+no.get("children",[]):
            percorrer(filho,complexo)
    for configuracao in cve.get("configurations",[]):
        percorrer(configuracao)
    return resultado


def avaliar_componente(cpe, versao, faixas, vex=()):
    if not faixas and not vex:
        return None
    try:
        produto, versao_cpe = identidade(cpe)
        versao = versao or versao_cpe
        for declaracao in vex:
            if (declaracao.get("status")=="not_affected" and declaracao.get("justificativa","").strip()
                    and identidade(declaracao.get("cpe23",""))[0]==produto
                    and (identidade(declaracao["cpe23"])[1] in ("*","-") or
                         comparar_versoes(versao,identidade(declaracao["cpe23"])[1])==0)):
                return False
        if not faixas:
            return None
        incerto = False
        for faixa in faixas:
            if not faixa.get("vulnerable"):
                continue
            outro, exata = identidade(faixa["criteria"])
            if produto != outro:
                continue
            if faixa.get("contexto_pendente"):
                incerto = True
                continue
            if exata not in ("*","-") and comparar_versoes(versao,exata)!=0:
                continue
            limites = (("versionStartIncluding",lambda c:c>=0),
                       ("versionStartExcluding",lambda c:c>0),
                       ("versionEndIncluding",lambda c:c<=0),
                       ("versionEndExcluding",lambda c:c<0))
            if all(teste(comparar_versoes(versao,faixa[chave])) for chave,teste in limites if chave in faixa):
                # Faixa sem versão conhecida não comprova aplicabilidade.
                tokens(versao)
                return True
        return None if incerto else False
    except (ValueError, KeyError, TypeError):
        return None

