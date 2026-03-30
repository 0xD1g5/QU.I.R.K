#!/bin/sh
set -e

export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
ENDPOINT="http://localstack-kms:4566"

echo "=== Waiting for LocalStack KMS to be ready ==="
until aws --endpoint-url="$ENDPOINT" kms list-keys > /dev/null 2>&1; do
  echo "Waiting for LocalStack KMS..."
  sleep 3
done

echo "=== Creating KMS keys ==="

# AES-256 symmetric key (maps to KMS_KEY_SPEC_MAP["SYMMETRIC_DEFAULT"])
aws --endpoint-url="$ENDPOINT" kms create-key \
  --key-spec SYMMETRIC_DEFAULT \
  --key-usage ENCRYPT_DECRYPT \
  --description "Lab symmetric AES-256 key"

# RSA-2048 signing key
aws --endpoint-url="$ENDPOINT" kms create-key \
  --key-spec RSA_2048 \
  --key-usage SIGN_VERIFY \
  --description "Lab RSA-2048 signing key"

# RSA-1024 signing key (weak — scanner should flag this)
# NOTE: LocalStack free tier does not support RSA_1024 key spec.
# Creating a second RSA_2048 key with "RSA-1024 weak equivalent" description as fallback.
aws --endpoint-url="$ENDPOINT" kms create-key \
  --key-spec RSA_2048 \
  --key-usage SIGN_VERIFY \
  --description "Lab RSA-1024 weak equivalent (downgraded to RSA_2048 for LocalStack compatibility)"

# ECC P-256 signing key
aws --endpoint-url="$ENDPOINT" kms create-key \
  --key-spec ECC_NIST_P256 \
  --key-usage SIGN_VERIFY \
  --description "Lab ECC P-256 signing key"

echo "=== KMS seed complete ==="
aws --endpoint-url="$ENDPOINT" kms list-keys
