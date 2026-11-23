from datetime import timedelta
import json
from unittest import TestCase
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings
from django.utils import timezone

from inventario.aplicacao.observacoes import importar, preparar, revisar
from inventario.dominio.observacoes import LIMITE_BYTES, extrair
from inventario.models import ObservacaoImportada, RegistroAuditoria, RelacaoAtivos, RevisaoObservacao
from .base import BancoTeste


class Adaptadores(TestCase):
    def test_perfis_scanner_e_inventario(self):
        trivy = {"SchemaVersion": 2, "Results": [{"Target": "url-privada", "Vulnerabilities": [
            {"VulnerabilityID": "CVE-2025-1234", "PkgName": "lib", "InstalledVersion": "1", "Description": "segredo"}]}]}
        grype = {"matches": [{"vulnerability": {"id": "CVE-2025-1234"}, "artifact": {"name": "lib", "version": "1"}}]}
        glpi_json = [{"id": 12, "name": "Servidor", "itemtype": "Computer", "password": "segredo"}]
        amostras = {
            "trivy": json.dumps(trivy).encode(), "grype": json.dumps(grype).encode(),
            "openvas": b'IP,Port,Port Protocol,NVT OID,CVEs\n192.0.2.1,443,tcp,1.2,CVE-2025-1234\n',
            "nessus": b'Host,Port,Protocol,Plugin ID,CVE\n192.0.2.1,443,tcp,100,CVE-2025-1234\n',
            "glpi_csv": b'ID,Name,Type\n12,Servidor,Computer\n',
            "glpi_json": json.dumps(glpi_json).encode(),
            "firewall": b'{"rules":[{"id":"R1","acao":"allow","origem_ativo":"A","destino_ativo":"B","escopo":"Rede","protocolo":"tcp","porta":443}]}',
        }
        for formato, conteudo in amostras.items():
            with self.subTest(formato=formato):
                itens, ignorados = extrair(formato, conteudo)
                self.assertEqual(len(itens), 1)
                self.assertEqual(ignorados, 0)
                self.assertNotIn("segredo", json.dumps(itens))
                self.assertNotIn("url-privada", json.dumps(itens))

    def test_duplicata_conflito_truncamento_e_limites(self):
        linha = '{"id":"1","name":"A","itemtype":"Computer"}'
        itens, _ = extrair("glpi_json", f"[{linha},{linha}]".encode())
        self.assertEqual(len(itens), 1)
        with self.assertRaisesRegex(ValueError, "conflitante"):
            extrair("glpi_json", f'[{linha},{{"id":"1","name":"B","itemtype":"Computer"}}]'.encode())
        for formato, conteudo in (("glpi_json", b'[{"id":1'), ("glpi_csv", b'ID,Name,Type\n1,"sem fim'),
                                   ("trivy", b'{"SchemaVersion":2,"SchemaVersion":2,"Results":[]}'),
                                   ("firewall", b'x' * (LIMITE_BYTES + 1))):
            with self.subTest(formato=formato), self.assertRaises(ValueError):
                extrair(formato, conteudo)
        with self.assertRaises(ValueError):
            extrair("nessus", b'Host,Port,Protocol,Plugin ID,CVE\nuser@example.org,443,tcp,100,CVE-2025-1234\n')
        with self.assertRaises(ValueError):
            extrair("grype", b'{"matches":[{"vulnerability":{"id":"CVE-2025-1234"},"artifact":{"name":"https://credencial","version":"1"}}]}')

    def test_cada_perfil_rejeita_truncamento_e_conflito_e_deduplica(self):
        trivy = {"VulnerabilityID": "CVE-2025-1234", "PkgName": "lib", "InstalledVersion": "1"}
        grype = {"vulnerability": {"id": "CVE-2025-1234"}, "artifact": {"name": "lib", "version": "1"}}
        glpi = {"id": "1", "name": "A", "itemtype": "Computer"}
        regra = {"id": "R1", "acao": "allow", "origem_ativo": "A", "destino_ativo": "B", "escopo": "Rede", "protocolo": "tcp", "porta": 443}
        casos = {
            "trivy": (lambda itens: {"SchemaVersion": 2, "Results": [{"Target": "alvo", "Vulnerabilities": itens}]}, trivy, {**trivy, "InstalledVersion": "2"}),
            "grype": (lambda itens: {"matches": itens}, grype, {**grype, "artifact": {"name": "lib", "version": "2"}}),
            "glpi_json": (lambda itens: itens, glpi, {**glpi, "name": "B"}),
            "firewall": (lambda itens: {"rules": itens}, regra, {**regra, "porta": 80}),
        }
        for formato, (embrulhar, primeiro, conflito) in casos.items():
            with self.subTest(formato=formato):
                doc = json.dumps(embrulhar([primeiro, primeiro])).encode()
                self.assertEqual(len(extrair(formato, doc)[0]), 1)
                with self.assertRaises(ValueError):
                    extrair(formato, json.dumps(embrulhar([primeiro, conflito])).encode())
                with self.assertRaises(ValueError):
                    extrair(formato, doc[:-1])
        casos_csv = {
            "openvas": ("IP,Port,Port Protocol,NVT OID,CVEs,Severity", "192.0.2.1,443,tcp,1.2,CVE-2025-1234,high", "192.0.2.1,443,tcp,1.2,CVE-2025-1234,critical"),
            "nessus": ("Host,Port,Protocol,Plugin ID,CVE,Risk", "192.0.2.1,443,tcp,100,CVE-2025-1234,high", "192.0.2.1,443,tcp,100,CVE-2025-1234,critical"),
            "glpi_csv": ("ID,Name,Type", "1,A,Computer", "1,B,Computer"),
        }
        for formato, (cabecalho, primeiro, conflito) in casos_csv.items():
            with self.subTest(formato=formato):
                self.assertEqual(len(extrair(formato, f"{cabecalho}\n{primeiro}\n{primeiro}\n".encode())[0]), 1)
                with self.assertRaises(ValueError):
                    extrair(formato, f"{cabecalho}\n{primeiro}\n{conflito}\n".encode())
                with self.assertRaises(ValueError):
                    extrair(formato, f'{cabecalho}\n"sem fim'.encode())


@override_settings(SAURON_IMPORTACAO_OBSERVACOES_ENABLED=True)
class FluxoObservacoes(BancoTeste):
    def meta(self):
        return {"fonte": "scanner-laboratorio", "versao": "1.0", "observado_em": (timezone.now()-timedelta(days=1)).isoformat(),
                "confianca": "MEDIA", "usuario": self.usuario}

    @override_settings(SAURON_IMPORTACAO_OBSERVACOES_ENABLED=False)
    def test_importacao_desabilitada_por_configuracao(self):
        with self.assertRaises(ValidationError):
            importar("glpi_json", b'[{"id":"1","name":"A","itemtype":"Computer"}]', **self.meta())
        self.assertFalse(ObservacaoImportada.objects.exists())
        self.assertContains(self.client.get("/observacoes/importar/"), "Importação desativada")

    def test_importacao_idempotente_conflito_e_rollback(self):
        dados = b'[{"id":"1","name":"A","itemtype":"Computer"}]'
        meta = self.meta()
        self.assertEqual(importar("glpi_json", dados, **meta)["novos"], 1)
        self.assertEqual(importar("glpi_json", dados, **meta)["repetidos"], 1)
        anterior = RegistroAuditoria.objects.count()
        conflito = b'[{"id":"2","name":"Novo","itemtype":"Computer"},{"id":"1","name":"Alterado","itemtype":"Computer"}]'
        with self.assertRaises(ValidationError):
            importar("glpi_json", conflito, **meta)
        self.assertEqual(ObservacaoImportada.objects.count(), 1)
        self.assertEqual(RegistroAuditoria.objects.count(), anterior + 1)
        self.assertEqual(RegistroAuditoria.objects.order_by("-pk").first().acao, "FALHA_OBSERVACOES")
        from inventario.infraestrutura.auditoria import verificar_cadeia
        self.assertTrue(verificar_cadeia(verificar_ancora=False)["integra"])

    def test_reimportacao_e_idempotente_em_cada_formato(self):
        trivy = {"SchemaVersion": 2, "Results": [{"Target": "alvo", "Vulnerabilities": [
            {"VulnerabilityID": "CVE-2025-1234", "PkgName": "lib", "InstalledVersion": "1"}]}]}
        grype = {"matches": [{"vulnerability": {"id": "CVE-2025-1234"}, "artifact": {"name": "lib", "version": "1"}}]}
        glpi = [{"id": 12, "name": "Servidor", "itemtype": "Computer"}]
        regras = {"rules": [{"id": "R1", "acao": "allow", "origem_ativo": self.a.pk, "destino_ativo": self.b.pk,
                              "escopo": "Rede", "protocolo": "tcp", "porta": 443}]}
        arquivos = {"trivy": json.dumps(trivy).encode(), "grype": json.dumps(grype).encode(),
            "openvas": b'IP,Port,Port Protocol,NVT OID,CVEs\n192.0.2.1,443,tcp,1.2,CVE-2025-1234\n',
            "nessus": b'Host,Port,Protocol,Plugin ID,CVE\n192.0.2.1,443,tcp,100,CVE-2025-1234\n',
            "glpi_csv": b'ID,Name,Type\n12,Servidor,Computer\n', "glpi_json": json.dumps(glpi).encode(),
            "firewall": json.dumps(regras).encode()}
        for formato, conteudo in arquivos.items():
            with self.subTest(formato=formato):
                meta = self.meta() | {"fonte": "laboratorio-" + formato}
                self.assertEqual(importar(formato, conteudo, **meta)["novos"], 1)
                self.assertEqual(importar(formato, conteudo, **meta)["repetidos"], 1)

    def test_falha_na_auditoria_desfaz_as_observacoes(self):
        dados = b'[{"id":"1","name":"A","itemtype":"Computer"}]'
        with patch("inventario.aplicacao.observacoes.registrar_evento", side_effect=RuntimeError("falha sintética")):
            with self.assertRaises(RuntimeError):
                importar("glpi_json", dados, **self.meta())
        self.assertFalse(ObservacaoImportada.objects.exists())

    def test_papeis_padrao_nao_recebem_leitura_de_observacoes_sensiveis(self):
        from django.contrib.auth.models import Group
        from inventario.management.commands.configurar_grupos import configurar_grupos
        configurar_grupos()
        for grupo in ("Operadores", "Auditores"):
            self.assertFalse(Group.objects.get(name=grupo).permissions.filter(codename="view_observacaoimportada").exists())
        self.assertTrue(Group.objects.get(name="Gerentes").permissions.filter(codename="view_observacaoimportada").exists())

    def test_regras_exigem_revisao_e_preservam_procedencia(self):
        doc = {"rules": [{"id": "R1", "acao": "allow", "origem_ativo": self.a.pk,
            "destino_ativo": self.b.pk, "escopo": "Rede", "protocolo": "tcp", "porta": 443}]}
        conteudo = json.dumps(doc).encode()
        importar("firewall", conteudo, **self.meta())
        observacao = ObservacaoImportada.objects.get()
        self.assertEqual(RelacaoAtivos.objects.count(), 0)
        revisao = revisar(observacao.pk, "RELACAO_CRIADA", "Verificação humana", self.usuario, timezone.localdate()+timedelta(days=30))
        self.assertEqual(revisao.relacao.origem_id, self.a.pk)
        self.assertEqual(revisao.relacao.destino_id, self.b.pk)
        self.assertEqual(observacao.confianca, "MEDIA")
        from inventario.aplicacao.relacoes import analisar_relacoes
        grafo = analisar_relacoes(self.usuario, "REDE", "Rede", self.a.pk, self.b.pk)
        self.assertEqual(grafo["evidencias"][0]["confianca_declarada"], "MEDIA")
        self.assertGreaterEqual(grafo["evidencias"][0]["idade_segundos"], 0)
        self.assertFalse(grafo["evidencias"][0]["relacao_alterada_apos_revisao"])
        leitor = get_user_model().objects.create_user("leitor-sem-procedencia")
        leitor.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario", codename__in=["view_ativo", "view_relacaoativos"]))
        visao = analisar_relacoes(leitor, "REDE", "Rede", self.a.pk, self.b.pk)
        self.assertNotIn("confianca_declarada", visao["evidencias"][0])
        from inventario.aplicacao.relacoes import salvar_relacao
        salvar_relacao({"evidencia": "Contexto foi atualizado"}, self.usuario, revisao.relacao.pk,
                       revisao.relacao.atualizado_em.isoformat())
        modificado = analisar_relacoes(self.usuario, "REDE", "Rede", self.a.pk, self.b.pk)
        self.assertTrue(modificado["evidencias"][0]["relacao_alterada_apos_revisao"])
        with self.assertRaises(ValidationError):
            revisar(observacao.pk, "RELACAO_CRIADA", "Repetição", self.usuario, timezone.localdate()+timedelta(days=30))
        with self.assertRaises(ValidationError):
            revisar(observacao.pk, "INCORRETA", "Evidência contestada", self.usuario)
        self.assertEqual(RelacaoAtivos.objects.count(), 1)
        self.assertEqual(RevisaoObservacao.objects.count(), 1)

    def test_permissoes_revalidadas_e_observacao_vencida(self):
        doc = {"rules": [{"id": "R1", "acao": "allow", "origem_ativo": self.a.pk,
            "destino_ativo": self.b.pk, "escopo": "Rede", "protocolo": "tcp", "porta": 443}]}
        antiga = self.meta() | {"observado_em": (timezone.now()-timedelta(days=100)).isoformat()}
        importar("firewall", json.dumps(doc).encode(), **antiga)
        observacao = ObservacaoImportada.objects.get()
        with self.assertRaises(ValidationError):
            revisar(observacao.pk, "RELACAO_CRIADA", "Revisar", self.usuario, timezone.localdate()+timedelta(days=30))
        self.assertEqual(RelacaoAtivos.objects.count(), 0)
        sem = get_user_model().objects.create_user("sem-observacao")
        with self.assertRaises(PermissionDenied):
            preparar("firewall", json.dumps(doc).encode(), **(self.meta() | {"usuario": sem}))
        permissoes = Permission.objects.filter(content_type__app_label="inventario", codename__in=["view_observacaoimportada", "view_revisaoobservacao", "add_observacaoimportada"])
        sem.user_permissions.set(permissoes)
        with patch("inventario.aplicacao.observacoes.travar_escrita", side_effect=lambda: get_user_model().objects.filter(pk=sem.pk).update(is_active=False)):
            with self.assertRaises(PermissionDenied):
                importar("firewall", json.dumps(doc).encode(), **(self.meta() | {"usuario": sem}))
        self.assertEqual(ObservacaoImportada.objects.count(), 1)

    def test_interface_exige_previa_mesmo_arquivo_e_revisao(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        doc = {"rules": [{"id": "R1", "acao": "allow", "origem_ativo": self.a.pk,
            "destino_ativo": self.b.pk, "escopo": "Rede", "protocolo": "tcp", "porta": 443}]}
        bruto = json.dumps(doc).encode()
        dados = {"formato": "firewall", "fonte": "laboratorio", "versao": "1", "confianca": "MEDIA",
                 "observado_em": (timezone.now()-timedelta(days=1)).isoformat()}
        def enviar(conteudo, extra=None):
            return self.client.post("/observacoes/importar/", {**dados, **(extra or {}),
                "arquivo": SimpleUploadedFile("regras.json", conteudo, content_type="application/json")})
        resposta = enviar(bruto)
        self.assertContains(resposta, "nenhuma gravação ainda")
        self.assertEqual(ObservacaoImportada.objects.count(), 0)
        token = resposta.context["form"].initial["confirmacao"]
        alterado = json.dumps({"rules": []}).encode()
        self.assertContains(enviar(alterado, {"confirmacao": token}), "Arquivo ou contexto mudou")
        self.assertEqual(ObservacaoImportada.objects.count(), 0)
        falha = RegistroAuditoria.objects.filter(acao="FALHA_OBSERVACOES").get()
        self.assertEqual(falha.detalhes["erro"], "ARQUIVO_OU_CONTEXTO_INVALIDO")
        self.assertEqual(enviar(bruto, {"confirmacao": token}).status_code, 302)
        observacao = ObservacaoImportada.objects.get()
        api = self.client.get(f"/api/observacoes/{observacao.pk}/")
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api.json()["versao"], "sauron.observacao/1")
        self.assertIsNone(api.json()["erro"])
        self.assertEqual(api["Cache-Control"], "no-store")
        resposta = self.client.post(f"/observacoes/{observacao.pk}/", {"classificacao": "RELACAO_CRIADA",
            "justificativa": "Revisão humana", "revisar_em": (timezone.localdate()+timedelta(days=30)).isoformat()})
        self.assertEqual(resposta.status_code, 302)
        self.assertContains(self.client.get("/relacoes/"), "confiança declarada MEDIA")

    def test_usuarios_sem_papel_e_sem_csrf_sao_bloqueados(self):
        from django.test import Client
        sem = get_user_model().objects.create_user("leitor-sem-observacoes")
        self.autenticar(sem)
        self.assertEqual(self.client.get("/observacoes/").status_code, 403)
        self.assertEqual(self.client.get("/observacoes/importar/").status_code, 403)
        cliente = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, cliente)
        self.assertEqual(cliente.post("/observacoes/importar/", {}).status_code, 403)

    def test_revisao_nao_cria_relacao_quando_gravacao_falha(self):
        doc = {"rules": [{"id": "R1", "acao": "allow", "origem_ativo": self.a.pk,
            "destino_ativo": self.b.pk, "escopo": "Rede", "protocolo": "tcp", "porta": 443}]}
        importar("firewall", json.dumps(doc).encode(), **self.meta())
        obs = ObservacaoImportada.objects.get()
        antes = RegistroAuditoria.objects.count()
        with patch.object(RevisaoObservacao, "save", side_effect=RuntimeError("falha sintética")):
            with self.assertRaises(RuntimeError):
                revisar(obs.pk, "RELACAO_CRIADA", "Revisão", self.usuario, timezone.localdate()+timedelta(days=30))
        self.assertFalse(RelacaoAtivos.objects.exists())
        self.assertEqual(RegistroAuditoria.objects.count(), antes)

    def test_promocao_exige_permissao_de_criar_relacoes(self):
        doc = {"rules": [{"id": "R1", "acao": "allow", "origem_ativo": self.a.pk,
            "destino_ativo": self.b.pk, "escopo": "Rede", "protocolo": "tcp", "porta": 443}]}
        importar("firewall", json.dumps(doc).encode(), **self.meta())
        obs = ObservacaoImportada.objects.get()
        usuario = get_user_model().objects.create_user("revisor-sem-relacao")
        codigos = ["view_observacaoimportada", "view_revisaoobservacao", "add_revisaoobservacao", "view_ativo", "view_relacaoativos"]
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario", codename__in=codigos))
        self.autenticar(usuario)
        resposta = self.client.post(f"/observacoes/{obs.pk}/", {"classificacao": "RELACAO_CRIADA", "justificativa": "Revisão",
            "revisar_em": (timezone.localdate()+timedelta(days=30)).isoformat()})
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(RelacaoAtivos.objects.exists())
