from copy import deepcopy
from datetime import timedelta
import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, override_settings
from django.utils import timezone
from inventario.aplicacao.documentos import importar, reconciliar, LEITURA
from inventario.dominio.documentos import carregar, purl_exata, MAX_BYTES
from inventario.models import (
    Software,
    DocumentoInventario,
    ItemSBOM,
    AchadoComponente,
    DeclaracaoVEX,
    Incidencia,
)
from .base import BancoTeste

PURL = "pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1"


def sbom():
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": "urn:uuid:22222222-2222-4222-8222-222222222222",
        "version": 1,
        "metadata": {"component": {"bom-ref": "app"}},
        "components": [
            {
                "type": "library",
                "bom-ref": "log4j",
                "name": "log4j-core",
                "version": "2.14.1",
                "purl": PURL,
                "supplier": {"name": "Apache"},
            }
        ],
        "dependencies": [{"ref": "app", "dependsOn": ["log4j"]}],
        "vulnerabilities": [{"id": "CVE-2021-44228", "affects": [{"ref": "log4j"}]}],
    }


def vex(status="not_affected", purl=PURL):
    return {
        "@context": "https://openvex.dev/ns/v0.2.0",
        "@id": "https://example.org/vex/1",
        "author": "Fornecedor declarado",
        "timestamp": (timezone.now() - timedelta(minutes=1)).isoformat(),
        "version": 1,
        "statements": [
            {
                "vulnerability": {"name": "CVE-2021-44228"},
                "products": [{"@id": purl}],
                "status": status,
                "justification": "vulnerable_code_not_in_execute_path",
                "action_statement": "Aplicar atualização",
            }
        ],
    }


def dados(d):
    return json.dumps(d, ensure_ascii=False).encode()


class PerfilDocumento(SimpleTestCase):
    def test_purl_canonica_sem_perder_qualificadores_e_versao(self):
        a = "pkg:generic/teste@1?b=2&a=1"
        self.assertEqual(purl_exata(a), purl_exata("pkg:generic/teste@1?a=1&b=2"))
        for invalida in ("pkg:generic/teste", "https://example.org/teste", "pkg:generic/teste@*"):
            with self.assertRaises(ValueError):
                purl_exata(invalida)
        with self.assertRaises(ValueError):
            purl_exata(PURL, "2.17.1")

    def test_json_ambiguo_excessivo_ou_nao_finito_rejeitado(self):
        for b in (
            b'{"bomFormat":"x","bomFormat":"CycloneDX"}',
            b'{"x":NaN}',
            b"[]",
            b" " * (MAX_BYTES + 1),
            b"{",
        ):
            with self.subTest(tamanho=len(b)), self.assertRaises(ValueError):
                carregar(b)

    def test_referencias_aninhamento_e_versao_invalidos_rejeitados(self):
        alteracoes = [
            lambda d: d.update(specVersion="9"),
            lambda d: d["components"].append(deepcopy(d["components"][0])),
            lambda d: d["dependencies"][0]["dependsOn"].append("ausente"),
            lambda d: d["components"][0].update(components=[{}]),
            lambda d: d["components"][0].update(version="2.17.1"),
        ]
        for alterar in alteracoes:
            d = sbom()
            alterar(d)
            with self.assertRaises(ValueError):
                carregar(dados(d))

    def test_vex_exige_escopo_exato_e_justificativa(self):
        a = vex()
        a["statements"][0].pop("justification")
        with self.assertRaises(ValueError):
            carregar(dados(a))
        a = vex()
        a["@context"] = "http://127.0.0.1/metadata"
        with self.assertRaises(ValueError):
            carregar(dados(a))
        a = vex()
        a["statements"].append(deepcopy(a["statements"][0]))
        a["statements"][1]["status"] = "affected"
        with self.assertRaises(ValueError):
            carregar(dados(a))


class DocumentosIntegrados(BancoTeste):
    def importar(self, d=None, **opcoes):
        return importar(
            self.a.pk,
            dados(d or sbom()),
            self.usuario,
            "Aplicação A / build 1",
            opcoes.pop("origem", "Scanner A"),
            **opcoes,
        )

    def test_previa_nao_grava_e_importacao_idempotente(self):
        self.assertTrue(self.importar()["previa"])
        self.assertFalse(DocumentoInventario.objects.exists())
        self.assertFalse(Software.objects.exists())
        a = self.importar(aplicar=True)
        b = self.importar(aplicar=True)
        self.assertTrue(a["novo"])
        self.assertFalse(b["novo"])
        self.assertEqual(DocumentoInventario.objects.count(), 1)
        self.assertEqual(Software.objects.count(), 1)
        self.assertEqual(ItemSBOM.objects.count(), 2)
        self.assertEqual(AchadoComponente.objects.count(), 1)
        self.assertEqual(self.i.pk, AchadoComponente.objects.get().incidencia_id)
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, "ABERTA")

    def test_fontes_distintas_preservadas_sem_duplicar_componente_ou_achado(self):
        self.importar(aplicar=True)
        self.importar(origem="Scanner B", aplicar=True)
        self.assertEqual(DocumentoInventario.objects.count(), 2)
        self.assertEqual(Software.objects.count(), 1)
        self.assertEqual(AchadoComponente.objects.get().fontes.count(), 2)
        self.assertEqual(Incidencia.objects.filter(ativo=self.a, vulnerabilidade=self.v).count(), 1)

    def test_componentes_de_outras_versoes_nao_se_fundem(self):
        self.importar(aplicar=True)
        d = sbom()
        d["version"] = 2
        d["components"][0]["version"] = "2.17.1"
        d["components"][0]["purl"] = PURL.replace("2.14.1", "2.17.1")
        self.importar(d, aplicar=True)
        self.assertEqual(Software.objects.count(), 2)
        self.assertEqual(AchadoComponente.objects.count(), 2)
        self.assertEqual(Incidencia.objects.filter(ativo=self.a, vulnerabilidade=self.v).count(), 1)

    def test_cve_ausente_aguarda_catalogo_sem_inventar_cvss(self):
        d = sbom()
        d["vulnerabilities"][0]["id"] = "CVE-2025-12345"
        r = self.importar(d, aplicar=True)
        achado = AchadoComponente.objects.get()
        self.assertIsNone(achado.incidencia_id)
        self.w.cve_id = "CVE-2025-12345"
        self.w.save()
        self.assertEqual(
            reconciliar(DocumentoInventario.objects.get(pk=r["documento"]), self.usuario), 1
        )
        achado.refresh_from_db()
        self.assertEqual(achado.incidencia.status, "SUGERIDA")
        self.assertEqual(achado.incidencia.vulnerabilidade.cvss, self.w.cvss)

    def test_documento_divergente_mesma_revisao_e_rejeitado_sem_gravar(self):
        self.importar(aplicar=True)
        d = sbom()
        d["components"][0]["name"] = "outro-nome"
        with self.assertRaises(ValidationError):
            self.importar(d, aplicar=True)
        self.assertEqual(DocumentoInventario.objects.count(), 1)

    def test_erro_no_ultimo_componente_reverte_todo_lote(self):
        d = sbom()
        item = deepcopy(d["components"][0])
        item.update(
            {"bom-ref": "outro", "purl": "pkg:generic/outro@1", "version": "1", "cpe": "invalido"}
        )
        d["components"].append(item)
        with self.assertRaises(ValidationError):
            self.importar(d, aplicar=True)
        self.assertFalse(Software.objects.exists())
        self.assertFalse(DocumentoInventario.objects.exists())

    def test_vex_nao_suprime_incidente_nem_afeta_outro_componente(self):
        self.importar(aplicar=True)
        r = self.importar(vex(), aplicar=True)
        self.assertEqual(DeclaracaoVEX.objects.count(), 1)
        self.assertEqual(AchadoComponente.objects.count(), 1)
        self.i.refresh_from_db()
        self.v.refresh_from_db()
        self.assertEqual(self.i.status, "ABERTA")
        self.assertEqual(self.v.vex, [])
        self.assertEqual(DocumentoInventario.objects.get(pk=r["documento"]).tipo, "VEX")
        d = vex(purl=PURL.replace("2.14.1", "2.17.1"))
        d["@id"] = "https://example.org/vex/2"
        self.importar(d, aplicar=True)
        self.assertEqual(DeclaracaoVEX.objects.count(), 2)
        self.assertEqual(Software.objects.count(), 1)

    def test_vex_contraditorio_em_outro_documento_preserva_ambos(self):
        self.importar(aplicar=True)
        self.importar(vex(), aplicar=True)
        d = vex("affected")
        d["@id"] = "https://example.org/vex/2"
        self.importar(d, aplicar=True)
        self.assertEqual(
            set(DeclaracaoVEX.objects.values_list("status", flat=True)),
            {"affected", "not_affected"},
        )
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, "ABERTA")

    def test_identidade_com_evidencia_nao_pode_ser_reescrita(self):
        self.importar(aplicar=True)
        s = Software.objects.get()
        s.versao = "2.17.1"
        s.purl = PURL.replace("2.14.1", "2.17.1")
        with self.assertRaises(ValidationError):
            s.save()

    def test_ssvc_reconhece_novas_evidencias_sem_alterar_resultado_antigo(self):
        from inventario.aplicacao.ssvc import contexto_atual, registrar_avaliacao, situacao

        entradas = {
            "exploitation": "active",
            "exposure": "open",
            "automatable": "yes",
            "human_impact": "high",
        }
        r = registrar_avaliacao(
            self.i.pk,
            self.usuario,
            entradas,
            "BIA/KEV",
            timezone.localdate() + timedelta(days=30),
            contexto_atual(self.i)[1],
            "Patch",
        )
        self.importar(aplicar=True)
        self.i.refresh_from_db()
        self.assertIn("alterado", situacao(r, contexto_atual(self.i)[1]))
        r.refresh_from_db()
        self.assertEqual(r.resultado["acao"], "immediate")

    def test_web_permissoes_csrf_download_e_sem_rede(self):
        r = self.importar(aplicar=True)
        url = f"/documentos/{r['documento']}/"
        with patch(
            "inventario.infraestrutura.cve_client._baixar_json",
            side_effect=AssertionError("Sem rede"),
        ):
            self.assertContains(self.client.get("/documentos/"), "Scanner A")
            self.assertContains(self.client.get(url), PURL)
            download = self.client.get(url + "baixar/")
            self.assertEqual(download.status_code, 200)
            self.assertEqual(json.loads(download.content), sbom())
        u = get_user_model().objects.create_user("leitor-doc")
        u.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="inventario",
                codename__in=[p.split(".")[1] for p in LEITURA],
            )
        )
        self.autenticar(u)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 403)
        with self.assertRaises(PermissionDenied):
            importar(self.a.pk, dados(sbom()), u, "app", "origem", True)
        c = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, c)
        self.assertEqual(c.post(url).status_code, 403)

    def test_upload_web_grava_mesmo_fluxo_e_escapa_textos(self):
        d = sbom()
        d["components"][0]["name"] = "<script>alert(1)</script>"
        r = self.client.post(
            "/documentos/",
            {
                "ativo": self.a.pk,
                "escopo": "App",
                "origem": "Scanner",
                "aplicar": "on",
                "arquivo": SimpleUploadedFile(
                    "sbom.json", dados(d), content_type="application/json"
                ),
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(DocumentoInventario.objects.count(), 1)
        doc = DocumentoInventario.objects.get()
        r = self.client.get(f"/documentos/{doc.pk}/")
        self.assertNotContains(r, "<script>alert(1)</script>")
        self.assertContains(r, "&lt;script&gt;")

    def test_backup_exportacao_e_fontes_sao_preservados(self):
        from cryptography.fernet import Fernet
        from django.conf import settings
        import sqlite3
        from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
        from inventario.infraestrutura.exportacao import inventario_completo

        self.importar(aplicar=True)
        self.importar(origem="B", aplicar=True)
        self.importar(vex(), aplicar=True)
        exportado = inventario_completo()["colecoes"]
        self.assertEqual(len(exportado["fontes_achados"]), 2)
        self.assertEqual(len(exportado["declaracaovex"]), 1)
        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode()):
            destino = settings.DATA_DIR / "documentos-restaurados.sqlite3"
            restaurar_backup(backup_sqlite(), destino)
        with sqlite3.connect(destino) as db:
            self.assertEqual(
                db.execute("select count(*) from inventario_achadocomponente_fontes").fetchone()[0],
                2,
            )
            self.assertEqual(
                db.execute("select count(*) from inventario_declaracaovex").fetchone()[0], 1
            )

    def test_vex_importado_antes_do_componente_pode_ser_reconciliado(self):
        r = self.importar(vex("affected"), aplicar=True)
        self.assertFalse(AchadoComponente.objects.exists())
        d = sbom()
        d["vulnerabilities"] = []
        self.importar(d, aplicar=True)
        self.assertEqual(
            reconciliar(DocumentoInventario.objects.get(pk=r["documento"]), self.usuario), 1
        )
        self.assertEqual(AchadoComponente.objects.count(), 1)

    def test_reconciliacao_recusa_ativo_baixado_sem_erro_500(self):
        r = self.importar(aplicar=True)
        self.a.status = "BAIXADO"
        self.a.save()
        resposta = self.client.post(f"/documentos/{r['documento']}/")
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "exige ativo ativo")

    def test_dependencias_de_pacote_nao_criam_arestas_de_rede(self):
        from inventario.models import Dependencia

        self.importar(aplicar=True)
        self.assertEqual(Dependencia.objects.count(), 1)  # Apenas a aresta prévia da fixture.
        self.assertEqual(ItemSBOM.objects.get(software__isnull=True).depende_de, ["log4j"])

    def test_vex_identifiers_purl_e_identificadores_contraditorios(self):
        d = vex()
        produto = d["statements"][0]["products"][0]
        produto["@id"] = "https://example.org/produto"
        produto["identifiers"] = {"purl": PURL}
        self.importar(d, aplicar=True)
        d["@id"] = "https://example.org/vex/contraditorio"
        produto["@id"] = PURL.replace("2.14.1", "2.17.1")
        with self.assertRaises(ValueError):
            self.importar(d, aplicar=True)

    def test_download_detecta_alteracao_do_conteudo_arquivado(self):
        r = self.importar(aplicar=True)
        DocumentoInventario.objects.filter(pk=r["documento"]).update(conteudo={"alterado": True})
        self.assertEqual(self.client.get(f"/documentos/{r['documento']}/baixar/").status_code, 409)

    def test_terminal_importa_pelo_mesmo_servico(self):
        from django.conf import settings
        from inventario.cli import SauronCLI
        from inventario.cli_operacional import documentos

        caminho = settings.DATA_DIR / "entrada.json"
        caminho.write_bytes(dados(sbom()))
        respostas = iter(["1", str(caminho), "App CLI", "Scanner CLI"])
        cli = SauronCLI(entrada=lambda _: next(respostas), saida=lambda _: None)
        cli.usuario = self.usuario
        self.addCleanup(setattr, cli, "usuario", None)
        with (
            patch.object(cli, "_ativo", return_value=self.a),
            patch.object(cli, "_confirmar", return_value=True),
        ):
            documentos(cli)
        self.assertEqual(DocumentoInventario.objects.get().origem, "Scanner CLI")

    def test_cve_conhecida_em_outro_ativo_entra_sugerida_sem_aumentar_risco(self):
        from inventario.aplicacao.risco import calcular_risco_banco

        antes = calcular_risco_banco()["indices"]
        importar(self.b.pk, dados(sbom()), self.usuario, "App B", "Scanner", True)
        inc = Incidencia.objects.get(ativo=self.b, vulnerabilidade=self.v)
        self.assertEqual(inc.status, "SUGERIDA")
        self.assertEqual(calcular_risco_banco()["indices"], antes)

    def test_novo_documento_nao_reabre_correcao_confirmada(self):
        from inventario.aplicacao.operacao import alterar_status

        segundo = get_user_model().objects.create_superuser("revisor-doc", "", "senha-revisor")
        alterar_status(self.i.pk, "CORRIGIDA", self.usuario, evidencia="scan:correcao")
        alterar_status(self.i.pk, "CORRIGIDA", segundo)
        self.importar(aplicar=True)
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, "CORRIGIDA")

    def test_fontes_na_tela_sao_limitadas_sem_perder_historico(self):
        primeiro = self.importar(origem="Scanner 0", aplicar=True)
        for n in range(1, 7):
            self.importar(origem=f"Scanner {n}", aplicar=True)
        r = self.client.get(f"/documentos/{primeiro['documento']}/")
        self.assertContains(r, "Scanner 6")
        self.assertNotContains(r, "Scanner 1")
        self.assertEqual(AchadoComponente.objects.get().fontes.count(), 7)

    def test_permissoes_revogadas_nao_usam_cache_antigo_no_servico(self):
        u = get_user_model().objects.create_user("importador")
        from inventario.aplicacao.documentos import ESCRITA

        u.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="inventario",
                codename__in=[p.split(".")[1] for p in ESCRITA],
            )
        )
        self.assertTrue(u.has_perms(ESCRITA))
        u.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            importar(self.a.pk, dados(sbom()), u, "app", "origem", True)
        self.assertFalse(DocumentoInventario.objects.exists())

    def test_terminal_revalida_conta_apos_confirmacao(self):
        from django.conf import settings
        from inventario.cli import SauronCLI
        from inventario.cli_operacional import documentos

        caminho = settings.DATA_DIR / "entrada.json"
        caminho.write_bytes(dados(sbom()))
        respostas = iter(["1", str(caminho), "App CLI", "Scanner CLI"])
        cli = SauronCLI(entrada=lambda _: next(respostas), saida=lambda _: None)
        cli.usuario = self.usuario
        self.addCleanup(setattr, cli, "usuario", None)

        def desativar(_):
            get_user_model().objects.filter(pk=self.usuario.pk).update(is_active=False)
            return True

        with (
            patch.object(cli, "_ativo", return_value=self.a),
            patch.object(cli, "_confirmar", side_effect=desativar),
        ):
            documentos(cli)
        self.assertFalse(DocumentoInventario.objects.exists())
