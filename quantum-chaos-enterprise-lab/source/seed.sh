#!/bin/sh
set -e

GITEA_URL="http://gitea:3000"
ADMIN_USER="admin"
ADMIN_PASS="admin123"

echo "=== Waiting for Gitea to be ready ==="
until curl -sf "${GITEA_URL}/" > /dev/null 2>&1; do
  echo "Waiting for Gitea..."
  sleep 3
done
sleep 3  # Extra buffer for full initialization

echo "=== Creating repos ==="

# Helper: create a file in a repo via Gitea API
put_file() {
  local repo="$1"
  local path="$2"
  local content_b64="$3"
  local msg="$4"
  curl -sf -X POST "${GITEA_URL}/api/v1/repos/${ADMIN_USER}/${repo}/contents/${path}" \
    -H "Content-Type: application/json" \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    -d "{\"message\": \"${msg}\", \"content\": \"${content_b64}\"}" > /dev/null
}

# ---- REPO 1: crypto-antipatterns-python ----
curl -sf -X POST "${GITEA_URL}/api/v1/user/repos" \
  -H "Content-Type: application/json" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -d '{"name": "crypto-antipatterns-python", "private": false, "auto_init": true, "default_branch": "main"}' > /dev/null
echo "Created repo: crypto-antipatterns-python"

# Category 1: Hardcoded keys (semgrep flags hardcoded RSA private keys and AES keys)
CONTENT1=$(printf '%s' '
# ANTI-PATTERN: Hardcoded RSA private key in source
HARDCODED_RSA_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA2a2rwplBQLF29amygykEMmYz0+Kcj3bKBp29T2rFOvkGpC4H
EBDexQvGqLMmxSWKGPzV9MpPGQ4OLFKpNKKMoI6QJL3g+bLkWzJXhxNVSGEVaB
-----END RSA PRIVATE KEY-----"""

# ANTI-PATTERN: Hardcoded AES key
AES_KEY = b"mysecretkey12345"
API_SECRET = "sk-1234567890abcdef1234567890abcdef"
' | base64 | tr -d '\n')
put_file "crypto-antipatterns-python" "secrets/hardcoded_keys.py" "$CONTENT1" "add hardcoded keys anti-pattern"

# Category 2: Weak algorithms (MD5, SHA1, DES, ECB mode)
CONTENT2=$(printf '%s' '
import hashlib
from Crypto.Cipher import DES, ARC4
from Crypto.Cipher import AES

# ANTI-PATTERN: MD5 for integrity check
def verify_password(password, stored_hash):
    return hashlib.md5(password.encode()).hexdigest() == stored_hash

# ANTI-PATTERN: SHA1 for signing
def sign_data(data):
    return hashlib.sha1(data).hexdigest()

# ANTI-PATTERN: DES encryption
def encrypt_des(key, data):
    cipher = DES.new(key, DES.MODE_ECB)
    return cipher.encrypt(data)

# ANTI-PATTERN: RC4 stream cipher
def encrypt_rc4(key, data):
    cipher = ARC4.new(key)
    return cipher.encrypt(data)

# ANTI-PATTERN: AES in ECB mode (no IV)
def encrypt_aes_ecb(key, data):
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(data)
' | base64 | tr -d '\n')
put_file "crypto-antipatterns-python" "crypto/weak_algorithms.py" "$CONTENT2" "add weak algorithm usage anti-patterns"

# Category 3: Weak random / custom crypto
CONTENT3=$(printf '%s' '
import random
import string

# ANTI-PATTERN: random.random() for security token generation
def generate_session_token():
    return "".join(random.choice(string.ascii_letters) for _ in range(32))

# ANTI-PATTERN: custom XOR-based encryption
def xor_encrypt(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

# ANTI-PATTERN: home-rolled PRNG using time seed
import time
def weak_prng_seed():
    random.seed(int(time.time()))
    return random.randint(0, 2**32)

# ANTI-PATTERN: MD5 PRNG
def md5_prng(seed: str) -> str:
    import hashlib
    return hashlib.md5(seed.encode()).hexdigest()
' | base64 | tr -d '\n')
put_file "crypto-antipatterns-python" "crypto/weak_random.py" "$CONTENT3" "add weak random anti-patterns"

# Category 4: Deprecated protocol usage
CONTENT4=$(printf '%s' '
import ssl
import socket

# ANTI-PATTERN: Explicit TLS 1.0 version pinning
def create_legacy_ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1  # TLS 1.0 deprecated
    return ctx

# ANTI-PATTERN: SSLv2/SSLv3 method reference
def create_insecure_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.verify_mode = ssl.CERT_NONE
    ctx.check_hostname = False
    return ctx

# ANTI-PATTERN: Explicit MD5 HMAC for message authentication
import hmac
import hashlib
def sign_message(key: bytes, message: bytes) -> bytes:
    return hmac.new(key, message, hashlib.md5).digest()
' | base64 | tr -d '\n')
put_file "crypto-antipatterns-python" "crypto/deprecated_protocols.py" "$CONTENT4" "add deprecated protocol anti-patterns"

# ---- REPO 2: crypto-antipatterns-go ----
curl -sf -X POST "${GITEA_URL}/api/v1/user/repos" \
  -H "Content-Type: application/json" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -d '{"name": "crypto-antipatterns-go", "private": false, "auto_init": true, "default_branch": "main"}' > /dev/null
echo "Created repo: crypto-antipatterns-go"

CONTENT_GO=$(printf '%s' '
package main

import (
	"crypto/md5"
	"crypto/des"
	"crypto/rc4"
	"crypto/sha1"
	"fmt"
	"math/rand"
)

// ANTI-PATTERN: MD5 hash for security
func hashWithMD5(data []byte) []byte {
	h := md5.New()
	h.Write(data)
	return h.Sum(nil)
}

// ANTI-PATTERN: SHA1 for signing
func hashWithSHA1(data []byte) []byte {
	h := sha1.New()
	h.Write(data)
	return h.Sum(nil)
}

// ANTI-PATTERN: DES cipher
func encryptDES(key, plaintext []byte) ([]byte, error) {
	block, err := des.NewCipher(key)
	if err != nil {
		return nil, err
	}
	ciphertext := make([]byte, len(plaintext))
	block.Encrypt(ciphertext, plaintext)
	return ciphertext, nil
}

// ANTI-PATTERN: RC4 stream cipher
func encryptRC4(key, plaintext []byte) ([]byte, error) {
	cipher, err := rc4.NewCipher(key)
	if err != nil {
		return nil, err
	}
	ciphertext := make([]byte, len(plaintext))
	cipher.XORKeyStream(ciphertext, plaintext)
	return ciphertext, nil
}

// ANTI-PATTERN: math/rand for security (not crypto/rand)
func generateToken() string {
	token := make([]byte, 16)
	for i := range token {
		token[i] = byte(rand.Intn(256))
	}
	return fmt.Sprintf("%x", token)
}

func main() {
	fmt.Println("Crypto anti-pattern demo")
	_ = hashWithMD5([]byte("test"))
	_ = hashWithSHA1([]byte("test"))
	fmt.Println(generateToken())
}
' | base64 | tr -d '\n')
put_file "crypto-antipatterns-go" "main.go" "$CONTENT_GO" "add Go crypto anti-patterns"

# ---- REPO 3: crypto-antipatterns-java ----
curl -sf -X POST "${GITEA_URL}/api/v1/user/repos" \
  -H "Content-Type: application/json" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -d '{"name": "crypto-antipatterns-java", "private": false, "auto_init": true, "default_branch": "main"}' > /dev/null
echo "Created repo: crypto-antipatterns-java"

CONTENT_JAVA=$(printf '%s' '
import java.security.MessageDigest;
import java.util.Random;
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public class CryptoAntiPatterns {

    // ANTI-PATTERN: MD5 for password hashing
    public static String hashMD5(String input) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] hash = md.digest(input.getBytes());
        StringBuilder sb = new StringBuilder();
        for (byte b : hash) sb.append(String.format("%02x", b));
        return sb.toString();
    }

    // ANTI-PATTERN: DES encryption (56-bit key, quantum-vulnerable and classically weak)
    public static byte[] encryptDES(byte[] key, byte[] data) throws Exception {
        SecretKeySpec keySpec = new SecretKeySpec(key, "DES");
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        return cipher.doFinal(data);
    }

    // ANTI-PATTERN: java.util.Random for security-sensitive token
    public static int generatePin() {
        Random rng = new Random();
        return rng.nextInt(9000) + 1000;
    }

    // ANTI-PATTERN: hardcoded secret key
    private static final String SECRET_KEY = "mysecretkey12345";
    private static final String API_TOKEN = "Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9.";
}
' | base64 | tr -d '\n')
put_file "crypto-antipatterns-java" "src/CryptoAntiPatterns.java" "$CONTENT_JAVA" "add Java crypto anti-patterns"

echo "=== Seed complete ==="
curl -sf "${GITEA_URL}/api/v1/repos/search?limit=10" -u "${ADMIN_USER}:${ADMIN_PASS}" | grep -o '"full_name":"[^"]*"' || true
echo ""
echo "=== Gitea source repos seeded successfully ==="
