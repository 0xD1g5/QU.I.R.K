# Recordings

This directory contains asciinema `.cast` recordings for pre-recorded attack phases.

## Recording Spec

- Terminal dimensions: **120 columns × 40 rows**
- Tool: `asciinema rec recordings/phase_N_name.cast`
- Real LLM responses required — do not stage or fake AI output
- Pause points defined in each phase's `atlas_mapping.json` under `pause_after_line`

## Files (produced in Milestone 8)

| File | Phase | Description |
|---|---|---|
| `phase_1_recon.cast` | Phase 1 | Recon & AI Pipeline Enumeration |
| `phase_2_fingerprint.cast` | Phase 2 | Model Behavior Fingerprinting |
| `phase_3_injection.cast` | Phase 3 | Indirect Prompt Injection |
| `phase_4_lateral.cast` | Phase 4 | Multi-Agent Trust Exploitation |
| `phase_5_memory.cast` | Phase 5 | Long-Term Memory Poisoning |

## Notes

- `.cast` files are excluded from git via `.gitignore` (binary / large files)
- Store recordings in a shared drive or artifact storage for distribution
- Playback via asciinema-player embedded in orchestrator RED TEAM tab
