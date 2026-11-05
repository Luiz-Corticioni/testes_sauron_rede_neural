"""Segundo fator por sessão; promoções exigem nova verificação."""
from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.utils import timezone


def usuario_privilegiado(usuario):
    # Promoções para contas com escrita exigem nova verificação de segundo fator.
    return usuario.is_staff or usuario.is_superuser or any(
        not permissao.split(".", 1)[-1].startswith("view_")
        for permissao in usuario.get_all_permissions()
    )


def exige_mfa(usuario):
    # A verificação pertence à sessão atual, não à confirmação anterior do e-mail.
    return True


class SessaoEMFAMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        if not request.user.is_authenticated:
            return self.get_response(request)
        agora=timezone.now().timestamp()
        inicio=request.session.setdefault("sauron_inicio",agora)
        ultima=request.session.get("sauron_ultima_atividade",agora)
        if (agora-ultima >= settings.SAURON_SESSAO_OCIOSA_MIN*60 or
                agora-inicio >= settings.SAURON_SESSAO_ABSOLUTA_HORAS*3600):
            logout(request)
            return HttpResponseRedirect(settings.LOGIN_URL)
        # Agrupa batimentos: evita UPDATE de sessão a cada leitura. A expiração
        # pode antecipar até 30s; a janela absoluta e o MFA continuam inalterados.
        intervalo = min(30, settings.SAURON_SESSAO_OCIOSA_MIN*30)
        if "sauron_ultima_atividade" not in request.session or agora-ultima >= intervalo:
            request.session["sauron_ultima_atividade"]=agora
        livre=request.path in ("/mfa/","/entrar/","/sair/","/api/saude/")
        if not livre and exige_mfa(request.user):
            from inventario.aplicacao.mfa_email import hash_email
            from inventario.models import DispositivoEmail
            dispositivo = request.user.otp_device
            if (isinstance(dispositivo, DispositivoEmail)
                    and dispositivo.email_confirmado_hash != hash_email(request.user.email)):
                request.session.pop("otp_device_id", None)
                request.user.otp_device = None
            privilegiado = usuario_privilegiado(request.user)
            anterior = request.session.get("sauron_mfa_privilegiado")
            if isinstance(dispositivo, DispositivoEmail) and privilegiado and anterior is False:
                request.session.pop("otp_device_id", None)
                request.user.otp_device = None
            elif request.user.is_verified() and anterior is None:
                request.session["sauron_mfa_privilegiado"] = privilegiado
            if not request.user.is_verified():
                return HttpResponseRedirect("/mfa/")
            if request.method=="POST" and agora-request.session.get("sauron_reauth_em",0)>settings.SAURON_REAUTH_SEGUNDOS:
                return HttpResponseRedirect("/mfa/")
        return self.get_response(request)

