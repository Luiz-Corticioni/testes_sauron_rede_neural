"""Exercita o transporte SMTP/STARTTLS do Django em loopback, sem enviar e-mail real."""

from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
import os
from pathlib import Path
import socketserver
import ssl
import sys
import tempfile
import threading

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


class SMTPTeste(socketserver.StreamRequestHandler):
    def responder(self, texto):
        self.wfile.write(texto + b"\r\n")
        self.wfile.flush()

    def handle(self):
        self.connection.settimeout(10)
        self.responder(b"220 smtp-local teste")
        cifrado = False
        while linha := self.rfile.readline(8192):
            comando = linha.decode("ascii", errors="replace").strip()
            operacao = comando.split(" ", 1)[0].upper()
            if operacao in {"EHLO", "HELO"}:
                if cifrado:
                    self.wfile.write(b"250-localhost\r\n250 AUTH PLAIN\r\n")
                else:
                    self.wfile.write(b"250-localhost\r\n250 STARTTLS\r\n")
                self.wfile.flush()
            elif operacao == "STARTTLS":
                self.responder(b"220 Inicie TLS")
                self.rfile.close()
                self.wfile.close()
                self.connection = self.server.contexto.wrap_socket(self.connection, server_side=True)
                self.rfile = self.connection.makefile("rb")
                self.wfile = self.connection.makefile("wb")
                cifrado = True
            elif operacao == "AUTH" and cifrado:
                self.server.autenticou = True
                self.responder(b"235 Autenticado para teste")
            elif operacao in {"MAIL", "RCPT"} and cifrado and self.server.autenticou:
                self.responder(b"250 OK")
            elif operacao == "DATA" and cifrado and self.server.autenticou:
                self.responder(b"354 Termine com ponto")
                mensagem = []
                while (parte := self.rfile.readline(8192)) not in (b".\r\n", b""):
                    mensagem.append(parte)
                self.server.mensagem = b"".join(mensagem)
                self.responder(b"250 Aceito")
            elif operacao == "QUIT":
                self.responder(b"221 Encerrado")
                return
            else:
                self.responder(b"503 Sequencia nao permitida")


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    os.environ.setdefault("SAURON_DEBUG", "1")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sauron_web.settings")
    from django.core.mail import EmailMessage, get_connection

    with tempfile.TemporaryDirectory(prefix="sauron-smtp-") as pasta:
        chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Sauron teste local")])
        agora = datetime.now(timezone.utc)
        certificado = (x509.CertificateBuilder().subject_name(nome).issuer_name(nome)
            .public_key(chave.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(agora - timedelta(minutes=5)).not_valid_after(agora + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ip_address("127.0.0.1"))]), False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
            .sign(chave, hashes.SHA256()))
        arquivo_cert = Path(pasta) / "cert.pem"
        arquivo_chave = Path(pasta) / "chave.pem"
        arquivo_cert.write_bytes(certificado.public_bytes(serialization.Encoding.PEM))
        arquivo_chave.write_bytes(chave.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto.load_cert_chain(arquivo_cert, arquivo_chave)
        anterior = os.environ.get("SSL_CERT_FILE")
        os.environ["SSL_CERT_FILE"] = str(arquivo_cert)
        try:
            with socketserver.TCPServer(("127.0.0.1", 0), SMTPTeste) as servidor:
                servidor.contexto = contexto
                servidor.autenticou = False
                servidor.mensagem = b""
                thread = threading.Thread(target=servidor.serve_forever, daemon=True)
                thread.start()
                try:
                    conexao = get_connection(host="127.0.0.1", port=servidor.server_address[1],
                        username="usuario-teste", password="senha-descartavel", use_tls=True, timeout=5)
                    email = EmailMessage("Teste local", "Sem código ou mensagem real.", "sauron@example.org",
                                         ["destinatario@example.org"], connection=conexao)
                    assert email.send() == 1
                    assert servidor.autenticou and b"destinatario@example.org" in servidor.mensagem
                finally:
                    servidor.shutdown()
                    thread.join(timeout=5)
        finally:
            if anterior is None:
                os.environ.pop("SSL_CERT_FILE", None)
            else:
                os.environ["SSL_CERT_FILE"] = anterior
    print("SMTP local: STARTTLS, certificado, autenticação e envio simulados com sucesso.")
    print("Nenhum e-mail foi enviado à internet; teste o provedor real separadamente.")


if __name__ == "__main__":
    main()
