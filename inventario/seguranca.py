"""Acesso uniforme às views existentes e login com limite persistente compartilhado pelo banco."""

import hashlib
import time

from django.conf import settings
from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.views import View

from inventario.infraestrutura.auditoria import registrar_evento, usar_usuario
from inventario.infraestrutura.limites_login import reservar, concluir


class AcessoObrigatorioMiddleware(LoginRequiredMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.resolver_match.url_name in {"entrar", "api_saude"}:
            return None
        if not request.user.is_authenticated:
            return self.handle_no_permission(request, view_func)
        if request.path.startswith("/admin/") and not request.user.is_staff:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Administração restrita a contas de equipe autorizadas.")
        return None


class AutoriaECabecalhosMiddleware:
    CSP = (
        "default-src 'self'; img-src 'self' data:; script-src 'self'; "
        "style-src 'self'; font-src 'self'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with usar_usuario(request.user):
            resposta = self.get_response(request)
            if resposta.status_code == 403:
                registrar_evento("ACESSO_NEGADO", "HTTP", request.path, {"ip": ip_cliente(request)})
        resposta["Content-Security-Policy"] = self.CSP
        resposta["Referrer-Policy"] = "same-origin"
        resposta["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return resposta


class AcessoInventarioMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Uma identidade autenticada e todas as permissões declaradas pela rota."""


class FuncaoProtegida(AcessoInventarioMixin, View):
    handler = None
    permission_required = ()

    def get(self, request, *args, **kwargs):
        return self.handler(request, *args, **kwargs)

    post = get


def proteger(handler, *permissoes):
    return FuncaoProtegida.as_view(handler=handler, permission_required=permissoes)


def ip_cliente(request):
    """Confia em XFF somente se o peer pertence aos CIDRs explicitamente configurados."""
    from ipaddress import ip_address, ip_network
    try:
        peer = ip_address(request.META.get("REMOTE_ADDR", ""))
        redes = [ip_network(cidr) for cidr in settings.SAURON_TRUSTED_PROXIES]
        confiavel = lambda ip: any(ip in rede for rede in redes)
        if not confiavel(peer):
            return str(peer)
        cadeia = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
        if len(cadeia) > 32:
            return str(peer)
        for valor in reversed(cadeia):
            if not confiavel(peer):
                break
            peer = ip_address(valor.strip())
        return str(peer)
    except ValueError:
        return request.META.get("REMOTE_ADDR", "")[:64]


def nome_auditavel(nome):
    from django.contrib.auth import get_user_model
    existente = get_user_model().objects.filter(username__iexact=nome).values_list("username", flat=True).first()
    return existente or "<desconhecido:" + hashlib.sha256(nome.encode()).hexdigest()[:8] + ">"


class LoginProtegido(LoginView):
    template_name = "inventario/entrar.html"

    def post(self, request, *args, **kwargs):
        self.nome = request.POST.get("username", "")[:150].strip().casefold()
        self.ip = ip_cliente(request)
        self.reserva = reservar(self.nome, self.ip)
        if self.reserva is None:
            registrar_evento("LOGIN_BLOQUEADO", "Autenticacao", nome_auditavel(self.nome), {"ip": self.ip})
            resposta = self.render_to_response(self.get_context_data(form=self.get_form_class()(request=request),
                erro_bloqueio="Origem temporariamente limitada por tentativas de autenticação."), status=429)
            resposta["Retry-After"] = "900"
            return resposta
        globais = self.reserva["globais"] - 1
        if globais:
            time.sleep(min(2.0, .05 * 2 ** min(globais, 6)))
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        from inventario.aplicacao.operacao import emitir_alerta
        falhas = self.reserva["falhas"]
        globais = self.reserva["globais"]
        nome = nome_auditavel(self.nome)
        registrar_evento("LOGIN_FALHOU", "Autenticacao", nome, {"ip": self.ip, "falhas": falhas})
        if globais >= 5:
            emitir_alerta("LOGIN", None, self.reserva["chaves"][2], f"Falhas distribuídas para {nome}; atraso progressivo ativo.", 3)
        return super().form_invalid(form)

    def form_valid(self, form):
        concluir(self.reserva, True)
        return super().form_valid(form)


class ProxiesConfiaveisMiddleware:
    """O protocolo encaminhado só tem autoridade quando recebido do proxy cadastrado."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from ipaddress import ip_address, ip_network
        try:
            peer = ip_address(request.META.get("REMOTE_ADDR", ""))
            confiavel = any(peer in ip_network(cidr) for cidr in settings.SAURON_TRUSTED_PROXIES)
        except ValueError:
            confiavel = False
        protocolo = request.META.get("HTTP_X_FORWARDED_PROTO", "")
        if not confiavel or protocolo not in ("http", "https"):
            request.META.pop("HTTP_X_FORWARDED_PROTO", None)
        return self.get_response(request)
