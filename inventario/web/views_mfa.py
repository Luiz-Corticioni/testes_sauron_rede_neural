from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django_otp import login as login_otp
from django_otp.plugins.otp_totp.models import TOTPDevice
from inventario.aplicacao.mfa_email import (
    configuracao_valida,
    desafio_pendente,
    email_valido,
    enviar_codigo,
    verificar_codigo,
    mascarar,
    ErroMFAEmail,
)
from inventario.infraestrutura.auditoria import registrar_evento
from inventario.seguranca_mfa import usuario_privilegiado


@login_required
@require_http_methods(["GET", "POST"])
def verificar_mfa(request):
    erro = ""
    aviso = ""
    dispositivos = TOTPDevice.objects.filter(user=request.user)
    if request.method == "POST":
        acao = request.POST.get("acao", "totp")
        if acao == "enviar_email":
            try:
                request.session["sauron_email_desafio"] = enviar_codigo(request.user)
                aviso = "O servidor de e-mail aceitou o envio. Confira sua caixa de entrada e spam."
            except ErroMFAEmail as exc:
                erro = str(exc)
        elif acao == "verificar_email":
            dispositivo = verificar_codigo(
                request.user,
                request.session.get("sauron_email_desafio", ""),
                request.POST.get("token", ""),
                request.POST.get("password", ""),
            )
            if dispositivo:
                request.session.pop("sauron_email_desafio", None)
                login_otp(request, dispositivo)
                request.session["sauron_mfa_privilegiado"] = usuario_privilegiado(request.user)
                request.session["sauron_reauth_em"] = timezone.now().timestamp()
                return redirect("/")
            erro = "Senha ou código de e-mail inválido, expirado ou bloqueado. Confira os dados e tente novamente."
        elif acao == "totp":
            with transaction.atomic():
                # Em SQLite, obtenha a trava de escrita antes de contar tentativas.
                from inventario.infraestrutura.auditoria import travar_escrita

                travar_escrita()
                identificador = request.POST.get("dispositivo", "")
                device = (
                    dispositivos.select_for_update().filter(pk=int(identificador)).first()
                    if identificador.isdigit() and len(identificador) < 19
                    else None
                )
                senha_valida = request.user.check_password(request.POST.get("password", ""))
                if device and not senha_valida and device.verify_is_allowed()[0]:
                    device.throttle_increment()
                if device and senha_valida and device.verify_token(request.POST.get("token", "")):
                    if not device.confirmed:
                        device.confirmed = True
                        device.save(update_fields=["confirmed"])
                    login_otp(request, device)
                    request.session["sauron_mfa_privilegiado"] = usuario_privilegiado(request.user)
                    request.session["sauron_reauth_em"] = timezone.now().timestamp()
                    registrar_evento("MFA_VERIFICADO", "Autenticacao", request.user.username)
                    return redirect("/")
            erro = "Senha ou código do autenticador inválido; aguarde antes de tentar novamente."
        else:
            erro = "Escolha um método de verificação válido."
    try:
        configuracao_valida()
        configurado = True
    except ErroMFAEmail:
        configurado = False
    return render(
        request,
        "inventario/mfa.html",
        {
            "dispositivos": dispositivos,
            "erro": erro,
            "aviso": aviso,
            "email_valido": email_valido(request.user.email),
            "email_mascarado": mascarar(request.user.email),
            "email_configurado": configurado,
            "privilegiado": usuario_privilegiado(request.user),
            "email_pendente": bool(
                request.session.get("sauron_email_desafio")
                and request.session.get("sauron_email_desafio") == desafio_pendente(request.user)
            ),
        },
    )
