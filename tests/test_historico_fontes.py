import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.utils import timezone

from inventario.aplicacao.epss import sincronizar_epss
from inventario.aplicacao.estado_fontes import resumo_fontes
from inventario.infraestrutura.cve_client import CisaKevClient, IntegracaoCVEError, NvdClient, URL_NVD
from inventario.infraestrutura.estado_consultas_fontes import ler_estado
from .base import BancoTeste


class HistoricoConsultaFontes(BancoTeste):
    def setUp(self):
        super().setUp()
        diretorio = TemporaryDirectory(prefix="sauron-estado-consultas-")
        self.addCleanup(diretorio.cleanup)
        config = self.settings(DATA_DIR=Path(diretorio.name))
        config.enable()
        self.addCleanup(config.disable)

    def test_nvd_preserva_falha_apos_sucesso_sem_guardar_credenciais(self):
        cliente = NvdClient(api_key="CHAVE-PRIVADA", cache_dir=settings.DATA_DIR / "nvd")
        with patch.object(cliente, "reservar_requisicao"), patch("inventario.infraestrutura.cve_client._baixar_json", side_effect=IntegracaoCVEError("senha-exemplo")):
            with self.assertRaises(IntegracaoCVEError):
                cliente.baixar(URL_NVD)
        self.assertEqual(ler_estado("nvd")["ultima_falha"]["estado"], "falha")
        with patch.object(cliente, "reservar_requisicao"), patch("inventario.infraestrutura.cve_client._baixar_json", return_value={}):
            self.assertEqual(cliente.baixar(URL_NVD), {})
        estado = ler_estado("nvd")
        self.assertEqual(estado["ultima"]["estado"], "resposta")
        self.assertEqual(estado["ultima_falha"]["estado"], "falha")
        texto = (settings.DATA_DIR / "estado_fontes" / "nvd.json").read_text(encoding="utf-8")
        self.assertNotIn("CHAVE-PRIVADA", texto)
        self.assertNotIn("senha-exemplo", texto)
        self.assertNotIn("http", texto)
        self.assertContains(self.client.get("/fontes/"), "Último problema registrado")

    @patch.dict(os.environ, {"SAURON_ROTINAS_SEM_REDE": "0"})
    def test_epss_falha_parcial_e_sucesso(self):
        with patch("inventario.aplicacao.epss.EpssClient.buscar", side_effect=IntegracaoCVEError("segredo")):
            self.assertTrue(sincronizar_epss()["avisos"])
        self.assertEqual(ler_estado("epss")["ultima"]["estado"], "falha")
        with patch("inventario.aplicacao.epss.EpssClient.buscar", return_value={}):
            self.assertTrue(sincronizar_epss()["avisos"])
        self.assertEqual(ler_estado("epss")["ultima"]["estado"], "parcial")
        item = {self.v.cve_id: {"epss": .2, "percentil": .5, "data": timezone.now().date().isoformat(), "modelo": ""}}
        with patch("inventario.aplicacao.epss.EpssClient.buscar", return_value=item):
            sincronizar_epss()
        self.assertEqual(ler_estado("epss")["ultima"]["estado"], "resposta")
        self.assertEqual(ler_estado("epss")["ultima_falha"]["estado"], "parcial")
        self.assertNotIn("segredo", (settings.DATA_DIR / "estado_fontes" / "epss.json").read_text())
        with patch("inventario.infraestrutura.cve_client._baixar_json", side_effect=AssertionError("GET não acessa rede")):
            self.assertEqual(resumo_fontes()["epss"]["consulta"]["ultima"]["descricao"], "resposta recebida")

    def test_estado_malformado_e_falha_ao_salvar_nao_interrompem_consulta(self):
        pasta = settings.DATA_DIR / "estado_fontes"
        pasta.mkdir()
        (pasta / "nvd.json").write_text('{"ultima": {"data": "errada", "estado": "resposta"}}')
        self.assertIsNone(ler_estado("nvd"))
        cliente = NvdClient(cache_dir=settings.DATA_DIR / "nvd")
        with patch.object(cliente, "reservar_requisicao"), patch("inventario.infraestrutura.cve_client._baixar_json", return_value={}), patch("inventario.infraestrutura.estado_consultas_fontes.salvar_json_atomico", side_effect=OSError("erro simulado")):
            self.assertEqual(cliente.baixar(URL_NVD), {})

    def test_kev_registra_falha_e_sucesso_sem_expor_detalhes(self):
        cliente = CisaKevClient(settings.DATA_DIR / "kev.json")
        with patch("inventario.infraestrutura.cve_client._baixar_json", side_effect=IntegracaoCVEError("segredo")):
            with self.assertRaises(IntegracaoCVEError):
                cliente.atualizar(forcar=True)
        self.assertEqual(ler_estado("kev")["ultima"]["estado"], "falha")
        with patch("inventario.infraestrutura.cve_client._baixar_json", return_value={"vulnerabilities": []}):
            cliente.atualizar(forcar=True)
        estado = ler_estado("kev")
        self.assertEqual(estado["ultima"]["estado"], "resposta")
        self.assertEqual(estado["ultima_falha"]["estado"], "falha")
        self.assertNotIn("segredo", (settings.DATA_DIR / "estado_fontes" / "kev.json").read_text())

    def test_importacao_scanner_registra_falha_e_sucesso_apos_commit(self):
        import json
        from django.core.exceptions import ValidationError
        from inventario.aplicacao.scanner import gravar

        with self.assertRaises(ValidationError):
            gravar(self.a.pk, "imagem", "origem", b'{"segredo":', self.usuario)
        self.assertEqual(ler_estado("scanner")["ultima"]["estado"], "falha")
        conteudo = json.dumps({"SchemaVersion": 2, "CreatedAt": "2026-11-13T12:00:00Z", "Results": []}).encode()
        with self.captureOnCommitCallbacks(execute=True):
            gravar(self.a.pk, "imagem", "origem", conteudo, self.usuario)
        dados = ler_estado("scanner")
        self.assertEqual(dados["ultima"]["estado"], "resposta")
        self.assertEqual(dados["ultima_falha"]["estado"], "falha")
        self.assertNotIn("segredo", (settings.DATA_DIR / "estado_fontes" / "scanner.json").read_text())
        self.assertContains(self.client.get("/fontes/"), "importação confirmada")

    def test_importacao_revertida_nao_registra_sucesso(self):
        import json
        from django.db import transaction
        from inventario.aplicacao.scanner import gravar
        from inventario.models import RelatorioScanner

        conteudo = json.dumps({"SchemaVersion": 2, "CreatedAt": "2026-11-13T12:00:00Z", "Results": []}).encode()
        with self.assertRaisesMessage(RuntimeError, "rollback"):
            with transaction.atomic():
                gravar(self.a.pk, "imagem", "origem", conteudo, self.usuario)
                raise RuntimeError("rollback")
        self.assertFalse(RelatorioScanner.objects.exists())
        self.assertIsNone(ler_estado("scanner"))
