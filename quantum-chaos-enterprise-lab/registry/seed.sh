#!/bin/sh
set -e

# REGISTRY: host-accessible address used for docker build/push (via mounted Docker socket)
# INTERNAL_REGISTRY: Compose-network address used for health-check wget only
REGISTRY="localhost:20005"
INTERNAL_REGISTRY="registry:5000"

echo "=== Waiting for registry to be ready ==="
until wget -q --spider "http://${INTERNAL_REGISTRY}/v2/" 2>/dev/null; do
  echo "Waiting for registry..."
  sleep 2
done

echo "=== Building and pushing image-old-libssl ==="
cd /registry-build/image-old-libssl
docker build -t "${REGISTRY}/image-old-libssl:latest" .
docker push "${REGISTRY}/image-old-libssl:latest"

echo "=== Building and pushing image-old-pycrypto ==="
cd /registry-build/image-old-pycrypto
docker build -t "${REGISTRY}/image-old-pycrypto:latest" .
docker push "${REGISTRY}/image-old-pycrypto:latest"

echo "=== Building and pushing image-mixed ==="
cd /registry-build/image-mixed
docker build -t "${REGISTRY}/image-mixed:latest" .
docker push "${REGISTRY}/image-mixed:latest"

echo "=== Seed complete. Registry catalog: ==="
wget -qO- "http://${INTERNAL_REGISTRY}/v2/_catalog"
echo ""
