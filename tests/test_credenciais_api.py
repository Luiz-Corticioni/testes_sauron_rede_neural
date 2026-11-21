from datetime import timedelta
from unittest.mock import patch
from unittest import skipIf
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.test import Client
from django.db import connection

from inventario.aplicacao.credenciais_api import (
    CredencialInvalida, LimiteCredencial, autenticar, criar, revogar, rotacionar,
)
from inventario.models import CredencialAPI, RegistroAuditoria
from .base import BancoTeste


class CredenciaisIntegracao(BancoTeste):
    def test_ciclo_rotacao_revogacao_e_auditoria_sem_segredo(self):
        credencial, segredo = criar(self.usuario, ["ativos"], 2)
        self.assertNotIn(segredo, credencial.segredo_hash)
        self.assertEqual(autenticar(segredo, "ativos").pk, self.usuario.pk)
        with self.assertRaises(PermissionDenied):
            autenticar(segredo, "risco")
        nova, novo_segredo = rotacionar(self.usuario, credencial.pk, 1)
        with self.assertRaises(CredencialInvalida):
            autenticar(segredo, "ativos")
        self.assertEqual(autenticar(novo_segredo, "ativos").pk, self.usuario.pk)
        revogar(self.usuario, nova.pk)
        with self.assertRaises(CredencialInvalida):
            autenticar(novo_segredo, "ativos")
        for registro in RegistroAuditoria.objects.filter(entidade="CredencialAPI"):
            self.assertNotIn(segredo, str(registro.detalhes))
            self.assertNotIn(novo_segredo, str(registro.detalhes))

    def test_expirada_alterada_limite_e_conta_desativada(self):
        credencial, segredo = criar(self.usuario, ["ativos"], 1)
        with self.assertRaises(CredencialInvalida):
            autenticar(segredo + "x", "ativos")
        with patch("inventario.aplicacao.credenciais_api.LIMITE_POR_MINUTO", 1):
            autenticar(segredo, "ativos")
            with self.assertRaises(LimiteCredencial):
                autenticar(segredo, "ativos")
        CredencialAPI.objects.filter(pk=credencial.pk).update(expira_em=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(CredencialInvalida):
            autenticar(segredo, "ativos")
        CredencialAPI.objects.filter(pk=credencial.pk).update(expira_em=timezone.now() + timedelta(days=1))
        self.usuario.is_active = False
        self.usuario.save()
        with self.assertRaises(CredencialInvalida):
            autenticar(segredo, "ativos")

    def test_parametros_e_permissao_rejeitados_e_rotacao_atomica(self):
        with self.assertRaises(ValidationError):
            criar(self.usuario, ["escrita"], 1)
        with self.assertRaises(ValidationError):
            criar(self.usuario, ["ativos"], 91)
        credencial, segredo = criar(self.usuario, ["ativos"], 1)
        with patch("inventario.aplicacao.credenciais_api._nova", side_effect=RuntimeError("falha")):
            with self.assertRaises(RuntimeError):
                rotacionar(self.usuario, credencial.pk, 1)
        self.assertIsNone(CredencialAPI.objects.get(pk=credencial.pk).revogada_em)
        self.assertEqual(autenticar(segredo, "ativos").pk, self.usuario.pk)
        self.usuario.is_superuser = False
        self.usuario.save()
        with self.assertRaises(PermissionDenied):
            criar(self.usuario, ["ativos"], 1)

    def test_administrador_nao_gerencia_credencial_de_outro(self):
        from django.contrib.auth import get_user_model
        credencial, segredo = criar(self.usuario, ["ativos"], 1)
        outro = get_user_model().objects.create_superuser("outro-admin", "outro@example.org", "senha-sintetica")
        with self.assertRaises(CredencialInvalida):
            revogar(outro, credencial.pk)
        with self.assertRaises(CredencialInvalida):
            rotacionar(outro, credencial.pk, 1)
        self.assertEqual(autenticar(segredo, "ativos").pk, self.usuario.pk)

    def test_fluxo_http_escopo_mfa_e_rotacao(self):
        anônimo = Client()
        self.assertEqual(anônimo.post("/api/v1/credenciais/", data="{}", content_type="application/json").status_code, 401)
        self.client.logout()
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.post("/api/v1/credenciais/", data="{}", content_type="application/json").status_code, 403)
        self.autenticar(self.usuario)
        resposta = self.client.post("/api/v1/credenciais/", data=json.dumps({"escopos": ["ativos"], "dias": 1}),
                                    content_type="application/json")
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta["Cache-Control"], "no-store")
        dados = resposta.json()
        listagem = self.client.get("/api/v1/credenciais/")
        self.assertEqual(listagem.status_code, 200)
        self.assertEqual(listagem.json()["total"], 1)
        self.assertNotIn(dados["segredo"], listagem.content.decode())
        self.assertEqual(self.client.get("/api/v1/credenciais/?pagina=0").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/credenciais/?pagina=2").status_code, 404)
        cabecalho = {"HTTP_AUTHORIZATION": "Bearer " + dados["segredo"]}
        self.assertEqual(anônimo.get("/api/v1/ativos/", **cabecalho).status_code, 200)
        self.assertEqual(anônimo.get("/api/v1/ativos/?ordenar=-risco", **cabecalho).status_code, 403)
        self.assertEqual(anônimo.get("/api/v1/openapi.json", **cabecalho).status_code, 401)
        self.assertNotEqual(anônimo.post("/api/v1/credenciais/", data="{}", content_type="application/json", **cabecalho).status_code, 201)
        rotacao = self.client.post(f"/api/v1/credenciais/{dados['id']}/rotacionar/", data='{"dias": 1}',
                                   content_type="application/json")
        self.assertEqual(rotacao.status_code, 201)
        self.assertEqual(anônimo.get("/api/v1/ativos/", **cabecalho).status_code, 401)
        novo = {"HTTP_AUTHORIZATION": "Bearer " + rotacao.json()["segredo"]}
        self.assertEqual(anônimo.get("/api/v1/ativos/", **novo).status_code, 200)
        revogacao = self.client.post(f"/api/v1/credenciais/{rotacao.json()['id']}/revogar/", data="{}",
                                     content_type="application/json")
        self.assertEqual(revogacao.status_code, 200)
        self.assertEqual(anônimo.get("/api/v1/ativos/", **novo).status_code, 401)

    def test_http_token_invalido_sem_autoridade_e_limite(self):
        cliente = Client()
        self.assertEqual(cliente.get("/api/v1/ativos/", HTTP_AUTHORIZATION="Bearer invalido").status_code, 401)
        _, segredo = criar(self.usuario, ["incidencias"], 1)
        cabecalho = {"HTTP_AUTHORIZATION": "Bearer " + segredo}
        self.assertEqual(cliente.get("/api/v1/ativos/", **cabecalho).status_code, 403)
        with patch("inventario.aplicacao.credenciais_api.LIMITE_POR_MINUTO", 1):
            self.assertEqual(cliente.get(f"/api/v1/vulnerabilidades/{self.v.pk}/ativos/", **cabecalho).status_code, 200)
            resposta = cliente.get(f"/api/v1/vulnerabilidades/{self.v.pk}/ativos/", **cabecalho)
            self.assertEqual(resposta.status_code, 429)
            self.assertEqual(resposta["Retry-After"], "60")

    def test_limite_por_origem_tambem_cobre_credenciais_invalidas(self):
        cliente = Client()
        with patch("inventario.aplicacao.credenciais_api.LIMITE_ORIGEM_POR_MINUTO", 1):
            self.assertEqual(cliente.get("/api/v1/ativos/", HTTP_AUTHORIZATION="Bearer invalido").status_code, 401)
            self.assertEqual(cliente.get("/api/v1/ativos/", HTTP_AUTHORIZATION="Bearer invalido").status_code, 429)

    def test_criacao_exige_csrf_reautenticacao_e_administrador(self):
        seguro = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, seguro)
        corpo = json.dumps({"escopos": ["ativos"], "dias": 1})
        self.assertEqual(seguro.post("/api/v1/credenciais/", data=corpo, content_type="application/json").status_code, 403)
        sessao = self.client.session
        sessao["sauron_reauth_em"] = 0
        sessao.save()
        self.assertEqual(self.client.post("/api/v1/credenciais/", data=corpo, content_type="application/json").status_code, 302)
        from django.contrib.auth import get_user_model
        comum = get_user_model().objects.create_user("sem-privilegio")
        self.autenticar(comum)
        self.assertEqual(self.client.post("/api/v1/credenciais/", data=corpo, content_type="application/json").status_code, 403)

    @skipIf(connection.vendor == "postgresql", "No PostgreSQL, a mesma garantia é testada fora de TestCase.")
    def test_credenciais_nao_sao_incluidas_em_backups_ou_exportacoes(self):
        from cryptography.fernet import Fernet
        from django.test import override_settings
        from inventario.infraestrutura.backup import backup_sqlite
        from inventario.infraestrutura.exportacao import inventario_completo

        _, segredo = criar(self.usuario, ["ativos"], 1)
        chave = Fernet.generate_key()
        with override_settings(SAURON_BACKUP_KEY=chave.decode(), SAURON_BACKUP_DESTINO_ADICIONAL=""):
            dados = Fernet(chave).decrypt(backup_sqlite().read_bytes())
        self.assertNotIn(segredo.encode(), dados)
        self.assertNotIn(b"inventario.credencialapi", dados.lower())
        self.assertNotIn("credencialapi", inventario_completo()["colecoes"])
