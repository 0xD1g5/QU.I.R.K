#!/bin/bash
set -e

# Provision on first start only (check for secrets.ldb)
if [ ! -f /var/lib/samba/private/secrets.ldb ]; then
    echo "Provisioning Samba DC for QUIRK.LAB realm..."

    # The Debian samba package ships /etc/samba/smb.conf with
    # `server role = standalone server`. `samba-tool domain provision
    # --server-role=dc` reads that file first and aborts with
    # "guess_names: 'server role=STANDALONE SERVER' ... must match chosen server
    # role 'dc'! Please remove the smb.conf file and let provision generate it".
    # The Dockerfile stages our config as smb.conf.quirk and never clears the
    # packaged default, so provisioning could never succeed on a fresh container
    # and the whole `kerberos` profile failed to start. Removing it here (rather
    # than in the Dockerfile) keeps the deletion scoped to the first-run
    # provisioning branch. Not architecture-specific — found on arm64
    # 2026-09-17, but the packaged default is identical on amd64.
    rm -f /etc/samba/smb.conf

    samba-tool domain provision \
        --server-role=dc \
        --use-rfc2307 \
        --dns-backend=SAMBA_INTERNAL \
        --realm=QUIRK.LAB \
        --domain=QUIRK \
        --adminpass='Passw0rd123!' \
        --option="kerberos encryption types = all" \
        --option="ntlm auth = ntlmv1-permitted" \
        --option="posix:eadb=/var/lib/samba/eadb.tdb"

    # posix:eadb above is required under Docker. Provisioning sets NT ACLs on sysvol
    # via the security.NTACL extended attribute, which overlayfs does not support:
    # provisioning aborts with "set_nt_acl_no_snum: fset_nt_acl returned
    # NT_STATUS_ACCESS_DENIED". Pointing posix:eadb at a TDB file stores those
    # attributes in a database instead of on the filesystem. The alternative fixes
    # (privileged container, or an xattr-capable bind mount) both widen the lab's
    # capability posture for no scanning benefit — the KDC only needs to answer on
    # 88 for the Kerberos connector to enumerate enctypes.

    # Copy our custom smb.conf over the provisioned one
    cp /etc/samba/smb.conf.quirk /etc/samba/smb.conf
    echo "Provisioning complete."
fi

# Start samba in foreground
exec samba --foreground --no-process-group
