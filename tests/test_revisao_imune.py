from inventario.aplicacao.imune_padroes import antigenos, aprender
from inventario.dominio.matching import avaliar_componente, comparar_versoes
from inventario.models import Software, Anticorpo, Incidencia
from .base import BancoTeste


class ImuneRevisado(BancoTeste):
    def test_todos_componentes_e_reaprendizagem_contada(self):
        for n in range(17):
            Software.objects.create(ativo=self.a, fornecedor="Equipe", nome=f"Programa {n}", versao="1")
        self.assertEqual(len(antigenos(self.a, self.v)), 17)
        self.assertGreater(aprender([]), 0)
        memoria = Anticorpo.objects.get(origem=self.i)
        memoria.estado = "ARQUIVADO"
        memoria.save()
        Incidencia.objects.filter(pk=self.i.pk).update(imune_aprendida=False)
        self.assertEqual(aprender([]), 1)


    def test_vex_alheio_nao_decide_e_prerelease_com_zero(self):
        cpe = "cpe:2.3:a:apache:log4j:*:*:*:*:*:*:*:*"
        vex = [{"cpe23":cpe.replace("log4j", "tomcat"), "status":"not_affected", "justificativa":"Investigado"}]
        self.assertIsNone(avaliar_componente(cpe, "2.14", [], vex))
        self.assertLess(comparar_versoes("1.0.0rc1", "1.0"), 0)

