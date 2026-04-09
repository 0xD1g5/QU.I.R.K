#!/bin/bash
set -e

# Provision on first start only (check for secrets.ldb)
if [ ! -f /var/lib/samba/private/secrets.ldb ]; then
    echo "Provisioning Samba DC for QUIRK.LAB realm..."
    samba-tool domain provision \
        --server-role=dc \
        --use-rfc2307 \
        --dns-backend=SAMBA_INTERNAL \
        --realm=QUIRK.LAB \
        --domain=QUIRK \
        --adminpass='Passw0rd123!' \
        --option="kerberos encryption types = all" \
        --option="ntlm auth = ntlmv1-permitted"

    # Copy our custom smb.conf over the provisioned one
    cp /etc/samba/smb.conf.quirk /etc/samba/smb.conf
    echo "Provisioning complete."
fi

# Start samba in foreground
exec samba --foreground --no-process-group
