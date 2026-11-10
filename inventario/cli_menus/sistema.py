"""Menu de sistema: adaptador de terminal."""

from __future__ import annotations
from getpass import getpass
import json
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from inventario.infraestrutura.auditoria import travar_escrita
from inventario.models import (
    Ativo,
    CertificadoDigital,
    Dependencia,
    Incidencia,
    Incidente,
    RegistroAuditoria,
    Sala,
    Vulnerabilidade,
)
from inventario.cli_menus.comum import Cor, menu_seguro


class SistemaMenu:

    @menu_seguro("")
    def menu_auditoria(self):
        while True:
            op = self._submenu(
                "AUDITORIA E EXPORTAÇÕES",
                [
                    ("1", "Últimos registros de auditoria"),
                    ("2", "Exportar quatro arrays JSON"),
                    ("3", "Exportar ativos CSV"),
                ],
            )
            if op == "0":
                return
            if op == "1":
                if self._exigir("inventario.view_registroauditoria"):
                    self.listar_auditoria()
            elif op == "2":
                if not self._exigir("auth.view_user") or not self.usuario.is_superuser:
                    self._falha("Exportação completa exige superusuário.")
                    continue
                destino = self._texto("Arquivo de saída JSON")
                if not self._exigir("auth.view_user", interativo=False) or not self.usuario.is_superuser:
                    continue
                self._comando("exportar_inventario", saida=destino)
                self._ok(f"Arquivos gravados em {settings.DATA_DIR}.")
            elif op == "3":
                self.exportar_csv()
            else:
                self._falha("Opção inválida.")
            self._pausa()

    def listar_auditoria(self):
        self._tabela(
            ["Data", "Usuário", "Ação", "Entidade", "ID", "Detalhes"],
            [
                [
                    r.ocorrido_em.strftime("%Y-%m-%d %H:%M"),
                    r.usuario.username if r.usuario else "sistema",
                    r.acao,
                    r.entidade,
                    r.entidade_id,
                    json.dumps(r.detalhes, ensure_ascii=False),
                ]
                for r in RegistroAuditoria.objects.select_related("usuario")[:50]
            ],
            [16, 14, 12, 18, 16, 35],
        )

    def exportar_csv(self):
        from inventario.infraestrutura.relatorios import relatorio_csv

        if not self._exigir("inventario.view_ativo"):
            return
        caminho = settings.DATA_DIR / "ativos_sauron.csv"
        if caminho.exists() and not self._confirmar("Sobrescrever ativos_sauron.csv?"):
            return
        if not self._exigir("inventario.view_ativo", interativo=False):
            return
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(relatorio_csv("ativos", self.usuario), encoding="utf-8")
        self._ok(f"CSV criado em {caminho}.")

    @menu_seguro("")
    def menu_sistema(self):
        while True:
            op = self._submenu(
                "SESSÃO, DADOS E SERVIDOR",
                [
                    ("1", "Entrar ou trocar usuário"),
                    ("2", "Encerrar sessão"),
                    ("3", "Criar primeiro administrador"),
                    ("4", "Carregar cenário demonstrativo"),
                    ("5", "Atualizar cache KEV"),
                    ("6", "Iniciar interface web"),
                    ("7", "Resumo do banco"),
                    ("8", "Diagnosticar a instalação web"),
                ],
            )
            if op == "0":
                return
            if op == "1":
                self.login()
            elif op == "2":
                self.usuario = None
                self._ok("Sessão encerrada.")
            elif op == "3":
                self.criar_admin()
            elif op == "4":
                if self._exigir("auth.change_user") and self.usuario.is_superuser:
                    self._comando("seed_demo")
                else:
                    self._falha("Carga demonstrativa exige superusuário.")
            elif op == "5":
                if self._exigir("inventario.change_vulnerabilidade"):
                    self._comando("sync_kev")
            elif op == "6":
                if not self._exigir("auth.change_user") or not self.usuario.is_superuser:
                    self._falha("Operação de servidor exige superusuário.")
                    continue
                self._comando('preparar_servidor')
                self.saida(
                    Cor.aviso(
                        "Servidor em http://127.0.0.1:8000/ — pressione Ctrl+C para retornar à CLI."
                    )
                )
                try:
                    call_command("runserver", "127.0.0.1:8000", use_reloader=False)
                except KeyboardInterrupt:
                    self.saida("\nServidor encerrado.")
            elif op == "7":
                self.resumo_banco()
            elif op == "8":
                if self._exigir('inventario.view_ativo'):
                    self._comando('diagnosticar')
            else:
                self._falha("Opção inválida.")
            self._pausa()

    def criar_admin(self):
        User = get_user_model()
        primeiro = not User.objects.filter(is_superuser=True).exists()
        if User.objects.filter(is_superuser=True).exists() and (
            not self._exigir("auth.add_user") or not self.usuario.is_superuser
        ):
            self._falha("Já existe administrador; entre como superusuário para criar outro.")
            return
        nome = self._texto("Nome do administrador")
        senha = getpass("Senha: ")
        confirmacao = getpass("Confirme a senha: ")
        if senha != confirmacao or len(senha) < 8:
            raise ValidationError("As senhas devem coincidir e possuir ao menos 8 caracteres.")
        email = self._texto("E-mail", permitir_vazio=True)
        if primeiro:
            from inventario.aplicacao.administrador_inicial import cadastrar_primeiro_administrador
            cadastrar_primeiro_administrador(nome, senha, email)
            self.usuario = None
            self._ok(f"Administrador {nome} cadastrado. Entre com usuário e senha nesta versão de apresentação.")
            return
        validate_password(senha, user=User(username=nome, email=email))
        with transaction.atomic():
            travar_escrita()
            if User.objects.filter(is_superuser=True).exists() and (
                not self._exigir("auth.add_user", interativo=False) or not self.usuario.is_superuser
            ):
                self._falha("A autorização mudou durante o preenchimento; entre novamente como administrador.")
                return
            User.objects.create_superuser(nome, email=email, password=senha)
        self.usuario = None
        self._ok(f"Administrador {nome} criado. Entre com usuário e senha nesta versão de apresentação.")

    def resumo_banco(self):
        if not self._acesso_risco():
            return
        dados = [
            ("Ativos", Ativo.objects.count()),
            ("Vulnerabilidades", Vulnerabilidade.objects.count()),
            ("Incidências", Incidencia.objects.count()),
            ("Salas", Sala.objects.count()),
            ("Dependências", Dependencia.objects.count()),
            ("Incidentes abertos", Incidente.objects.filter(encerrado_em__isnull=True).count()),
            ("Certificados", CertificadoDigital.objects.count()),
            (
                "Auditorias",
                (
                    RegistroAuditoria.objects.count()
                    if self.usuario.has_perm("inventario.view_registroauditoria")
                    else "sem permissão"
                ),
            ),
        ]
        self._tabela(["Entidade", "Quantidade"], dados)
