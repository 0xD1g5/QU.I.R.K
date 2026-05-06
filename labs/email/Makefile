.PHONY: certs clean help

CERTS_DIR := certs

help:
	@echo "labs/email targets:"
	@echo "  make certs   - regenerate self-signed RSA-2048 certs (D-15/D-16)"
	@echo "  make clean   - remove generated certs"

certs:
	@mkdir -p $(CERTS_DIR)
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/postfix.key \
	    -out $(CERTS_DIR)/postfix.crt -days 3650 -nodes \
	    -subj "/CN=postfix.chaos.local" 2>/dev/null
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/dovecot.key \
	    -out $(CERTS_DIR)/dovecot.crt -days 3650 -nodes \
	    -subj "/CN=dovecot.chaos.local" 2>/dev/null
	chmod 644 $(CERTS_DIR)/*.crt
	chmod 600 $(CERTS_DIR)/*.key
	@echo "Generated $(CERTS_DIR)/{postfix,dovecot}.{crt,key}"

clean:
	rm -f $(CERTS_DIR)/postfix.* $(CERTS_DIR)/dovecot.*
