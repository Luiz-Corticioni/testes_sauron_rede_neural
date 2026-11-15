"""Cria somente contas fictícias em banco descartável explicitamente habilitado."""
import json
import os
from pathlib import Path
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.db import transaction
from django_otp.plugins.otp_totp.models import TOTPDevice

from inventario.models import Ativo

if os.getenv("SAURON_CARGA_DESCARTAVEL") != "1":
    raise RuntimeError("Ensaio exige SAURON_CARGA_DESCARTAVEL=1 e banco descartável vazio.")
if get_user_model().objects.exists() or Ativo.objects.exists():
    raise RuntimeError("Banco não está vazio. Não use este procedimento em instalação existente.")

senha = secrets.token_urlsafe(24)
hash_senha = make_password(senha)
contas = []
grupo = Group.objects.get(name="Operadores")
with transaction.atomic():
    for indice in range(100):
        usuario = get_user_model().objects.create(username=f"bench-{indice:03}", password=hash_senha,
            is_staff=indice < 4, is_superuser=indice < 4)
        if indice >= 4:
            usuario.groups.add(grupo)
        dispositivo = TOTPDevice.objects.create(user=usuario, name="Carga sintética", confirmed=True)
        contas.append({"username": usuario.username, "device": dispositivo.pk, "key": dispositivo.key,
            "step": dispositivo.step, "t0": dispositivo.t0, "digits": dispositivo.digits})
    destino = Path("/bench/credentials.json")
    with os.fdopen(os.open(destino, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w", encoding="utf-8") as arquivo:
        json.dump({"password": senha, "users": contas}, arquivo)
print("Cem contas sintéticas preparadas. Apague credentials.json depois do ensaio.")
