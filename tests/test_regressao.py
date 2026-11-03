import importlib
import json
from pathlib import Path
from django.core.management import call_command
from django.urls import reverse
from inventario.aplicacao.risco import carregar_modelo_risco, parametros_risco
from inventario.models import Ativo, Vulnerabilidade, Incidencia, Dependencia
from inventario.infraestrutura.importacao import importar_csv
from inventario.infraestrutura.exportacao import colecoes_json
from .base import BancoTeste


class Regressao(BancoTeste):
    def test_golden(self):
        obtido = {}
        for perfil in ("puro", "operacional"):
            modelo, _ = carregar_modelo_risco(perfil)
            api = self.client.get(reverse("api_risco"), {"perfil": perfil})
            self.assertEqual(api.status_code, 200)
            resultado = api.json()
            resultado.pop("versao_dados")  # Hash inclui timestamps, não é saída numérica.
            simulacao = self.client.post(reverse("api_simular_risco"),
                data=json.dumps({"perfil": perfil, "incidencias_corrigidas": [self.i.pk]}), content_type="application/json")
            self.assertEqual(simulacao.status_code, 200)
            obtido[perfil] = {"modelo": modelo.calcular(**parametros_risco(perfil)).to_dict(),
                              "api": resultado, "simulacao": simulacao.json()}
        caminho = Path(__file__).with_name("golden_risco.json")
        self.assertEqual(obtido, json.loads(caminho.read_text(encoding="utf-8")))

    def test_rotas_nomeadas_get(self):
        from inventario.web.urls import urlpatterns
        for padrao in urlpatterns:
            if not padrao.name:
                continue
            kwargs = {}
            for chave in padrao.pattern.converters:
                if chave == "colecao":
                    kwargs[chave] = "ativos"
                elif chave == "cve_id":
                    kwargs[chave] = self.v.cve_id
                elif chave == "pk":
                    nome = padrao.name
                    obj = (self.v if "vulnerabilidade" in nome and "ativo" not in nome else
                           self.i if "incidencia" in nome else self.dep if "dependencia" in nome else
                           self.sala if "sala" in nome else self.a)
                    if nome.startswith(("editar_", "remover_")):
                        from django.apps import apps
                        modelo = apps.get_model("inventario", nome.split("_", 1)[1])
                        existente = modelo.objects.first()
                        kwargs[chave] = existente.pk if existente else (999 if modelo._meta.pk.get_internal_type() in {"BigAutoField", "AutoField"} else "INEXISTENTE")
                    else:
                        kwargs[chave] = obj.pk if padrao.pattern.converters[chave].__class__.__name__ != "IntConverter" else 999
            with self.subTest(rota=padrao.name):
                resposta = self.client.get(reverse(padrao.name, kwargs=kwargs))
                self.assertIn(resposta.status_code, [200, 302, 400, 404, 405, 422, 503])
                if resposta.status_code == 503:
                    self.assertIn(padrao.name, ["api_nvd", "api_kev", "api_consultar_cves"])

    def test_saude_entrada(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/saude/").status_code, 200)
        self.assertEqual(self.client.get("/entrar/").status_code, 200)

    def test_round_trip(self):
        from django.conf import settings
        import io
        call_command("exportar_json", saida=str(settings.DATA_DIR), stdout=io.StringIO())
        modelos = {"equipamentos.json": Ativo, "vulnerabilidades.json": Vulnerabilidade,
                   "incidencias.json": Incidencia, "dependencias.json": Dependencia}
        for nome, modelo in modelos.items():
            for dados in json.loads((settings.DATA_DIR / nome).read_text(encoding="utf-8")):
                dominio = modelo.objects.get(pk=dados["id"]).para_dominio() if "id" in dados else self.dep.para_dominio()
                novo = modelo.de_dominio(dominio)
                self.assertEqual(novo.para_dominio().to_dict(), dados)
        texto = "tipo,nome,fabricante,sala,responsavel,confidencialidade,exposto_internet\n1,Importado,Dell,SALA-TESTE,Equipe,4,true\n"
        r = importar_csv(texto, self.usuario, dry_run=False)
        self.assertEqual(r["erros"], [])
        self.assertEqual(r["gravados"], 1)
        importado = Ativo.objects.get(nome="Importado")
        self.assertEqual(importado.para_dominio().to_dict(), Ativo.de_dominio(importado.para_dominio()).para_dominio().to_dict())
        self.assertEqual(len(colecoes_json()["equipamentos.json"]), 3)

    def test_import_cli(self):
        self.assertTrue(importlib.import_module("inventario.cli").SauronCLI)
