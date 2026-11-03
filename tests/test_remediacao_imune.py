"""Reproduções dos achados I-1 a I-9, sem consultas externas."""

from datetime import timedelta


from django.test import override_settings

from django.utils import timezone


from inventario.aplicacao.imune import executar_ciclo

from inventario.aplicacao.imune_padroes import aprender

from inventario.models import Anticorpo, Incidencia, Software, SugestaoImune

from .base import BancoTeste


class MemoriaTeste(BancoTeste):

    def preparar(self):

        for ativo in (self.a, self.b):

            Software.objects.create(ativo=ativo, nome="log4j", versao="2.14.1", fornecedor="Apache",

                cpe23="cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*")

        aprender([])

        return Anticorpo.objects.get(origem=self.i)


class R1(MemoriaTeste):

    def test_cpe_exato_dia_60_sugere(self):

        m = self.preparar()

        m.reforcado_em = timezone.now() - timedelta(days=60)

        m.save()

        executar_ciclo()

        self.assertTrue(SugestaoImune.objects.filter(ativo=self.b, vulnerabilidade=self.v).exists())

        m.refresh_from_db()

        self.assertEqual(m.estado, "ATIVO")


    def test_arquivo_e_perda_reaprendem(self):

        m = self.preparar()

        m.estado = "ARQUIVADO"

        m.save()

        self.i.refresh_from_db()

        self.assertFalse(self.i.imune_aprendida)

        executar_ciclo()

        m.refresh_from_db()

        self.assertEqual(m.estado, "ATIVO")

        m.delete()

        self.i.refresh_from_db()

        self.assertFalse(self.i.imune_aprendida)

        executar_ciclo()

        self.assertTrue(Anticorpo.objects.filter(origem=self.i, estado="ATIVO").exists())


    @override_settings(IMUNE_PISO=.4)

    def test_nao_apaga_memoria_inativa(self):

        m = self.preparar()

        Incidencia.objects.filter(pk=self.i.pk).update(status="MITIGADA")

        m.reforcado_em = timezone.now() - timedelta(days=200)

        m.save()

        executar_ciclo()

        m.refresh_from_db()

        self.assertEqual(m.estado, "ARQUIVADO")


class R2(MemoriaTeste):

    def test_cinquenta_descartados_nao_bloqueiam_aprendizado(self):

        m = self.preparar()

        for n in range(50):

            Anticorpo.objects.create(vulnerabilidade=self.v, prototipo=m.prototipo,

                estado="DESCARTADO", chave=f"descartado{n}", linhagem=f"descartado{n}")

        m.delete()

        self.assertGreater(aprender([]), 0)

        self.assertTrue(Anticorpo.objects.filter(origem=self.i, estado="ATIVO").exists())


    @override_settings(IMUNE_MAX_POPULACAO=2)

    def test_despeja_menor_forca_e_alerta(self):

        from inventario.models import Alerta

        m = self.preparar()

        m.forca = .1

        m.save()

        Incidencia.objects.create(id="INC-3", ativo=self.b, vulnerabilidade=self.v)

        aprender([])

        m.refresh_from_db()

        self.assertEqual(m.estado, "ARQUIVADO")

        self.assertEqual(Anticorpo.objects.filter(estado="ATIVO").count(), 2)

        self.assertTrue(Alerta.objects.filter(chave="capacidade-imune").exists())


class R3(MemoriaTeste):
    def test_aprende_software_afetado_segundo(self):
        Software.objects.create(ativo=self.a, nome="aaa", versao="1", fornecedor="Outro")
        afetado = Software.objects.create(ativo=self.a, nome="log4j", versao="2.14.1", fornecedor="Apache")
        Software.objects.create(ativo=self.a, nome="zzz", versao="3", fornecedor="Outro")
        self.i.software = afetado
        self.i.save()
        aprender([])
        self.assertEqual(Anticorpo.objects.get(origem=self.i).prototipo["familia"], "log4j")

    def test_recusa_componente_de_outro_ativo(self):
        from django.core.exceptions import ValidationError
        self.i.software = Software.objects.create(ativo=self.b, nome="log4j", versao="2", fornecedor="Apache")
        with self.assertRaises(ValidationError):
            self.i.save()


class R5(MemoriaTeste):
    def test_autoria_persiste_com_auditoria(self):
        from inventario.aplicacao.imune import decidir_sugestao
        from inventario.models import RegistroAuditoria
        self.preparar()
        executar_ciclo()
        s = SugestaoImune.objects.get(ativo=self.b, vulnerabilidade=self.v)
        decidir_sugestao(s.pk, False, self.usuario, "Scan não encontrou o componente")
        s.refresh_from_db()
        self.assertEqual(s.decidido_por, self.usuario)
        self.assertIsNotNone(s.decidido_em)
        registro = RegistroAuditoria.objects.filter(entidade="SugestaoImune", entidade_id=str(s.pk)).order_by("id").last()
        self.assertEqual(registro.detalhes["decidido_por_id"], s.decidido_por_id)
        self.assertEqual(registro.detalhes["decidido_em"], s.decidido_em.isoformat(timespec="milliseconds").replace("+00:00", "Z"))


class R6(MemoriaTeste):
    def test_revogar_base_reativa(self):
        from inventario.aplicacao.cadastros import salvar_cadastro
        m = self.preparar()
        self.b.linha_base_saudavel = True
        self.b.evidencia_scan = "scanner:42"
        salvar_cadastro(self.b, self.usuario)
        executar_ciclo()
        m.refresh_from_db()
        self.assertEqual(m.estado, "DESCARTADO")
        self.b.linha_base_saudavel = False
        salvar_cadastro(self.b, self.usuario)
        m.refresh_from_db()
        self.assertEqual(m.estado, "ATIVO")

    def test_evidencia_e_permissao_obrigatorias(self):
        from django.core.exceptions import ValidationError, PermissionDenied
        from django.contrib.auth import get_user_model
        from inventario.aplicacao.cadastros import salvar_cadastro
        self.a.linha_base_saudavel = True
        with self.assertRaises(ValidationError):
            salvar_cadastro(self.a, self.usuario)
        self.a.evidencia_scan = "scan:1"
        operador = get_user_model().objects.create_user("operador")
        from django.contrib.auth.models import Permission
        operador.user_permissions.add(Permission.objects.get(codename="change_ativo"))
        with self.assertRaises((ValidationError, PermissionDenied)):
            salvar_cadastro(self.a, operador)

