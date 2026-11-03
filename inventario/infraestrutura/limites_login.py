"""Reserva tentativas antes de autenticar, sem segurar lock durante hash/sleep.

Instâncias web/CLI devem usar o mesmo banco. SQLite continua limitado a um host;
PostgreSQL usa a trava transacional compartilhada já adotada pela aplicação.
"""
from datetime import timedelta
import hashlib
from django.db import transaction
from django.utils import timezone
from inventario.models import LimiteLogin
from inventario.infraestrutura.auditoria import travar_escrita

JANELA = 900
LIMITE_PAR = 5
LIMITE_IP = 20


def digest(texto):
    return hashlib.sha256(texto.encode()).hexdigest()


def reservar(nome, origem):
    nome = nome[:150].strip().casefold()
    chaves = ('par:' + digest(nome + '|' + origem), 'ip:' + digest(origem), 'usuario:' + digest(nome))
    agora = timezone.now()
    with transaction.atomic():
        travar_escrita()
        LimiteLogin.objects.filter(expira_em__lte=agora).delete()
        registros = [LimiteLogin.objects.get_or_create(chave=c, defaults={'expira_em': agora + timedelta(seconds=JANELA)})[0] for c in chaves]
        par, ip, usuario = registros
        if par.quantidade >= LIMITE_PAR or len(ip.usuarios) >= LIMITE_IP:
            return None
        par.quantidade += 1
        usuario.quantidade = min(usuario.quantidade + 1, 1_000_000_000)
        ip.usuarios = sorted(set(ip.usuarios) | {digest(nome)})
        for registro in registros:
            registro.save()
        return {'chaves': chaves, 'usuario_hash': digest(nome), 'falhas': par.quantidade,
                'globais': usuario.quantidade, 'expira_em': par.expira_em.isoformat()}


def concluir(reserva, sucesso):
    # Falhas/erros já ficam contabilizados. Nunca depender do processo sobreviver
    # até o fim da autenticação para registrar uma tentativa concorrente.
    if not sucesso:
        return
    with transaction.atomic():
        travar_escrita()
        par, ip, usuario = reserva['chaves']
        atual = LimiteLogin.objects.filter(chave=par).first()
        if atual is None or atual.expira_em.isoformat() != reserva['expira_em']:
            return  # Resposta antiga não pode limpar uma nova janela.
        atual.delete()
        registro = LimiteLogin.objects.filter(chave=usuario).first()
        if registro:
            registro.quantidade = max(0, registro.quantidade - 1)
            registro.save(update_fields=['quantidade'])
        registro = LimiteLogin.objects.filter(chave=ip).first()
        if registro:
            registro.usuarios = [u for u in registro.usuarios if u != reserva['usuario_hash']]
            registro.save(update_fields=['usuarios'])
