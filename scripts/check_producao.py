"""Executa check --deploy com configurações de produção, sem banco real."""
import os
import secrets
import subprocess
import sys

ambiente = dict(os.environ)
ambiente.update(SAURON_AUDIT_HMAC_KEY=secrets.token_urlsafe(64), SAURON_DEBUG="0", SAURON_SECRET_KEY=secrets.token_urlsafe(64),
    SAURON_ALLOWED_HOSTS="sauron.example.org", SAURON_SECURE_COOKIES="1",
    SAURON_SSL_REDIRECT="1", SAURON_HSTS_PRELOAD="1",
    SAURON_CSRF_TRUSTED_ORIGINS="https://sauron.example.org")
subprocess.run([sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
               env=ambiente, check=True)

