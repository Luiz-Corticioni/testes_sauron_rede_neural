"""Parser mínimo de DATABASE_URL sem dependência adicional."""
from urllib.parse import urlsplit, unquote, parse_qs


def configurar_banco(url, padrao):
    if not url:
        return padrao
    partes=urlsplit(url)
    if partes.scheme=="sqlite":
        nome=unquote(partes.path)
        if len(nome)>3 and nome[0]=="/" and nome[2]==":":
            nome=nome[1:]
        if nome=="/:memory:":
            nome=":memory:"
        if not nome:
            raise ValueError("DATABASE_URL SQLite exige caminho.")
        return {"ENGINE":"django.db.backends.sqlite3","NAME":nome,
                "CONN_MAX_AGE":60,"CONN_HEALTH_CHECKS":True,"OPTIONS":{"timeout":20}}
    if partes.scheme not in ("postgres","postgresql") or not partes.path.strip("/"):
        raise ValueError("DATABASE_URL deve usar sqlite, postgres ou postgresql com nome de banco.")
    consulta=parse_qs(partes.query)
    opcoes={"sslmode":consulta.get("sslmode",["require"])[0],"connect_timeout":10}
    for campo in ("sslrootcert","sslcert","sslkey"):
        if campo in consulta:
            opcoes[campo]=consulta[campo][0]
    return {"ENGINE":"django.db.backends.postgresql","NAME":unquote(partes.path[1:]),
        "USER":unquote(partes.username or ""),"PASSWORD":unquote(partes.password or ""),
        "HOST":partes.hostname or "localhost","PORT":partes.port or 5432,
        "CONN_MAX_AGE":60,"CONN_HEALTH_CHECKS":True,"OPTIONS":opcoes}

