import argparse
from datetime import datetime, timezone

from qcscan.config import load_config
from qcscan.interactive import interactive_config
from qcscan.db import init_db, get_session
from qcscan.models import CryptoEndpoint

from qcscan.scanner.target_expander import expand_targets
from qcscan.scanner.fingerprint import fingerprint_service
from qcscan.scanner.tls_scanner import scan_tls_targets
from qcscan.scanner.ssh_scanner import scan_ssh_targets

from qcscan.engine.risk_engine import evaluate_endpoints
from qcscan.reports.writer import write_reports


def main():
    parser = argparse.ArgumentParser(description="Quantum Crypto Scanner (qcscan)")
    parser.add_argument("--config", help="Path to config.yaml (skip prompts)")
    args = parser.parse_args()

    if args.config:
        print(f"🧾 Loading config from: {args.config}")
        cfg = load_config(args.config)
    else:
        cfg = interactive_config()

    init_db(cfg.output.db_path)

    targets = expand_targets(cfg)
    if not targets:
        print("⚠️ No targets provided. Add CIDRs/FQDNs/IPs and re-run.")
        return

    print(f"🔎 Fingerprinting {len(targets)} targets...")
    tls_targets = []
    ssh_targets = []
    inventory_endpoints = []

    for host, port in targets:
        fp = fingerprint_service(host, port, timeout=cfg.scan.timeout_seconds)

        # Create an inventory record even if non-TLS
        ep = CryptoEndpoint(
            host=host,
            port=port,
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
            sni_used=bool(cfg.scan.include_sni),
        )

        if not fp.is_open:
            ep.protocol = "CLOSED"
            ep.scan_error = f"{fp.proto}: {fp.detail}"
            inventory_endpoints.append(ep)
            continue

        if fp.proto == "SSH":
            ssh_targets.append((host, port))
            # We'll store richer info in SSH scan result; still keep the fingerprint note
            ep.protocol = "SSH"
            ep.tls_version = fp.detail
            inventory_endpoints.append(ep)
            continue

        if fp.proto == "HTTP":
            ep.protocol = "HTTP"
            ep.tls_version = fp.detail  # store HTTP status line
            inventory_endpoints.append(ep)
            continue

        if fp.proto == "TLS":
            tls_targets.append((host, port))
            # Don’t add ep here; TLS scan will add the richer record
            continue

        # UNKNOWN open port
        ep.protocol = "UNKNOWN"
        ep.tls_version = fp.detail
        inventory_endpoints.append(ep)

    print(f"🔐 TLS candidates: {len(tls_targets)} | 🔑 SSH candidates: {len(ssh_targets)} | 📦 Other inventory: {len(inventory_endpoints)}")

    tls_endpoints = scan_tls_targets(cfg, tls_targets) if tls_targets else []
    ssh_endpoints = scan_ssh_targets(cfg, ssh_targets) if ssh_targets else []

    endpoints = inventory_endpoints + tls_endpoints + ssh_endpoints
    findings = evaluate_endpoints(cfg, endpoints)

    # Persist
    with get_session(cfg.output.db_path) as session:
        for ep in endpoints:
            session.add(ep)
        session.commit()

    write_reports(cfg, endpoints, findings)


if __name__ == "__main__":
    main()
