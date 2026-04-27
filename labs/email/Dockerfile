FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        postfix \
        dovecot-imapd \
        dovecot-pop3d \
        openssl \
        ca-certificates \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY postfix/main.cf   /etc/postfix/main.cf
COPY postfix/master.cf /etc/postfix/master.cf
COPY dovecot/dovecot.conf  /etc/dovecot/dovecot.conf
COPY dovecot/10-ssl.conf   /etc/dovecot/conf.d/10-ssl.conf

RUN mkdir -p /etc/postfix/certs /etc/dovecot/private /var/mail \
 && printf '[supervisord]\nnodaemon=true\nuser=root\n\n[program:postfix]\ncommand=/usr/sbin/postfix start-fg\nautorestart=true\nstdout_logfile=/dev/stdout\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/stderr\nstderr_logfile_maxbytes=0\n\n[program:dovecot]\ncommand=/usr/sbin/dovecot -F\nautorestart=true\nstdout_logfile=/dev/stdout\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/stderr\nstderr_logfile_maxbytes=0\n' > /etc/supervisor/conf.d/email-lab.conf

EXPOSE 25 465 587 110 143 993 995

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
