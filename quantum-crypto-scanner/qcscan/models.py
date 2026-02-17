from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text

Base = declarative_base()

class CryptoEndpoint(Base):
    __tablename__ = "crypto_endpoints"

    id = Column(Integer, primary_key=True)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    ip = Column(String, nullable=True)

    protocol = Column(String, nullable=False, default="TLS")
    tls_version = Column(String, nullable=True)
    cipher_suite = Column(String, nullable=True)

    cert_subject = Column(Text, nullable=True)
    cert_issuer = Column(Text, nullable=True)
    cert_sans = Column(Text, nullable=True)
    cert_sig_alg = Column(String, nullable=True)
    cert_pubkey_alg = Column(String, nullable=True)
    cert_pubkey_size = Column(Integer, nullable=True)
    cert_not_before = Column(DateTime, nullable=True)
    cert_not_after = Column(DateTime, nullable=True)

    scan_error = Column(Text, nullable=True)
    scanned_at = Column(DateTime, nullable=True)
    sni_used = Column(Boolean, default=True)
