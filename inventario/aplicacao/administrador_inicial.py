"""Bootstrap local: cria somente o primeiro superusuário, sem sessão ou MFA."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from inventario.infraestrutura.auditoria import travar_escrita


def cadastrar_primeiro_administrador(nome, senha, email=''):
    User = get_user_model()
    usuario = User(username=nome.strip(), email=email.strip(), is_staff=True, is_superuser=True)
    usuario.full_clean(exclude=['password'])
    validate_password(senha, user=usuario)
    with transaction.atomic():
        travar_escrita()
        if User.objects.filter(is_superuser=True).exists():
            raise ValidationError('Já existe um administrador. O cadastro inicial não cria administradores adicionais.')
        return User.objects.create_superuser(usuario.username, email=usuario.email, password=senha)
