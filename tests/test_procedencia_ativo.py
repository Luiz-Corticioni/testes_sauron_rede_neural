from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from inventario.models import DocumentoInventario, RelatorioScanner
from .base import BancoTeste


class ProcedenciaAtivo(BancoTeste):
    def setUp(self):
        super().setUp()
        DocumentoInventario.objects.create(ativo=self.a, tipo='SBOM', versao=1, escopo='escopo-privado',
            origem='fonte-documento-privada', sha256='1'*64, conteudo='{}', importado_por=self.usuario)
        RelatorioScanner.objects.create(ativo=self.a, escopo='scanner-privado', origem='origem-scanner-privada',
            observado_em=timezone.now(), sha256='2'*64, achados=[], importado_por=self.usuario)

    def test_fontes_autorizadas_sao_exibidas_com_datas_distintas(self):
        resposta = self.client.get(reverse('detalhe_ativo', args=[self.a.pk]))
        self.assertContains(resposta, 'fonte-documento-privada')
        self.assertContains(resposta, 'origem-scanner-privada')
        self.assertContains(resposta, 'data é da importação')
        self.assertContains(resposta, 'não comprovam afetação')
        self.assertEqual(len(resposta.context['procedencia']['documentos']), 1)
        self.assertEqual(len(resposta.context['procedencia']['scanners']), 1)

    def test_usuario_sem_permissoes_nao_ve_origem_nem_contagens(self):
        usuario = get_user_model().objects.create_user('leitor-procedencia', password='senha-teste-123')
        usuario.user_permissions.add(Permission.objects.get(content_type__app_label='inventario', codename='view_ativo'))
        self.autenticar(usuario)
        resposta = self.client.get(reverse('detalhe_ativo', args=[self.a.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Documentos e relatórios exigem permissões específicas.')
        self.assertNotContains(resposta, 'fonte-documento-privada')
        self.assertNotContains(resposta, 'origem-scanner-privada')
        self.assertNotIn('documentos', resposta.context['procedencia'])
        self.assertNotIn('scanners', resposta.context['procedencia'])

    def test_fonte_ausente_nao_e_retratada_como_seguranca(self):
        resposta = self.client.get(reverse('detalhe_ativo', args=[self.b.pk]))
        self.assertContains(resposta, 'Nenhum relatório importado para este ativo.')
        self.assertContains(resposta, 'Ausência de evidência não comprova segurança')
