.PHONY: certs clean help

CERTS_DIR := certs

help:
	@echo "labs/redis-tls targets:"
	@echo "  make certs   - regenerate self-signed RSA-2048 cert (redis-tls)"
	@echo "  make clean   - remove generated certs"

certs:
	@mkdir -p $(CERTS_DIR)
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/redis-tls.key \
	    -out $(CERTS_DIR)/redis-tls.crt -days 3650 -nodes \
	    -subj "/CN=redis-tls.chaos.local" 2>/dev/null
	chmod 644 $(CERTS_DIR)/redis-tls.crt
	chmod 600 $(CERTS_DIR)/redis-tls.key
	@echo "Generated $(CERTS_DIR)/redis-tls.{crt,key}"

clean:
	rm -f $(CERTS_DIR)/redis-tls.crt $(CERTS_DIR)/redis-tls.key
