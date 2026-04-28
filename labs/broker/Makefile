.PHONY: certs clean help

CERTS_DIR := certs

help:
	@echo "labs/broker targets:"
	@echo "  make certs   - regenerate self-signed RSA-2048 certs (D-17)"
	@echo "  make clean   - remove generated certs"

certs:
	@mkdir -p $(CERTS_DIR)
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/kafka.key \
	    -out $(CERTS_DIR)/kafka.crt -days 3650 -nodes \
	    -subj "/CN=kafka.chaos.local" 2>/dev/null
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/rabbitmq.key \
	    -out $(CERTS_DIR)/rabbitmq.crt -days 3650 -nodes \
	    -subj "/CN=rabbitmq.chaos.local" 2>/dev/null
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/redis.key \
	    -out $(CERTS_DIR)/redis.crt -days 3650 -nodes \
	    -subj "/CN=redis.chaos.local" 2>/dev/null
	chmod 644 $(CERTS_DIR)/*.crt
	chmod 600 $(CERTS_DIR)/*.key
	@echo "Generated $(CERTS_DIR)/{kafka,rabbitmq,redis}.{crt,key}"

clean:
	rm -f $(CERTS_DIR)/kafka.* $(CERTS_DIR)/rabbitmq.* $(CERTS_DIR)/redis.*
