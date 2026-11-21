import json
import time
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.conf import settings
from django.utils import timezone

from inventario.aplicacao.estado_fontes import resumo_fontes, estado_cobertura, classificar_fonte, idade_segundos
from inventario.models import ObservacaoEPSS, RelatorioScanner, SensorHoneypot
from .base import BancoTeste


class EstadoFontes(BancoTeste):
    def test_situacoes_sao_conservadoras_e_separam_falha_de_dados(self):
        self.assertEqual(classificar_fonte("lacuna", 0, None)["codigo"], "vazio")
        self.assertEqual(classificar_fonte("atualizada", 1, None)["codigo"], "ok")
        self.assertEqual(classificar_fonte("desatualizada", 1, None)["codigo"], "vencido")
        self.assertEqual(classificar_fonte("lacuna", 1, None)["codigo"], "incompleto")
        self.assertEqual(classificar_fonte("atualizada", 1, {"ultima": {"estado": "falha"}})["codigo"], "inacessivel")
        self.assertEqual(classificar_fonte("atualizada", 1, {"ultima": {"estado": "parcial"}})["codigo"], "incompleto")
        self.assertIsNone(idade_segundos("não é data"))
        self.assertIsNone(idade_segundos(timezone.now() + timedelta(days=1)))

    def test_fogueiras_diferenciam_cobertura_local_e_lacunas(self):
        self.assertEqual(estado_cobertura(0, 0), 'lacuna')
        self.assertEqual(estado_cobertura(3, 3), 'atualizada')
        self.assertEqual(estado_cobertura(3, 2, 1), 'desatualizada')
        self.assertEqual(estado_cobertura(3, 2, lacunas=1), 'lacuna')
        self.assertEqual(estado_cobertura(3, 3, parcial=True), 'lacuna')

    def setUp(self):
        super().setUp()
        diretorio = TemporaryDirectory(prefix="sauron-fontes-")
        self.addCleanup(diretorio.cleanup)
        override = self.settings(DATA_DIR=Path(diretorio.name))
        override.enable()
        self.addCleanup(override.disable)

    def kev(self, data, itens):
        (settings.DATA_DIR / "cache_kev.json").write_text(json.dumps({
            "atualizado_em": data.isoformat(), "fonte": "CISA KEV", "dados": {"vulnerabilities": itens}}), encoding="utf-8")

    def epss(self, v, dias):
        data = timezone.now().date() - timedelta(days=dias)
        o = ObservacaoEPSS.objects.create(cve_id=v.cve_id, data=data, epss=0.2, percentil=0.5,
                                           assinatura=(v.cve_id + str(dias)).ljust(64, "0"))
        v.epss, v.epss_data, v.epss_observacao = o.epss, o.data, o
        v.save()

    def test_sem_dados_nao_significa_seguranca_ou_fonte_offline(self):
        with patch("inventario.infraestrutura.cve_client._baixar_json", side_effect=AssertionError("GET não usa rede")):
            r = resumo_fontes()
            pagina = self.client.get("/fontes/")
        self.assertEqual(r["kev"]["estado"], "Sem cache")
        self.assertEqual(r["nvd"]["ausentes"], 1)
        self.assertEqual(r["epss"]["sem_dados_coerentes"], 1)
        self.assertEqual((r['kev']['fogueira'], r['nvd']['fogueira'], r['epss']['fogueira']), ('lacuna', 'lacuna', 'lacuna'))
        self.assertContains(pagina, 'Cobertura local incompleta ou desconhecida')
        self.assertContains(pagina, "status da conexão é desconhecido")
        self.assertContains(pagina, "ausência de registro não significa segurança")

    def test_kev_recente_vencido_vazio_e_invalido(self):
        agora = timezone.now()
        item = {"cveID": "CVE-2021-44228", "dateAdded": "2021-12-10", "dueDate": "2022-01-01"}
        self.kev(agora, [item])
        self.assertEqual(resumo_fontes()["kev"]["estado"], "Atualizado no cache")
        self.assertEqual(resumo_fontes()['kev']['fogueira'], 'atualizada')
        self.kev(agora - timedelta(days=2), [item])
        self.assertEqual(resumo_fontes()["kev"]["estado"], "Desatualizado")
        self.assertEqual(resumo_fontes()['kev']['fogueira'], 'desatualizada')
        self.kev(agora, [])
        self.assertEqual(resumo_fontes()["kev"]["estado"], "Catálogo vazio")
        self.kev(agora - timedelta(days=2), [])
        self.assertEqual(resumo_fontes()["kev"]["estado"], "Catálogo vazio (desatualizado)")
        (settings.DATA_DIR / "cache_kev.json").write_text("{malformado", encoding="utf-8")
        self.assertEqual(resumo_fontes()["kev"]["estado"], "Cache inválido")

    def test_nvd_cache_validade_e_falha_de_rotina_sem_inventar_falha_de_rede(self):
        pasta = settings.DATA_DIR / "cache" / "nvd"
        pasta.mkdir(parents=True)
        caminho = pasta / f"{self.v.cve_id}.json"
        caminho.write_text(json.dumps({"ts": time.time(), "cve": {"id": self.v.cve_id}}), encoding="utf-8")
        self.assertEqual(resumo_fontes()["nvd"]["recentes"], 1)
        caminho.write_text(json.dumps({"ts": time.time() - 172800, "cve": {"id": self.v.cve_id}}), encoding="utf-8")
        self.assertEqual(resumo_fontes()["nvd"]["antigos"], 1)
        caminho.write_text("{", encoding="utf-8")
        self.assertEqual(resumo_fontes()["nvd"]["invalidos"], 1)
        (settings.DATA_DIR / "ultima_rotina.json").write_text(json.dumps({"erros": {"kev": "falha de teste"}}), encoding="utf-8")
        self.assertIn("registrou falha", resumo_fontes()["kev"]["rotina"])

    def test_nvd_limita_leitura_e_identifica_resultado_parcial(self):
        pasta = settings.DATA_DIR / "cache" / "nvd"
        pasta.mkdir(parents=True)
        (pasta / f"{self.v.cve_id}.json").write_text("x" * 32, encoding="utf-8")
        with patch("inventario.aplicacao.estado_fontes.LIMITE_BYTES_NVD", 16):
            dados = resumo_fontes()["nvd"]
        self.assertEqual(dados["nao_lidos"], 1)
        self.assertTrue(dados["parcial"])
        self.assertEqual(dados["invalidos"], 0)

    def test_epss_coverage_considera_data_e_coerencia_da_observacao(self):
        self.w.cve_id = "CVE-2024-0002"
        self.w.save()
        self.epss(self.v, 0)
        self.epss(self.w, 4)
        dados = resumo_fontes()["epss"]
        self.assertEqual((dados["total"], dados["recentes"], dados["antigos"]), (2, 1, 1))
        self.w.epss = 0.9
        type(self.w).objects.filter(pk=self.w.pk).update(epss=0.9)
        dados = resumo_fontes()["epss"]
        self.assertEqual((dados["recentes"], dados["sem_dados_coerentes"]), (1, 1))

    def test_sem_cves_mostra_base_vazia_e_protege_dados_de_isca(self):
        type(self.v).objects.filter(pk=self.v.pk).update(cve_id=None)
        r = resumo_fontes()
        self.assertEqual(r["nvd"]["total"], 0)
        self.assertEqual(r["epss"]["total"], 0)
        SensorHoneypot.objects.create(nome="Restrito", responsavel="SOC")
        leitor = get_user_model().objects.create_user("leitor-fontes")
        leitor.user_permissions.add(Permission.objects.get(content_type__app_label="inventario", codename="view_vulnerabilidade"))
        self.autenticar(leitor)
        pagina = self.client.get("/fontes/")
        self.assertEqual(pagina.status_code, 200)
        self.assertNotContains(pagina, "Sensores de isca")
        self.assertNotContains(pagina, "Relatórios importados")
        self.assertNotContains(pagina, "Restrito")
        self.autenticar(self.usuario)
        self.assertContains(self.client.get("/fontes/"), "Sensores de isca")
        self.assertContains(self.client.get("/fontes/"), "Relatórios importados")

    def test_acesso_exige_permissao_e_mfa(self):
        sem = get_user_model().objects.create_user("sem-fontes")
        self.autenticar(sem)
        self.assertEqual(self.client.get("/fontes/").status_code, 403)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get("/fontes/").url, "/mfa/")

    def test_importacao_preserva_origem_data_e_exige_permissoes(self):
        RelatorioScanner.objects.create(ativo=self.a, escopo="teste", origem="Scanner fictício",
            observado_em=timezone.now() - timedelta(days=1), sha256="a" * 64, achados=[],
            importado_por=self.usuario)
        dados = resumo_fontes(ver_importacoes=True)["importacoes"]
        self.assertEqual(dados["total"], 1)
        self.assertEqual(dados["ultima"]["origem"], "Scanner fictício")
        self.assertGreaterEqual(dados["idade_observacao_segundos"], 86400)
        self.assertContains(self.client.get("/fontes/"), "Scanner fictício")
        leitor = get_user_model().objects.create_user("sem-scanner")
        leitor.user_permissions.add(Permission.objects.get(content_type__app_label="inventario", codename="view_vulnerabilidade"))
        self.autenticar(leitor)
        self.assertNotContains(self.client.get("/fontes/"), "Scanner fictício")
