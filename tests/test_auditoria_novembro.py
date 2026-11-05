from inventario.models import Vulnerabilidade
from .base import BancoTeste


class CadastroAdministrativo(BancoTeste):
    def dados(self):
        return {'id': 'VUL-RCE-9001', 'descricao': 'Caso de teste', 'categoria': 'RCE', 'cvss': '1.0',
                'cvss_versao': '3.1', 'cvss_vetor': 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
                'fonte': 'Manual', 'faixas_afetadas': '[]', 'vex': '[]', 'cvss_v4': '{}', 'referencias': '[]'}

    def test_admin_recalcula_cvss_a_partir_do_vetor(self):
        resposta = self.client.post('/admin/inventario/vulnerabilidade/add/', self.dados())
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Vulnerabilidade.objects.get(pk='VUL-RCE-9001').cvss, 9.8)

    def test_admin_rejeita_id_que_quebraria_calculo_de_risco(self):
        dados = self.dados()
        dados['id'] = 'ID-INVALIDO'
        resposta = self.client.post('/admin/inventario/vulnerabilidade/add/', dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'ID deve corresponder')
        self.assertFalse(Vulnerabilidade.objects.filter(pk='ID-INVALIDO').exists())

    def test_admin_nao_permite_editar_identidade_existente(self):
        resposta = self.client.get(f'/admin/inventario/vulnerabilidade/{self.v.pk}/change/')
        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, 'name="id"')
