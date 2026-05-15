from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _now() -> float:
    return time.time()


def cache_dir(output_dir: str) -> str:
    return os.path.join(output_dir, ".cache")


def _write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def scope_hash(cfg, discovery_mode: str, nmap_extra_args: str = "", ports: Optional[List[int]] = None) -> str:
    t = cfg.targets
    scan = cfg.scan

    parts = {
        "discovery_mode": discovery_mode,
        "fqdns": sorted(t.fqdns or []),
        "cidrs": sorted(t.cidrs or []),
        "include_ips": sorted(t.include_ips or []),
        "exclude_ips": sorted(t.exclude_ips or []),
        "ports": sorted(ports if ports is not None else (scan.ports_tls or [])),
        "include_sni": bool(scan.include_sni),
        "nmap_extra_args": (nmap_extra_args or "").strip(),
    }
    raw = json.dumps(parts, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def load_cache(output_dir: str, key: str, ttl_hours: int) -> Optional[Dict[str, Any]]:
    cdir = cache_dir(output_dir)
    path = os.path.join(cdir, f"{key}.json")
    if not os.path.exists(path):
        return None

    obj = _read_json(path)
    ts = obj.get("_cached_at", 0)
    age = _now() - float(ts or 0)
    if ttl_hours <= 0:
        # ttl_hours <= 0 means "cache disabled" — never return cached data
        # (D-10 / BLOCK-05). Previously this branch returned obj, which was
        # the opposite of intended semantics.
        return None
    if age <= ttl_hours * 3600:
        return obj
    return None


def save_cache(output_dir: str, key: str, payload: Dict[str, Any]) -> str:
    cdir = cache_dir(output_dir)
    _ensure_dir(cdir)
    payload = dict(payload)
    payload["_cached_at"] = _now()
    path = os.path.join(cdir, f"{key}.json")
    _write_json(path, payload)
    return path


def targets_to_serial(targets: List[Tuple[str, int]]) -> List[Dict[str, Any]]:
    return [{"host": h, "port": int(p)} for h, p in targets]


def serial_to_targets(serial: List[Dict[str, Any]]) -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    for item in serial or []:
        h = item.get("host")
        p = item.get("port")
        if h and p is not None:
            out.append((str(h), int(p)))
    return out
