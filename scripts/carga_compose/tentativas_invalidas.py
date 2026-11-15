"""Verifica bloqueio temporário em conta sintética; somente loopback e banco descartável."""
import json
import re
import secrets
import sys
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener


def main():
    dados = json.loads(Path("credentials.json").read_text(encoding="utf-8"))
    usuario = dados["users"][0]["username"]
    if not usuario.startswith("bench-"):
        raise ValueError("Teste exige conta sintética bench- em banco descartável.")
    senha_errada = secrets.token_urlsafe(32)
    if senha_errada == dados["password"]:
        raise ValueError("Senha de teste precisa ser diferente.")
    cliente = build_opener(HTTPCookieProcessor(CookieJar()))
    codigos = []
    espera = None
    for _ in range(6):
        with cliente.open("http://127.0.0.1:2230/entrar/", timeout=30) as resposta:
            corpo = resposta.read().decode("utf-8", errors="replace")
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', corpo)
        if not token:
            raise ValueError("Token CSRF ausente no formulário.")
        requisicao = Request("http://127.0.0.1:2230/entrar/", data=urlencode({
            "username": usuario, "password": senha_errada, "csrfmiddlewaretoken": token.group(1)}).encode())
        try:
            resposta = cliente.open(requisicao, timeout=30)
        except HTTPError as erro:
            resposta = erro
        with resposta:
            codigos.append(resposta.code)
            espera = resposta.headers.get("Retry-After")
            resposta.read()
    print(json.dumps({"status": codigos, "retry_after": espera}, ensure_ascii=False))
    return 0 if codigos == [200] * 5 + [429] and espera else 1


if __name__ == "__main__":
    sys.exit(main())
