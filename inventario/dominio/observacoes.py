"""Adaptadores offline de perfis delimitados; sem rede e sem efeitos no inventário."""
import csv
import hashlib
import io
import json
import re

LIMITE_BYTES = 2 * 1024 * 1024
LIMITE_ITENS = 5000
FORMATOS = ("trivy", "grype", "openvas", "nessus", "glpi_csv", "glpi_json", "firewall")
CVE = re.compile(r"CVE-\d{4}-\d{4,21}$", re.IGNORECASE)


def texto(valor, nome, limite=200):
    if not isinstance(valor, str) or not valor.strip() or len(valor.strip()) > limite or any(ord(c) < 32 for c in valor):
        raise ValueError(f"{nome}: texto ausente ou inválido.")
    return valor.strip()


def pacote_texto(valor, nome):
    valor = texto(valor, nome)
    if "://" in valor or "?" in valor:
        raise ValueError(f"{nome}: URLs não são aceitas.")
    return valor


def pares_unicos(pares):
    objeto = {}
    for chave, valor in pares:
        if chave in objeto:
            raise ValueError("JSON contém campo duplicado.")
        objeto[chave] = valor
    return objeto


def rejeitar_constante(_valor):
    raise ValueError("JSON contém número não finito.")


def json_local(conteudo):
    try:
        return json.loads(conteudo.decode("utf-8-sig"), object_pairs_hook=pares_unicos, parse_constant=rejeitar_constante)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as erro:
        raise ValueError("JSON inválido ou incompleto.") from erro


def csv_local(conteudo, obrigatorios):
    try:
        leitor = csv.DictReader(io.StringIO(conteudo.decode("utf-8-sig"), newline=""), strict=True)
        cabecalho = leitor.fieldnames
        if not cabecalho or len(cabecalho) != len(set(cabecalho)) or not obrigatorios <= set(cabecalho):
            raise ValueError("Cabeçalho CSV inválido ou incompleto.")
        itens = []
        for linha in leitor:
            if None in linha or any(valor is None for valor in linha.values()):
                raise ValueError("Linha CSV truncada ou com colunas excedentes.")
            itens.append(linha)
            if len(itens) > LIMITE_ITENS:
                raise ValueError("Limite de 5.000 linhas excedido.")
        if not itens:
            raise ValueError("O CSV não contém linhas de dados.")
        return itens
    except (UnicodeDecodeError, csv.Error) as erro:
        raise ValueError("CSV inválido ou truncado.") from erro


def extrair(formato, conteudo):
    if formato not in FORMATOS or not isinstance(conteudo, bytes) or not 0 < len(conteudo) <= LIMITE_BYTES:
        raise ValueError("Formato inválido ou arquivo vazio/acima de 2 MiB.")
    itens, ignorados = [], 0

    def incluir(chave, tipo, dados):
        if len(itens) >= LIMITE_ITENS:
            raise ValueError("Limite de 5.000 observações excedido.")
        itens.append({"chave": chave, "tipo": tipo, "dados": dados})

    if formato in {"trivy", "grype"}:
        doc = json_local(conteudo)
        if not isinstance(doc, dict):
            raise ValueError("Relatório deve ser um objeto JSON.")
        if formato == "trivy":
            if doc.get("SchemaVersion") != 2 or not isinstance(doc.get("Results"), list):
                raise ValueError("Esperado Trivy SchemaVersion 2 com Results.")
            grupos = doc["Results"]
            if len(grupos) > 500:
                raise ValueError("Limite de 500 grupos excedido.")
            registros = []
            for grupo in grupos:
                if not isinstance(grupo, dict) or not isinstance(grupo.get("Vulnerabilities", []), list):
                    raise ValueError("Grupo Trivy inválido.")
                alvo = grupo.get("Target", "")
                if not isinstance(alvo, str) or len(alvo) > 4000:
                    raise ValueError("Identificador de alvo inválido.")
                alvo_hash = hashlib.sha256(alvo.encode()).hexdigest()
                for item in grupo.get("Vulnerabilities", []):
                    registros.append((item, alvo_hash))
                    if len(registros) > LIMITE_ITENS:
                        raise ValueError("Limite de 5.000 achados excedido.")
            for item, alvo_hash in registros:
                if not isinstance(item, dict):
                    raise ValueError("Achado Trivy inválido.")
                cve, pacote, versao = item.get("VulnerabilityID"), item.get("PkgName"), item.get("InstalledVersion")
                if not isinstance(cve, str) or not CVE.fullmatch(cve):
                    ignorados += 1
                    continue
                pacote, versao = pacote_texto(pacote, "Pacote"), pacote_texto(versao, "Versão")
                dados = {"cve": cve.upper(), "pacote": pacote, "versao": versao, "alvo_sha256": alvo_hash}
                incluir([alvo_hash, cve.upper(), pacote], "ACHADO", dados)
        else:
            if not isinstance(doc.get("matches"), list) or len(doc["matches"]) > LIMITE_ITENS:
                raise ValueError("Esperado Grype JSON com até 5.000 matches.")
            for item in doc["matches"]:
                if not isinstance(item, dict) or not isinstance(item.get("vulnerability"), dict) or not isinstance(item.get("artifact"), dict):
                    raise ValueError("Match Grype inválido.")
                cve = item["vulnerability"].get("id")
                if not isinstance(cve, str) or not CVE.fullmatch(cve):
                    ignorados += 1
                    continue
                pacote = pacote_texto(item["artifact"].get("name"), "Pacote")
                versao = pacote_texto(item["artifact"].get("version"), "Versão")
                dados = {"cve": cve.upper(), "pacote": pacote, "versao": versao}
                incluir([cve.upper(), pacote], "ACHADO", dados)
    elif formato in {"openvas", "nessus"}:
        campos = {"openvas": {"IP", "Port", "Port Protocol", "NVT OID", "CVEs"},
                  "nessus": {"Host", "Port", "Protocol", "Plugin ID", "CVE"}}[formato]
        for linha in csv_local(conteudo, campos):
            host = texto(linha["IP" if formato == "openvas" else "Host"], "Host", 253)
            if not re.fullmatch(r"[A-Za-z0-9._:-]+", host):
                raise ValueError("Host deve ser IP ou nome ASCII sem URL ou credenciais.")
            identificador = texto(linha["NVT OID" if formato == "openvas" else "Plugin ID"], "Plugin", 120)
            porta, protocolo = texto(linha["Port"], "Porta", 20), texto(linha["Port Protocol" if formato == "openvas" else "Protocol"], "Protocolo", 20)
            campo = linha["CVEs" if formato == "openvas" else "CVE"].strip()
            severidade = linha.get("Severity" if formato == "openvas" else "Risk", "").strip()
            if len(severidade) > 40 or any(ord(c) < 32 for c in severidade):
                raise ValueError("Severidade declarada inválida.")
            candidatos = [x.strip() for x in re.split(r"[,;\s]+", campo) if x.strip()]
            if not candidatos:
                ignorados += 1
                continue
            if any(not CVE.fullmatch(cve) for cve in candidatos):
                raise ValueError("Lista de CVEs inválida no CSV.")
            for cve in sorted({x.upper() for x in candidatos}):
                dados = {"cve": cve, "host": host, "plugin": identificador, "porta": porta, "protocolo": protocolo,
                         "severidade_declarada": severidade}
                incluir([host, identificador, porta, protocolo, cve], "ACHADO", dados)
    elif formato in {"glpi_csv", "glpi_json"}:
        if formato == "glpi_csv":
            registros = csv_local(conteudo, {"ID", "Name", "Type"})
            registros = [{"id": i["ID"], "name": i["Name"], "itemtype": i["Type"]} for i in registros]
        else:
            registros = json_local(conteudo)
            if not isinstance(registros, list) or len(registros) > LIMITE_ITENS:
                raise ValueError("GLPI JSON deve ser uma lista de até 5.000 itens.")
        for item in registros:
            if not isinstance(item, dict) or isinstance(item.get("id"), bool) or not isinstance(item.get("id"), (str, int)):
                raise ValueError("Identificador GLPI inválido.")
            identificador = texto(str(item["id"]), "ID GLPI", 120)
            nome, tipo = texto(item.get("name"), "Nome"), texto(item.get("itemtype"), "Tipo", 120)
            incluir([tipo, identificador], "ATIVO", {"id_externo": identificador, "nome": nome, "tipo_externo": tipo})
    else:
        doc = json_local(conteudo)
        if not isinstance(doc, dict) or not isinstance(doc.get("rules"), list) or len(doc["rules"]) > LIMITE_ITENS:
            raise ValueError("Esperado objeto com lista rules limitada a 5.000 entradas.")
        for regra in doc["rules"]:
            if not isinstance(regra, dict):
                raise ValueError("Regra inválida.")
            acao = regra.get("acao")
            if acao == "deny":
                ignorados += 1
                continue
            if acao != "allow":
                raise ValueError("Ação deve ser allow ou deny.")
            rid = texto(regra.get("id"), "ID da regra", 120)
            origem, destino = texto(regra.get("origem_ativo"), "Ativo de origem", 60), texto(regra.get("destino_ativo"), "Ativo de destino", 60)
            escopo, protocolo = texto(regra.get("escopo"), "Escopo"), texto(regra.get("protocolo"), "Protocolo", 4).lower()
            porta = regra.get("porta")
            if origem == destino or type(porta) is not int or not ((protocolo in {"tcp", "udp"} and 1 <= porta <= 65535) or (protocolo == "icmp" and porta == 0)):
                raise ValueError("A regra exige ativos distintos e protocolo/porta suportados.")
            dados = {"id_regra": rid, "origem_ativo": origem, "destino_ativo": destino, "escopo": escopo, "protocolo": protocolo, "porta": porta}
            incluir([rid], "RELACAO", dados)
    unicos = {}
    for item in itens:
        chave = json.dumps(item["chave"], ensure_ascii=True, separators=(",", ":"))
        if chave in unicos and unicos[chave] != item:
            raise ValueError("Identificador repetido com conteúdo conflitante.")
        unicos[chave] = item
    return [unicos[k] for k in sorted(unicos)], ignorados
