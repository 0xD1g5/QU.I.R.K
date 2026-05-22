"""Phase 89 Wave-0 doc-completeness test.

Asserts that ``expected_results_v4.md`` contains a ``## Profile: <name>``
section for each of the three new Phase-89 profiles (postgres-tls, redis-tls,
kafka-tls) AND that each section body mentions the profile's published host port.

Also asserts that ``quantum-chaos-enterprise-lab/README.md`` Profile Summary
table contains a row for each of the three profile names.

Pure file-parse — no Docker daemon, no network required. Runs in the default
(non-slow) pytest suite.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_RESULTS = (
    REPO_ROOT / "quantum-chaos-enterprise-lab" / "expected_results_v4.md"
)
README = REPO_ROOT / "quantum-chaos-enterprise-lab" / "README.md"

# (profile_name, host_port_substring)
PROFILES = [
    ("postgres-tls", "39432"),
    ("redis-tls", "39380"),
    ("kafka-tls", "39093"),
]


def _read_lines(path: Path) -> list:
    return path.read_text(encoding="utf-8").splitlines()


def _section_body(lines: list, header: str) -> list:
    """Return lines after *header* up to (not including) the next ## heading."""
    collecting = False
    body: list = []
    for line in lines:
        if line.strip() == header:
            collecting = True
            continue
        if collecting:
            if line.startswith("## ") and line.strip() != header:
                break
            body.append(line)
    return body


class TestExpectedResultsSections:
    """expected_results_v4.md must have a section for each new profile."""

    def test_postgres_tls_section_exists(self):
        lines = _read_lines(EXPECTED_RESULTS)
        headers = [l.strip() for l in lines if l.startswith("## Profile:")]
        assert "## Profile: postgres-tls" in headers, (
            "expected_results_v4.md is missing '## Profile: postgres-tls'"
        )

    def test_redis_tls_section_exists(self):
        lines = _read_lines(EXPECTED_RESULTS)
        headers = [l.strip() for l in lines if l.startswith("## Profile:")]
        assert "## Profile: redis-tls" in headers, (
            "expected_results_v4.md is missing '## Profile: redis-tls'"
        )

    def test_kafka_tls_section_exists(self):
        lines = _read_lines(EXPECTED_RESULTS)
        headers = [l.strip() for l in lines if l.startswith("## Profile:")]
        assert "## Profile: kafka-tls" in headers, (
            "expected_results_v4.md is missing '## Profile: kafka-tls'"
        )

    def test_postgres_tls_section_mentions_port(self):
        lines = _read_lines(EXPECTED_RESULTS)
        body = _section_body(lines, "## Profile: postgres-tls")
        body_text = "\n".join(body)
        assert "39432" in body_text, (
            "'## Profile: postgres-tls' section does not mention host port 39432"
        )

    def test_redis_tls_section_mentions_port(self):
        lines = _read_lines(EXPECTED_RESULTS)
        body = _section_body(lines, "## Profile: redis-tls")
        body_text = "\n".join(body)
        assert "39380" in body_text, (
            "'## Profile: redis-tls' section does not mention host port 39380"
        )

    def test_kafka_tls_section_mentions_port(self):
        lines = _read_lines(EXPECTED_RESULTS)
        body = _section_body(lines, "## Profile: kafka-tls")
        body_text = "\n".join(body)
        assert "39093" in body_text, (
            "'## Profile: kafka-tls' section does not mention host port 39093"
        )


class TestReadmeProfileTable:
    """README.md Profile Summary table must contain a row for each new profile."""

    def test_postgres_tls_in_readme(self):
        lines = _read_lines(README)
        assert any("postgres-tls" in l for l in lines), (
            "README.md Profile Summary table is missing a 'postgres-tls' row"
        )

    def test_redis_tls_in_readme(self):
        lines = _read_lines(README)
        assert any("redis-tls" in l for l in lines), (
            "README.md Profile Summary table is missing a 'redis-tls' row"
        )

    def test_kafka_tls_in_readme(self):
        lines = _read_lines(README)
        assert any("kafka-tls" in l for l in lines), (
            "README.md Profile Summary table is missing a 'kafka-tls' row"
        )
