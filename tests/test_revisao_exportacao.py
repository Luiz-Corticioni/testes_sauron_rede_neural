import json
from django.conf import settings
from django.core.management import call_command
from inventario.models import Software
from .base import BancoTeste


class ExportacaoRevisada(BancoTeste):
    def test_exportacao_inclui_componentes_e_evidencias(self):
        componente = Software.objects.create(ativo=self.a, fornecedor="Equipe", nome="Motor", versao="2.0")
        self.i.software = componente
        self.i.evidencia = "Relatório de teste 123"
        self.i.save()
        caminho = settings.DATA_DIR / "inventario-completo.json"
        call_command("exportar_inventario", saida=str(caminho))
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        self.assertEqual(dados["formato"], "sauron.inventario/v2")
        self.assertEqual(dados["colecoes"]["software"][0]["id"], componente.pk)
        self.assertEqual(dados["colecoes"]["incidencia"][0]["evidencia"], self.i.evidencia)
        self.assertIn("sala", dados["colecoes"])
        self.assertNotIn("user", dados["colecoes"])
        self.assertNotIn("registroauditoria", dados["colecoes"])


    def test_exportacao_negada_nao_registra_sucesso(self):
        from django.contrib.auth import get_user_model
        from inventario.models import RegistroAuditoria
        leitor = get_user_model().objects.create_user("sem-exportacao", password="teste")
        self.autenticar(leitor)
        resposta = self.client.get("/exportar/ativos.csv")
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(RegistroAuditoria.objects.filter(acao="EXPORTAR_CSV").exists())
        self.autenticar(self.usuario)
        resposta = self.client.get("/exportar/ativos.csv")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(RegistroAuditoria.objects.filter(acao="EXPORTAR_CSV").count(), 1)

