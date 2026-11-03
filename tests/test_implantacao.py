from io import StringIO
import json
from pathlib import Path
from unittest.mock import patch
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management import call_command, CommandError
from django.test import override_settings
from inventario.infraestrutura.implantacao import verificar_implantacao
from .base import BancoTeste


class Implantacao(BancoTeste):
    def config(self):
        raiz = settings.DATA_DIR
        for pasta in ('dados', 'copia', 'ancoras'):
            (raiz/pasta).mkdir(exist_ok=True)
        return dict(DEBUG=False, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
                    SECURE_SSL_REDIRECT=True, DATA_DIR=raiz/'dados', SAURON_BACKUP_KEY=Fernet.generate_key().decode(),
                    SAURON_BACKUP_DESTINO_ADICIONAL=str(raiz/'copia'), SAURON_AUDIT_ANCHOR_PATH=raiz/'ancoras'/'cadeia.jsonl',
                    SAURON_EXIGIR_ANCORA=True, SAURON_TRUSTED_PROXIES=[], SECURE_PROXY_SSL_HEADER=None)

    @patch('inventario.infraestrutura.implantacao.run_checks', return_value=[])
    def test_configuracao_completa_tem_ressalvas_operacionais(self, checks):
        with override_settings(**self.config()):
            r = verificar_implantacao()
        self.assertTrue(r['ok'], r)
        self.assertIn('Restauração em ambiente separado', r['validacao_manual'])

    @patch('inventario.infraestrutura.implantacao.run_checks', return_value=[])
    def test_destinos_internos_e_chave_invalida_reprovados_sem_expor_segredo(self, checks):
        config = self.config()
        config.update(SAURON_BACKUP_DESTINO_ADICIONAL=str(Path(config['DATA_DIR'])/'backup'),
                      SAURON_AUDIT_ANCHOR_PATH=Path(config['DATA_DIR'])/'ancoras.jsonl', SAURON_BACKUP_KEY='segredo-invalido-nao-exibir')
        saida = StringIO()
        with override_settings(**config), self.assertRaises(CommandError):
            call_command('verificar_implantacao', json=True, stdout=saida)
        r = json.loads(saida.getvalue())
        self.assertFalse(r['ok'])
        self.assertNotIn('segredo-invalido', saida.getvalue())
        erros = [i['nome'] for i in r['verificacoes'] if not i['ok']]
        for nome in ('Destino adicional backup', 'Âncora de auditoria', 'Chave backup'):
            self.assertIn(nome, erros)

    @patch('inventario.infraestrutura.implantacao.run_checks', return_value=[])
    def test_proxy_sem_cidr_reprovado(self, checks):
        config = self.config()
        config['SECURE_PROXY_SSL_HEADER'] = ('HTTP_X_FORWARDED_PROTO', 'https')
        with override_settings(**config):
            r = verificar_implantacao()
        self.assertFalse(next(i for i in r['verificacoes'] if i['nome']=='Proxy')['ok'])
