"""Emit the multihost oracle's per-host markdown rows from MEASURED findings.

Column 'Intended posture' comes from docker-compose.yml's own service comments
(what the host was BUILT to be). Column 'Measured findings' comes only from the
findings JSON. Where they disagree the row says so -- that disagreement is the
oracle's most useful content and must never be smoothed over.
"""
import json
import sys
from collections import defaultdict

SEV = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

# (name, intended posture) -- from the compose file's comments and service defs.
HOSTS = [
    ("10.80.0.10", "mh-edge-legacy", "nginx, TLS 1.0/1.1 + weak ciphers"),
    ("10.80.0.11", "mh-edge-expired", "nginx, expired certificate"),
    ("10.80.0.12", "mh-edge-rsa1024", "nginx, RSA-1024 key"),
    ("10.80.0.13", "mh-edge-sha1", "nginx, SHA-1 signed cert"),
    ("10.80.0.14", "mh-edge-chainbroken", "nginx, missing intermediate"),
    ("10.80.0.15", "mh-legacy-intranet", "plaintext HTTP only"),
    ("10.80.0.16", "mh-intranet-wiki", "plaintext HTTP"),
    ("10.80.0.17", "mh-intranet-tickets", "plaintext HTTP"),
    ("10.80.0.18", "mh-intranet-jenkins", "plaintext HTTP"),
    ("10.80.0.19", "mh-intranet-fileshare", "plaintext HTTP"),
    ("10.80.0.20", "mh-app-crownjewel", "nginx, modern TLS — the CROWN JEWEL"),
    ("10.80.0.21", "mh-intranet-printsrv", "plaintext HTTP"),
    ("10.80.0.22", "mh-intranet-monitoring", "plaintext HTTP"),
    ("10.80.0.30", "mh-db-finance", "Postgres 16.6, no TLS"),
    ("10.80.0.31", "mh-cache-session", "Redis 7.4.1, no TLS/auth"),
    ("10.80.0.40", "mh-identity-dc", "OpenLDAP, 389 cleartext + 636"),
    ("10.80.0.41", "mh-saml-idp", "simplesamlphp IdP metadata"),
    ("10.80.0.50", "mh-storage-archive", "MinIO; 1 SSE-S3 + 1 UNENCRYPTED bucket"),
    ("10.80.0.60", "mh-pki-ca", "step-ca 0.28.1"),
    ("10.80.0.70", "mh-ssh-jump", "OpenSSH server"),
    ("10.80.0.101", "mh-vpn-gateway", "expired certificate"),
    ("10.80.0.102", "mh-mail-relay", "expired certificate"),
    ("10.80.0.103", "mh-vendor-portal", "expired certificate"),
    ("10.80.0.104", "mh-backup-console", "expired certificate"),
    ("10.80.0.105", "mh-devtest-api", "self-signed certificate"),
    ("10.80.0.106", "mh-staging-web", "self-signed certificate"),
    ("10.80.0.107", "mh-iot-controller", "self-signed certificate"),
    ("10.80.0.108", "mh-erp-frontend", "legacy TLS"),
    ("10.80.0.109", "mh-hr-portal", "legacy TLS"),
    ("10.80.0.110", "mh-payroll", "legacy TLS"),
    ("10.80.0.111", "mh-db-hr", "MySQL plaintext"),
]

# Short labels for measured finding titles, so the table stays readable.
SHORT = {
    "TLS certificate expired": "expired cert",
    "TLS certificate is self-signed": "self-signed cert",
    "TLS certificate uses undersized RSA key": "undersized RSA key",
    "TLS certificate uses quantum-vulnerable RSA key": "QV RSA key",
    "TLS certificate uses quantum-vulnerable ECDSA key": "QV ECDSA key",
    "TLS certificate issued by untrusted CA": "untrusted CA",
    "TLS certificate expiring within 30 days": "expiring <30d",
    "Legacy TLS cipher suites accepted": "legacy ciphers",
    "Plaintext HTTP service detected": "plaintext HTTP",
    "TLS handshake blocked assessment": "handshake blocked",
    "Unknown open service": "unknown service",
}


def main(path):
    findings = json.load(open(path))
    counts = defaultdict(lambda: defaultdict(int))
    titles = defaultdict(lambda: defaultdict(set))
    for f in findings:
        h, s = f.get("host", ""), (f.get("severity") or "").upper()
        counts[h][s] += 1
        if s != "INFO":
            titles[h][s].add(f.get("title", ""))

    print("| Host IP | Service | Intended posture | Measured findings (2026-09-14) | Severity counts |")
    print("|---|---|---|---|---|")
    for ip, name, posture in HOSTS:
        c = counts.get(ip, {})
        obs = []
        for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            for t in sorted(titles[ip].get(s, ())):
                lbl = SHORT.get(t, t)
                obs.append(f"**{lbl}**" if s in ("CRITICAL", "HIGH") else lbl)
        observed = ", ".join(obs) if obs else "_INFO only — no actionable finding_"
        sev = " ".join(
            (f"**{s}:{c[s]}**" if s in ("CRITICAL", "HIGH") else f"{s}:{c[s]}")
            for s in SEV if c.get(s)
        )
        print(f"| {ip} | {name} | {posture} | {observed} | {sev} |")
    print("| 10.80.0.200 | mh-prober | QU.I.R.K. sensor image | _n/a — scan origin, not a target_ | n/a |")


if __name__ == "__main__":
    main(sys.argv[1])
