from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from inventario.models import Incidencia
from .base import BancoTeste


class EventosOlho(BancoTeste):
    def test_nova_incidencia_critica_e_devolvida_uma_vez_com_cursor(self):
        cursor = self.client.get(reverse('dashboard')).context['cursor_olho']
        Incidencia.objects.create(id='INC-CRITICA-1', ativo=self.b, vulnerabilidade=self.v)
        resposta = self.client.get(reverse('eventos_olho'), {'cursor': cursor})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta['Cache-Control'], 'no-store')
        dados = resposta.json()
        self.assertEqual(len(dados['eventos']), 1)
        self.assertEqual(dados['eventos'][0]['cve'], 'CVE-2021-44228')
        self.assertEqual(dados['eventos'][0]['url'], reverse('detalhe_ativo', args=[self.b.pk]))
        self.assertFalse(self.client.get(reverse('eventos_olho'), {'cursor': dados['cursor']}).json()['eventos'])
        self.assertEqual(self.client.get(reverse('eventos_olho'), {'cursor': 'invalido'}).status_code, 400)

    def test_usuario_sem_auditoria_nao_acessa_eventos(self):
        usuario = get_user_model().objects.create_user('sem-auditoria')
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label='inventario',
            codename__in=['view_ativo', 'view_vulnerabilidade', 'view_incidencia', 'view_dependencia']))
        self.autenticar(usuario)
        self.assertNotIn('cursor_olho', self.client.get(reverse('dashboard')).context)
        self.assertEqual(self.client.get(reverse('eventos_olho'), {'cursor': 'x'}).status_code, 403)
