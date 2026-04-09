FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        samba \
        samba-dsdb-modules \
        samba-vfs-modules \
        winbind \
        krb5-user \
        dnsutils \
        procps \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration
COPY smb.conf /etc/samba/smb.conf.quirk
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose Kerberos (88), LDAP (389), DNS (53)
EXPOSE 88/tcp 88/udp 389/tcp 53/tcp 53/udp

ENTRYPOINT ["/entrypoint.sh"]
