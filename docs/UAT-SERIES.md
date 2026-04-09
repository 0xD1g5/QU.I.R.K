# QU.I.R.K. — UAT Test Series (Gating Document)

**Version:** 4.2.0
**Last Updated:** 2026-04-09 (Phase 20: Kerberos scanner added UAT-5-22)
**Purpose:** Comprehensive user acceptance testing covering all features — CLI, lab environments, cryptographic findings, web dashboard, reports, and edge cases.
**Gate Status:** This document is the **release gate** for QU.I.R.K. v4.1. All series must meet minimum pass thresholds (see Series 12: Gating Checklist) before any backlog or roadmap work proceeds.

---

## How to Use This Document

Each test case follows this format:

```
ID: UAT-{series}-{number}
Title: What is being tested
Prerequisites: What must be in place before running the test
Steps: Numbered actions to perform
Expected: What success looks like
Pass Criteria: Specific measurable condition(s)
```

**Status tracking:** Mark each test as `PASS`, `FAIL`, or `SKIP` with date and tester initials.

---

## Test Environment Requirements

- Python 3.11+
- Docker + Docker Compose v2
- `ssh-audit` installed (`pip install ssh-audit` or OS package)
- `sslyze` installed (`pip install sslyze`)
- `syft` installed (https://github.com/anchore/syft)
- `semgrep` installed (`pip install semgrep`)
- `nmap` installed (OS package, optional)
- Node.js 18+ (for dashboard development builds)
- QuRisk installed: `pip install -e ".[dashboard]"`

---

---

# Series 1: Installation & Environment Setup

---

### UAT-1-01: Package Installation — Clean Install

**Prerequisites:** Python 3.11+ virtual environment, no QuRisk installed.

**Steps:**
1. Create a fresh virtual environment: `python -m venv .venv && source .venv/bin/activate`
2. Clone repository: `git clone <repo-url> && cd QuRisk`
3. Install with dashboard extras: `pip install -e ".[dashboard]"`
4. Verify the `quirk` CLI is available: `which quirk`
5. Run: `quirk --help`

**Expected:** Help text appears listing all available flags. No import errors.

**Pass Criteria:**
- `quirk --help` exits with code 0
- Output includes `--config`, `--profile`, `--score-profile`, `--verbose` flags
- No `ModuleNotFoundError` or `ImportError` in output

---

### UAT-1-02: Version Flag

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk --version`

**Expected:** Version string printed to stdout.

**Pass Criteria:**
- Output matches format: `quirk 4.1.0` or `QU.I.R.K. v4.1.0`
- Exit code 0

---

### UAT-1-03: `quirk init` Subcommand — Default Config Generation

**Prerequisites:** QuRisk installed, empty working directory.

**Steps:**
1. Create a temp directory: `mkdir /tmp/quirk-test && cd /tmp/quirk-test`
2. Run: `quirk init`
3. List directory contents: `ls -la`
4. Open generated config: `cat config.yaml`

**Expected:** A `config.yaml` is created with all required fields pre-populated as commented examples.

**Pass Criteria:**
- `config.yaml` exists in current directory
- File contains `targets:` key
- File contains commented examples with format explanation
- No error output

---

### UAT-1-04: `quirk init` — Config at Custom Path

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk init --output /tmp/my-quirk-config.yaml`
2. Verify: `cat /tmp/my-quirk-config.yaml`

**Expected:** Config file written to the specified custom path.

**Pass Criteria:**
- File exists at `/tmp/my-quirk-config.yaml`
- File is valid YAML
- Exit code 0

---

### UAT-1-05: Dashboard Server Startup

**Prerequisites:** QuRisk installed with dashboard extras, at least one completed scan in `output/quirk.db`.

**Steps:**
1. Run: `quirk serve --no-open`
2. Wait 3 seconds for startup
3. In a new terminal: `curl -s http://127.0.0.1:8512/api/health`

**Expected:** Server starts and responds to health check.

**Pass Criteria:**
- Health endpoint returns HTTP 200
- Response body contains `{"status": "ok"}` or similar
- Server startup log shows `Uvicorn running on http://127.0.0.1:8512`

---

### UAT-1-06: Dashboard Server — Custom Port

**Prerequisites:** QuRisk installed with dashboard extras.

**Steps:**
1. Run: `quirk serve --port 9000 --no-open`
2. Wait 3 seconds
3. `curl -s http://127.0.0.1:9000/api/health`

**Expected:** Server binds to port 9000.

**Pass Criteria:**
- HTTP 200 on port 9000
- Exit code 0 for curl

---

### UAT-1-07: Identity Extras Group — Installation

**Prerequisites:** Python 3.11+ virtual environment, quirk installed without extras.

**Steps:**
1. Run: `pip install -e ".[identity]"`
2. Verify impacket is installed: `python -c "import impacket; print(impacket.__version__)"`
3. Verify dnspython is installed: `python -c "import dns.dnssec; print('dnssec ok')"`
4. Verify lxml is installed: `python -c "import lxml.etree; print('lxml ok')"`
5. Verify defusedxml is installed: `python -c "import defusedxml; print('defusedxml ok')"`
6. Verify signxml is installed: `python -c "import signxml; print('signxml ok')"`

**Expected:** All identity scanner dependencies install without conflicts.

**Pass Criteria:**
- `pip install -e ".[identity]"` exits code 0
- All five imports succeed without error
- No `ImportError` or dependency conflict in pip output
- Core quirk functionality still works: `quirk --help` exits 0

---

### UAT-1-08: Config Template — Identity Connectors Section

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk init --output /tmp/quirk-identity-test.yaml`
2. Inspect the connectors section: `cat /tmp/quirk-identity-test.yaml`
3. Confirm identity fields are commented out

**Expected:** Generated config contains commented identity fields inside the `connectors:` block.

**Pass Criteria:**
- `config.yaml` connectors block contains commented `# enable_kerberos: false`
- `config.yaml` connectors block contains commented `# enable_saml: false`
- `config.yaml` connectors block contains commented `# enable_dnssec: false`
- Only ONE `connectors:` key at column 0 (no duplicate top-level key)
- File is valid YAML: `python -c "import yaml; yaml.safe_load(open('/tmp/quirk-identity-test.yaml'))"`

---

---

# Series 2: CLI — Interactive Mode (No Config)

---

### UAT-2-01: Interactive Wizard Launch

**Prerequisites:** QuRisk installed, no `--config` flag.

**Steps:**
1. Run: `quirk` (no arguments)
2. Observe the startup banner and prompts

**Expected:** Interactive wizard launches asking for targets.

**Pass Criteria:**
- Startup banner is displayed (QU.I.R.K. branding)
- First prompt asks for target hosts/IPs
- No crash before first prompt

---

### UAT-2-02: Interactive Wizard — Single Target

**Prerequisites:** Lab running with core services (`docker compose up -d`).

**Steps:**
1. Run: `quirk`
2. When prompted for targets, enter: `127.0.0.1`
3. Accept defaults for all other prompts
4. Wait for scan to complete

**Expected:** Scan runs against `127.0.0.1`, discovers open ports, and generates output files.

**Pass Criteria:**
- At least one finding generated
- `quirk-output/findings-*.json` file created
- `quirk-output/quirk.db` exists and is non-empty
- Progress bar or status shown during scan

---

### UAT-2-03: Interactive Wizard — Multiple Targets

**Prerequisites:** Lab running.

**Steps:**
1. Run: `quirk`
2. Enter: `127.0.0.1, 127.0.0.2` or space-separated `127.0.0.1 127.0.0.2`

**Expected:** Both targets are queued for scanning.

**Pass Criteria:**
- Scan output includes results for both hosts
- No error about invalid target format

---

### UAT-2-04: Interactive Wizard — No Auto-Derivable Prompts

> Updated Phase 13 (2026-04-06): timezone, SNI, and ADCS are now auto-detected or hardcoded. Port range prompt removed — consulting set applied automatically.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` (no arguments) and step through the interactive wizard.
2. Observe every prompt that appears from start to finish.

**Expected:** The wizard never asks for timezone, SNI inclusion, Windows ADCS, or TLS ports. These are now internally derived.

**Pass Criteria:**
- No prompt containing "timezone" or "time zone" appears
- No prompt containing "SNI" or "server name indication" appears
- No prompt containing "ADCS" or "windows_adcs" appears
- No prompt asking to specify or customize TLS ports appears

---

### UAT-2-05: Interactive Wizard — Targets-First Prompt Order

> Added Phase 13 (2026-04-06): prompt order resequenced to targets-first.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` and begin the interactive wizard.
2. Note which category of question appears first.

**Expected:** The first questions ask for scan targets (IP ranges, hostnames, domains). Metadata questions (org name, data classification, output format) appear later in the sequence.

**Pass Criteria:**
- First interactive prompt is about targets/hosts/IPs
- Org name / assessment metadata prompts appear after scanner and connector options
- No metadata question appears before at least one target-related question

---

### UAT-2-06: Interactive Wizard — Scan Profile Selection Menu

> Added Phase 13 (2026-04-06): numbered profile menu replaces free-text input.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` and progress through the wizard until the profile selection step.
2. Enter a number (e.g. `2`) to select a profile.

**Expected:** A numbered menu appears listing scan profiles (e.g. Quick, Standard, Deep). Entering the corresponding number selects the profile without free-text parsing.

**Pass Criteria:**
- A numbered list of profiles is displayed
- Entering `1`, `2`, or `3` selects the profile without error
- Selected profile is reflected in scan behavior or output metadata

---

### UAT-2-07: Interactive Wizard — Data Classification Menu

> Added Phase 13 (2026-04-06): unified 4-tier numbered menu for data classification.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` and reach the data classification step.
2. Enter a number to select a tier.

**Expected:** A numbered menu appears with at least 3 tiers (e.g. Public, Internal/Confidential, Regulated, Sensitive/Restricted). Selecting a number maps to the correct `data_classification` and `data_types` fields.

**Pass Criteria:**
- Numbered menu with classification tiers is displayed
- Entering a number (not a text label) completes the selection
- No free-text classification input required

---

### UAT-2-08: Interactive Wizard — Connector Labels and Credential Warnings

> Added Phase 13 (2026-04-06): stub labels removed; credential warnings added.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` and reach the connector enable step.
2. Enable the AWS connector (or Azure).
3. Observe the label shown for the connector option and any messages printed after enabling.

**Expected:** The connector option does not contain "(stub)" in its label. After enabling, a credential warning message is printed reminding you to configure the relevant environment variable (e.g. `AWS_ACCESS_KEY_ID`).

**Pass Criteria:**
- No `(stub)` text appears in any connector option label
- Enabling AWS connector prints a message referencing `AWS_ACCESS_KEY_ID` or similar
- Enabling Azure connector prints a message referencing `AZURE_CLIENT_ID` or similar

---

### UAT-2-09: Interactive Wizard — Consulting TLS Port Set Applied

> Added Phase 13 (2026-04-06): 17-port consulting set hardcoded, no port prompt.

**Prerequisites:** Lab running with core services.

**Steps:**
1. Run `quirk`, complete the interactive wizard with `127.0.0.1` as target.
2. After the scan, inspect `output/run-stats-*.json` or the findings output for the port list used.

**Expected:** The scan uses the consulting-grade 17-port TLS set including non-standard ports such as 636 (LDAPS), 6443 (Kubernetes API), 8200 (Vault), and database ports (5432, 3306, 1433). No port selection prompt appears during the wizard.

**Pass Criteria:**
- Port 636, 6443, 8200 present in the scanned port set (check run-stats or findings)
- Port 443 and 8443 present
- No prompt asking the user to specify ports appeared during the wizard

---

---

# Series 3: CLI — Config-File Mode

---

### UAT-3-01: Scan with Config File — Minimal

**Prerequisites:** Lab running with core services. Config file created via `quirk init`.

**Steps:**
1. Edit `config.yaml`:
   ```yaml
   targets:
     - host: 127.0.0.1
       ports: [443, 8443, 8000, 2222]
   ```
2. Run: `quirk --config config.yaml`

**Expected:** Scan runs using config file targets, bypassing interactive prompts.

**Pass Criteria:**
- No interactive prompts appear
- Scan starts immediately
- Findings generated for specified ports
- Exit code 0

---

### UAT-3-02: Scan Profiles — Quick vs Standard vs Deep

**Prerequisites:** Lab running, config file pointing to `127.0.0.1:443`.

**Steps:**
1. Run quick scan: `quirk --config config.yaml --profile quick`
2. Record output file name (timestamp in name)
3. Run standard scan: `quirk --config config.yaml --profile standard`
4. Run deep scan: `quirk --config config.yaml --profile deep`
5. Compare `run-stats-*.json` files for each run

**Expected:** Deep scan takes longer and produces more detailed TLS cipher data than quick scan.

**Pass Criteria:**
- All three profiles complete without error
- Deep scan `run-stats` shows `tls_enum_mode: deep`
- Quick scan `run-stats` shows `tls_enum_mode: off` or `fast`
- Deep scan output has more cipher suite details in findings

---

### UAT-3-03: Score Profile — Strict vs Balanced vs Lenient

**Prerequisites:** Lab running, completed scan in `output/quirk.db`.

**Steps:**
1. Run: `quirk --config config.yaml --score-profile strict`
2. Note the score in `scorecard-*.md`
3. Run: `quirk --config config.yaml --score-profile balanced`
4. Note the score
5. Run: `quirk --config config.yaml --score-profile lenient`
6. Note the score

**Expected:** Strict produces lowest score, lenient produces highest.

**Pass Criteria:**
- `score_strict <= score_balanced <= score_lenient`
- All three `scorecard-*.md` files contain the score profile name
- No error output for any profile

---

### UAT-3-04: Verbose Output

**Prerequisites:** Lab running with core services.

**Steps:**
1. Run: `quirk --config config.yaml --verbose`
2. Observe terminal output

**Expected:** Per-endpoint scan details printed during execution.

**Pass Criteria:**
- Each scanned endpoint produces a log line
- TLS handshake results visible per port
- Output is noticeably more verbose than without `--verbose`

---

### UAT-3-05: Progress Bars

**Prerequisites:** Lab running with multiple ports.

**Steps:**
1. Run: `quirk --config config.yaml --progress`
2. Watch terminal during scan

**Expected:** Rich progress bar displayed during scan phases.

**Pass Criteria:**
- Progress bar renders with phase name (e.g., "Fingerprinting", "TLS Scanning")
- Bar advances as endpoints are processed
- Bar disappears or completes cleanly at scan end
- Summary table printed after scan completes

---

### UAT-3-06: Safe Mode

**Prerequisites:** Config file with multiple targets.

**Steps:**
1. Run: `quirk --config config.yaml --safe-mode`
2. Compare timing to a standard scan

**Expected:** Scan runs slower (halved concurrency, raised timeouts).

**Pass Criteria:**
- Scan completes successfully
- `run-stats-*.json` documents that safe mode was used or concurrency is reduced
- No timeout errors that would appear in standard mode

---

### UAT-3-07: Discovery Mode — nmap

**Prerequisites:** `nmap` installed. Lab running.

**Steps:**
1. Create config targeting `127.0.0.1` with no explicit ports
2. Run: `quirk --config config.yaml --discovery nmap`
3. Check which ports were discovered

**Expected:** nmap pre-scan discovers open ports before the main scan.

**Pass Criteria:**
- Discovered ports include at least 443, 8443, 8000, 2222
- `run-stats-*.json` shows `discovery_mode: nmap`
- No crash if nmap is installed

---

### UAT-3-08: Cache Mode

**Prerequisites:** Lab running. Initial scan completed.

**Steps:**
1. Run first scan: `quirk --config config.yaml --cache`
2. Note completion time
3. Run second scan with cache: `quirk --config config.yaml --resume`
4. Note completion time

**Expected:** Cached scan is significantly faster (skips discovery/fingerprint phases).

**Pass Criteria:**
- Second scan completes faster than first
- `run-stats-*.json` for second run shows lower discovery time
- Results are equivalent between runs

---

### UAT-3-09: Quiet Mode — Banner Suppression

**Prerequisites:** Lab running with core services.

**Steps:**
1. Run: `quirk --quiet --config config.yaml`
2. Observe terminal output during scan
3. Wait for scan to complete

**Expected:** Startup banner is suppressed, but the rich scan summary table still appears at completion.

**Pass Criteria:**
- No `QU.I.R.K.` ASCII art or banner text visible at startup
- Scan summary table (protocol counts, timing) is still printed
- Scan completes normally with exit code 0
- Output files generated as usual

---

### UAT-3-10: Rate Limiting

**Prerequisites:** Lab running with core services. Config file targeting at least 5 ports.

**Steps:**
1. Run unlimited: `quirk --config config.yaml` and record `run-stats-*.json` total time
2. Run rate-limited: `quirk --config config.yaml --rate-limit 2` and record total time
3. Compare fingerprinting phase duration between runs

**Expected:** Rate-limited scan is noticeably slower due to throttled target/second rate.

**Pass Criteria:**
- Both scans complete without error
- Rate-limited `run-stats-*.json` shows `rate_limit: 2.0`
- Fingerprinting phase in rate-limited run takes longer than unlimited
- Same number of findings produced by both runs

---

---

# Series 4: Lab Environment — Core Services (Baseline)

**Prerequisites for all Series 4 tests:**
```bash
cd quantum-chaos-enterprise-lab
docker compose up -d
sleep 10  # allow services to initialize
```

---

### UAT-4-01: Lab Health Check — All Core Services Up

**Steps:**
1. Run: `docker compose ps`
2. Check all core services show `running` or `healthy`

**Expected:** All 10 core services are running.

**Pass Criteria:**
All of these services show status `Up` or `running`:
- `tls-modern` (443)
- `tls-legacy` (8443)
- `tls-expired` (9443)
- `tls-selfsigned` (10443)
- `tls-mtls-required` (11443)
- `http-on-8444` (8444)
- `legacy-http` (8000)
- `ssh-alt` (2222)
- `unknown-port` (5555)
- `tls-slow-proxy` (12443)

---

### UAT-4-02: Modern TLS Service (Port 443)

**Steps:**
1. Verify service: `curl -sk https://127.0.0.1:443 | head -5`
2. Check TLS version: `openssl s_client -connect 127.0.0.1:443 -tls1_3 2>&1 | grep "Protocol"`

**Expected:** TLS 1.3 negotiated, valid (self-signed lab) certificate returned.

**Pass Criteria:**
- `openssl` output shows `Protocol : TLSv1.3`
- curl returns HTTP response (not connection refused)

---

### UAT-4-03: Legacy TLS Service (Port 8443)

**Steps:**
1. Check legacy TLS availability: `openssl s_client -connect 127.0.0.1:8443 -tls1_2 2>&1 | grep "Protocol"`
2. Attempt TLS 1.0: `openssl s_client -connect 127.0.0.1:8443 -tls1 2>&1 | grep -E "Protocol|error"`

**Expected:** TLS 1.2 negotiates. TLS 1.0 may or may not succeed depending on OpenSSL version.

**Pass Criteria:**
- TLS 1.2 handshake succeeds
- Port responds to TLS connections

---

### UAT-4-04: Expired Certificate (Port 9443)

**Steps:**
1. Connect: `openssl s_client -connect 127.0.0.1:9443 2>&1 | grep -E "notAfter|verify error"`

**Expected:** Certificate has an expiry date in the past.

**Pass Criteria:**
- `notAfter` date is before today's date (2026-03-31)
- `verify error:num=10` (certificate has expired) visible, OR cert is within 30 days of expiry

---

### UAT-4-05: Self-Signed Certificate (Port 10443)

**Steps:**
1. `openssl s_client -connect 127.0.0.1:10443 2>&1 | grep -E "verify error|self.signed"`

**Expected:** Self-signed certificate error.

**Pass Criteria:**
- `verify error:num=18` (self-signed certificate) OR
- `verify error:num=19` (self-signed certificate in chain)

---

### UAT-4-06: mTLS Required (Port 11443)

**Steps:**
1. Attempt without client cert: `curl -sk https://127.0.0.1:11443`
2. Observe error

**Expected:** Connection fails or returns mTLS error without a client certificate.

**Pass Criteria:**
- curl exits with non-zero code OR returns `400 No required SSL certificate was sent`
- Port is reachable (not connection refused — service is up)

---

### UAT-4-07: HTTP on TLS-like Port (Port 8444)

**Steps:**
1. `curl -s http://127.0.0.1:8444`
2. `curl -sk https://127.0.0.1:8444`

**Expected:** HTTP (plaintext) works; HTTPS does not.

**Pass Criteria:**
- HTTP curl returns HTTP 200 response
- HTTPS curl fails with SSL error

---

### UAT-4-08: Legacy HTTP Plaintext (Port 8000)

**Steps:**
1. `curl -s http://127.0.0.1:8000`
2. Check response: no TLS, plain HTTP.

**Expected:** Plaintext HTTP response.

**Pass Criteria:**
- HTTP 200 or 301 returned
- No TLS involved

---

### UAT-4-09: SSH Alt Port (Port 2222)

**Steps:**
1. `ssh-keyscan -p 2222 127.0.0.1 2>&1`
2. Or: `nc -z 127.0.0.1 2222 && echo "open"`

**Expected:** SSH service responds.

**Pass Criteria:**
- ssh-keyscan returns at least one host key line
- Port is open and responding to SSH banner

---

### UAT-4-10: Unknown Port (Port 5555)

**Steps:**
1. `nc -z 127.0.0.1 5555 && echo "open"`
2. `echo "test" | nc 127.0.0.1 5555`

**Expected:** Port is open, responds with raw data (not HTTP or TLS).

**Pass Criteria:**
- Port 5555 is open
- No HTTP or TLS protocol recognized

---

### UAT-4-11: Full Core Lab Scan via QuRisk CLI

**Steps:**
1. Create `lab-core.yaml`:
   ```yaml
   targets:
     - host: 127.0.0.1
       ports: [443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555]
   output:
     directory: output/lab-core
   ```
2. Run: `quirk --config lab-core.yaml --profile standard`
3. Check `output/lab-core/findings-*.json`

**Expected:** All 10 core services scanned and classified correctly.

**Pass Criteria:**
- Port 443 → protocol: `TLS`, condition includes `MODERN_TLS`
- Port 8443 → protocol: `TLS`, condition includes `LEGACY_TLS`
- Port 9443 → protocol: `TLS`, condition includes `CERT_EXPIRED` or `CERT_EXPIRING`
- Port 10443 → protocol: `TLS`, condition includes `CERT_SELFSIGNED`
- Port 11443 → protocol: `TLS`, condition includes `MTLS_REQUIRED`
- Port 8444 → protocol: `HTTP`, condition includes `HTTP_ON_TLS_LIKE_PORT`
- Port 8000 → protocol: `HTTP`, condition includes `PLAINTEXT_HTTP`
- Port 2222 → protocol: `SSH`
- Port 5555 → protocol: `UNKNOWN`
- Total findings count ≥ 5

---

---

# Series 5: Lab Profiles — Extended Scenarios

---

### UAT-5-01: Phase A Profile — Start Services

**Steps:**
1. `cd quantum-chaos-enterprise-lab`
2. `docker compose --profile phaseA up -d`
3. `sleep 10`
4. Verify: `docker compose --profile phaseA ps`

**Expected:** All Phase A services are up alongside core services.

**Pass Criteria:**
- Services on ports 13443, 14443, 15443, 15001, 18000, 5556, 15432, 16379, 15672, 24443 show `Up`

---

### UAT-5-02: Weak TLS Chain — Missing Intermediate (Port 13443)

**Steps:**
1. `openssl s_client -connect 127.0.0.1:13443 2>&1 | grep -E "verify error|depth"`

**Expected:** Certificate chain validation fails due to missing intermediate.

**Pass Criteria:**
- `verify error:num=2` (unable to get issuer certificate) or similar chain error
- Connection still establishes (TLS is present, chain is incomplete)

---

### UAT-5-03: Weak RSA-1024 Key (Port 14443)

**Steps:**
1. `openssl s_client -connect 127.0.0.1:14443 2>&1 | openssl x509 -noout -text 2>/dev/null | grep "Public-Key"`

**Expected:** Certificate uses 1024-bit RSA key.

**Pass Criteria:**
- Output shows `Public-Key: (1024 bit)`

---

### UAT-5-04: SHA-1 Signed Certificate (Port 15443)

**Steps:**
1. `openssl s_client -connect 127.0.0.1:15443 2>&1 | openssl x509 -noout -text 2>/dev/null | grep "Signature Algorithm"`

**Expected:** Certificate signed with SHA-1.

**Pass Criteria:**
- Output shows `sha1WithRSAEncryption` or similar SHA-1 algorithm

---

### UAT-5-05: JWT Profile — Start Services

**Steps:**
1. `docker compose --profile jwt up -d`
2. `sleep 5`
3. Verify ports 20001–20004 are accessible

**Expected:** Four JWT services running.

**Pass Criteria:**
- `curl -s http://127.0.0.1:20001/.well-known/jwks.json` → returns JSON with keys
- Ports 20001, 20002, 20003, 20004 all respond to curl

---

### UAT-5-06: JWT — RS256 (Good) Service (Port 20001)

**Steps:**
1. `curl -s http://127.0.0.1:20001/.well-known/jwks.json | python3 -m json.tool`

**Expected:** JWKS endpoint returns RS256 key with key size ≥ 2048.

**Pass Criteria:**
- `alg` field shows `RS256`
- `kty` is `RSA`
- Key modulus length (base64url `n`) decodes to ≥ 2048 bits

---

### UAT-5-07: JWT — HS256 (Symmetric Weak) Service (Port 20002)

**Steps:**
1. `curl -s http://127.0.0.1:20002/.well-known/jwks.json | python3 -m json.tool`

**Expected:** Service returns HS256 symmetric algorithm — a quantum-vulnerable finding.

**Pass Criteria:**
- `alg` field shows `HS256`
- OR JWT scanner detects symmetric key usage (no public key in JWKS)

---

### UAT-5-08: JWT — RSA-1024 Weak Key (Port 20003)

**Steps:**
1. `curl -s http://127.0.0.1:20003/.well-known/jwks.json | python3 -m json.tool`

**Expected:** JWKS returns RSA key with 1024-bit modulus.

**Pass Criteria:**
- RSA modulus length decodes to 1024 bits
- QuRisk JWT scanner flags this as weak key size

---

### UAT-5-09: JWT — Algorithm None (Port 20004)

**Steps:**
1. `curl -s http://127.0.0.1:20004/.well-known/jwks.json`

**Expected:** Service uses `alg: none` — critical vulnerability (no signature verification).

**Pass Criteria:**
- Response indicates `alg: none` usage or scanner classifies as `CRITICAL_NO_SIGNATURE`
- QuRisk flags this as a critical finding

---

### UAT-5-10: Full JWT Lab Scan

**Steps:**
1. Create `lab-jwt.yaml`:
   ```yaml
   targets:
     - host: 127.0.0.1
       ports: [20001, 20002, 20003, 20004]
   ```
2. Run: `quirk --config lab-jwt.yaml`
3. Check findings for JWT-specific results

**Expected:** At least 3 JWT findings: HS256, RSA-1024, alg:none.

**Pass Criteria:**
- Findings include at least one CRITICAL severity (alg:none)
- Findings include HS256 symmetric key finding
- Findings include RSA-1024 weak key finding
- Total JWT-related findings ≥ 3

---

### UAT-5-11: SSH Weak Profile (Port 20022)

**Steps:**
1. `docker compose --profile ssh-weak up -d && sleep 5`
2. `ssh-audit 127.0.0.1:20022 2>&1 | head -40`

**Expected:** ssh-audit returns critical/warning findings for weak algorithms.

**Pass Criteria:**
- KEX: `diffie-hellman-group1-sha1` flagged as CRITICAL
- Host Key: `ssh-dss` flagged as CRITICAL
- MAC: `hmac-md5` flagged as CRITICAL
- Total critical+warning findings ≥ 3

---

### UAT-5-12: Weak SSH Scan via QuRisk CLI

**Steps:**
1. Create `lab-ssh-weak.yaml`:
   ```yaml
   targets:
     - host: 127.0.0.1
       ports: [20022]
   ```
2. Run: `quirk --config lab-ssh-weak.yaml --verbose`
3. Review `output/findings-*.json` for SSH findings

**Expected:** QuRisk captures and surfaces weak SSH algorithm findings.

**Pass Criteria:**
- Finding for `diffie-hellman-group1-sha1` present with HIGH or CRITICAL severity
- Finding for `ssh-dss` host key present
- Finding for `hmac-md5` MAC present
- All findings have quantum vulnerability assessment

---

### UAT-5-13: Identity Profile — Keycloak TLS (Port 15449)

**Steps:**
1. `docker compose --profile identity up -d && sleep 20`
2. `curl -sk https://127.0.0.1:15449/ | head -5`
3. `openssl s_client -connect 127.0.0.1:15449 2>&1 | grep "Protocol"`

**Expected:** Keycloak running behind TLS proxy, TLS certificate served.

**Pass Criteria:**
- Port 15449 responds to HTTPS
- TLS certificate has Keycloak-related subject
- TLS version ≥ 1.2

---

### UAT-5-14: Container Registry Scan (Profile: registry)

**Steps:**
1. `docker compose --profile registry up -d && sleep 10`
2. Check registry is up: `curl -s http://127.0.0.1:20005/v2/`
3. Create `lab-registry.yaml`:
   ```yaml
   containers:
     - 127.0.0.1:20005/image-old-libssl
     - 127.0.0.1:20005/image-old-pycrypto
     - 127.0.0.1:20005/image-mixed
   ```
4. Run: `quirk --config lab-registry.yaml`
5. Check container findings in `output/findings-*.json`

**Expected:** Syft detects outdated crypto libraries in all three seeded images.

**Pass Criteria:**
- Finding for `openssl 1.0.2n` in `image-old-libssl`
- Finding for `cryptography 2.9.2` in `image-old-pycrypto`
- Finding for `pyopenssl 19.1.0` in `image-old-pycrypto`
- Total container crypto findings ≥ 4

---

### UAT-5-15: Source Code Scan (Profile: source)

**Steps:**
1. `docker compose --profile source up -d && sleep 15`
2. Verify Gitea: `curl -s http://127.0.0.1:20006`
3. Create `lab-source.yaml`:
   ```yaml
   sources:
     - http://127.0.0.1:20006/admin/crypto-antipatterns-python
     - http://127.0.0.1:20006/admin/crypto-antipatterns-go
   ```
4. Run: `quirk --config lab-source.yaml`

**Expected:** Semgrep detects hardcoded keys, weak algorithms, and deprecated protocols.

**Pass Criteria:**
- MD5 usage detected in Python repo
- Hardcoded keys detected
- Weak random usage detected
- Deprecated protocol (TLS 1.0 pinning) detected
- Total source findings ≥ 4 across both repos

---

### UAT-5-16: Cloud KMS Scan — LocalStack (Profile: storage)

**Steps:**
1. `docker compose --profile storage up -d && sleep 10`
2. Create `lab-kms.yaml`:
   ```yaml
   cloud:
     aws:
       endpoint: http://127.0.0.1:20007
       region: us-east-1
   ```
3. Run: `quirk --config lab-kms.yaml --cloud aws`

**Expected:** AWS connector enumerates KMS keys and classifies their cryptographic properties.

**Pass Criteria:**
- At least 3 KMS keys discovered
- `RSA_2048` key classified as quantum-vulnerable
- `ECC_NIST_P256` key classified as quantum-vulnerable
- `SYMMETRIC_DEFAULT` (AES-256) key classified

---

### UAT-5-17: LDAPS Profile Scan via CLI (Port 636)

**Prerequisites:** `sslyze` installed.

**Steps:**
1. Start LDAPS: `cd quantum-chaos-enterprise-lab && PROFILE_ARGS="--profile ldaps" ./lab.sh up && sleep 10`
2. Verify service: `openssl s_client -connect 127.0.0.1:636 2>&1 | grep "Protocol"`
3. Create `lab-ldaps.yaml` with TLS ports including 636:
   ```yaml
   assessment:
     name: "LDAPS Test"
     data_classification: "internal"
     report_owner: "Lab"
     timezone: "UTC"
   targets:
     ips: ["127.0.0.1"]
   scan:
     ports_tls: [636]
     timeout: 10
     max_workers: 5
   output:
     directory: "./output-ldaps"
     db_path: "./output-ldaps/quirk.db"
   ```
4. Run: `quirk --config lab-ldaps.yaml`
5. Review findings in `output-ldaps/`

**Expected:** sslyze scans LDAPS on port 636 and returns TLS certificate findings.

**Pass Criteria:**
- TLS handshake succeeds on port 636
- Certificate findings include self-signed lab cert detection
- Protocol support (TLS 1.2/1.3) documented in findings
- CBOM includes algorithms from the LDAPS TLS negotiation
- No scan errors for port 636

---

### UAT-5-18: Storage Profile — Vault Transit Keys

**Prerequisites:** Storage profile running (`docker compose --profile storage up -d`), Vault healthy on port 20009.

**Steps:**
1. Verify Vault is running: `curl -s http://localhost:20009/v1/sys/health | python3 -m json.tool`
2. Verify seeded keys exist:
   ```bash
   curl -s -H "X-Vault-Token: root" http://localhost:20009/v1/transit/keys/rsa-2048 | python3 -m json.tool | head -10
   curl -s -H "X-Vault-Token: root" http://localhost:20009/v1/transit/keys/rsa-1024 | python3 -m json.tool | head -10
   curl -s -H "X-Vault-Token: root" http://localhost:20009/v1/transit/keys/aes256 | python3 -m json.tool | head -10
   ```
3. Run QUIRK scan with storage config (same as UAT-5-16 but include Vault endpoint)
4. Review findings and CBOM output

**Expected:** Vault transit keys are enumerated with their cryptographic properties.

**Pass Criteria:**
- `rsa-2048` key detected and classified as quantum-vulnerable
- `rsa-1024` key detected and flagged as both weak key size AND quantum-vulnerable
- `aes256` key detected and classified (quantum-vulnerable via Grover)
- All three keys appear as components in the CBOM output

---

### UAT-5-19: Storage Profile — PostgreSQL pgcrypto Reachability

**Prerequisites:** Storage profile running (`docker compose --profile storage up -d`).

**Steps:**
1. Verify PostgreSQL is running: `pg_isready -h 127.0.0.1 -p 20010 -U pglab` (or `docker compose exec postgres-pgcrypto pg_isready`)
2. Verify pgcrypto data exists:
   ```bash
   docker compose exec postgres-pgcrypto psql -U pglab -d pgcrypto_lab -c "SELECT count(*) FROM encrypted_demo;"
   ```
3. Confirm the `encrypted_demo` table uses `pgp_sym_encrypt` with a weak passphrase

**Expected:** PostgreSQL pgcrypto service is reachable and contains seeded encrypted data.

**Pass Criteria:**
- Port 20010 responds to PostgreSQL connections
- `encrypted_demo` table exists with encrypted rows
- `pgp_sym_encrypt` function was used (visible in table schema or seed script)
- Service is a valid scan target for future database-level crypto detection (BACK-12)

---

### UAT-5-20: DNSSEC Profile — Chaos Lab Zones

**Prerequisites:** Phase 18 DNSSEC scanner implemented. Docker available. `dnspython` installed.

**Steps:**
1. Start the DNSSEC chaos lab:
   ```bash
   cd quantum-chaos-enterprise-lab
   docker compose --profile dnssec up -d
   sleep 15
   ```
2. Verify BIND9 is serving zones:
   ```bash
   dig @127.0.0.1 -p 15353 weak.chaos.local SOA
   dig @127.0.0.1 -p 15353 weak.chaos.local DNSKEY
   dig @127.0.0.1 -p 15353 unsigned.chaos.local SOA
   ```
3. Run integration scan:
   ```bash
   QUIRK_INTEGRATION_TESTS=1 python3 -m pytest tests/test_dnssec_scanner.py -k "integration" -v
   ```
4. Tear down:
   ```bash
   docker compose --profile dnssec down
   ```

**Expected:** BIND9 serves all 4 zones. Integration test passes with all required findings.

**Pass Criteria:**
- `docker compose --profile dnssec ps` shows `bind9-dnssec` with `Up` status
- `dig @127.0.0.1 -p 15353 weak.chaos.local DNSKEY` returns DNSKEY RRs with algorithm 5 (RSASHA1)
- `dig @127.0.0.1 -p 15353 unsigned.chaos.local DNSKEY` returns NOERROR with no DNSKEY in answer
- Integration test `test_chaos_lab_integration` passes:
  - `RSASHA1` in algorithm names (weak.chaos.local)
  - `ECDSAP256SHA256` in algorithm names (safe.chaos.local)
  - `ds-chain-broken` in service details (broken.chaos.local)
  - `unsigned-zone` in service details (unsigned.chaos.local)
- No test failures

---

### UAT-5-21: SAML/OIDC Profile — Chaos Lab SimpleSAMLphp

**Prerequisites:** Phase 19 SAML/OIDC scanner implemented. Docker available. `lxml` installed (`pip install lxml`).

**Steps:**
1. Start the SAML chaos lab:
   ```bash
   cd quantum-chaos-enterprise-lab
   docker compose --profile saml up -d
   sleep 20
   ```
2. Verify SimpleSAMLphp is serving the IdP metadata:
   ```bash
   curl -sf "http://localhost:8080/simplesaml/" | head -5
   curl -sf "http://localhost:8080/simplesaml/saml2/idp/metadata.php" | grep -o 'use="signing"'
   ```
3. Run integration scan:
   ```bash
   QUIRK_INTEGRATION_TESTS=1 python3 -m pytest tests/test_saml_scanner.py -k "chaos_lab" -v
   ```
4. Tear down:
   ```bash
   docker compose --profile saml down
   ```

**Expected:** SimpleSAMLphp serves IdP metadata with RSA-1024 signing cert. Integration test detects cert_pubkey_size=1024.

**Pass Criteria:**
- `docker compose --profile saml ps` shows `simplesamlphp` with `Up` status
- `curl http://localhost:8080/simplesaml/saml2/idp/metadata.php` returns XML with `<md:KeyDescriptor use="signing">`
- Integration test `test_chaos_lab_integration` passes:
  - At least one `CryptoEndpoint` returned
  - `cert_pubkey_size=1024` present in results (RSA-1024 weak cert detected)
- No test failures

---

### UAT-5-22: Kerberos Profile — Chaos Lab Samba DC

**Prerequisites:** Phase 20 Kerberos scanner implemented. Docker available. `impacket` installed (`pip install -e ".[identity]"`).

**Steps:**
1. Start the Kerberos chaos lab:
   ```bash
   cd quantum-chaos-enterprise-lab
   docker compose --profile kerberos up -d
   sleep 90
   ```
2. Verify Samba DC is running and serving Kerberos:
   ```bash
   docker compose --profile kerberos ps
   docker exec quantum-chaos-enterprise-lab-samba-dc-1 smbclient -L localhost -N 2>/dev/null | grep QUIRK
   ```
3. Run integration scan:
   ```bash
   QUIRK_KERBEROS_INTEGRATION=1 python3 -m pytest tests/test_kerberos_scanner.py -k "samba_dc_integration" -v
   ```
4. Tear down:
   ```bash
   docker compose --profile kerberos down
   ```

**Expected:** Samba DC serves Kerberos on port 88 with RC4-HMAC enabled. Integration test detects `rc4-hmac` in etype results.

**Pass Criteria:**
- `docker compose --profile kerberos ps` shows `samba-dc` with `Up (healthy)` status
- `smbclient -L localhost -N` returns output containing `QUIRK`
- Integration test `test_samba_dc_integration` passes:
  - At least one `CryptoEndpoint` returned
  - `rc4-hmac` present in result etype names (RC4-HMAC enabled)
  - All endpoints have `protocol="KERBEROS"` and `port=88`
  - `kerberos_scan_json` is valid JSON with `realm`, `etypes`, `ldap_status` keys
- No test failures

---

---

# Series 6: Cryptographic Findings — CLI Verification

---

### UAT-6-01: Findings Output — JSON Structure

**Prerequisites:** Completed scan with findings.

**Steps:**
1. Open `output/findings-*.json` (most recent)
2. Validate structure with: `python3 -c "import json; d=json.load(open('output/findings-TIMESTAMP.json')); print(list(d[0].keys()))"`

**Expected:** Each finding has required fields.

**Pass Criteria:**
Each finding object contains:
- `host`
- `port`
- `protocol`
- `severity` (one of: CRITICAL, HIGH, MEDIUM, LOW, INFO)
- `title` or `finding_type`
- `description`
- `quantum_risk` or equivalent quantum safety assessment

---

### UAT-6-02: TLS Findings — Cipher Suite Detection

**Prerequisites:** Lab core running. Completed scan covering port 8443 (legacy TLS).

**Steps:**
1. Review `output/findings-*.json`
2. Filter for port 8443: `python3 -c "import json; data=json.load(open('output/findings-TIMESTAMP.json')); [print(f) for f in data if f.get('port')==8443]"`

**Expected:** Legacy TLS findings on port 8443 reference specific weak cipher suites.

**Pass Criteria:**
- At least one finding for port 8443
- Finding includes cipher suite name (e.g., `TLS_RSA_WITH_AES_128_CBC_SHA`)
- Finding severity is MEDIUM or HIGH
- `quantum_risk: quantum-vulnerable` for RSA key exchange

---

### UAT-6-03: Certificate Expiry Detection

**Prerequisites:** Lab core running (port 9443 = expired cert). Completed scan.

**Steps:**
1. Check findings for port 9443: `cat output/findings-*.json | python3 -m json.tool | grep -A5 '"port": 9443'`
2. Review certificate fields: expiry date, days remaining

**Expected:** Finding indicates certificate is expired.

**Pass Criteria:**
- Finding severity is HIGH or CRITICAL
- `cert_not_after` is in the past relative to scan date
- Finding type references `CERT_EXPIRED` or similar
- Days remaining is negative

---

### UAT-6-04: Self-Signed Certificate Detection

**Prerequisites:** Lab core running (port 10443 = self-signed). Completed scan.

**Steps:**
1. Check findings for port 10443
2. Look for self-signed indicator in cert data

**Expected:** Finding identifies self-signed certificate.

**Pass Criteria:**
- Finding type references `CERT_SELFSIGNED` or `SELF_SIGNED`
- `cert_issuer` equals `cert_subject` in the scan data
- Finding severity is MEDIUM or HIGH

---

### UAT-6-05: mTLS Endpoint Classification

**Prerequisites:** Lab core running (port 11443 = mTLS). Completed scan.

**Steps:**
1. Check findings for port 11443
2. Review protocol classification

**Expected:** Endpoint classified as TLS-present but handshake blocked.

**Pass Criteria:**
- Protocol is `TLS` (not HTTP or UNKNOWN)
- Condition includes `MTLS_REQUIRED` or `TLS_HANDSHAKE_FAILED`
- Service correctly identified as TLS, not misclassified as HTTP

---

### UAT-6-06: Plaintext HTTP Finding — Severity Check

**Prerequisites:** Lab core running (port 8000 = plaintext HTTP). Completed scan.

**Steps:**
1. Check findings for port 8000
2. Verify severity level

**Expected:** Plaintext HTTP exposure flagged as HIGH severity.

**Pass Criteria:**
- Finding type: `PLAINTEXT_HTTP` or `HTTP_EXPOSURE`
- Severity: HIGH or CRITICAL
- Finding includes remediation guidance

---

### UAT-6-07: HTTP on TLS-Like Port Detection

**Prerequisites:** Lab core running (port 8444 = HTTP on TLS port). Completed scan.

**Steps:**
1. Check findings for port 8444
2. Verify it's not misclassified as TLS

**Expected:** Port 8444 classified as HTTP (not TLS), with a specific finding for misconfiguration.

**Pass Criteria:**
- Protocol: `HTTP`
- Finding type references `HTTP_ON_TLS_LIKE_PORT`
- Severity: HIGH

---

### UAT-6-08: Quantum Safety Classification — SSH Algorithms

**Prerequisites:** Lab running with SSH on port 2222. Completed scan.

**Steps:**
1. Review SSH-related findings in output JSON
2. Check algorithm classifications

**Expected:** SSH algorithms classified with quantum safety labels.

**Pass Criteria:**
- ED25519 host key (if present) classified as `quantum-safe` or at least not quantum-vulnerable
- RSA host key classified as `quantum-vulnerable`
- ECDSA algorithms classified as `quantum-vulnerable`
- Each algorithm has NIST quantum level in the finding

---

### UAT-6-09: Scorecard Output — CLI Review

**Prerequisites:** Completed scan.

**Steps:**
1. `cat output/scorecard-*.md`
2. Review all sections

**Expected:** Scorecard contains score, confidence, key drivers, and action items.

**Pass Criteria:**
- Score between 0 and 100
- Confidence score present
- `## Key Risk Drivers` section with at least 1 item
- `## Recommended Actions (Next 30 Days)` section
- `## Recommended Actions (Next 60 Days)` section

---

### UAT-6-10: Roadmap Output — Migration Phases

**Prerequisites:** Completed scan with findings.

**Steps:**
1. `cat output/roadmap-*.md`
2. Review NOW/NEXT/LATER sections

**Expected:** Roadmap organized into three phases with evidence-driven recommendations.

**Pass Criteria:**
- `## NOW (0–30 days)` section present with ≥ 1 item
- `## NEXT (31–90 days)` section present with ≥ 1 item
- `## LATER (90+ days)` section present with ≥ 1 item
- Each item has `Why:` evidence description
- Each item has an `Owner:` placeholder

---

### UAT-6-11: CBOM JSON Structure

**Prerequisites:** Completed TLS scan.

**Steps:**
1. `python3 -c "import json; d=json.load(open('output/cbom-TIMESTAMP.json')); print(d['bomFormat'], d['specVersion'])"`
2. Count components: `python3 -c "import json; d=json.load(open('output/cbom-TIMESTAMP.json')); print(len(d.get('components', [])))"`

**Expected:** Valid CycloneDX 1.6 JSON with algorithm, certificate, and protocol components.

**Pass Criteria:**
- `bomFormat: "CycloneDX"`
- `specVersion: "1.6"`
- Components include at minimum:
  - At least one `type: "cryptographic-asset"` component
  - At least one algorithm component (e.g., AES-256-GCM, RSA)
- CBOM has a `serialNumber` BOM-ref

---

### UAT-6-12: CBOM XML Validity

**Prerequisites:** Completed scan, `cbom-*.xml` present.

**Steps:**
1. `python3 -c "import xml.etree.ElementTree as ET; ET.parse('output/cbom-TIMESTAMP.xml'); print('Valid XML')"`

**Expected:** XML file is well-formed and parseable.

**Pass Criteria:**
- No XML parse error
- Root element is CycloneDX namespace element

---

### UAT-6-13: Intelligence JSON — Machine-Readable Output

**Prerequisites:** Completed scan.

**Steps:**
1. `python3 -c "import json; d=json.load(open('output/intelligence-TIMESTAMP.json')); print(list(d.keys()))"`

**Expected:** Machine-readable JSON with score, confidence, evidence, and roadmap.

**Pass Criteria:**
- Keys include: `score`, `confidence`, `score_label`, `evidence`, `roadmap`
- `score` is numeric, 0–100
- `confidence` is numeric, 0–100
- `roadmap` contains NOW/NEXT/LATER items
- `evidence` contains finding counts

---

---

# Series 7: Web Dashboard — UI Testing

**Prerequisites for all Series 7 tests:**
1. Completed scan producing findings in `output/quirk.db`
2. Dashboard running: `quirk serve --no-open`
3. Open browser to `http://127.0.0.1:8512`

---

### UAT-7-01: Dashboard Loads — No Blank Screen

**Steps:**
1. Navigate to `http://127.0.0.1:8512`
2. Observe page load

**Expected:** Dashboard loads with QU.I.R.K. branding visible.

**Pass Criteria:**
- Page loads within 5 seconds
- QU.I.R.K. wordmark visible in sidebar
- No JavaScript console errors (check DevTools)
- No blank white screen

---

### UAT-7-02: Dashboard — Favicon

**Steps:**
1. Check browser tab
2. Inspect page source: `curl -s http://127.0.0.1:8512 | grep favicon`

**Expected:** QU.I.R.K. electric-blue favicon displayed in browser tab.

**Pass Criteria:**
- Favicon appears in browser tab (not browser default icon)
- Page title is `QU.I.R.K.` or similar branded title

---

### UAT-7-03: Executive Page — Score Gauge

**Steps:**
1. Navigate to Executive page (default landing or `/executive` route)
2. Observe the score gauge component

**Expected:** Quantum Readiness Score displayed as a visual gauge.

**Pass Criteria:**
- Score gauge renders with a numeric value 0–100
- Score label visible (EXCELLENT/GOOD/MODERATE/FAIR/POOR)
- Score color-coded (green = good, red = poor)
- Confidence badge present with value

---

### UAT-7-04: Executive Page — Severity Chart

**Steps:**
1. On Executive page, locate severity distribution chart

**Expected:** Bar or pie chart showing CRITICAL/HIGH/MEDIUM/LOW/INFO finding counts.

**Pass Criteria:**
- Chart renders with at least 2 severity levels
- Severity counts match findings in `output/findings-*.json`
- Chart is interactive (hover shows count)

---

### UAT-7-05: Executive Page — Score Driver Cards

**Steps:**
1. On Executive page, scroll to driver cards section

**Expected:** Four score driver cards: Hygiene, Modern TLS, Identity Trust, Agility Signals.

**Pass Criteria:**
- All 4 subscores visible (each out of 25 pts)
- Each card shows the subscore value
- Each card has a brief description
- Cards total ≤ 100

---

### UAT-7-06: Findings Page — Table Renders

**Steps:**
1. Navigate to Findings page (sidebar link)
2. Observe findings table

**Expected:** Table displays all findings with sortable columns.

**Pass Criteria:**
- Table renders with rows (not empty)
- Columns: Severity, Host, Port, Protocol, Finding Title
- Row count matches `output/findings-*.json` count
- Severity badges color-coded correctly

---

### UAT-7-07: Findings Page — Sorting

**Steps:**
1. On Findings page, click the "Severity" column header
2. Observe sort order change
3. Click again to reverse sort

**Expected:** Table sorts by severity in both ascending and descending order.

**Pass Criteria:**
- First click: sorted ascending (INFO → CRITICAL)
- Second click: sorted descending (CRITICAL → INFO)
- Sort indicator (arrow) visible on column header

---

### UAT-7-08: Findings Page — Filtering

**Steps:**
1. On Findings page, locate filter/search input
2. Type `CRITICAL` in the filter
3. Observe table rows

**Expected:** Table filters to show only CRITICAL severity findings.

**Pass Criteria:**
- Only rows with CRITICAL severity shown
- Row count decreases when filter applied
- Clearing filter restores all rows

---

### UAT-7-09: Findings Page — Detail Slide-out

**Steps:**
1. On Findings page, click any finding row
2. Observe right-side detail panel/sheet

**Expected:** Slide-out panel opens with full finding details.

**Pass Criteria:**
- Detail panel opens on click
- Full description visible
- Host, port, protocol, severity all shown
- Quantum risk assessment visible
- Panel closes when clicking outside or X button

---

### UAT-7-10: Certificates Page — Inventory Table

**Steps:**
1. Navigate to Certificates page (sidebar link)

**Expected:** Certificate inventory showing all TLS certificates discovered.

**Pass Criteria:**
- Table renders with at least 1 row (from lab TLS services)
- Columns: Subject, Issuer, Expiry, Algorithm, Quantum Safety
- Expired certificates shown with visual indicator (red date)
- Self-signed certs flagged

---

### UAT-7-11: Certificates Page — Quantum Safety Labels

**Steps:**
1. On Certificates page, look for quantum safety column
2. Check labels for different certificate algorithms

**Expected:** Each certificate has a quantum safety assessment badge.

**Pass Criteria:**
- RSA certificates show `quantum-vulnerable` badge
- ECDSA certificates show `quantum-vulnerable` badge
- Badge colors differentiate safety levels
- Badge tooltip or description available

---

### UAT-7-12: Certificates Page — Expiry Sorting

**Steps:**
1. On Certificates page, click the Expiry column header to sort
2. Verify expired certs appear first (ascending) or last (descending)

**Expected:** Certificates sortable by expiry date.

**Pass Criteria:**
- Expired cert (port 9443) appears in the correct sort position
- Near-expiry certs show days remaining
- Date format is human-readable

---

### UAT-7-13: CBOM Page — Algorithm Table

**Steps:**
1. Navigate to CBOM page (sidebar link)
2. Select "Algorithms" tab (if tabbed)

**Expected:** Table of all cryptographic algorithms found in the scan.

**Pass Criteria:**
- Algorithm names visible (e.g., AES-256-GCM, RSA-2048, Ed25519)
- Quantum safety badge per algorithm
- Primitive type visible (e.g., KEY_AGREEMENT, ASYMMETRIC, SYMMETRIC)
- NIST PQC level displayed where available

---

### UAT-7-14: CBOM Page — Graph Visualization

**Steps:**
1. On CBOM page, select "Graph" tab (or equivalent)
2. Observe Cytoscape.js force-directed graph
3. Interact: drag nodes, zoom in/out

**Expected:** Interactive graph showing relationships between algorithms, protocols, and endpoints.

**Pass Criteria:**
- Graph renders with visible nodes and edges
- Nodes draggable
- Scroll-to-zoom works
- Clicking a node shows details panel or tooltip
- At least 3 connected nodes visible

---

### UAT-7-15: Roadmap Page — DAG Visualization

**Steps:**
1. Navigate to Roadmap page (sidebar link)
2. Observe directed acyclic graph

**Expected:** Migration roadmap shown as a DAG with NOW/NEXT/LATER color coding.

**Pass Criteria:**
- Graph renders with colored nodes (e.g., red=NOW, yellow=NEXT, green=LATER)
- Nodes labeled with roadmap item titles
- Clicking a node shows detail panel with `Why:` text and owner placeholder
- Dependencies shown as directed edges

---

### UAT-7-16: Roadmap Page — Node Detail Panel

**Steps:**
1. On Roadmap page, click any node

**Expected:** Right-side panel shows full roadmap item details.

**Pass Criteria:**
- Item title visible
- Timeframe visible (e.g., "0–30 days")
- `Why:` evidence text visible
- Owner placeholder shown
- Dependency list shown (if any)

---

### UAT-7-17: PDF Export — Generate Report

**Steps:**
1. On Executive page, locate "Export PDF" button
2. Click the button
3. Wait for PDF to generate (may take 10–30 seconds — Playwright renders headlessly)
4. Observe download

**Expected:** PDF file downloaded named `quirk-report.pdf`.

**Pass Criteria:**
- File downloads or save dialog appears
- File is valid PDF (open in viewer)
- PDF contains score, findings summary, and charts
- PDF is A4 format
- No error toast or error message

---

### UAT-7-18: PDF Export — API Endpoint Direct Test

**Steps:**
1. `curl -X POST http://127.0.0.1:8512/api/export/pdf -o /tmp/test-report.pdf`
2. Verify file: `file /tmp/test-report.pdf`

**Expected:** PDF file created via API.

**Pass Criteria:**
- `file` command reports `PDF document`
- File size > 50KB (not empty or truncated)
- HTTP 200 from the API endpoint

---

### UAT-7-19: Dashboard — API Latest Scan Endpoint

**Steps:**
1. `curl -s http://127.0.0.1:8512/api/scan/latest | python3 -m json.tool | head -30`

**Expected:** JSON response with full scan data.

**Pass Criteria:**
- Response includes `score`, `confidence`, `findings`, `certificates`, `cbom`, `roadmap`
- `findings` array is non-empty
- `score` is numeric
- Response time < 3 seconds

---

### UAT-7-20: Dashboard — SPA Routing

**Steps:**
1. Navigate to `http://127.0.0.1:8512/findings` directly (not via sidebar)
2. Observe page load

**Expected:** Findings page loads directly — SPA routing works.

**Pass Criteria:**
- Page renders correctly (not 404)
- Same content as navigating via sidebar
- URL stays at `/findings`

---

### UAT-7-21: Dashboard Theme — No Hardcoded Colors

**Steps:**
1. Open browser DevTools (F12) → Elements
2. Select several UI components (buttons, badges, cards)
3. Check computed styles for hardcoded hex/rgb colors (e.g., `#007bff`, `#28a745`)

**Expected:** All colors reference CSS custom properties (design tokens), not hardcoded values.

**Pass Criteria:**
- Primary interactive elements use `var(--color-*)` or equivalent CSS tokens
- No hardcoded `#hex` colors in inline styles on major components
- Electric-blue (`#00D8FF` or design system equivalent) used for accents
- Dark background palette consistent across all pages

---

### UAT-7-22: Dark/Light Theme Toggle

**Steps:**
1. Open dashboard at `http://127.0.0.1:8512`
2. Locate the dark/light mode toggle button at the bottom of the sidebar
3. Click the toggle to switch from dark to light mode
4. Observe all page elements (cards, charts, tables, sidebar) change to light theme
5. Refresh the page (F5 / Cmd+R)
6. Check that light mode persists after refresh
7. Open DevTools → Application → Local Storage → check `quirk-ui-theme` key
8. Click toggle again to return to dark mode

**Expected:** Theme toggles instantly between dark and light; preference persists across page reload.

**Pass Criteria:**
- Clicking toggle switches theme instantly (no flash of wrong theme)
- All page elements update: sidebar, cards, charts, tables, badges
- `localStorage` key `quirk-ui-theme` stores `"light"` or `"dark"`
- Theme persists after full page reload
- Both themes are visually coherent (no invisible text, unreadable badges, or broken contrast)

---

### UAT-7-23: Sidebar Responsive Collapse

**Steps:**
1. Open dashboard at full desktop width (≥ 1024px)
2. Confirm sidebar shows full 240px width with text labels and QU.I.R.K. wordmark
3. Slowly resize browser window to below 1024px width
4. Observe sidebar collapse to 48px icon-only mode
5. Verify QU.I.R.K. wordmark changes to "Q" monogram
6. Click each navigation icon — verify navigation still works
7. Hover over a nav icon — verify tooltip shows page name
8. Resize back above 1024px — verify sidebar expands to full width with labels

**Expected:** Sidebar responsively collapses and expands at the 1024px breakpoint.

**Pass Criteria:**
- Above 1024px: sidebar shows 240px with full text labels
- Below 1024px: sidebar collapses to 48px icon-only
- Wordmark transitions to monogram on collapse
- All navigation icons remain clickable and route correctly
- Tooltips appear on hover in collapsed state
- Transition is smooth (no layout jumps or flicker)

---

### UAT-7-24: Findings Page — Pagination

**Prerequisites:** Scan producing more than 25 findings (full lab scan should produce 30+).

**Steps:**
1. Navigate to Findings page
2. Count visible rows in the table
3. Look for pagination controls at the bottom of the table
4. Click "Next page" or page 2
5. Observe new rows load
6. Click "Previous page" or page 1
7. Verify original rows return

**Expected:** Table paginates at 25 rows per page with working navigation controls.

**Pass Criteria:**
- First page shows exactly 25 rows (or fewer if total < 25)
- Pagination controls visible (page numbers, next/prev buttons)
- Navigating to page 2 shows remaining findings
- Row count indicator shows "Showing X–Y of Z findings"
- Applying a filter respects pagination (re-paginates filtered results)

---

### UAT-7-25: CBOM Page — Algorithm Search

**Steps:**
1. Navigate to CBOM page → Table tab
2. Note total row count
3. Type `AES` in the algorithm search box
4. Observe table filtering in real-time
5. Clear the search box
6. Verify all rows return

**Expected:** Search filters the CBOM algorithm table by algorithm name.

**Pass Criteria:**
- Typing filters rows to only those containing the search term
- Filter is case-insensitive (`aes` matches `AES-256-GCM`)
- Clearing search restores full table
- No results shows empty state (not a crash)

---

### UAT-7-26: CBOM Page — Quantum Safety Filter

**Steps:**
1. Navigate to CBOM page → Table tab
2. Locate the Quantum Safety dropdown/filter
3. Select "Vulnerable"
4. Observe table shows only quantum-vulnerable algorithms
5. Select "Safe" (if any safe algorithms exist)
6. Clear filter to show all

**Expected:** Dropdown filters CBOM table by quantum-safety classification.

**Pass Criteria:**
- Selecting "Vulnerable" shows only red-badged algorithms (RSA, ECDSA, etc.)
- Selecting "Safe" shows only green-badged algorithms (if any)
- Clearing filter restores all rows
- Filter and search combine correctly (both applied simultaneously)

---

### UAT-7-27: CBOM Graph — Node Interaction

**Steps:**
1. Navigate to CBOM page → Graph tab
2. Wait for Cytoscape.js graph to render
3. Click an algorithm node (e.g., `AES-256-GCM`)
4. Observe detail panel on right side
5. Click a source system node (e.g., `127.0.0.1:443`)
6. Observe detail panel update

**Expected:** Clicking nodes shows contextual information in a detail panel.

**Pass Criteria:**
- Algorithm node click shows: algorithm name, quantum-safety classification, connected source systems
- Source system node click shows: host:port or file path, connected algorithms
- Panel updates when clicking different nodes
- Node colors match quantum-safety: green (Safe), amber (At Risk), red (Vulnerable)

---

### UAT-7-28: CBOM Graph — Zoom Controls

**Steps:**
1. On CBOM Graph tab, locate zoom controls (In/Out/Fit buttons)
2. Click "Zoom In" — verify graph zooms in
3. Click "Zoom Out" — verify graph zooms out
4. Pan the graph by click-dragging the background
5. Click "Fit to Viewport" — verify graph auto-scales to show all nodes
6. Use mouse scroll wheel — verify zoom works

**Expected:** All zoom and pan controls function correctly.

**Pass Criteria:**
- Zoom in/out buttons change zoom level visibly
- "Fit to Viewport" shows all nodes within visible area
- Mouse scroll wheel zooms
- Click-drag on background pans the view
- No nodes disappear off-screen permanently

---

### UAT-7-29: Roadmap — Node Drag

**Steps:**
1. Navigate to Roadmap page
2. Click and drag a node to a new position
3. Observe edges (arrows) follow the node
4. Release the node
5. Verify edges remain connected

**Expected:** DAG nodes are draggable for manual repositioning; edges follow.

**Pass Criteria:**
- Node moves smoothly during drag
- All connected edges update position in real-time
- Node stays in new position after release
- Other nodes not affected by the drag
- Layout does not reset on node release

---

### UAT-7-30: Print View

**Steps:**
1. Navigate directly to `http://127.0.0.1:8512/print`
2. Observe the page layout

**Expected:** Print-optimized single-column layout with no interactive elements.

**Pass Criteria:**
- No sidebar visible
- No interactive controls (no filters, no toggle buttons)
- Full-width single-column layout
- CSS page breaks between major sections
- Content includes: score summary, findings, certificates, CBOM reference
- Background colors and borders render (print background styling enabled)

---

### UAT-7-31: Dashboard Page Title and Branding

**Steps:**
1. Open dashboard at `http://127.0.0.1:8512`
2. Check browser tab title
3. Check sidebar header for QU.I.R.K. wordmark
4. Check favicon in browser tab

**Expected:** Professional branding visible throughout.

**Pass Criteria:**
- Browser tab title shows `QU.I.R.K. — Quantum Readiness Dashboard` or similar branded title
- Sidebar displays bold monospace electric-blue QU.I.R.K. wordmark
- Favicon shows electric-blue "Q" (not browser default icon)
- No JS console errors on page load

---

### UAT-7-32: No JavaScript Console Errors — All Pages

**Steps:**
1. Open browser DevTools (F12) → Console tab
2. Clear console
3. Navigate to Executive page (`/`) — check for errors
4. Navigate to Findings page (`/findings`) — check for errors
5. Navigate to Certificates page (`/certificates`) — check for errors
6. Navigate to CBOM page (`/cbom`) — switch between Table and Graph tabs — check for errors
7. Navigate to Roadmap page (`/roadmap`) — check for errors
8. Navigate to Print view (`/print`) — check for errors

**Expected:** Zero JavaScript errors across all pages.

**Pass Criteria:**
- No red `Error` entries in console on any page
- No unhandled promise rejections
- No `TypeError` or `ReferenceError` entries
- Warnings are acceptable (yellow) but errors (red) are not
- API requests all return 200 (check Network tab)

---

---

# Series 8: Scoring & Intelligence

---

### UAT-8-01: Score Range Validation

**Prerequisites:** Lab scanned with at least 5 diverse endpoints.

**Steps:**
1. Review `output/intelligence-*.json`
2. Extract score: `python3 -c "import json; d=json.load(open('output/intelligence-TIMESTAMP.json')); print(d['score'], d['score_label'])"`

**Expected:** Score is in range, label matches.

**Pass Criteria:**
- Score is integer or float 0–100
- Label matches:
  - 85–100 → EXCELLENT
  - 70–84 → GOOD
  - 55–69 → MODERATE
  - 35–54 → FAIR
  - 0–34 → POOR

---

### UAT-8-02: Confidence Score — Low Coverage Scenario

**Prerequisites:** Scan with high error rate (e.g., many closed ports or timeouts).

**Steps:**
1. Create config targeting mostly unreachable ports
2. Run scan
3. Check `confidence` in `output/intelligence-*.json`

**Expected:** Confidence score decreases when scan coverage is poor.

**Pass Criteria:**
- Confidence is lower than a full lab scan
- If scan error rate > 50%, confidence < 60
- Confidence score in output JSON

---

### UAT-8-03: Score Impact — Adding Plaintext HTTP

**Prerequisites:** Two scans: one with only TLS services, one also including HTTP services.

**Steps:**
1. Scan 1: `--config lab-tls-only.yaml` (only ports 443, 8443)
2. Record score
3. Scan 2: `--config lab-tls-plus-http.yaml` (add ports 8000, 8444)
4. Record score

**Expected:** Score decreases when plaintext HTTP exposure is added.

**Pass Criteria:**
- `score_scan2 < score_scan1`
- Score difference ≥ 5 points (HTTP exposure is penalized up to 18 pts)

---

### UAT-8-04: Hygiene Subscore — Plaintext Ratio

**Prerequisites:** Scan with mixed HTTP and TLS endpoints.

**Steps:**
1. Review `output/scorecard-*.md` Hygiene subscore
2. Compare with findings

**Expected:** Hygiene subscore reflects ratio of plaintext endpoints.

**Pass Criteria:**
- Hygiene subscore < 25 when ≥ 1 plaintext HTTP endpoint exists
- Subscore decreases proportionally to number of HTTP endpoints

---

### UAT-8-05: mTLS Bonus — Identity Trust Subscore

**Prerequisites:** Scan including port 11443 (mTLS required).

**Steps:**
1. Review Identity Trust subscore in scorecard

**Expected:** mTLS enforcement provides a bonus to Identity Trust subscore.

**Pass Criteria:**
- Identity Trust subscore is higher when mTLS endpoint is scanned
- mTLS bonus noted in scorecard or intelligence JSON

---

### UAT-8-06: Roadmap Evidence Links

**Prerequisites:** Completed scan with plaintext HTTP and expired cert findings.

**Steps:**
1. Review `output/roadmap-*.md` NOW section

**Expected:** NOW items reference specific discovered evidence.

**Pass Criteria:**
- NOW items reference specific finding types (e.g., "2 plaintext HTTP endpoints")
- Why text references actual scan data (not generic placeholder)
- Remediation steps are specific to findings

---

### UAT-8-07: Score Profile Consistency — CLI vs Dashboard

> Added Phase 14 (2026-04-07): dashboard now reads stored calibration profile from intelligence JSON.

**Prerequisites:** Completed scan run with a non-default score profile (e.g., `--score-profile strict`).

**Steps:**
1. Run: `quirk --config config.yaml --score-profile strict`
2. Note score from `output/scorecard-*.md`
3. Start dashboard: `quirk serve`
4. Open `http://127.0.0.1:8512` and view the score gauge on the Executive Summary page

**Expected:** Dashboard score matches the CLI scorecard score exactly, not a recalculated balanced-profile score.

**Pass Criteria:**
- Dashboard score gauge value equals score in `scorecard-*.md`
- Running the same scan again with `--score-profile balanced` and refreshing the dashboard shows a *different* score
- Dashboard score does not silently default to balanced when strict or lenient was used

---

### UAT-8-08: validate.py — Clean Output Directory Validation

> Added Phase 14 (2026-04-07): validate_run signature simplified — dead require_delta_if_baseline parameter removed.

**Prerequisites:** Completed scan with all expected output files present.

**Steps:**
1. Run: `python3 -c "from quirk.validate import validate_run; from pathlib import Path; r = validate_run(Path('output')); print(r)"`
2. Run: `quirk --help` and confirm no `--no-require-delta` flag appears

**Expected:** `validate_run` accepts only `output_dir` with no extra parameters. CLI has no dead delta flag.

**Pass Criteria:**
- `validate_run(Path('output'))` returns a `ValidationResult` without error
- `quirk --help` output contains no `--no-require-delta` or `--require-delta` flags
- Passing a second positional argument to `validate_run` raises `TypeError` (no dead parameter to silently absorb it)

---

---

# Series 9: Report Generation & Validation

---

### UAT-9-01: All Output Files Generated

**Prerequisites:** Completed scan.

**Steps:**
1. `ls output/ | sort`

**Expected:** All 9 output artifact types present for the latest scan.

**Pass Criteria:**
- `findings-{stamp}.json` ✓
- `executive-summary-{stamp}.md` ✓
- `technical-findings-{stamp}.md` ✓
- `scorecard-{stamp}.md` ✓
- `roadmap-{stamp}.md` ✓
- `intelligence-{stamp}.json` ✓
- `cbom-{stamp}.json` ✓
- `cbom-{stamp}.xml` ✓
- `run-stats-{stamp}.json` ✓
- `quirk.db` ✓

---

### UAT-9-02: Executive Summary — Structure

**Prerequisites:** Completed scan.

**Steps:**
1. `cat output/executive-summary-*.md`

**Expected:** Professional executive summary with score, risk overview, and top issues.

**Pass Criteria:**
- Starts with score summary
- Contains a risk overview section
- Lists top 3–5 findings
- Contains recommended next steps
- Does not contain raw JSON or technical jargon

---

### UAT-9-03: Technical Findings — Per-Endpoint Detail

**Prerequisites:** Completed scan.

**Steps:**
1. `cat output/technical-findings-*.md`

**Expected:** Technical details per endpoint including cipher suites, cert data, and algorithm details.

**Pass Criteria:**
- Each finding has host:port label
- Cipher suite details present for TLS findings
- Certificate expiry dates present for cert findings
- Algorithm quantum assessment present

---

### UAT-9-04: Run Stats — Timing Data

**Prerequisites:** Completed scan.

**Steps:**
1. `python3 -c "import json; d=json.load(open('output/run-stats-TIMESTAMP.json')); print(json.dumps(d, indent=2))"`

**Expected:** Timing breakdown per scan phase.

**Pass Criteria:**
- `discovery_duration_ms` present
- `tls_scan_duration_ms` present
- `ssh_scan_duration_ms` present
- `total_duration_ms` present
- `endpoint_count` matches actual scanned endpoints
- `profile` field matches used profile

---

### UAT-9-05: HTML Report Generation (Phase 7 Feature)

**Prerequisites:** QU.I.R.K. 4.1.0 with HTML report feature. Completed scan.

**Steps:**
1. Run scan: `quirk --config config.yaml`
2. Check output for HTML file: `ls output/*.html`
3. Open in browser

**Expected:** Standalone HTML report generated alongside existing markdown reports.

**Pass Criteria:**
- `report-{stamp}.html` file exists in output directory
- File opens in browser without JavaScript errors
- Contains score, findings table, and certificate inventory
- Fully self-contained (no external CDN dependencies)

---

### UAT-9-06: HTML Report — Visual Quality

**Prerequisites:** Completed scan with multiple finding types.

**Steps:**
1. Open `output/report-*.html` in Chrome or Firefox
2. Check dark-mode background renders
3. Verify score card section at the top
4. Scroll to Executive Summary section
5. Scroll to Technical Appendix / Findings section
6. Check for broken CSS (unstyled elements, missing fonts, layout breaks)
7. Resize browser to mobile width and check responsiveness

**Expected:** Professional, dark-themed HTML report with clean layout and all sections populated.

**Pass Criteria:**
- Dark-mode background (Zinc palette) renders correctly
- Score card with numeric score and label visible at top
- Executive Summary section with key metrics
- Technical Appendix with per-endpoint findings
- No broken images, missing fonts, or unstyled raw HTML elements
- No horizontal scroll overflow
- Print to PDF from browser produces clean output

---

### UAT-9-07: CBOM JSON — Cross-Scanner Algorithm Coverage

**Prerequisites:** Completed scan that exercised TLS, SSH, and JWT scanners (core + jwt + ssh-weak profiles).

**Steps:**
1. Open `output/cbom-*.json`
2. Parse and extract all component algorithm names:
   ```bash
   python3 -c "
   import json
   cbom = json.load(open('output/cbom-TIMESTAMP.json'))
   components = cbom.get('components', [])
   for c in components:
       print(c.get('name', 'unnamed'), '-', c.get('type', 'unknown'))
   "
   ```
3. Verify algorithms from each scanner type are present

**Expected:** CBOM contains algorithms discovered by all active scanners.

**Pass Criteria:**
- TLS algorithms present (e.g., AES-256-GCM, ECDHE, RSA from cipher suites)
- SSH algorithms present (e.g., diffie-hellman-group14-sha256, ssh-ed25519, hmac-sha2-256)
- JWT algorithms present (e.g., RS256, HS256) when JWT scanner was active
- Each component has `quantum-safety` classification
- Total component count ≥ 10 for a full lab scan
- No duplicate components (same algorithm not listed twice)

---

### UAT-9-08: CBOM XML — Schema Validation

**Prerequisites:** Completed scan producing CBOM XML output.

**Steps:**
1. Locate CBOM XML: `ls output/cbom-*.xml`
2. Validate XML is well-formed:
   ```bash
   python3 -c "import xml.etree.ElementTree as ET; ET.parse('output/cbom-TIMESTAMP.xml'); print('XML well-formed')"
   ```
3. Validate against CycloneDX schema (if `xmllint` available):
   ```bash
   xmllint --noout output/cbom-TIMESTAMP.xml && echo "Valid XML"
   ```
4. Check root element is a CycloneDX BOM

**Expected:** CBOM XML is well-formed and follows CycloneDX structure.

**Pass Criteria:**
- XML parses without errors
- Root element is `<bom>` with CycloneDX namespace
- `<components>` section contains algorithm entries
- Each component has `<name>`, `<type>` attributes
- File size > 1KB (not empty or stub)

---

---

# Series 10: Edge Cases & Error Handling

---

### UAT-10-01: No Reachable Targets — Graceful Handling

**Prerequisites:** Lab stopped (`docker compose down`).

**Steps:**
1. Create config with unreachable targets:
   ```yaml
   targets:
     - host: 127.0.0.1
       ports: [443, 8443, 8000]
   ```
2. Run: `quirk --config config.yaml`

**Expected:** Scan completes with all endpoints marked as errors; does not crash.

**Pass Criteria:**
- Scan completes (exit code 0)
- All findings show `scan_error` set
- Scorecard still generated (low confidence score)
- No uncaught Python exception traceback

---

### UAT-10-02: Config File Not Found — Helpful Error

**Steps:**
1. Run: `quirk --config /nonexistent/path/config.yaml`

**Expected:** Clear error message pointing to the bad path.

**Pass Criteria:**
- Error message names the missing file path
- Exit code is non-zero
- No Python traceback exposed to user

---

### UAT-10-03: Invalid Config YAML — Parse Error

**Steps:**
1. Create `bad.yaml`:
   ```
   targets: [unclosed bracket
   this: is: not: valid: yaml:
   ```
2. Run: `quirk --config bad.yaml`

**Expected:** Clear YAML parse error, not a cryptic crash.

**Pass Criteria:**
- Error message mentions YAML or config parsing issue
- Line number of error indicated if possible
- Exit code non-zero

---

### UAT-10-04: Mixed Reachable/Unreachable Targets

**Prerequisites:** Lab running core services.

**Steps:**
1. Create config with mix of live and dead ports:
   ```yaml
   targets:
     - host: 127.0.0.1
       ports: [443, 9999, 8000, 1234]
   ```
2. Run scan

**Expected:** Reachable ports scanned normally; unreachable ports recorded as errors; scan completes.

**Pass Criteria:**
- Port 443 and 8000 have findings
- Port 9999 and 1234 show as CLOSED or scan_error
- Scan does not hang or crash
- Run stats reflect actual reachable vs. error count

---

### UAT-10-05: Rate Limiting — Token Bucket

**Prerequisites:** Lab running.

**Steps:**
1. Run: `quirk --config config.yaml --rate-limit 1.0` (1 target/second)
2. Observe scan pacing

**Expected:** Scan paces itself to ~1 target/second.

**Pass Criteria:**
- Scan takes noticeably longer than without rate limiting
- All targets still scanned
- No errors caused by rate limiting itself
- `run-stats` shows longer duration

---

### UAT-10-06: Concurrent Scan Safety — No Race Conditions

**Prerequisites:** Lab running. Multiple ports configured.

**Steps:**
1. Create config with 20+ targets
2. Run scan without `--safe-mode`
3. Review output for consistency

**Expected:** Concurrent scanning produces consistent results without duplicate or missing entries.

**Pass Criteria:**
- Number of findings in JSON matches number of scanned endpoints (no duplicates)
- No Python `RuntimeError` or threading errors in output
- SQLite database is not corrupted: `sqlite3 output/quirk.db "PRAGMA integrity_check"`

---

### UAT-10-07: Database Persistence — Multiple Scans

**Prerequisites:** Run two separate scans.

**Steps:**
1. Run first scan
2. Run second scan (same targets)
3. Open database: `sqlite3 output/quirk.db "SELECT COUNT(*) FROM crypto_endpoints"`

**Expected:** Both scans are persisted with timestamps.

**Pass Criteria:**
- Row count is 2× single scan (both scans stored)
- Timestamps differ between runs
- `scanned_at` field distinguishes runs

---

### UAT-10-08: Dashboard — No Scan Data State

**Prerequisites:** Empty or absent `output/quirk.db`.

**Steps:**
1. Move database: `mv output/quirk.db /tmp/`
2. Start dashboard: `quirk serve --no-open`
3. Navigate to `http://127.0.0.1:8512`

**Expected:** Dashboard shows empty state message, not a crash.

**Pass Criteria:**
- Dashboard loads (not 500 error)
- Empty state message displayed (e.g., "No scan data yet — run `quirk` to begin")
- No JavaScript runtime errors in console

---

### UAT-10-09: SSH Scan Without ssh-audit Installed

**Prerequisites:** `ssh-audit` not installed (test in clean environment).

**Steps:**
1. Temporarily rename ssh-audit: `sudo mv $(which ssh-audit) /tmp/ssh-audit-bak`
2. Run scan against port 2222
3. Check findings

**Expected:** SSH scan gracefully falls back to banner-grab mode.

**Pass Criteria:**
- No crash or unhandled exception
- SSH finding still generated with banner information
- Warning logged indicating ssh-audit fallback
- Restore: `sudo mv /tmp/ssh-audit-bak $(dirname $(which python))/ssh-audit`

---

### UAT-10-10: sslyze Not Installed — Graceful Degradation

**Prerequisites:** sslyze not installed.

**Steps:**
1. Run deep TLS scan against port 443: `quirk --config config.yaml --profile deep`
2. Check findings for cipher suite detail

**Expected:** TLS scan completes using built-in ssl module; sslyze cipher enumeration skipped gracefully.

**Pass Criteria:**
- No crash
- Warning logged about sslyze unavailability
- Basic TLS data (version, cert) still captured
- `tls_enum_mode` reflected as `fast` or `off` in run-stats

---

---

# Series 11: Full End-to-End Workflow

---

### UAT-11-01: Complete Workflow — Lab to Dashboard

**Steps:**
1. Start lab: `cd quantum-chaos-enterprise-lab && docker compose up -d && sleep 10`
2. Initialize config: `quirk init`
3. Edit `config.yaml` to point at all core lab ports
4. Run scan: `quirk --config config.yaml --profile standard --progress`
5. Start dashboard: `quirk serve --no-open`
6. Open browser: `http://127.0.0.1:8512`
7. Navigate through all dashboard pages
8. Export PDF

**Expected:** End-to-end workflow completes successfully.

**Pass Criteria:**
- Scan completes without errors
- All 9 output files generated
- Dashboard loads and shows scan data
- All 5 pages render correctly (Executive, Findings, Certificates, CBOM, Roadmap)
- PDF export succeeds
- Score reflects lab environment (should be POOR or FAIR given all the intentional vulnerabilities)

---

### UAT-11-02: Multi-Profile Lab Run — Progressive Discovery

**Steps:**
1. Run base scan (core only)
2. Add `phaseA` profile: `docker compose --profile phaseA up -d`
3. Run expanded scan
4. Add `jwt` profile: `docker compose --profile jwt up -d`
5. Run JWT scan
6. Compare scores across three runs

**Expected:** Each lab expansion adds new findings and may affect score.

**Pass Criteria:**
- Each successive scan discovers more endpoints
- JWT alg:none finding appears after JWT profile scan
- CBOM grows with each scan (more algorithms discovered)
- Dashboard reflects latest scan on each page refresh

---

### UAT-11-03: CLI to Dashboard Handoff — Report Consistency

**Steps:**
1. Run scan via CLI
2. Note score from `output/scorecard-*.md`
3. Open dashboard
4. Compare CLI score to dashboard score gauge

**Expected:** CLI and dashboard show identical scores.

**Pass Criteria:**
- Score in `scorecard-*.md` matches score in dashboard gauge
- Finding count in `findings-*.json` matches dashboard findings table count
- Certificate count matches across CLI and UI

---

### UAT-11-04: Repeat Scan — Delta Detection

**Steps:**
1. Run scan with lab in normal state
2. Stop the expired-cert service: `docker compose stop tls-expired`
3. Run second scan
4. Compare findings between scans

**Expected:** Second scan no longer includes expired cert finding for port 9443.

**Pass Criteria:**
- Port 9443 shows as CLOSED or absent in second scan
- Score may improve slightly (one less critical finding)
- Run stats show fewer scanned endpoints

---

---

# Series 12: Release Gate — Sign-Off Checklist

This checklist is the formal gating mechanism for QU.I.R.K. v4.0. **All categories must meet their minimum pass threshold** before any backlog or roadmap items may proceed. A category is blocked if any CRITICAL test within it fails.

## Gate Rules

1. **100% pass required** for Series 1 (Installation), Series 11 (E2E), and all tests marked CRITICAL
2. **90% pass required** for Series 3–6 (CLI, Lab, Findings) and Series 8–9 (Scoring, Reports)
3. **85% pass required** for Series 7 (Dashboard UI) and Series 10 (Edge Cases)
4. **SKIP** is acceptable only with documented justification (e.g., `nmap` not installed → UAT-3-07 may SKIP)
5. **FAIL** on any CRITICAL test blocks the gate regardless of overall pass rate

## Sign-Off Table

| Series | Category | Total Tests | Pass | Fail | Skip | Pass Rate | Gate Met? | Tester |
|--------|----------|-------------|------|------|------|-----------|-----------|--------|
| 1 | Installation & Setup | 6 | | | | | ☐ | |
| 2 | CLI — Interactive Mode | 4 | | | | | ☐ | |
| 3 | CLI — Config-File Mode | 10 | | | | | ☐ | |
| 4 | Lab — Core Services | 11 | | | | | ☐ | |
| 5 | Lab — Extended Profiles | 19 | | | | | ☐ | |
| 6 | Cryptographic Findings | 13 | | | | | ☐ | |
| 7 | Web Dashboard UI | 32 | | | | | ☐ | |
| 8 | Scoring & Intelligence | 6 | | | | | ☐ | |
| 9 | Report Generation | 8 | | | | | ☐ | |
| 10 | Edge Cases & Errors | 10 | | | | | ☐ | |
| 11 | End-to-End Workflow | 4 | | | | | ☐ | |
| **TOTAL** | | **123** | | | | | | |

## Critical Tests (Must Pass — No Exceptions)

These tests validate core functionality. Any failure here blocks the release gate.

| ID | Test Name | Series | Rationale |
|----|-----------|--------|-----------|
| UAT-1-01 | Package Installation | 1 | Cannot proceed if install fails |
| UAT-1-02 | Version Flag | 1 | Basic CLI health |
| UAT-1-05 | Dashboard Server Startup | 1 | Dashboard must start |
| UAT-3-01 | Scan with Config File | 3 | Core scanning workflow |
| UAT-4-01 | Lab Health Check — All Core Services | 4 | Lab must be operational |
| UAT-4-11 | Full Core Lab Scan | 4 | End-to-end core scan |
| UAT-5-10 | Full JWT Lab Scan | 5 | JWT scanner validation |
| UAT-5-12 | Weak SSH Scan | 5 | SSH scanner validation |
| UAT-6-01 | Findings Output — JSON Structure | 6 | Output format correctness |
| UAT-6-11 | CBOM JSON Structure | 6 | CBOM deliverable correctness |
| UAT-7-01 | Dashboard Loads | 7 | Dashboard must render |
| UAT-7-03 | Executive Page — Score Gauge | 7 | Core dashboard feature |
| UAT-7-06 | Findings Page — Table Renders | 7 | Core dashboard feature |
| UAT-7-17 | PDF Export — Generate Report | 7 | Consulting deliverable |
| UAT-9-01 | All Output Files Generated | 9 | Complete output artifact set |
| UAT-11-01 | Complete Workflow — Lab to Dashboard | 11 | Full E2E validation |
| UAT-11-03 | CLI to Dashboard Handoff | 11 | Score consistency |

## Final Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | | | |
| Reviewer | | | |
| Approver | | | |

**Gate Decision:** ☐ PASS — All categories meet thresholds, all critical tests pass
**Gate Decision:** ☐ FAIL — Blocked items listed below with remediation plan

**Blocking Issues (if FAIL):**

| ID | Test | Issue Description | Remediation | Owner | Target Date |
|----|------|-------------------|-------------|-------|-------------|
| | | | | | |

---

---

# Appendix A: Quick Reference — Lab Port Map

| Port | Service | Profile | What to Verify |
|------|---------|---------|----------------|
| 443 | tls-modern | core | TLS 1.3, modern cipher |
| 8443 | tls-legacy | core | Legacy TLS 1.2, weaker ciphers |
| 9443 | tls-expired | core | Expired certificate |
| 10443 | tls-selfsigned | core | Self-signed cert |
| 11443 | tls-mtls | core | mTLS required |
| 12443 | tls-slow | core | Timeout behavior |
| 8444 | http-on-tls-port | core | Protocol mismatch |
| 8000 | http-plain | core | Plaintext HTTP |
| 2222 | ssh | core | SSH algorithms |
| 5555 | unknown | core | Unknown classification |
| 13443 | tls-missing-chain | phaseA | Incomplete cert chain |
| 14443 | tls-rsa1024 | phaseA | Weak RSA key |
| 15443 | tls-sha1 | phaseA | SHA-1 signature |
| 20001 | jwt-rs256 | jwt | Good JWT (RS256) |
| 20002 | jwt-hs256 | jwt | Weak JWT (symmetric) |
| 20003 | jwt-rsa1024 | jwt | Weak JWT (1024-bit RSA) |
| 20004 | jwt-algnone | jwt | Critical (no signature) |
| 20022 | ssh-weak | ssh-weak | All weak SSH algorithms |
| 20005 | registry | registry | Container crypto libs |
| 20006 | gitea | source | Source code crypto patterns |
| 20007 | kms-localstack | storage | KMS key crypto specs |
| 20009 | vault | storage | Vault transit key specs |
| 15449 | keycloak-tls | identity | IdP TLS quality |
| 636 | ldaps | ldaps | LDAP over TLS |

---

# Appendix B: Expected Score Ranges by Lab Config

| Lab Config | Expected Score | Rationale |
|------------|---------------|-----------|
| Core only, no HTTP | 45–60 (FAIR) | Expired cert, self-signed, legacy TLS |
| Core with HTTP services | 25–40 (POOR) | Plaintext HTTP penalty applied |
| Core + phaseA (RSA-1024, SHA-1) | 15–35 (POOR) | Additional weak key/sig findings |
| JWT profile (alg:none) | 10–25 (POOR) | Critical JWT findings, high-impact ratio |
| JWT profile with RS256 only | 40–55 (FAIR) | Mixed signals |
| Clean TLS only (443 modern only) | 75–90 (GOOD/EXCELLENT) | No significant issues |

---

# Appendix C: Common Failure Patterns

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Dashboard shows blank page | No scan data in `quirk.db` | Run a scan first |
| Score is 0 | All endpoints errored | Check lab is running, ports reachable |
| CBOM has no components | TLS scanner returned no data | Verify TLS ports are accessible |
| PDF export hangs | Playwright Chromium not installed | `playwright install chromium` |
| SSH findings missing | ssh-audit not in PATH | `pip install ssh-audit` |
| JWT findings missing | JWKS endpoint not reachable | Check jwt profile containers are up |
| Source scan empty | semgrep not installed | `pip install semgrep` |
| Container scan empty | syft not installed or no images | Install syft, ensure registry profile is up |
| Kerberos/SAML/DNSSEC scan empty | identity extras not installed | `pip install quirk[identity]` |
| enable_kerberos: unknown field error | Old quirk installation (pre-v4.2) | Upgrade quirk to v4.2+ |
