import json
import os
from datetime import datetime

from qcscan.reports.executive import build_exec_markdown
from qcscan.reports.technical import build_tech_markdown
from qcscan.engine.migration_planner import categorize_waves

from qcscan.assessment.readiness_score import compute_readiness_score
from qcscan.assessment.transition_planner import build_transition_roadmap
from qcscan.assessment.migration_advisor import recommend_migration_paths
from qcscan.assessment.operator_context import get_context


def write_reports(cfg, endpoints, findings):
    outdir = cfg.output.directory
    os.makedirs(outdir, exist_ok=True)

    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    json_path = os.path.join(outdir, f"findings-{stamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)

    assessment = {
        "context": get_context(cfg),
        "readiness_score": compute_readiness_score(cfg, endpoints, findings).to_dict(),
        "transition_roadmap": build_transition_roadmap(cfg, endpoints, findings).to_dict(),
        "migration_paths": recommend_migration_paths(findings),
        "migration_waves": categorize_waves(findings),
        "notes": "v3.6 includes TLS capability enumeration persisted to DB on TLS-success endpoints.",
    }
    assess_path = os.path.join(outdir, f"assessment-{stamp}.json")
    with open(assess_path, "w", encoding="utf-8") as f:
        json.dump(assessment, f, indent=2)

    exec_md = build_exec_markdown(cfg, endpoints, findings)
    exec_path = os.path.join(outdir, f"executive-summary-{stamp}.md")
    with open(exec_path, "w", encoding="utf-8") as f:
        f.write(exec_md)

    tech_md = build_tech_markdown(cfg, endpoints, findings)
    tech_path = os.path.join(outdir, f"technical-findings-{stamp}.md")
    with open(tech_path, "w", encoding="utf-8") as f:
        f.write(tech_md)

    waves = categorize_waves(findings)
    print("\n📊 Migration Waves:")
    for wave, items in waves.items():
        print(f"  {wave}: {len(items)} findings")

    rs = assessment["readiness_score"]
    print(f"\n🔐 Quantum Readiness Score: {rs.get('score')}/100 ({rs.get('rating')})")

    print("\n✅ Wrote reports:")
    print(f"- {json_path}")
    print(f"- {assess_path}")
    print(f"- {exec_path}")
    print(f"- {tech_path}")
