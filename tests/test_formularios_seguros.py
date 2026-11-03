
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from inventario.web.forms import IncidenciaForm
from inventario.infraestrutura.auditoria import usar_usuario
from inventario.aplicacao.cadastros import salvar_cadastro
from .base import BancoTeste


class FormulariosSeguros(BancoTeste):
    def test_formulario_encaminha_aceite_para_aprovacao(self):
        dados={"ativo":self.a.pk,"vulnerabilidade":self.v.pk,"status":"ACEITA",
               "detectada_em":timezone.localdate().isoformat(),"justificativa":"Exceção controlada",
               "aceita_ate":timezone.localdate().isoformat()}
        form=IncidenciaForm(data=dados,instance=self.i,usuario=self.usuario)
        with usar_usuario(self.usuario):
            self.assertTrue(form.is_valid(),form.errors)
            i=salvar_cadastro(form.save(commit=False),self.usuario)
        self.assertEqual(i.status,"TRATAMENTO")
        self.assertEqual(i.decisao_pendente,"ACEITA")

    def test_save_direto_nao_fabrica_autorizacao(self):
        operador=get_user_model().objects.create_user("operador-sem-poder")
        self.a.alocacao_excepcional_autorizada=True
        self.a.autorizado_por=self.usuario
        self.a.justificativa_excecao="Tentativa"
        with usar_usuario(operador), self.assertRaises(ValidationError):
            self.a.save()


    def test_admin_declaracao_dedicada_exige_evidencia(self):
        from django.urls import reverse
        url=reverse("admin:inventario_ativo_linha_base",args=[self.a.pk])
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(self.client.post(url,{"saudavel":"on","evidencia_scan":""}).status_code,200)
        self.assertEqual(self.client.post(url,{"saudavel":"on","evidencia_scan":"scan:admin-1"}).status_code,302)
        self.a.refresh_from_db()
        self.assertTrue(self.a.linha_base_saudavel)
        self.assertEqual(self.client.post(url,{}).status_code,302)
        self.a.refresh_from_db()
        self.assertFalse(self.a.linha_base_saudavel)

