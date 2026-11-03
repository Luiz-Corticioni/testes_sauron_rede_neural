"""Inspeção operacional de instalação, sem acessar serviços externos ou expor segredos."""

import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.template.loader import get_template


def verificar_instalacao():
    verificacoes = []

    def verificar(nome, funcao):
        try:
            detalhe = funcao()
            verificacoes.append({'nome': nome, 'ok': True, 'detalhe': detalhe})
        except Exception as erro:
            # O comando precisa continuar para mostrar todos os problemas de instalação.
            # Não imprime caminhos do banco, credenciais ou conteúdo de arquivos privados.
            verificacoes.append({'nome': nome, 'ok': False, 'detalhe': type(erro).__name__})

    def escrita():
        with NamedTemporaryFile(dir=settings.DATA_DIR, prefix='.diagnostico-') as f:
            f.write(b'sauron')
            f.flush()
        return 'Diretório de dados permite gravação.'

    def banco():
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            if cursor.fetchone() != (1,):
                raise RuntimeError("Banco não respondeu ao diagnóstico.")
        executor = MigrationExecutor(connection)
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            raise RuntimeError('Migrações pendentes')
        return 'Banco acessível e migrações aplicadas.'

    raiz = Path(__file__).resolve().parents[1]

    def templates():
        total = 0
        for arquivo in (raiz/'templates').rglob('*.html'):
            get_template(arquivo.relative_to(raiz/'templates').as_posix())
            total += 1
        return f'{total} templates compilados.'

    def estaticos():
        nomes = set()
        for arquivo in (raiz/'templates').rglob('*.html'):
            nomes.update(re.findall(r"{%\s*static\s+['\"]([^'\"]+)['\"]", arquivo.read_text(encoding='utf-8')))
        for nome in nomes:
            if not finders.find(nome):
                raise FileNotFoundError(nome)
            staticfiles_storage.url(nome)
        if not settings.DEBUG:
            if not (settings.STATIC_ROOT/'staticfiles.json').is_file():
                raise FileNotFoundError('Manifesto não construído')
            for nome in nomes:
                if not staticfiles_storage.exists(staticfiles_storage.stored_name(nome)):
                    raise FileNotFoundError('Estático publicado ausente')
        return f'{len(nomes)} referências verificadas; modo ' + ('desenvolvimento.' if settings.DEBUG else 'produção.')

    verificar('Dados', escrita)
    verificar('Banco e migrações', banco)
    verificar('Templates HTML', templates)
    verificar('CSS, JS e imagens', estaticos)
    return {'ok': all(v['ok'] for v in verificacoes), 'verificacoes': verificacoes}
