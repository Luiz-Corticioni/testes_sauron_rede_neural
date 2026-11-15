import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.utils import timezone

from inventario.aplicacao.epss import sincronizar_epss
from inventario.aplicacao.estado_fontes import resumo_fontes
from inventario.infraestrutura.cve_client import IntegracaoCVEError, NvdClient, URL_NVD
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
