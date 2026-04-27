FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        postfix \
        dovecot-imapd \
        dovecot-pop3d \
        openssl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY postfix/main.cf   /etc/postfix/main.cf
COPY postfix/master.cf /etc/postfix/master.cf
COPY dovecot/dovecot.conf  /etc/dovecot/dovecot.conf
COPY dovecot/10-ssl.conf   /etc/dovecot/conf.d/10-ssl.conf
COPY dovecot/openssl-tls12-only.cnf /etc/dovecot/openssl-tls12-only.cnf

RUN mkdir -p /etc/postfix/certs /etc/dovecot/private /var/mail

EXPOSE 25 465 587 110 143 993 995

# Default CMD runs Postfix in foreground. The dovecot-email service overrides
# this in docker-compose.yml to run dovecot instead. Each container runs ONE
# daemon so cert mounts and OPENSSL_CONF apply only to the relevant process.
CMD ["/usr/sbin/postfix", "start-fg"]
