.PHONY: certs build clean help

CERTS_DIR := certs
CN        := grpc-tls.chaos.local

help:
	@echo "labs/grpc-tls targets:"
	@echo "  make certs   - regenerate self-signed RSA-2048 TLS cert for the gRPC server"
	@echo "  make build   - build the grpc-server binary via Docker (for local testing)"
	@echo "  make clean   - remove generated certs"

certs:
	@mkdir -p $(CERTS_DIR)
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/grpc-tls.key \
	    -out $(CERTS_DIR)/grpc-tls.crt -days 3650 -nodes \
	    -subj "/CN=$(CN)" 2>/dev/null
	chmod 644 $(CERTS_DIR)/grpc-tls.crt
	chmod 640 $(CERTS_DIR)/grpc-tls.key
	@echo "Generated $(CERTS_DIR)/grpc-tls.{crt,key} (CN=$(CN), RSA-2048)"

build:
	docker build -t grpc-tls-test -f Dockerfile .

clean:
	rm -f $(CERTS_DIR)/grpc-tls.*
