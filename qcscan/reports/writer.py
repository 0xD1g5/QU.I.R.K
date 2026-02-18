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
from qcscan.assessment.confidence import compute_confidence


def write_reports(cfg, endpoints, findings, run_stats=None):
    outdir = cfg.output.directory
    os.makedirs(outdir, exist_ok=True)

    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    json_path = os.path.join(outdir, f"findings-{stamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)

    confidence = compute_confidence(cfg, endpoints)

    assessment = {
        "context": get_context(cfg),
        "confidence": confidence,
        "readiness_score": compute_readiness_score(cfg, endpoints, findings).to_dict(),
        "transition_roadmap": build_transition_roadmap(cfg, endpoints, findings).to_dict(),
        "migration_paths": recommend_migration_paths(findings),
        "migration_waves": categorize_waves(findings),
        "run_stats": run_stats or {},
        "notes": "v3.7 adds profiles, caching/resume, phase tuning, confidence engine, and run telemetry.",
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

    # run stats file
    if run_stats:
        stats_path = os.path.join(outdir, f"run-stats-{stamp}.json")
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(run_stats, f, indent=2)
    else:
        stats_path = None

    waves = categorize_waves(findings)
    print("\n📊 Migration Waves:")
    for wave, items in waves.items():
        print(f"  {wave}: {len(items)} findings")

    rs = assessment["readiness_score"]
    print(f"\n🔐 Quantum Readiness Score: {rs.get('score')}/100 ({rs.get('rating')})")
    print(f"🧪 Confidence: {confidence.get('confidence_rating')} ({confidence.get('confidence_score')}/100)")

    print("\n✅ Wrote reports:")
    print(f"- {json_path}")
    print(f"- {assess_path}")
    if stats_path:
        print(f"- {stats_path}")
    print(f"- {exec_path}")
    print(f"- {tech_path}")
