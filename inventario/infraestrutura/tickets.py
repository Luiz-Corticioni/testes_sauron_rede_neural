"""Adaptadores HTTP explícitos. Não fazem chamada até criar() ser invocado."""
from abc import ABC, abstractmethod
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Redirecionamento recusado", headers, fp)


def enviar_json(url, headers, payload):
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={**headers, "Content-Type": "application/json"}, method="POST")
    with build_opener(SemRedirecionamento()).open(req, timeout=10) as resposta:
        if resposta.status not in (200, 201):
            raise ValueError("Resposta inesperada do serviço.")
        corpo = resposta.read(65537)
        if len(corpo) > 65536:
            raise ValueError("Resposta excede limite.")
        return json.loads(corpo)


def base_segura(base):
    partes = urlsplit(base)
    if (partes.scheme != "https" or not partes.hostname or partes.username or partes.password
            or partes.query or partes.fragment or any(c in base for c in "\r\n")):
        raise ValueError("Endereço do serviço deve ser HTTPS, sem credenciais ou parâmetros.")
    return base.rstrip("/")


def cabecalho(valor):
    if not valor or len(valor) > 4096 or any(c in valor for c in "\r\n"):
        raise ValueError("Credencial de integração ausente ou inválida.")
    return valor


class AdaptadorTicket(ABC):
    @abstractmethod
    def criar(self, titulo, referencia):
        """Retorna identificador externo; erros não devem expor resposta ou segredo."""


class Jira(AdaptadorTicket):
    def __init__(self, base, autorizacao, projeto, tipo, transporte=enviar_json):
        self.base, self.autorizacao = base_segura(base), cabecalho(autorizacao)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,19}", projeto) or not tipo or len(tipo) > 100:
            raise ValueError("Projeto ou tipo Jira inválido.")
        self.projeto, self.tipo, self.transporte = projeto, tipo, transporte

    def criar(self, titulo, referencia):
        payload = {"fields": {"project": {"key": self.projeto}, "summary": titulo,
            "issuetype": {"name": self.tipo}, "description": {"type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": referencia}]}]}}}
        resposta = self.transporte(self.base + "/rest/api/3/issue", {"Authorization": self.autorizacao}, payload)
        chave = resposta.get("key") if isinstance(resposta, dict) else None
        if not isinstance(chave, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,19}-[1-9][0-9]{0,15}", chave):
            raise ValueError("Identificador Jira inválido.")
        return chave


class GLPI(AdaptadorTicket):
    def __init__(self, base, sessao, app_token, transporte=enviar_json):
        self.base, self.sessao, self.app_token = base_segura(base), cabecalho(sessao), cabecalho(app_token)
        self.transporte = transporte

    def criar(self, titulo, referencia):
        resposta = self.transporte(self.base + "/apirest.php/Ticket", {"Session-Token": self.sessao,
            "App-Token": self.app_token}, {"input": {"name": titulo, "content": referencia}})
        chave = resposta.get("id") if isinstance(resposta, dict) else None
        if isinstance(chave, bool) or not re.fullmatch(r"[1-9][0-9]{0,15}", str(chave)):
            raise ValueError("Identificador GLPI inválido.")
        return str(chave)
