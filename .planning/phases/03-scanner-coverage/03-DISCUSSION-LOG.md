# Phase 3: Scanner Coverage - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-03-29
**Phase:** 03-scanner-coverage
**Mode:** assumptions
**Areas analyzed:** CryptoEndpoint Model Extension, Scanner Integration, JWT/API Scanner, Container Scanner, Source Code Scanner, Cloud Connectors, CBOM Builder Extension

## Assumptions Presented

### CryptoEndpoint Model Extension
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| JSON blob columns per scanner surface (jwt_scan_json, container_scan_json, etc.) | Confident | `quirk/models.py:49,54`, Phase 1 D-05 |
| `protocol` field as CBOM builder discriminator ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE") | Likely | `quirk/cbom/builder.py:274,307` branches only on "SSH" |

### Scanner Integration in run_scan.py
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Each scanner returns List[CryptoEndpoint], merged before write_reports() | Confident | `run_scan.py:315-356` established pattern |
| New enable flags in ConnectorsCfg for jwt/container/source; existing enable_aws/enable_azure for cloud | Confident | `quirk/config.py:44-48` |

### Source Code Scanner (SCAN-05)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| CBOMkit Hyperion not usable (Java SonarQube plugin, not pip-installable) | Confident | External research |
| semgrep with p/cryptography ruleset | Unclear → Corrected | External research + user confirmation |

### Container/Binary Scanner (SCAN-04)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Syft subprocess only (not Trivy), parse artifacts array | Likely | Phase 1 D-04 (subprocess for Go tools); external research confirmed Syft JSON schema |

### Cloud Connectors (SCAN-06/07)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Ambient credential resolution (boto3 chain / DefaultAzureCredential) | Likely | `quirk/config.py:44-48` no credential fields exist |
| ConnectorsCfg needs aws_region + azure_subscription_id | Likely | Stubs have no config hints; ambient credentials alone insufficient |

## Corrections Made

### Source Code Scanner
- **Original assumption:** CBOMkit Hyperion / PQCA integration (per REQUIREMENTS.md SCAN-05)
- **Finding:** CBOMkit Hyperion is a Java SonarQube plugin — requires a running SonarQube server, not pip-installable, breaks offline/air-gapped use case
- **User correction:** semgrep + crypto rules (p/cryptography ruleset)
- **Reason:** Fits consultant offline constraint; pip-installable; ~200 crypto detection rules

## External Research

- **CBOMkit Hyperion availability:** NOT pip-installable. Java SonarQube plugin (Maven/fat JAR). No PyPI package. (Source: medium.com/@chmodshubham, postquantum.com)
- **Syft JSON schema:** `syft <target> -o json` → `artifacts` array with `name`, `version`, `type`, `purl` keys. No dedicated crypto mode — filter by allowlist. Schema stable since v1.0. (Source: oss.anchore.com docs)
- **Azure SDK packages:** `azure-keyvault-certificates`, `azure-keyvault-keys`, `azure-mgmt-network` (App Gateway via NetworkManagementClient), `azure-identity` (DefaultAzureCredential). (Source: PyPI, Microsoft Learn)
