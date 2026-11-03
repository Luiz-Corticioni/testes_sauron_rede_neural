"""Perfil local estrito de CycloneDX/OpenVEX JSON; nunca resolve URLs externas."""
import hashlib
import json
from datetime import datetime, timezone
from packageurl import PackageURL
from inventario.infraestrutura.cve_client import CVE_RE

MAX_BYTES = 2 * 1024 * 1024


def exigir(condicao, mensagem):
    if not condicao:
        raise ValueError(mensagem)


def texto(valor, limite=512):
    exigir(isinstance(valor, str) and bool(valor.strip()) and len(valor) <= limite, "Texto ausente ou acima do limite.")
    return valor.strip()


def purl_exata(valor, versao=None):
    p = PackageURL.from_string(texto(valor))
    exigir(bool(p.version) and not any(c in p.version for c in "*?\n\r"), "PURL exige versão exata.")
    exigir(versao is None or p.version == versao, "Versão do componente diverge da PURL.")
    normalizada = p.to_string()
    exigir(len(normalizada) <= 512, "PURL normalizada excede 512 caracteres.")
    return normalizada


def cve(valor):
    valor = texto(valor, 30).upper()
    exigir(bool(CVE_RE.fullmatch(valor)), "Este perfil aceita identificadores CVE válidos.")
    return valor


def serializar(dados):
    return json.dumps(dados, sort_keys=True, ensure_ascii=False, allow_nan=False)


def carregar(conteudo):
    exigir(isinstance(conteudo, bytes) and len(conteudo) <= MAX_BYTES, "Envie JSON UTF-8 de até 2 MB.")
    def pares(itens):
        resultado = {}
        for chave, valor in itens:
            exigir(chave not in resultado, "JSON com chave duplicada.")
            resultado[chave] = valor
        return resultado
    def constante(_):
        raise ValueError("JSON não aceita NaN ou infinito.")
    try:
        dados = json.loads(conteudo.decode("utf-8-sig"), object_pairs_hook=pares, parse_constant=constante)
        exigir(isinstance(dados, dict), "O documento deve ser um objeto JSON.")
        assinatura = hashlib.sha256(serializar(dados).encode()).hexdigest()
        if dados.get("bomFormat") == "CycloneDX":
            resultado = sbom(dados)
        else:
            resultado = vex(dados)
        return dados, assinatura, resultado
    except (KeyError, TypeError, AttributeError, RecursionError, UnicodeError) as erro:
        raise ValueError("Estrutura de documento inválida para o perfil suportado.") from erro


def sbom(d):
    exigir(d.get("specVersion") in ("1.5", "1.6"), "Perfil CycloneDX JSON suporta versões 1.5 e 1.6.")
    componentes = d.get("components", [])
    exigir(isinstance(componentes, list) and 1 <= len(componentes) <= 300, "SBOM exige de 1 a 300 componentes planos.")
    exigir(not d.get("services"), "Serviços CycloneDX não são processados neste perfil de componentes.")
    itens, referencias = [], set()
    for item in componentes:
        exigir(not item.get("components") and not item.get("services"), "Componentes aninhados não são aceitos neste perfil; use lista plana e dependencies.")
        exigir(item.get("type") in ("application", "framework", "library", "container", "operating-system"), "Tipo de componente não suportado neste perfil de software.")
        ref = texto(item["bom-ref"])
        exigir(ref not in referencias, "bom-ref duplicado.")
        referencias.add(ref)
        versao = texto(item["version"], 80)
        nome = texto(item["name"], 120)
        purl = purl_exata(item["purl"], versao)
        itens.append({"ref": ref, "nome": nome, "versao": versao, "fornecedor": texto(item.get("supplier", {}).get("name", "Não informado"), 120), "purl": purl, "cpe23": item.get("cpe", "")})
    meta = d.get("metadata", {}).get("component", {})
    exigir(not meta.get("components") and not meta.get("services"), "Raiz aninhada não suportada; use componentes planos.")
    raiz = meta.get("bom-ref")
    if raiz:
        raiz = texto(raiz)
        exigir(raiz not in referencias, "Referência raiz duplica componente.")
        referencias.add(raiz)
    dependencias = {}
    exigir(isinstance(d.get("dependencies", []), list) and len(d.get("dependencies", [])) <= 301, "Dependências inválidas ou excessivas.")
    for item in d.get("dependencies", []):
        ref, destinos = item["ref"], item.get("dependsOn", [])
        exigir(ref in referencias and ref not in dependencias and isinstance(destinos, list) and len(destinos) <= 300, "Origem de dependência inválida ou duplicada.")
        exigir(all(isinstance(v, str) and v in referencias for v in destinos) and ref not in destinos, "Dependência aponta para referência ausente ou para si mesma.")
        dependencias[ref] = sorted(set(destinos))
    achados = []
    exigir(isinstance(d.get("vulnerabilities", []), list) and len(d.get("vulnerabilities", [])) <= 500, "Achados excedem o limite de 500.")
    refs_software = {i["ref"] for i in itens}
    for item in d.get("vulnerabilities", []):
        codigo = cve(item["id"])
        afetados = item["affects"]
        exigir(isinstance(afetados, list) and 1 <= len(afetados) <= 300, "Achado exige referências de componentes.")
        for alvo in afetados:
            exigir(alvo["ref"] in refs_software and not alvo.get("versions"), "Achado deve referir componente exato, sem faixa adicional de versões.")
            achados.append((alvo["ref"], codigo))
    exigir(len(achados) <= 500 and sum(map(len, dependencias.values())) <= 2000, "Documento excede limite de vínculos.")
    return {"tipo": "SBOM", "id": d.get("serialNumber", ""), "versao": d.get("version", 1), "itens": itens, "raiz": raiz, "dependencias": dependencias, "achados": sorted(set(achados))}


def vex(d):
    exigir(d.get("@context") == "https://openvex.dev/ns/v0.2.0", "Perfil OpenVEX aceita apenas contexto v0.2.0, sem resolução JSON-LD.")
    texto(d["author"], 200)
    emitido = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
    exigir(emitido.tzinfo is not None and emitido <= datetime.now(timezone.utc), "Timestamp VEX exige fuso e não pode estar no futuro.")
    declaracoes = []
    exigir(isinstance(d.get("statements"), list) and 1 <= len(d["statements"]) <= 500, "VEX exige de 1 a 500 declarações.")
    chaves = set()
    justificativas = {"component_not_present", "vulnerable_code_not_present", "vulnerable_code_not_in_execute_path", "vulnerable_code_cannot_be_controlled_by_adversary", "inline_mitigations_already_exist"}
    for item in d["statements"]:
        codigo, status = cve(item["vulnerability"]["name"]), item["status"]
        exigir(status in ("affected", "not_affected", "fixed", "under_investigation"), "Status VEX inválido.")
        justificativa = item.get("justification", "")
        exigir(not justificativa or justificativa in justificativas, "Justificativa VEX desconhecida.")
        impacto, acao = item.get("impact_statement", ""), item.get("action_statement", "")
        notas = item.get("status_notes", "")
        exigir(isinstance(notas, str) and len(notas) <= 8000, "Notas VEX inválidas ou excessivas.")
        exigir(isinstance(impacto, str) and isinstance(acao, str) and len(impacto)+len(acao) <= 8000, "Texto VEX inválido ou excessivo.")
        exigir(status != "not_affected" or justificativa or impacto.strip(), "not_affected exige justificativa ou impacto documentado.")
        exigir(status != "affected" or acao.strip(), "affected exige ação descrita.")
        exigir(isinstance(item["products"], list) and 1 <= len(item["products"]) <= 300, "Produtos VEX inválidos.")
        for produto in item["products"]:
            exigir(not produto.get("subcomponents"), "Perfil VEX exige produto PURL exato, sem subcomponentes implícitos.")
            identificador = produto.get("@id", "")
            alternativo = produto.get("identifiers", {}).get("purl")
            principal = identificador if isinstance(identificador, str) and identificador.startswith("pkg:") else alternativo
            purl = purl_exata(principal)
            exigir(not alternativo or purl_exata(alternativo) == purl, "Identificadores PURL contraditórios no produto VEX.")
            exigir((purl, codigo) not in chaves, "Declarações repetidas/conflitantes para o mesmo produto/CVE no documento.")
            chaves.add((purl, codigo))
            declaracoes.append({"purl": purl, "cve_id": codigo, "status": status, "justificativa": justificativa, "texto": "\n".join(v for v in (impacto, acao, notas) if v)})
    exigir(len(declaracoes) <= 500, "VEX excede 500 pares produto/CVE.")
    return {"tipo": "VEX", "id": texto(d["@id"]), "versao": d["version"], "declaracoes": declaracoes}
