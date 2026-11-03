from unittest.mock import patch
from .base import BancoTeste


class FormulariosRevisados(BancoTeste):
    def test_post_vazio_exibe_erros(self):
        for rota in ("/software/", "/importar/"):
            resposta = self.client.post(rota, {})
            self.assertEqual(resposta.status_code, 200)
            self.assertTrue(resposta.context["form"].errors)


    def test_concorrencia_no_cadastro_software_vira_erro_legivel(self):
        from django.db import IntegrityError
        with patch("inventario.aplicacao.servicos.salvar_cadastro", side_effect=IntegrityError("duplicado")):
            resposta = self.client.post("/software/", {"ativo":self.a.pk, "nome":"Aplicação", "versao":"1", "fornecedor":"Equipe"})
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.context["form"].errors)

