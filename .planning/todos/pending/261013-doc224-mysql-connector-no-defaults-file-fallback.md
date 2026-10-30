---
type: todo
created: 2026-10-13
source: Phase 224 GC2 re-audit (R05 chunk F); ledger row DCL-REPORTINT-1062 (report-interpretation.md §22, Phase 193 credentials paragraph)
priority: low
area: quirk/scanner/db_connector.py (MySQL branch)
status: pending
resolves_phase: null
owner: "999.126"
---

# MySQL connector claims a defaults-file fallback that pymysql never performs

`docs/report-interpretation.md` §22 said that a database connector run without configured credentials lets the client
library read its own defaults, "the defaults file for MySQL". The code comment says the same
(`quirk/scanner/db_connector.py:228` "lets pymysql read from defaults file / env" and `:239`
"pymysql will read from defaults file / env if configured"). It does not:

- `quirk/scanner/db_connector.py:231-237` builds `my_kwargs` with host, port, `user=user or "root"`,
  `connect_timeout`, `ssl_disabled=True`, and no `read_default_file` / `read_default_group`.
- pymysql 2.2.8 (`.venv`) `Connection.__init__` has `read_default_file=None`, and only reads a `my.cnf` when
  `read_default_file` or `read_default_group` is passed (`pymysql/connections.py:238-249`). It reads no password
  environment variable.

So a MySQL target with no configured password gets a password-less login attempt as the configured user or `root`,
and an operator's `~/.my.cnf` is ignored. The PostgreSQL branch is fine (libpq reads `.pgpass` / `PGPASSWORD`).
The doc now states the real behaviour.

- [ ] Either pass `read_default_file="~/.my.cnf"` (expanded) when no password is configured, or correct the two
      comments to say no fallback exists.
- [ ] If the fallback is added, restore the doc sentence and add a test that the kwarg is passed.

## Feasibility & Effort

- **CONFIRMED**: `inspect.signature(pymysql.connections.Connection.__init__)` -> `read_default_file` default `None`;
  `pymysql/connections.py:244` `if read_default_file:` gates the cnf read; `db_connector.py:238-239` passes nothing.
- Effort **S** (one kwarg, or two comment lines). Unknowns: whether reading `~/.my.cnf` silently is desirable for a
  scanner (it could pick up an operator's personal credentials); that is a product decision, not a spike.
