"""Casos adversariais dos fluxos completos, além da renderização GET."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from inventario.aplicacao.cadastros import salvar_cadastro
from inventario.aplicacao.operacao import alterar_status
from inventario.models import Software
from .base import BancoTeste


class DecisoesRevisadas(BancoTeste):
    def outro(self, nome="revisor"):
        return get_user_model().objects.create_superuser(nome, "", "senha-revisor-teste")

    def aceitar(self):
        i = alterar_status(self.i.pk, "ACEITA", self.usuario, "Prazo aprovado", timezone.localdate())
        return alterar_status(i.pk, "ACEITA", self.outro())

    def test_renovacao_no_servico_nao_reutiliza_aprovacao(self):
        i = self.aceitar()
        i.aceita_ate = timezone.localdate() + timedelta(days=20)
        i.justificativa = "Novo escopo"
        i = salvar_cadastro(i, self.usuario)
        self.assertEqual(i.status, "TRATAMENTO")
        self.assertEqual(i.decisao_pendente, "ACEITA")
        self.assertIsNone(i.aprovada_por_id)

    def test_operador_nao_troca_software(self):
        operador = get_user_model().objects.create_user("operador")
        operador.user_permissions.add(Permission.objects.get(codename="change_incidencia"))
        self.i.software = Software.objects.create(ativo=self.a, nome="componente", versao="1", fornecedor="Fornecedor")
        with self.assertRaises(ValidationError):
            salvar_cadastro(self.i, operador)

    def test_edicao_inocua_nao_reabre_decisao(self):
        i = self.aceitar()
        aprovador = i.aprovada_por_id
        from inventario.web.forms import IncidenciaForm
        dados = {"ativo":i.ativo_id, "vulnerabilidade":i.vulnerabilidade_id,
                 "status":"ACEITA", "detectada_em":i.detectada_em.isoformat(),
                 "justificativa":i.justificativa, "aceita_ate":i.aceita_ate.isoformat(),
                 "observacoes":"Atualização administrativa"}
        form = IncidenciaForm(dados, instance=i, usuario=self.usuario)
        self.assertTrue(form.is_valid(), form.errors)
        salvo = salvar_cadastro(form.save(commit=False), self.usuario)
        self.assertEqual(salvo.status, "ACEITA")
        self.assertEqual(salvo.aprovada_por_id, aprovador)

    def test_aprovador_delegado_tem_fila_e_nao_precisa_ser_solicitante(self):
        alterar_status(self.i.pk, "ACEITA", self.usuario, "Prazo", timezone.localdate())
        aprovador = get_user_model().objects.create_user("aprovador")
        aprovador.user_permissions.add(*Permission.objects.filter(codename__in=[
            "change_incidencia", "aprovar_aceite_risco", "view_incidencia", "view_vulnerabilidade",
            "view_ativo", "view_alerta"]))
        self.autenticar(aprovador)
        fila = self.client.get(reverse("alertas"), {"pendentes":"1"})
        self.assertContains(fila, "Aprovar decisão")
        resposta = self.client.post(reverse("decidir_pendencia", args=[self.i.pk]), {"acao":"aprovar"})
        self.assertEqual(resposta.status_code, 302)
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, "ACEITA")

    def test_devolver_exige_motivo_e_outro_usuario(self):
        from inventario.aplicacao.operacao import decidir_pendencia
        alterar_status(self.i.pk, "CORRIGIDA", self.usuario, evidencia="scan:1")
        revisor = self.outro()
        with self.assertRaises(ValidationError):
            decidir_pendencia(self.i.pk, False, revisor, "")
        with self.assertRaises(ValidationError):
            decidir_pendencia(self.i.pk, True, self.usuario)
        decidir_pendencia(self.i.pk, False, revisor, "Evidência insuficiente")
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, "TRATAMENTO")
        self.assertFalse(self.i.decisao_pendente)

