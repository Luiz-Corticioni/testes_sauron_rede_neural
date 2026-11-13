from pathlib import Path
import os

from .ambiente import carregar_ambiente, lista_ambiente, validar_chave


BASE_DIR = Path(__file__).resolve().parent.parent
carregar_ambiente(BASE_DIR / ".env")
DEBUG = os.getenv("SAURON_DEBUG", "0") == "1"
SECRET_KEY = os.getenv("SAURON_SECRET_KEY", "dev-only-change-me" if DEBUG else "")
validar_chave(SECRET_KEY, DEBUG)
ALLOWED_HOSTS = lista_ambiente("SAURON_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = lista_ambiente("SAURON_CSRF_TRUSTED_ORIGINS")
DATA_DIR = Path(os.getenv("SAURON_DATA_DIR", BASE_DIR / "dados"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "inventario",
]

MIDDLEWARE = [
    'inventario.web.erros.IdentificadorRequisicaoMiddleware',
    "inventario.seguranca.ProxiesConfiaveisMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "inventario.web.saude.LivenessMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "inventario.seguranca_mfa.SessaoEMFAMiddleware",
    "inventario.seguranca.AutoriaECabecalhosMiddleware",
    "inventario.seguranca.AcessoObrigatorioMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'inventario.web.erros.FalhasOperacionaisMiddleware',
]

ROOT_URLCONF = "sauron_web.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "inventario.web.orientacao.contexto_orientacao",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "sauron_web.wsgi.application"
ASGI_APPLICATION = "sauron_web.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(os.getenv("SAURON_DB_PATH", DATA_DIR / "sauron.sqlite3")),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"timeout": 20},
    }
}

# Argon2id é usado em senhas novas; os verificadores legados permitem que
# o Django atualize hashes anteriores após uma autenticação bem-sucedida.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = Path(os.getenv('SAURON_STATIC_ROOT', BASE_DIR / 'staticfiles'))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": ('django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG else
                    'whitenoise.storage.CompressedManifestStaticFilesStorage'),
    },
}
WHITENOISE_USE_FINDERS = DEBUG
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/entrar/"
CSRF_FAILURE_VIEW = 'inventario.web.erros.erro_csrf'
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/entrar/"
CSRF_COOKIE_SECURE = os.getenv("SAURON_SECURE_COOKIES", "0") == "1"
SESSION_COOKIE_SECURE = os.getenv("SAURON_SECURE_COOKIES", "0") == "1"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
NVD_API_KEY = os.getenv("NVD_API_KEY")
SECURE_SSL_REDIRECT = os.getenv('SAURON_SSL_REDIRECT', '0') == '1'
SECURE_REDIRECT_EXEMPT = [r'^api/saude/$']
SECURE_HSTS_PRELOAD = os.getenv('SAURON_HSTS_PRELOAD', '0') == '1'
# Só habilitar atrás de um proxy confiável que sobrescreva esse cabeçalho.
if os.getenv('SAURON_TRUST_PROXY', '0') == '1':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {'requisicao': {'()': 'inventario.web.erros.FiltroLogRequisicao'}},
    'formatters': {'sauron': {'format': '{asctime} {levelname} {name} [{request_id}]: {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'sauron', 'filters': ['requisicao']}},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
        'inventario': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}

CACHES = {
    "default": {
        "BACKEND": "inventario.infraestrutura.cache_arquivo.CacheArquivoAtomico",
        "VERSION": 2,
        "LOCATION": DATA_DIR / "cache" / "django",
        "OPTIONS": {"MAX_ENTRIES": 10000},
    }
}
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000 if SESSION_COOKIE_SECURE else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = SESSION_COOKIE_SECURE

RISCO_KAPPA = float(os.getenv("SAURON_RISCO_KAPPA", "0.3"))
RISCO_TAU = float(os.getenv("SAURON_RISCO_TAU", "25"))
RISCO_LIMIAR_TENDENCIA = float(os.getenv("SAURON_LIMIAR_TENDENCIA", "10"))
SLA_DIAS = {
    nome: int(os.getenv(f"SAURON_SLA_{nome}", str(dias)))
    for nome, dias in {"KEV": 7, "CRITICA": 7, "ALTA": 30, "MEDIA": 90, "BAIXA": 180}.items()
}
ALERTA_EOL_DIAS = int(os.getenv("SAURON_EOL_DIAS", "90"))
ALERTA_CERT_DIAS = int(os.getenv("SAURON_CERT_DIAS", "45"))
BACKUP_RETENCAO = int(os.getenv("SAURON_BACKUP_RETENCAO", "7"))

# Valores acadêmicos do recomendador; não foram calibrados em dados de produção.
# Limites do recomendador, configuráveis sem alterar código.
SAURON_TOLERANCIA_MAX_DIAS = int(os.getenv("SAURON_TOLERANCIA_MAX_DIAS", "90"))
SAURON_ACEITE_MAX_DIAS = int(os.getenv("SAURON_ACEITE_MAX_DIAS", "90"))
SAURON_ACEITE_NORMAL_MAX_DIAS = int(os.getenv("SAURON_ACEITE_NORMAL_MAX_DIAS", "180"))
IMUNE_LIMIAR = float(os.getenv("SAURON_IMUNE_LIMIAR", ".75"))
IMUNE_LIMIAR_RISCO = float(os.getenv("SAURON_IMUNE_RISCO", "25"))
IMUNE_MEIA_VIDA_DIAS = float(os.getenv("SAURON_IMUNE_MEIA_VIDA", "30"))
IMUNE_PISO = float(os.getenv("SAURON_IMUNE_PISO", ".05"))
IMUNE_MAX_POPULACAO = int(os.getenv("SAURON_IMUNE_POPULACAO", "50"))
IMUNE_TOLERANCIA_DIAS = int(os.getenv("SAURON_IMUNE_TOLERANCIA", "30"))
IMUNE_TAXA_REJEICAO = float(os.getenv("SAURON_IMUNE_REJEICAO", ".6"))
IMUNE_MIN_REJEICOES = int(os.getenv("SAURON_IMUNE_MIN_REJEICOES", "3"))
import math

if not (
    0 < IMUNE_LIMIAR <= 1
    and 0 < IMUNE_PISO < IMUNE_LIMIAR
    and 0 < IMUNE_TAXA_REJEICAO < 1
    and 1 <= IMUNE_MIN_REJEICOES <= 100
    and 1 <= IMUNE_MAX_POPULACAO <= 1000
    and 1 <= IMUNE_TOLERANCIA_DIAS <= 3650
    and math.isfinite(IMUNE_LIMIAR_RISCO)
    and IMUNE_LIMIAR_RISCO >= 0
    and math.isfinite(IMUNE_MEIA_VIDA_DIAS)
    and IMUNE_MEIA_VIDA_DIAS > 0
):
    raise ValueError("Configuração IMUNE inválida; confira .env.example e o README.")

SAURON_TRUSTED_PROXIES = lista_ambiente("SAURON_TRUSTED_PROXIES")

NVD_CVSS_MINIMO = float(os.getenv("SAURON_NVD_CVSS_MINIMO", "7"))
NVD_MAX_SUGESTOES_CPE = int(os.getenv("SAURON_NVD_MAX_SUGESTOES_CPE", "100"))

ALERTA_SUPRESSAO_DIAS = int(os.getenv("SAURON_ALERTA_SUPRESSAO_DIAS", "7"))

TEST_RUNNER = "tests.runner.SemRedeRunner"

SAURON_AUDIT_HMAC_KEY = os.getenv("SAURON_AUDIT_HMAC_KEY", "desenvolvimento-auditoria" if DEBUG else "")
if not SAURON_AUDIT_HMAC_KEY:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("SAURON_AUDIT_HMAC_KEY é obrigatória fora de DEBUG.")
SAURON_AUDIT_ANCHOR_PATH = Path((os.getenv("SAURON_AUDIT_ANCHOR_PATH") or DATA_DIR / "ancoras-auditoria.jsonl"))
SAURON_AUDIT_SYSLOG = os.getenv("SAURON_AUDIT_SYSLOG", "")

SAURON_SESSAO_OCIOSA_MIN = int(os.getenv("SAURON_SESSAO_OCIOSA_MIN", "30"))
SAURON_SESSAO_ABSOLUTA_HORAS = int(os.getenv("SAURON_SESSAO_ABSOLUTA_HORAS", "8"))
SAURON_REAUTH_SEGUNDOS = int(os.getenv("SAURON_REAUTH_SEGUNDOS", "300"))
SESSION_COOKIE_AGE = SAURON_SESSAO_ABSOLUTA_HORAS * 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

from .banco import configurar_banco
DATABASES["default"] = configurar_banco(os.getenv("DATABASE_URL"), DATABASES["default"])
SAURON_BACKUP_KEY = os.getenv("SAURON_BACKUP_KEY", "")
SAURON_BACKUP_DESTINO_ADICIONAL = os.getenv("SAURON_BACKUP_DESTINO_ADICIONAL", "")

SAURON_SAUDE_LIMITE_IP = int(os.getenv("SAURON_SAUDE_LIMITE_IP", "120"))

RISCO_JANELA_MINIMA_HORAS = float(os.getenv("SAURON_RISCO_JANELA_MINIMA_HORAS", "24"))

IMUNE_MAX_ATIVOS_CICLO = int(os.getenv("SAURON_IMUNE_MAX_ATIVOS_CICLO", "200"))
IMUNE_MAX_APRENDIZADOS_CICLO = int(os.getenv("SAURON_IMUNE_MAX_APRENDIZADOS_CICLO", "10"))

import json
RISCO_POLITICA = os.getenv("SAURON_RISCO_POLITICA", "leontief")
RISCO_FATORES_EXPOSICAO = json.loads(os.getenv("SAURON_RISCO_FATORES_EXPOSICAO", "{}"))
RISCO_MULTIPLICADOR_INTERNET = float(os.getenv("SAURON_RISCO_MULTIPLICADOR_INTERNET", "1.25"))
RISCO_MULTIPLICADOR_ADMIN_REMOTA = float(os.getenv("SAURON_RISCO_MULTIPLICADOR_ADMIN_REMOTA", "1.10"))
if RISCO_POLITICA not in ("leontief", "noisy-or"):
    raise ValueError("Política de risco desconhecida.")

SAURON_EXIGIR_ANCORA = os.getenv("SAURON_EXIGIR_ANCORA", "0" if DEBUG else "1") == "1"

# SMTP: envio desativado até configuração explícita; TLS habilitado por padrão.
SAURON_EMAIL_ENABLED = os.getenv("SAURON_EMAIL_ENABLED", "0") == "1"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("SAURON_EMAIL_HOST", "").strip()
EMAIL_PORT = int(os.getenv("SAURON_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("SAURON_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("SAURON_EMAIL_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("SAURON_EMAIL_FROM", "").strip()
EMAIL_USE_TLS = os.getenv("SAURON_EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.getenv("SAURON_EMAIL_USE_SSL", "0") == "1"
EMAIL_TIMEOUT = 10

# Hosts externos não podem iniciar com transporte de sessão inseguro.
if not DEBUG and any(h not in ("localhost", "127.0.0.1", "[::1]") for h in ALLOWED_HOSTS):
    if not SESSION_COOKIE_SECURE or not SECURE_SSL_REDIRECT:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("Hosts externos exigem SAURON_SECURE_COOKIES=1 e SAURON_SSL_REDIRECT=1.")
    if any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("Origens CSRF externas exigem HTTPS.")
