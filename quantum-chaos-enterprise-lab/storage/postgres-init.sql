-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypted demo table using pgcrypto symmetric encryption
CREATE TABLE encrypted_demo (
    id SERIAL PRIMARY KEY,
    label TEXT NOT NULL,
    data_sym TEXT,        -- pgp_sym_encrypt (symmetric PGP)
    data_hash TEXT,       -- crypt() + gen_salt() (password hashing)
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed with pgcrypto encryption examples
-- Note: pgp_sym_encrypt with a weak passphrase -- scanner finding
INSERT INTO encrypted_demo (label, data_sym, data_hash)
VALUES
    ('weakpassword-sym',
     pgp_sym_encrypt('sensitive-value', 'weakpassword'),
     crypt('password123', gen_salt('md5'))),  -- MD5 salt = weak
    ('md5-hash',
     pgp_sym_encrypt('another-secret', '1234567890'),
     crypt('admin', gen_salt('md5'))),
    ('bf-hash',
     pgp_sym_encrypt('blowfish-test', 'passphrase'),
     crypt('securepass', gen_salt('bf')));    -- blowfish = stronger

-- Crypto algorithm reference table (scannable metadata)
CREATE TABLE crypto_config (
    id SERIAL PRIMARY KEY,
    algorithm TEXT NOT NULL,
    key_size INTEGER,
    notes TEXT
);

INSERT INTO crypto_config (algorithm, key_size, notes)
VALUES
    ('DES', 56, 'Legacy block cipher -- 56-bit key, classically broken'),
    ('3DES', 112, 'Triple DES -- deprecated by NIST 2023'),
    ('AES-256-GCM', 256, 'Current recommendation'),
    ('RSA-1024', 1024, 'Weak RSA -- factored in under 1 year with modern hardware'),
    ('RSA-2048', 2048, 'Current minimum recommendation'),
    ('ECDH-P256', 256, 'Quantum-vulnerable -- 128-bit classical security');

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pglab;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pglab;
