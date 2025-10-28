import tempfile
from fastapi import FastAPI
import uvicorn

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime


def generate_self_signed_cert():
    # Генерация ключа
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BY"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Minsk"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Minsk"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FastAPI In-Memory"),
        x509.NameAttribute(NameOID.COMMON_NAME, "666"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now())
        .not_valid_after(datetime.datetime.now() + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    # Сохраняем во временные файлы
    key_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")

    key_file.write(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_file.close()

    cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
    cert_file.close()

    return key_file.name, cert_file.name


app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello over HTTPS (in-memory cert)!"}


if __name__ == "__main__":
    key_path, cert_path = generate_self_signed_cert()
    uvicorn.run(
        "main:app",
        host="10.100.0.2",
        port=443,
        ssl_keyfile=key_path,
        ssl_certfile=cert_path,
    )
