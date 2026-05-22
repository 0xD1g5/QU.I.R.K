.PHONY: certs clean help

CERTS_DIR := certs

help:
	@echo "labs/postgres-tls targets:"
	@echo "  make certs   - regenerate self-signed RSA-2048 cert (postgres-tls)"
	@echo "  make clean   - remove generated certs"

certs:
	@mkdir -p $(CERTS_DIR)
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/postgres-tls.key \
	    -out $(CERTS_DIR)/postgres-tls.crt -days 3650 -nodes \
	    -subj "/CN=postgres-tls.chaos.local" 2>/dev/null
	chmod 644 $(CERTS_DIR)/postgres-tls.crt
	chmod 640 $(CERTS_DIR)/postgres-tls.key
	@echo "Generated $(CERTS_DIR)/postgres-tls.{crt,key}"

clean:
	rm -f $(CERTS_DIR)/postgres-tls.crt $(CERTS_DIR)/postgres-tls.key
