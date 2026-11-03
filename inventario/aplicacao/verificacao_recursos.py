"""Auditoria estática de URLs: namespaces SVG não são requisições de rede."""

from pathlib import Path
import re

NAMESPACE_SVG = "http://www.w3.org/2000/svg"


def urls_externas(texto):
    # Não liberamos um domínio externo: só o identificador padrão do namespace SVG.
    texto = re.sub(
        r"(xmlns\s*=\s*|const namespace\s*=\s*)[\"\']" + re.escape(NAMESPACE_SVG) + r"[\"\']",
        "namespace SVG local",
        texto,
    )
    return re.findall(r"https?://[^\s\"'<>)]*|(?<=[\"'(])//[^\s\"'<>)]*", texto)


def verificar_recursos():
    raiz = Path(__file__).resolve().parent.parent
    problemas = []
    for pasta, extensoes in (("templates", {".html"}), ("static", {".css", ".js", ".svg"})):
        for arquivo in (raiz / pasta).rglob("*"):
            if arquivo.suffix in extensoes:
                problemas.extend(
                    f"{arquivo.relative_to(raiz)}: {u}" for u in urls_externas(arquivo.read_text())
                )
    return problemas
