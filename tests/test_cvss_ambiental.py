
from unittest import TestCase
from .base import BancoTeste
from inventario.matematica.cvss import CalculadoraCVSS31


class M6(TestCase):
    def test_ambiental_referencias_first(self):
        vetor="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        self.assertEqual(CalculadoraCVSS31.ambiental(vetor,1,1,1).score,8.0)
        self.assertEqual(CalculadoraCVSS31.ambiental(vetor,2,2,2).score,9.8)
        self.assertEqual(CalculadoraCVSS31.ambiental(vetor,4,4,4).score,9.8)
        self.assertEqual(CalculadoraCVSS31.ambiental(vetor+"/MC:N/MI:N/MA:N",4,4,4).score,0)
        with self.assertRaises(ValueError):
            CalculadoraCVSS31.ambiental(vetor,5,1,1)



    def test_ambiental_128_combinacoes_contra_equacao_literal(self):
        from itertools import product
        from tests.test_nao_regressao import roundup
        for escopo,c,i,a in product(("U","C"),range(1,5),range(1,5),range(1,5)):
            fatores={1:.5,2:1,3:1.5,4:1.5}
            miss=min(1-(1-.56*fatores[c])*(1-.56*fatores[i])*(1-.56*fatores[a]),.915)
            impacto=6.42*miss if escopo=="U" else 7.52*(miss-.029)-3.25*(miss*.9731-.02)**13
            explorabilidade=8.22*.85*.77*.85*.85
            esperado=roundup(roundup(min((impacto+explorabilidade)*(1 if escopo=="U" else 1.08),10)))
            vetor=f"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:{escopo}/C:H/I:H/A:H"
            with self.subTest(escopo=escopo,cia=(c,i,a)):
                self.assertEqual(CalculadoraCVSS31.ambiental(vetor,c,i,a).score,esperado)


class AmbientalSLA(BancoTeste):
    def test_sla_usa_ambiental(self):
        from inventario.aplicacao.operacao import prazo_sla
        self.v.kev=False
        self.v.cvss=9.8
        self.v.cvss_vetor="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        self.v.save()
        self.i.vulnerabilidade=self.v
        self.assertEqual((prazo_sla(self.i)-self.i.detectada_em).days,30)
