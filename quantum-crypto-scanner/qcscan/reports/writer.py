import json
import os
from datetime import datetime

from qcscan.reports.executive import build_exec_markdown
from qcscan.reports.technical import build_tech_markdown
from qcscan.engine.migration_planner import categorize_waves


def write_reports(cfg, endpoints, findings):
    outdir = cfg.output.directory
    os.makedirs(outdir, exist_ok=True)

    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    # ==============================
    # JSON EXPORT
    # ==============================
    json_path = os.path.join(outdir, f"findings-{stamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)

    # ==============================
    # EXECUTIVE REPORT
    # ==============================
    exec_md = build_exec_markdown(cfg, endpoints, findings)
    exec_path = os.path.join(outdir, f"executive-summary-{stamp}.md")
    with open(exec_path, "w", encoding="utf-8") as f:
        f.write(exec_md)

    # ==============================
    # TECHNICAL REPORT
    # ==============================
    tech_md = build_tech_markdown(cfg, endpoints, findings)
    tech_path = os.path.join(outdir, f"technical-findings-{stamp}.md")
    with open(tech_path, "w", encoding="utf-8") as f:
        f.write(tech_md)

    # ==============================
    # MIGRATION WAVE SUMMARY
    # ==============================
    waves = categorize_waves(findings)

    print("\n📊 Migration Waves:")
    for wave, items in waves.items():
        print(f"  {wave}: {len(items)} findings")

    print("\n✅ Wrote reports:")
    print(f"- {json_path}")
    print(f"- {exec_path}")
    print(f"- {tech_path}")
