"""Backup lógico consistente cifrado; restauração explícita em SQLite novo."""
from datetime import datetime, date
import json
import os
from pathlib import Path
import shutil
import sqlite3
from contextlib import closing
# Subprocessos usam apenas Python/manage.py locais e argv fixo, sem shell.
import subprocess  # nosec B404
import sys
import tempfile
import uuid
from cryptography.fernet import Fernet, InvalidToken
from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.utils import timezone
from inventario.infraestrutura.arquivos import trava_arquivo


class PrecisaoJSONEncoder(DjangoJSONEncoder):
    def default(self,valor):
        if isinstance(valor,(datetime,date)):
            return valor.isoformat()
        return super().default(valor)


def cifra():
    try:
        return Fernet(settings.SAURON_BACKUP_KEY.encode())
    except (ValueError,AttributeError) as erro:
        raise ValueError("Configure SAURON_BACKUP_KEY com uma chave Fernet válida.") from erro


def backup_sqlite(retencao=None):
    """Nome legado: exportação lógica também suporta backend PostgreSQL configurado."""
    retencao=settings.BACKUP_RETENCAO if retencao is None else retencao
    if type(retencao) is not int or not 1<=retencao<=365:
        raise ValueError("Retenção deve estar entre 1 e 365 cópias.")
    criptografia=cifra()
    pasta=settings.DATA_DIR/"backups"
    pasta.mkdir(parents=True,exist_ok=True)
    destino=pasta/f"sauron-{timezone.now():%Y%m%dT%H%M%S%f}-{uuid.uuid4().hex[:6]}.json.fernet"
    with trava_arquivo(pasta/"backup.lock"),transaction.atomic():
        if connection.vendor=="postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        objetos=[]
        # Ao atualizar, novos modelos ainda podem não ter tabela. O backup deve
        # refletir o esquema antigo e continuar restaurável após as migrações.
        from django.db.migrations.recorder import MigrationRecorder
        tabelas=set(connection.introspection.table_names())
        aplicadas=MigrationRecorder(connection).applied_migrations()
        for modelo in apps.get_models():
            if not modelo._meta.managed or modelo._meta.proxy or modelo._meta.label_lower in ("sessions.session", "inventario.limitelogin"):
                continue
            if modelo._meta.db_table not in tabelas:
                if (modelo._meta.label_lower=="inventario.dispositivoemail"
                        and ("inventario", "0020_dispositivo_email") not in aplicadas):
                    continue
                if modelo._meta.label_lower == "inventario.observacaoepss" and ("inventario", "0022_historico_epss") not in aplicadas:
                    continue
                if modelo._meta.label_lower == "inventario.avaliacaossvc" and ("inventario", "0023_avaliacoes_ssvc") not in aplicadas:
                    continue
                if modelo._meta.model_name in ("documentoinventario", "itemsbom", "achadocomponente", "declaracaovex") and ("inventario", "0024_documentos_componentes") not in aplicadas:
                    continue
                if modelo._meta.model_name == "relacaoativos" and ("inventario", "0025_relacoes_tipadas") not in aplicadas:
                    continue
                if modelo._meta.model_name in ("perimetrorelacoes", "membroperimetro", "revisaocobertura") and ("inventario", "0026_cobertura_evidencias") not in aplicadas:
                    continue
                raise ValueError(f"Tabela ausente para {modelo._meta.label}; backup interrompido.")
            registros=modelo.objects.order_by(modelo._meta.pk.name)
            if modelo._meta.label_lower == "inventario.software" and ("inventario", "0024_documentos_componentes") not in aplicadas:
                campos = [f.name for f in modelo._meta.fields if f.name != "purl"]
                itens = serializers.serialize("python", registros.only(*campos).iterator(), fields=campos)
            elif modelo._meta.label_lower == "inventario.vulnerabilidade" and ("inventario", "0022_historico_epss") not in aplicadas:
                campos = [f.name for f in modelo._meta.fields if f.name != "epss_observacao"]
                itens = serializers.serialize("python", registros.only(*campos).iterator(), fields=campos)
            else:
                itens=serializers.serialize("python",registros.iterator())
            if modelo._meta.label_lower=="inventario.dispositivoemail":
                for item in itens:
                    item["fields"].update(codigo_hash="", nonce="", pode_adotar=False, expira_em=None)
            objetos.extend(itens)
        dados=json.dumps(objetos,cls=PrecisaoJSONEncoder,ensure_ascii=False).encode()
        token=criptografia.encrypt(dados)
        with destino.open("xb") as arquivo:
            arquivo.write(token)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        destino.chmod(0o600)
        adicional=settings.SAURON_BACKUP_DESTINO_ADICIONAL
        if adicional:
            Path(adicional).mkdir(parents=True,exist_ok=True)
            shutil.copy2(destino,Path(adicional)/destino.name)
        for antigo in sorted(pasta.glob("sauron-*.json.fernet"),reverse=True)[retencao:]:
            antigo.unlink()
    return destino


def restaurar_backup(arquivo,saida):
    destino=Path(saida).resolve()
    if destino.exists():
        raise ValueError("Restauração exige arquivo de destino novo; nenhum banco é sobrescrito.")
    try:
        dados=cifra().decrypt(Path(arquivo).read_bytes())
        if not isinstance(json.loads(dados),list):
            raise ValueError("Formato de backup inválido.")
    except (InvalidToken,UnicodeError,json.JSONDecodeError) as erro:
        raise ValueError("Backup inválido ou chave Fernet incorreta.") from erro
    destino.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent,prefix="restauracao-") as pasta:
        fixture=Path(pasta)/"inventario.json"
        fixture.write_bytes(dados)
        fixture.chmod(0o600)
        ambiente=dict(os.environ)
        temporario=Path(pasta)/"restaurado.sqlite3"
        ambiente.update(SAURON_DB_PATH=str(temporario),DATABASE_URL="",
                        SAURON_DATA_DIR=str(Path(pasta)/"dados"),
                        SAURON_AUDIT_HMAC_KEY=settings.SAURON_AUDIT_HMAC_KEY)
        raiz=Path(__file__).resolve().parents[2]
        try:
            for comando in (["migrate","--noinput"],["loaddata",str(fixture)],["verificar_auditoria", "--somente-cadeia"]):
                subprocess.run([sys.executable,str(raiz/"manage.py"),*comando],cwd=raiz,env=ambiente,check=True,capture_output=True,text=True)  # nosec B603
            with closing(sqlite3.connect(temporario)) as banco:
                banco.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                banco.execute("PRAGMA journal_mode=DELETE")
            temporario.chmod(0o600)
            # Link exclusivo no mesmo volume publica somente o banco validado.
            # O destino surgido durante a restauração nunca é substituído.
            if os.name == "nt":
                os.rename(temporario, destino)  # Windows recusa destino existente.
            else:
                os.link(temporario, destino)
        except FileExistsError as erro:
            raise ValueError("O destino passou a existir; restauração não publicada.") from erro
        except subprocess.CalledProcessError as erro:
            raise ValueError("Restauração interrompida: migração, carga ou auditoria falhou; destino preservado.") from erro
    return destino

