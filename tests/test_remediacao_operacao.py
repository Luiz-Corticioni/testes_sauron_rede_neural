
from datetime import timedelta, date
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from django.utils import timezone
from inventario.aplicacao.operacao import alterar_status
from inventario.models import Tolerancia
from .base import BancoTeste


class R7(BancoTeste):
    def test_tolerancia_tem_teto(self):
        with self.assertRaises(ValidationError):
            Tolerancia.objects.create(linhagem="teste", ativo=self.a, por=self.usuario,
                                     motivo="teste", valida_ate=date(9999,12,31))

    def test_aceite_tem_teto(self):
        for dias in (91, 100000):
            with self.subTest(dias=dias), self.assertRaises(ValidationError):
                alterar_status(self.i.pk, "ACEITA", self.usuario, "exceção",
                               timezone.localdate()+timedelta(days=dias))

    def test_aceite_alto_exige_segundo_aprovador(self):
        segundo = get_user_model().objects.create_superuser("segundo", "", "senha-segundo")
        i = alterar_status(self.i.pk, "ACEITA", self.usuario, "exceção", timezone.localdate())
        self.assertEqual(i.status, "TRATAMENTO")
        self.assertEqual(i.decisao_pendente, "ACEITA")
        with self.assertRaises(ValidationError):
            alterar_status(i.pk, "ACEITA", self.usuario, "exceção", timezone.localdate())
        i = alterar_status(i.pk, "ACEITA", segundo)
        self.assertEqual(i.status, "ACEITA")
        self.assertEqual(i.aceita_por, self.usuario)
        self.assertEqual(i.aprovada_por, segundo)

    def test_correcao_evidencia_e_confirmacao(self):
        segundo = get_user_model().objects.create_superuser("segundo", "", "senha-segundo")
        for status in ("CORRIGIDA", "MITIGADA"):
            with self.subTest(status=status), self.assertRaises(ValidationError):
                alterar_status(self.i.pk, status, self.usuario)
        i = alterar_status(self.i.pk, "CORRIGIDA", self.usuario, evidencia="scan:sem-falha")
        self.assertEqual(i.status, "TRATAMENTO")
        with self.assertRaises(ValidationError):
            alterar_status(i.pk, "CORRIGIDA", self.usuario)
        i = alterar_status(i.pk, "CORRIGIDA", segundo)
        self.assertEqual(i.status, "CORRIGIDA")

    def test_save_direto_nao_contorna_evidencia(self):
        self.i.status = "CORRIGIDA"
        with self.assertRaises(ValidationError):
            self.i.save()

    def test_permissao_do_segundo(self):
        segundo = get_user_model().objects.create_user("segundo")
        from django.contrib.auth.models import Permission
        segundo.user_permissions.add(Permission.objects.get(codename="change_incidencia"))
        alterar_status(self.i.pk, "ACEITA", self.usuario, "exceção", timezone.localdate())
        with self.assertRaises(PermissionDenied):
            alterar_status(self.i.pk, "ACEITA", segundo)


class R11(BancoTeste):
    def test_reconhecer_suprime_sete_dias(self):
        from inventario.aplicacao.operacao import emitir_alerta, reconhecer_alerta
        from inventario.models import Alerta
        a = emitir_alerta("SLA", self.a, "prazo", "Vencido")
        reconhecer_alerta(a.pk, self.usuario)
        self.assertEqual(emitir_alerta("SLA", self.a, "prazo", "Vencido").pk, a.pk)
        self.assertEqual(Alerta.objects.filter(chave="prazo").count(), 1)
        Alerta.objects.filter(pk=a.pk).update(suprimido_ate=timezone.now()-timedelta(seconds=1))
        self.assertNotEqual(emitir_alerta("SLA", self.a, "prazo", "Vencido").pk, a.pk)

