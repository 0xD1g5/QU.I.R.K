.PHONY: certs clean help

CERTS_DIR := certs

help:
	@echo "labs/kafka-tls targets:"
	@echo "  make certs   - regenerate self-signed RSA-2048 cert (kafka-tls)"
	@echo "  make clean   - remove generated certs"

certs:
	@mkdir -p $(CERTS_DIR)
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/kafka-tls.key \
	    -out $(CERTS_DIR)/kafka-tls.crt -days 3650 -nodes \
	    -subj "/CN=kafka-tls.chaos.local" 2>/dev/null
	chmod 644 $(CERTS_DIR)/kafka-tls.crt
	chmod 600 $(CERTS_DIR)/kafka-tls.key
	@echo "Generated $(CERTS_DIR)/kafka-tls.{crt,key}"

clean:
	rm -f $(CERTS_DIR)/kafka-tls.crt $(CERTS_DIR)/kafka-tls.key
