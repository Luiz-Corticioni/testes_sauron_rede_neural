"""Sessão e navegação principal; menus separados por responsabilidade."""

from __future__ import annotations
from getpass import getpass
import shutil
import time
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.db.models import ProtectedError
from inventario.infraestrutura.cve_client import IntegracaoCVEError
from inventario.infraestrutura.auditoria import definir_usuario, registrar_evento
import io
from inventario.cli_menus.comum import Cor
from inventario.cli_menus.guias import GUIAS
from inventario.cli_menus.ativos import AtivosMenu
from inventario.cli_menus.vulnerabilidades import VulnerabilidadesMenu
from inventario.cli_menus.incidencias import IncidenciasMenu
from inventario.cli_menus.salas import SalasMenu
from inventario.cli_menus.dependencias import DependenciasMenu
from inventario.cli_menus.risco import RiscoMenu
from inventario.cli_menus.cves import CvesMenu
from inventario.cli_menus.euler import EulerMenu
from inventario.cli_menus.incidentes import IncidentesMenu
from inventario.cli_menus.sistema import SistemaMenu
from inventario.cli_menus.entrada import EntradaMenu


class SauronCLI(
    AtivosMenu,
    VulnerabilidadesMenu,
    IncidenciasMenu,
    SalasMenu,
    DependenciasMenu,
    RiscoMenu,
    CvesMenu,
    EulerMenu,
    IncidentesMenu,
    SistemaMenu,
    EntradaMenu,
):

    def __init__(self, entrada=input, saida=print):
        self.entrada = entrada
        self.saida = saida
        self.usuario = None

    @property
    def usuario(self):
        return self._usuario

    @usuario.setter
    def usuario(self, usuario):
        self._usuario = usuario
        definir_usuario(usuario)

    def executar(self):
        try:
            self._executar()
        except (KeyboardInterrupt, EOFError):
            self.saida("\nSessão encerrada; alterações concluídas permanecem salvas.")
            self.usuario = None

    def _executar(self):
        while True:
            self._cabecalho()
            self.saida("  1  Ativos de TI")
            self.saida("  2  Vulnerabilidades")
            self.saida("  3  Incidências N:M")
            self.saida("  4  Salas e subsetores")
            self.saida("  5  Dependências entre ativos")
            self.saida("  6  Análise matricial de risco")
            self.saida("  7  CVE, KEV e CVSS")
            self.saida("  8  Modo Euler")
            self.saida("  9  Incidentes e certificados")
            self.saida(" 10  Auditoria e exportações")
            self.saida(" 11  Sessão, dados e servidor web")
            self.saida(" 12  Software, alertas e rotinas operacionais")
            self.saida(" 13  Sistema imune de vulnerabilidades")
            self.saida("  0  Encerrar")
            opcao = self._texto("\nEscolha: ", permitir_vazio=True)
            acoes = {
                "1": self.menu_ativos,
                "2": self.menu_vulnerabilidades,
                "3": self.menu_incidencias,
                "4": self.menu_salas,
                "5": self.menu_dependencias,
                "6": self.menu_risco,
                "7": self.menu_cve_cvss,
                "8": self.menu_euler,
                "9": self.menu_incidentes,
                "10": self.menu_auditoria,
                "11": self.menu_sistema,
                "12": self.menu_operacional,
                "13": self.menu_imune,
            }
            if opcao == "0":
                self.saida(Cor.fraco("\nO olho se fecha, mas os dados permanecem. Até logo."))
                self.usuario = None
                return
            acao = acoes.get(opcao)
            if acao:
                try:
                    acao()
                except (
                    ValidationError,
                    ValueError,
                    IntegrityError,
                    ProtectedError,
                    PermissionDenied,
                    ObjectDoesNotExist,
                    OSError,
                    IntegracaoCVEError,
                ) as erro:
                    self._falha(erro)
                    self._pausa()
            else:
                self._falha("Opção inexistente.")

    def _cabecalho(self, titulo: str | None = None):
        largura = min(shutil.get_terminal_size((88, 24)).columns, 100)
        self.saida("\n" + "═" * largura)
        self.saida(
            Cor.titulo("  ◉  S A U R O N")
            + Cor.fraco("  ·  Inventário científico de cibersegurança")
        )
        if titulo:
            self.saida(Cor.destaque(f"  {titulo}"))
        sessao = (
            f"usuário: {self.usuario.username}"
            if self.usuario
            else "sem autenticação; entre no menu 11"
        )
        self.saida(Cor.fraco(f"  {sessao}"))
        self.saida("─" * largura)

    def _submenu(self, titulo: str, opcoes: list[tuple[str, str]]) -> str:
        self._cabecalho(titulo)
        for codigo, rotulo in opcoes:
            self.saida(f" {codigo:>2}  {rotulo}")
        self.saida("  0  Voltar")
        self.saida("  ?  Instruções e exemplos de preenchimento")
        escolha = self._texto("\nEscolha: ", permitir_vazio=True)
        while escolha == "?":
            self.saida(GUIAS.get(titulo, "Use os IDs da listagem; 0 volta ao menu anterior."))
            escolha = self._texto("Escolha", permitir_vazio=True)
        return escolha

    def login(self) -> bool:
        self.saida("\nEntre para acessar os dados e executar operações conforme seu perfil.")
        self.usuario = None
        usuario = self._texto("Usuário")
        senha = getpass("Senha: ")
        from inventario.infraestrutura.limites_login import reservar, concluir
        reserva = reservar(usuario, "terminal-local")
        if reserva is None:
            self._falha("Tentativas temporariamente limitadas; aguarde 15 minutos.")
            return False
        globais = reserva["globais"] - 1
        if globais:
            time.sleep(min(2.0, .05 * 2 ** min(globais, 6)))
        autenticado = authenticate(username=usuario, password=senha)
        if not autenticado:
            from inventario.seguranca import nome_auditavel
            registrar_evento("LOGIN_CLI_FALHOU", "Autenticacao", nome_auditavel(usuario))
            self._falha("Credenciais inválidas.")
            return False
        from inventario.seguranca_mfa import exige_mfa
        if exige_mfa(autenticado) and not self._validar_mfa_cli(autenticado, senha):
            self._falha("Verificação em duas etapas não concluída.")
            return False
        concluir(reserva, True)
        self.usuario = autenticado
        self._inicio_cli = self._ultima_cli = self._reauth_cli = time.monotonic()
        registrar_evento("LOGIN_CLI", "Autenticacao", usuario)
        self._ok(f"Sessão iniciada como {autenticado.username}.")
        return True

    def _validar_totp_cli(self, usuario):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from django.db import transaction
        token = getpass("Código TOTP: ")
        with transaction.atomic():
            from inventario.infraestrutura.auditoria import travar_escrita
            travar_escrita()
            for dispositivo in TOTPDevice.objects.select_for_update().filter(user=usuario):
                if dispositivo.verify_token(token):
                    if not dispositivo.confirmed:
                        dispositivo.confirmed=True
                        dispositivo.save(update_fields=["confirmed"])
                    self._mfa_cli_id = dispositivo.persistent_id
                    return True
        return False

    def _validar_mfa_cli(self, usuario, senha):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from inventario.aplicacao.mfa_email import (configuracao_valida, adotar_desafio_inicial, email_valido,
            enviar_codigo, verificar_codigo, ErroMFAEmail, mascarar)
        tem_totp=TOTPDevice.objects.filter(user=usuario).exists()
        try:
            configuracao_valida()
            tem_email=email_valido(usuario.email)
            motivo="Cadastre um e-mail válido para receber códigos."
        except ErroMFAEmail as erro:
            tem_email=False
            motivo=str(erro)
        if not tem_totp and not tem_email:
            self._falha(motivo+" Ou provisione um aplicativo autenticador no servidor.")
            return False
        opcao="1" if tem_totp else "2"
        if tem_totp and tem_email:
            opcao=self._texto("Segundo fator: 1 = autenticador; 2 = e-mail",padrao="1")
        if opcao=="1" and tem_totp:
            return self._validar_totp_cli(usuario)
        if opcao!="2" or not tem_email:
            self._falha("Método de verificação inválido.")
            return False
        nonce=adotar_desafio_inicial(usuario)
        try:
            if nonce:
                self.saida(f"Há um código recente para {mascarar(usuario.email)}; confira também o spam.")
                if self._confirmar("Solicitar um novo código?"):
                    nonce=enviar_codigo(usuario)
            else:
                nonce=enviar_codigo(usuario)
                self.saida(f"Código enviado para {mascarar(usuario.email)}.")
        except ErroMFAEmail as erro:
            self._falha(str(erro))
            return False
        token=getpass("Código de 6 dígitos do e-mail: ")
        dispositivo = verificar_codigo(usuario, nonce, token, senha)
        if dispositivo:
            self._mfa_cli_id = dispositivo.persistent_id
            from inventario.seguranca_mfa import usuario_privilegiado
            self._mfa_cli_privilegiado = usuario_privilegiado(usuario)
        return dispositivo is not None

    def _exigir(self, permissao: str, *, interativo=True) -> bool:
        agora=time.monotonic()
        if hasattr(self, "_ultima_cli"):
            if (agora-self._ultima_cli >= settings.SAURON_SESSAO_OCIOSA_MIN*60
                    or agora-self._inicio_cli >= settings.SAURON_SESSAO_ABSOLUTA_HORAS*3600):
                self.usuario=None
            self._ultima_cli=agora
        if not self.usuario:
            if not interativo or not self.login():
                return False
        from django.contrib.auth import get_user_model
        atual = get_user_model().objects.filter(pk=self.usuario.pk, is_active=True).first()
        if atual is None:
            self.usuario = None
            self._falha("Conta desativada ou removida.")
            return False
        self.usuario = atual
        if getattr(self, "_mfa_cli_id", None):
            from django_otp.models import Device
            from inventario.models import DispositivoEmail
            from inventario.aplicacao.mfa_email import hash_email
            from inventario.seguranca_mfa import usuario_privilegiado
            dispositivo = Device.from_persistent_id(self._mfa_cli_id)
            if (not dispositivo or not dispositivo.confirmed or dispositivo.user_id != atual.pk
                    or (isinstance(dispositivo, DispositivoEmail)
                        and (dispositivo.email_confirmado_hash != hash_email(atual.email)
                             or (getattr(self, '_mfa_cli_privilegiado', False) is False and usuario_privilegiado(atual))))):
                self.usuario = None
                self._falha("Segundo fator revogado ou incompatível com os privilégios; entre novamente.")
                return False
        if not self.usuario.has_perm(permissao):
            self._falha(f"O usuário não possui a permissão {permissao}.")
            return False
        if not permissao.split(".", 1)[-1].startswith("view_") and hasattr(self, "_reauth_cli"):
            if agora-self._reauth_cli > settings.SAURON_REAUTH_SEGUNDOS:
                if not interativo:
                    self._falha("Reautenticação necessária; volte ao menu para validar senha e MFA.")
                    return False
                senha=getpass("Reautenticação — senha: ")
                if not self.usuario.check_password(senha) or not self._validar_mfa_cli(self.usuario,senha):
                    self._falha("Reautenticação inválida.")
                    return False
                self._reauth_cli=time.monotonic()
        return True

    def _comando(self, nome, *args, **kwargs):
        captura = io.StringIO()
        call_command(nome, *args, stdout=captura, **kwargs)
        self.saida(captura.getvalue().strip())

    def menu_imune(self):
        from inventario.cli_imune import menu_imune

        menu_imune(self)
