import json
import os
from datetime import date
from django.utils import timezone
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from inventario.aplicacao.montecarlo import calcular_montecarlo, sincronizar_epss
from inventario.infraestrutura.cve_client import IntegracaoCVEError
from inventario.infraestrutura.exportacao import colecoes_json
from inventario.models import Vulnerabilidade, ObservacaoEPSS
from .base import BancoTeste


class IntegracaoMonteCarlo(BancoTeste):
    parametros = {"n": 500, "custos": {"C": 100, "I": 20, "A": 30}}
    def setUp(self):
        super().setUp()
        self.w.cve_id = "CVE-2024-0002"
        self.w.save()
        for indice, v in enumerate((self.v, self.w)):
            o = ObservacaoEPSS.objects.create(cve_id=v.cve_id, data=timezone.now().date(), epss=.1,
                percentil=.5, modelo="fixture", assinatura=str(indice)*64)
            v.epss, v.epss_data, v.epss_observacao = .1, o.data, o
            v.save()

    def post(self, dados):
        return self.client.post(reverse("api_montecarlo"), json.dumps(dados), content_type="application/json")

    def test_api_reprodutivel_nao_grava(self):
        antes = colecoes_json()
        r = self.post(self.parametros)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), self.post(self.parametros).json())
        self.assertEqual(antes, colecoes_json())
        self.assertEqual(r.json()["n"], 500)
        self.assertEqual(r.json()["entradas"][0]["origem_epss"], "informado")
        self.assertEqual(r.json()["horizonte_dias"], 30)
        self.assertNotIn("mensal", r.json())
        corrigido = self.post({**self.parametros, "incidencias_corrigidas": [self.i.pk]}).json()
        self.assertGreaterEqual(corrigido["ganho_media"], 0)
        self.assertEqual(r.json()["antes"], corrigido["antes"])
        cve = self.post({**self.parametros, "cves_corrigidas": [self.v.cve_id]}).json()
        self.assertEqual(corrigido["depois"], cve["depois"])

    def test_erros_json(self):
        for dados in (None, [], {"n": 1}, {"seed": True}, {"custos": {}}, {"teto": -1},
                      {"exposicao_interna": float("nan")}, {"incidencias_corrigidas": [1]},
                      {"cves_corrigidas": ["ausente"]}, {"incidencias_corrigidas": ["ausente"]}, {"surpresa": 1}):
            with self.subTest(dados=dados):
                r = self.post(dados)
                self.assertEqual(r.status_code, 400)
                self.assertTrue(r.json()["erro"])
        self.assertEqual(self.client.post(reverse("api_montecarlo"), "{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.get(reverse("api_montecarlo")).status_code, 405)
        self.assertEqual(self.client.post(reverse("api_montecarlo"), {}).status_code, 400)

    def test_autenticacao_permissoes_csrf(self):
        self.client.logout()
        self.assertEqual(self.post({}).status_code, 302)
        from django.contrib.auth import get_user_model
        usuario = get_user_model().objects.create_user("sem-permissao")
        self.autenticar(usuario)
        self.assertEqual(self.post({}).status_code, 403)
        seguro = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, cliente=seguro)
        self.assertEqual(seguro.post(reverse("api_montecarlo"), "{}", content_type="application/json").status_code, 403)
        pagina = seguro.get(reverse("montecarlo"))
        token = pagina.context["csrf_token"]
        r = seguro.post(reverse("api_montecarlo"), json.dumps(self.parametros), content_type="application/json", HTTP_X_CSRFTOKEN=str(token))
        self.assertEqual(r.status_code, 200)

    def test_cache_invalida_e_escopo(self):
        a = calcular_montecarlo(self.parametros)
        with patch("inventario.aplicacao.montecarlo.simular", side_effect=AssertionError("Cache não utilizado")):
            self.assertEqual(calcular_montecarlo(self.parametros), a)
        self.v.epss_observacao = None
        self.v.epss, self.v.epss_data = 1., date(2026, 10, 26)
        self.v.save()
        b = calcular_montecarlo(self.parametros)
        self.assertNotEqual(a["versao_dados"], b["versao_dados"])
        # O teste mede invalidação após decisão válida, incluindo o segundo usuário.
        from django.contrib.auth import get_user_model
        from inventario.aplicacao.operacao import alterar_status
        segundo = get_user_model().objects.create_superuser("revisor", "", "senha-revisor")
        alterar_status(self.i.pk, "CORRIGIDA", self.usuario, evidencia="fixture:scan")
        alterar_status(self.i.pk, "CORRIGIDA", segundo)
        self.i.refresh_from_db()
        c = calcular_montecarlo(self.parametros)
        self.assertEqual(c["quantidade_incidencias"], 1)
        self.b.status = "BAIXADO"
        self.b.save()
        self.assertEqual(calcular_montecarlo(self.parametros)["quantidade_incidencias"], 0)

    def test_versao_muda_mesmo_se_relogio_nao_avancar(self):
        from django.utils import timezone
        instante = timezone.now()
        with patch('django.db.models.fields.timezone.now', return_value=instante):
            self.v.save()
            antes = calcular_montecarlo(self.parametros)['versao_dados']
            self.v.epss_observacao = None
            self.v.epss = 0.8
            self.v.save()
            depois = calcular_montecarlo(self.parametros)['versao_dados']
        self.assertNotEqual(antes, depois)

    def test_roundtrip_epss(self):
        self.v.epss_observacao = None
        self.v.epss, self.v.epss_data = .75, date(2026, 10, 26)
        self.v.save()
        d = self.v.para_dominio()
        from inventario.dominio.vulnerabilidades import Vulnerabilidade as Dominio
        restaurada = Vulnerabilidade.de_dominio(Dominio.from_dict(d.to_dict()))
        self.assertEqual(restaurada.epss, .75)
        self.assertEqual(restaurada.epss_data, self.v.epss_data)
        j = next(i for i in colecoes_json()["vulnerabilidades.json"] if i["id"] == self.v.id)
        self.assertEqual(j["epss"], .75)
        self.assertEqual(j["epss_data"], "2026-10-26")
        for valor in (-1, 2, float("nan"), float("inf")):
            self.v.epss = valor
            with self.assertRaises(ValidationError):
                self.v.save()

    def test_sync_offline_falha_e_sucesso(self):
        with patch.dict(os.environ, {"SAURON_ROTINAS_SEM_REDE": "1"}), patch("inventario.infraestrutura.cve_client._baixar_json") as rede:
            r = sincronizar_epss()
            rede.assert_not_called()
            self.assertEqual(r["atualizadas"], 0)
            self.assertTrue(r["avisos"])
        with patch.dict(os.environ, {"SAURON_ROTINAS_SEM_REDE": "0"}), patch("inventario.infraestrutura.cve_client._baixar_json", side_effect=IntegracaoCVEError("Sem rede")):
            self.assertEqual(sincronizar_epss()["atualizadas"], 0)
        resposta = {"data": [{"cve": self.v.cve_id, "epss": "0.7", "percentile": "0.95", "date": timezone.now().date().isoformat()}]}
        with patch.dict(os.environ, {"SAURON_ROTINAS_SEM_REDE": "0"}), patch("inventario.infraestrutura.cve_client._baixar_json", return_value=resposta):
            self.assertEqual(sincronizar_epss()["atualizadas"], 1)
        self.v.refresh_from_db()
        self.assertEqual(self.v.epss, .7)
        resposta["data"][0]["epss"] = "nan"
        with patch.dict(os.environ, {"SAURON_ROTINAS_SEM_REDE": "0"}), patch("inventario.infraestrutura.cve_client._baixar_json", return_value=resposta):
            self.assertTrue(sincronizar_epss()["avisos"])
        self.v.refresh_from_db()
        self.assertEqual(self.v.epss, .7)


    def test_renderizacao_pagina(self):
        r = self.client.get(reverse("montecarlo"))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "inventario/montecarlo.html")
        self.assertContains(r, "Estimativa, não previsão")
        self.assertContains(r, "simulacao-montecarlo")
        self.assertContains(r, self.v.cve_id)
        self.assertContains(r, "montecarlo.js")
        self.assertContains(r, 'name="csrfmiddlewaretoken"')
        self.assertContains(r, "Leitura acessível dos resultados")
        self.assertNotContains(r, 'src="https://')
        html = r.content.decode()
        secoes = ["mc-frase", "mc-distribuicao", "mc-excedencia", "mc-corrigir-titulo", "mc-controles-titulo", "mc-tabelas-titulo"]
        posicoes = [html.index(f'id="{s}"') for s in secoes]
        self.assertEqual(posicoes, sorted(posicoes))
        # O laboratório antigo continua com sua API e seu script originais.
        antigo = self.client.get(reverse("dashboard"))
        self.assertContains(antigo, 'id="simulacao-risco"')
        self.assertContains(antigo, reverse("api_simular_risco"))
        self.assertContains(antigo, "simulacao.js")


    def test_cli_utiliza_servico(self):
        from inventario.cli import SauronCLI
        linhas = []
        cli = SauronCLI(entrada=lambda _: json.dumps(self.parametros), saida=linhas.append)
        cli.usuario = self.usuario
        cli.montecarlo_terminal()
        self.assertTrue(any("9 de cada 10" in linha for linha in linhas))
        self.assertTrue(any("Estimativa, não previsão" in linha for linha in linhas))
        cli.usuario = None

    def test_limite_de_trabalho(self):
        with patch("inventario.aplicacao.montecarlo.incidencias_elegiveis", return_value=[self.i] * 81):
            with self.assertRaisesMessage(ValueError, "Cenário muito grande"):
                calcular_montecarlo({**self.parametros, "n": 100000})
