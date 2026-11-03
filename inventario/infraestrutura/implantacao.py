"""Checagens locais de pré-requisitos; não certificam infraestrutura externa."""
from ipaddress import ip_network
from pathlib import Path
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.checks import run_checks


def verificar_implantacao():
    itens = []

    def adicionar(nome, ok, detalhe):
        itens.append({'nome': nome, 'ok': bool(ok), 'detalhe': detalhe})

    erros = run_checks(include_deployment_checks=True)
    adicionar('Django deploy', not erros, ', '.join(e.id for e in erros) or 'Sem avisos ou erros.')
    adicionar('Modo produção', not settings.DEBUG, 'DEBUG deve estar desativado.')
    adicionar('Transporte', settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE and settings.SECURE_SSL_REDIRECT,
              'Cookies seguros e redirecionamento HTTPS obrigatórios.')
    try:
        proxies = [ip_network(c) for c in settings.SAURON_TRUSTED_PROXIES]
        ok = not getattr(settings, 'SECURE_PROXY_SSL_HEADER', None) or bool(proxies)
    except ValueError:
        ok = False
    adicionar('Proxy', ok, 'Cabeçalho encaminhado exige CIDRs de proxies válidos e explícitos.')
    try:
        Fernet(settings.SAURON_BACKUP_KEY.encode())
        ok = True
    except (ValueError, TypeError, AttributeError):
        ok = False
    adicionar('Chave backup', ok, 'Chave Fernet válida; segredo nunca incluído no diagnóstico.')
    dados = settings.DATA_DIR.resolve()
    for nome, valor, arquivo in (
        ('Destino adicional backup', settings.SAURON_BACKUP_DESTINO_ADICIONAL, False),
        ('Âncora de auditoria', settings.SAURON_AUDIT_ANCHOR_PATH, True),
    ):
        caminho = Path(valor).resolve() if valor else None
        pasta = caminho.parent if caminho and arquivo else caminho
        ok = caminho is not None and not caminho.is_relative_to(dados) and pasta.is_dir()
        adicionar(nome, ok, 'Destino configurado fora de DATA_DIR com diretório existente; independência física e retenção exigem validação operacional.')
    adicionar('Verificação da âncora', settings.SAURON_EXIGIR_ANCORA, 'A exigência de âncora deve estar habilitada.')
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    try:
        executor = MigrationExecutor(connection)
        ok = not executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception:
        ok = False
    adicionar('Migrações', ok, 'Banco deve estar acessível e com migrações aplicadas.')
    return {'ok': all(i['ok'] for i in itens), 'verificacoes': itens,
            'validacao_manual': ['TLS e regras de rede reais', 'Restauração em ambiente separado',
                                 'Independência e retenção dos destinos', 'SMTP e fontes externas',
                                 'Calibração com histórico real rotulado']}
