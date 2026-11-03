"""Carga HTTP local e descartável; nunca usa o banco/configuração da instalação.

python scripts/testar_carga.py --saida resultado.json
O servidor WSGI de teste não é uma recomendação de servidor de produção.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
import json
from math import ceil
import os
from pathlib import Path
import platform
import re
import secrets
import statistics
import sys
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from time import perf_counter
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, HTTPRedirectHandler, Request
from wsgiref.simple_server import make_server


class SemRedirecionar(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, required=True)
    parser.add_argument('--rotulo', default='local')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    with TemporaryDirectory(prefix='sauron-carga-') as pasta:
        dados = Path(pasta)
        os.environ.update(DJANGO_SETTINGS_MODULE='sauron_web.settings', SAURON_DEBUG='0',
            SAURON_SECRET_KEY=secrets.token_urlsafe(64), SAURON_AUDIT_HMAC_KEY=secrets.token_urlsafe(64),
            SAURON_DATA_DIR=str(dados), SAURON_DB_PATH=str(dados/'teste.sqlite3'), DATABASE_URL='',
            SAURON_ALLOWED_HOSTS='127.0.0.1', SAURON_SSL_REDIRECT='0', SAURON_SECURE_COOKIES='0',
            SAURON_EXIGIR_ANCORA='0', SAURON_STATIC_ROOT=str(dados/'static'), SAURON_ROTINAS_SEM_REDE='1',
            SAURON_EMAIL_ENABLED='0', SAURON_TRUSTED_PROXIES='', SAURON_TRUST_PROXY='0')
        import django
        django.setup()
        from django.core.management import call_command
        from django.core.wsgi import get_wsgi_application
        from django.core.cache import cache
        from django.conf import settings
        from django.db import connection, connections, transaction
        from django.contrib.auth import get_user_model
        from django.contrib.auth.hashers import make_password
        from django.contrib.auth.models import Group, Permission
        from django.utils import timezone
        from django_otp.oath import totp
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from django.core.servers.basehttp import ThreadedWSGIServer, WSGIRequestHandler
        from inventario.models import Ativo, Sala, Vulnerabilidade, Incidencia, Dependencia
        from inventario.infraestrutura.auditoria import verificar_cadeia
        call_command('migrate', interactive=False, verbosity=0)
        call_command('collectstatic', interactive=False, verbosity=0)
        senha = secrets.token_urlsafe(24)
        hash_senha = make_password(senha)  # Mesmo custo real de verificação em cada login.
        contas = []
        with transaction.atomic():
            grupo = Group.objects.create(name='Leitores de carga')
            grupo.permissions.set(Permission.objects.filter(content_type__app_label='inventario', codename__startswith='view_'))
            for n in range(100):
                u = get_user_model().objects.create(username=f'carga-{n:03}', password=hash_senha,
                    is_staff=n < 4, is_superuser=n < 4)
                if n >= 4:
                    u.groups.add(grupo)
                dispositivo = TOTPDevice.objects.create(user=u, name='Carga sintética', confirmed=True)
                contas.append((u.username, dispositivo))
            sala = Sala.objects.create(id='SALA-CARGA', nome='Carga sintética')
            vuls = [Vulnerabilidade.objects.create(id=f'VUL-RCE-{n:04}', descricao='Carga sintética', cvss=7.5) for n in range(10)]
            ativos = [Ativo.objects.create(tipo='1', nome=f'Ativo {n}', fabricante='Carga', sala=sala) for n in range(100)]
            for n, ativo in enumerate(ativos):
                Incidencia.objects.create(id=f'INC-CARGA-{n:04}', ativo=ativo, vulnerabilidade=vuls[n % 10])
                if n:
                    Dependencia.objects.create(dependente=ativo, fornecedor=ativos[n-1], peso=.1)
        application = get_wsgi_application()
        metricas = {'ativas': 0, 'pico': 0, 'sql': 0, 'escritas_sessao': 0}
        trava = Lock()

        def contar(execute, sql, params, many, context):
            with trava:
                metricas['sql'] += 1
                metricas['escritas_sessao'] += int(sql.lstrip().upper().startswith('UPDATE "DJANGO_SESSION"'))
            return execute(sql, params, many, context)

        def instrumentada(environ, start_response):
            with trava:
                metricas['ativas'] += 1
                metricas['pico'] = max(metricas['pico'], metricas['ativas'])
            try:
                with connection.execute_wrapper(contar):
                    return application(environ, start_response)
            finally:
                with trava:
                    metricas['ativas'] -= 1

        class Servidor(ThreadedWSGIServer):
            request_queue_size = 256
            daemon_threads = True

        class Handler(WSGIRequestHandler):
            def log_message(self, format, *args):
                pass

        servidor = make_server('127.0.0.1', 0, instrumentada, server_class=Servidor, handler_class=Handler)
        thread = Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{servidor.server_port}'
        clientes = [build_opener(HTTPCookieProcessor(CookieJar()), SemRedirecionar()) for _ in contas]

        def pedir(cliente, caminho, dados_post=None):
            req = Request(base+caminho, data=urlencode(dados_post).encode() if dados_post is not None else None)
            try:
                resposta = cliente.open(req, timeout=120)
            except HTTPError as erro:
                resposta = erro
            with resposta:
                return resposta.code, resposta.read().decode('utf-8', errors='replace'), resposta.headers

        def csrf(cliente, caminho):
            codigo, corpo, _ = pedir(cliente, caminho)
            if codigo != 200:
                raise ValueError(f'GET {caminho}: {codigo}')
            return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', corpo).group(1)

        resultados = []

        def medir(nome, funcao, indices=range(100), concorrencia=100):
            with trava:
                metricas.update(pico=0, sql=0, escritas_sessao=0)
            inicio = perf_counter()
            def item(n):
                t = perf_counter()
                try:
                    ok, status = funcao(n)
                    return {'ok': ok, 'status': str(status), 'ms': (perf_counter()-t)*1000}
                except Exception as erro:
                    return {'ok': False, 'status': type(erro).__name__+': '+str(erro), 'ms': (perf_counter()-t)*1000}
            with ThreadPoolExecutor(max_workers=concorrencia) as executor:
                amostras = list(executor.map(item, indices))
            duracao = perf_counter()-inicio
            tempos = sorted(a['ms'] for a in amostras)
            status = {s: sum(a['status'] == s for a in amostras) for s in sorted({a['status'] for a in amostras})}
            resumo = {'etapa': nome, 'fluxos': len(amostras), 'concorrencia_cliente': concorrencia,
                'sucessos': sum(a['ok'] for a in amostras), 'status': status, 'duracao_s': round(duracao, 3),
                'fluxos_s': round(len(amostras)/duracao, 2), 'p50_ms': round(statistics.median(tempos), 2),
                'p95_ms': round(tempos[max(0, ceil(.95*len(tempos))-1)], 2), 'max_ms': round(max(tempos), 2),
                **{k: v for k, v in metricas.items() if k != 'ativas'}}
            resultados.append(resumo)
            print(json.dumps(resumo, ensure_ascii=False), flush=True)

        def login(n, cliente=None, mfa=True):
            cliente = cliente or clientes[n]
            nome, d = contas[n]
            token = csrf(cliente, '/entrar/')
            codigo, _, _ = pedir(cliente, '/entrar/', {'username': nome, 'password': senha, 'csrfmiddlewaretoken': token})
            if codigo != 302 or not mfa:
                return codigo == 302, codigo
            token = csrf(cliente, '/mfa/')
            otp = str(totp(d.bin_key, step=d.step, t0=d.t0, digits=d.digits, drift=d.drift)).zfill(d.digits)
            codigo, _, _ = pedir(cliente, '/mfa/', {'dispositivo': d.pk, 'password': senha, 'token': otp, 'csrfmiddlewaretoken': token})
            return codigo == 302, codigo

        try:
            medir('login_senha_totp_gradual_mesmo_ip', login, concorrencia=10)
            cache.clear()
            medir('painel_frio_100', lambda n: (lambda r: (r[0] == 200 and contas[n][0] in r[1], r[0]))(pedir(clientes[n], '/')))
            medir('painel_aquecido_100', lambda n: (lambda r: (r[0] == 200 and contas[n][0] in r[1], r[0]))(pedir(clientes[n], '/')))
            medir('api_risco_100', lambda n: (lambda r: (r[0] == 200 and 'ids_ativos' in r[1], r[0]))(pedir(clientes[n], '/api/risco/')))
            medir('lista_ativos_100', lambda n: (lambda r: (r[0] == 200, r[0]))(pedir(clientes[n], '/ativos/')))
            medir('isolamento_administracao_100', lambda n: (lambda r: (r[0] == (200 if n < 4 else 403), r[0]))(pedir(clientes[n], '/admin/auth/user/')))
            def escrever(n):
                token = csrf(clientes[n], '/')
                codigo, _, _ = pedir(clientes[n], f'/incidencias/INC-CARGA-{n:04}/status/', {'status': 'TRATAMENTO', 'csrfmiddlewaretoken': token})
                return codigo == 200, codigo
            medir('quatro_administradores_escrevendo', escrever, range(4), 4)
            assert Incidencia.objects.filter(status='TRATAMENTO').count() == 4
            def misto(n):
                if n < 4:
                    return escrever(n)
                codigo, corpo, _ = pedir(clientes[n], '/')
                return codigo == 200 and contas[n][0] in corpo, codigo
            medir('misto_quatro_admins_escrevem_96_comuns_leem', misto)
            def negar_escrita(n):
                token = csrf(clientes[n], '/')
                codigo, _, _ = pedir(clientes[n], f'/incidencias/INC-CARGA-{n:04}/status/', {'status': 'TRATAMENTO', 'csrfmiddlewaretoken': token})
                return codigo == 403, codigo
            medir('escrita_negada_96_comuns', negar_escrita, range(4, 100), 96)
            assert Incidencia.objects.filter(status='TRATAMENTO').count() == 4
            from inventario.aplicacao.painel import contexto_painel
            assert contexto_painel()['salas'] == 1
            Sala.objects.create(id='SALA-CONFIRMADA', nome='Commit de carga')
            assert contexto_painel()['salas'] == 2
            try:
                with transaction.atomic():
                    Sala.objects.create(id='SALA-ROLLBACK', nome='Não deve aparecer fora da transação')
                    assert contexto_painel()['salas'] == 3
                    raise ValueError('Rollback de carga intencional')
            except ValueError:
                pass
            assert contexto_painel()['salas'] == 2
            rajada = [build_opener(HTTPCookieProcessor(CookieJar()), SemRedirecionar()) for _ in contas]
            medir('rajada_senha_100_mesmo_ip_sem_mudar_limites', lambda n: login(n, rajada[n], mfa=False))
            integridade = verificar_cadeia(verificar_ancora=False)
            resultado = {'rotulo': args.rotulo, 'data_utc': timezone.now().isoformat(),
                'ambiente': {'python': platform.python_version(), 'django': django.get_version(), 'sistema': platform.platform(),
                    'cpus_logicas': os.cpu_count(), 'banco': 'SQLite/WAL', 'debug': False, 'servidor': 'WSGI local com threads; apenas teste',
                    'transporte': 'HTTP/loopback, sem TLS', 'cache': settings.CACHES['default']['BACKEND'], 'usuarios': 100, 'administradores': 4,
                    'comuns_somente_leitura': 96, 'ativos': 100, 'vulnerabilidades': 10, 'incidencias': 100, 'dependencias': 99,
                    'senhas': 'PBKDF2 real, sem diminuir custo', 'rede_externa': False},
                'etapas': resultados, 'auditoria_integra': integridade['integra'], 'cache_commit_rollback_aprovado': True,
                'funcional_aprovado': all(r['sucessos'] == r['fluxos'] for r in resultados[:-1]) and integridade['integra']}
            args.saida.parent.mkdir(parents=True, exist_ok=True)
            args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
        finally:
            servidor.shutdown()
            servidor.server_close()
            thread.join(timeout=5)
            connections.close_all()
        return 0 if resultado['funcional_aprovado'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
