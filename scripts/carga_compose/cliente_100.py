"""Cem fluxos sintéticos no Compose local; execute somente em ambiente descartável."""
import json
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from pathlib import Path
from threading import Barrier
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener

from django_otp.oath import totp


class SemRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    dados = json.loads(Path("credentials.json").read_text(encoding="utf-8"))
    if len(dados.get("users", [])) != 100 or any(not u["username"].startswith("bench-") for u in dados["users"]):
        raise ValueError("São necessárias 100 contas sintéticas bench- criadas no banco descartável.")
    barreira = Barrier(100, timeout=60)

    def fluxo(usuario):
        comeco = time.monotonic()
        cliente = build_opener(HTTPCookieProcessor(CookieJar()), SemRedirect())

        def pedir(caminho, dados_post=None):
            requisicao = Request("http://127.0.0.1:2230" + caminho,
                data=urlencode(dados_post).encode() if dados_post is not None else None)
            try:
                resposta = cliente.open(requisicao, timeout=150)
            except HTTPError as erro:
                resposta = erro
            with resposta:
                return resposta.code, resposta.read().decode("utf-8", errors="replace")

        def csrf(caminho):
            codigo, corpo = pedir(caminho)
            if codigo != 200:
                raise RuntimeError(f"GET {caminho}: HTTP {codigo}")
            encontrado = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', corpo)
            if not encontrado:
                raise RuntimeError("Token CSRF ausente")
            return encontrado.group(1)

        def resultado(status):
            return status, round(time.monotonic() - comeco, 3)

        try:
            token = csrf("/entrar/")
            barreira.wait()
            codigo, _ = pedir("/entrar/", {"username": usuario["username"], "password": dados["password"], "csrfmiddlewaretoken": token})
            if codigo != 302:
                return resultado(f"senha HTTP {codigo}")
            token = csrf("/mfa/")
            otp = str(totp(bytes.fromhex(usuario["key"]), step=usuario["step"], t0=usuario["t0"], digits=usuario["digits"])).zfill(usuario["digits"])
            codigo, _ = pedir("/mfa/", {"dispositivo": usuario["device"], "password": dados["password"], "token": otp, "csrfmiddlewaretoken": token})
            if codigo != 302:
                return resultado(f"mfa HTTP {codigo}")
            codigo, _ = pedir("/guia/")
            if codigo != 200:
                return resultado(f"guia HTTP {codigo}")
            administrador = int(usuario["username"].removeprefix("bench-")) < 4
            codigo, _ = pedir("/admin/auth/user/")
            esperado = 200 if administrador else 403
            if codigo != esperado:
                return resultado(f"admin HTTP {codigo}, esperado {esperado}")
            return resultado("sucesso_admin" if administrador else "sucesso_comum")
        except Exception as erro:
            barreira.abort()
            return resultado("erro " + type(erro).__name__)

    inicio = time.monotonic()
    with ThreadPoolExecutor(max_workers=100) as pool:
        saidas = list(pool.map(fluxo, dados["users"]))
    contagem = {s: sum(item[0] == s for item in saidas) for s in sorted({item[0] for item in saidas})}
    tempos = sorted(item[1] for item in saidas)
    print(json.dumps({"fluxos": len(saidas), "concorrencia_cliente": 100, "status": contagem,
        "duracao_segundos": round(time.monotonic() - inicio, 2), "p50_todos_s": statistics.median(tempos),
        "p95_todos_s": tempos[94], "max_s": max(tempos)}, ensure_ascii=False), flush=True)
    return 0 if contagem == {"sucesso_admin": 4, "sucesso_comum": 96} else 1


if __name__ == "__main__":
    sys.exit(main())
