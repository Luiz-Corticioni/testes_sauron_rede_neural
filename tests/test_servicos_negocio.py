from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from inventario.models import MembroPerimetro, PerimetroRelacoes, RegistroAuditoria, ServicoNegocio
from .base import BancoTeste


class ServicosNegocio(BancoTeste):
    def setUp(self):
        super().setUp()
        self.perimetro = PerimetroRelacoes.objects.create(nome='pedidos', descricao='Loja de exemplo',
            criada_por=self.usuario, atualizada_por=self.usuario)
        MembroPerimetro.objects.create(perimetro=self.perimetro, ativo=self.a)
        self.dados = {'nome': 'Vendas', 'descricao': 'Serviço de pedidos', 'responsavel': 'Equipe',
                      'impacto_interrupcao': 'Pedidos indisponíveis', 'criticidade': '4',
                      'objetivo_recuperacao_horas': '2', 'perimetro': self.perimetro.pk}

    def test_cadastro_e_ficha_reutilizam_perimetro_e_auditoria(self):
        resposta = self.client.post(reverse('servico_negocio_novo'), self.dados, follow=True)
        self.assertEqual(resposta.status_code, 200)
        servico = ServicoNegocio.objects.get(nome='Vendas')
        self.assertEqual(servico.criado_por, self.usuario)
        self.assertContains(resposta, self.a.hostname)
        self.assertContains(resposta, 'CVE-2021-44228')
        self.assertContains(resposta, 'não comprova conectividade')
        self.assertTrue(RegistroAuditoria.objects.filter(acao='CRIAR', entidade='ServicoNegocio',
            entidade_id=str(servico.pk), usuario=self.usuario).exists())

    def test_leitor_do_servico_sem_permissao_nao_ve_cves(self):
        from inventario.aplicacao.cobertura import LEITURA
        self.client.post(reverse('servico_negocio_novo'), self.dados)
        servico = ServicoNegocio.objects.get(nome='Vendas')
        usuario = get_user_model().objects.create_user('leitor-sem-cve', password='senha-teste-123')
        nomes = [p.split('.')[1] for p in LEITURA] + ['view_serviconegocio']
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label='inventario', codename__in=nomes))
        self.autenticar(usuario)
        resposta = self.client.get(reverse('servico_negocio', args=[servico.pk]))
        self.assertContains(resposta, self.a.hostname)
        self.assertContains(resposta, 'Incidências e vulnerabilidades exigem permissões específicas.')
        self.assertNotContains(resposta, 'CVE-2021-44228')

    def test_leitor_nao_pode_cadastrar_nem_acessar_sem_cobertura(self):
        from inventario.aplicacao.cobertura import LEITURA
        usuario = get_user_model().objects.create_user('leitor-servico', password='senha-teste-123')
        nomes = [permissao.split('.')[1] for permissao in LEITURA] + ['view_serviconegocio']
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label='inventario', codename__in=nomes))
        self.autenticar(usuario)
        self.assertEqual(self.client.get(reverse('servicos_negocio')).status_code, 200)
        self.assertEqual(self.client.post(reverse('servico_negocio_novo'), self.dados).status_code, 403)
        usuario.user_permissions.remove(Permission.objects.get(content_type__app_label='inventario', codename='view_revisaocobertura'))
        usuario = get_user_model().objects.get(pk=usuario.pk)
        self.autenticar(usuario)
        self.assertEqual(self.client.get(reverse('servicos_negocio')).status_code, 403)
        self.assertFalse(ServicoNegocio.objects.exists())

    def test_dados_invalidos_nao_sao_salvos(self):
        self.dados['criticidade'] = '5'
        resposta = self.client.post(reverse('servico_negocio_novo'), self.dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(ServicoNegocio.objects.exists())

    def test_edicao_concorrente_nao_sobrescreve_alteracao(self):
        self.client.post(reverse('servico_negocio_novo'), self.dados)
        servico = ServicoNegocio.objects.get(nome='Vendas')
        versao = servico.atualizado_em.isoformat()
        url = reverse('servico_negocio_editar', args=[servico.pk])
        primeira = self.dados | {'responsavel': 'Equipe nova', 'versao': versao}
        self.assertEqual(self.client.post(url, primeira).status_code, 302)
        resposta = self.client.post(url, self.dados | {'responsavel': 'Dado antigo', 'versao': versao})
        self.assertContains(resposta, 'O serviço mudou')
        servico.refresh_from_db()
        self.assertEqual(servico.responsavel, 'Equipe nova')

    def test_sem_permissao_de_alterar_nao_edita(self):
        from inventario.aplicacao.cobertura import LEITURA
        self.client.post(reverse('servico_negocio_novo'), self.dados)
        servico = ServicoNegocio.objects.get(nome='Vendas')
        usuario = get_user_model().objects.create_user('leitor-sem-edicao', password='senha-teste-123')
        nomes = [p.split('.')[1] for p in LEITURA] + ['view_serviconegocio']
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label='inventario', codename__in=nomes))
        self.autenticar(usuario)
        self.assertEqual(self.client.get(reverse('servico_negocio_editar', args=[servico.pk])).status_code, 403)

    def test_backup_inclui_servico_e_perimetro(self):
        import json
        from cryptography.fernet import Fernet
        from django.test import override_settings
        from inventario.infraestrutura.backup import backup_sqlite
        self.client.post(reverse('servico_negocio_novo'), self.dados)
        chave = Fernet.generate_key()
        with override_settings(SAURON_BACKUP_KEY=chave.decode(), SAURON_BACKUP_DESTINO_ADICIONAL=''):
            registros = json.loads(Fernet(chave).decrypt(backup_sqlite().read_bytes()))
        servico = next(item for item in registros if item['model'] == 'inventario.serviconegocio')
        self.assertEqual(servico['fields']['perimetro'], self.perimetro.pk)
        self.assertTrue(any(item['model'] == 'inventario.membroperimetro' for item in registros))
