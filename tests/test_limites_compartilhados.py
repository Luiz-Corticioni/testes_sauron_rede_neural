from datetime import timedelta
from unittest.mock import patch
from django.core.cache import cache
from django.utils import timezone
from django.test import Client
from inventario.models import LimiteLogin
from inventario.infraestrutura.limites_login import reservar, concluir
from .base import BancoTeste


class LimitesCompartilhados(BancoTeste):
    def test_reserva_limita_tentativas_em_curso(self):
        for _ in range(5):
            self.assertIsNotNone(reservar('alvo', 'origem'))
        self.assertIsNone(reservar('alvo', 'origem'))
        self.assertIsNotNone(reservar('alvo', 'outra-origem'))

    def test_cache_vazio_e_clientes_diferentes_nao_reiniciam_limite(self):
        with patch('inventario.seguranca.time.sleep'):
            for _ in range(5):
                Client().post('/entrar/', {'username': 'alvo', 'password': 'errada'})
                cache.clear()
            self.assertEqual(Client().post('/entrar/', {'username': 'alvo', 'password': 'errada'}).status_code, 429)

    def test_expiracao_libera_sem_limpar_nova_janela_com_resposta_antiga(self):
        antiga = reservar('alvo', 'origem')
        LimiteLogin.objects.update(expira_em=timezone.now()-timedelta(seconds=1))
        nova = reservar('alvo', 'origem')
        concluir(antiga, True)
        self.assertEqual(LimiteLogin.objects.get(chave=nova['chaves'][0]).quantidade, 1)
        concluir(nova, True)
        self.assertFalse(LimiteLogin.objects.filter(chave=nova['chaves'][0]).exists())

    def test_origem_bloqueia_password_spraying(self):
        for n in range(20):
            self.assertIsNotNone(reservar(f'alvo{n}', 'origem'))
        self.assertIsNone(reservar('mais-um', 'origem'))
        self.assertFalse('alvo' in str(list(LimiteLogin.objects.values())))

    def test_falha_nao_libera_reserva_e_sucesso_libera(self):
        reserva = reservar('alvo', 'origem')
        concluir(reserva, False)
        self.assertEqual(LimiteLogin.objects.get(chave=reserva['chaves'][0]).quantidade, 1)
        concluir(reserva, True)
        self.assertFalse(LimiteLogin.objects.filter(chave=reserva['chaves'][0]).exists())

    def test_cli_respeita_mesmo_limite_persistido(self):
        from inventario.cli import SauronCLI
        for _ in range(5):
            reservar('alvo', 'terminal-local')
        cli = SauronCLI(entrada=lambda _: 'alvo', saida=lambda _: None)
        with patch('inventario.cli.getpass', return_value='errada'), patch('inventario.cli.authenticate') as autenticar:
            self.assertFalse(cli.login())
            autenticar.assert_not_called()

class PrivilegiosTerminal(BancoTeste):
    def test_permissoes_de_cadastro_nao_liberam_backup_e_rotinas(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        from inventario.cli import SauronCLI
        from inventario.cli_operacional import backup, rotinas
        u = get_user_model().objects.create_user('operador-com-permissoes')
        u.user_permissions.add(*Permission.objects.filter(codename__in=['add_ativo', 'change_vulnerabilidade', 'change_user']))
        cli = SauronCLI(entrada=lambda _: '', saida=lambda _: None)
        cli.usuario = u
        with patch('inventario.cli_operacional.backup_sqlite') as salvar, patch('inventario.cli_operacional.executar_rotinas') as executar:
            backup(cli)
            rotinas(cli)
            salvar.assert_not_called()
            executar.assert_not_called()

    def test_superusuario_pode_executar_backup_pelo_terminal(self):
        from inventario.cli import SauronCLI
        from inventario.cli_operacional import backup
        cli = SauronCLI(entrada=lambda _: '', saida=lambda _: None)
        cli.usuario = self.usuario
        with patch('inventario.cli_operacional.backup_sqlite', return_value='backup-cifrado') as salvar:
            backup(cli)
            salvar.assert_called_once()
