from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


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
    # Phase 72 D-18 / WR-15: corrupt cache file (malformed JSON or invalid
    # UTF-8) returns None instead of raising — caller treats as cache miss.
    # File is intentionally left on disk for forensics (do NOT delete).
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Cache file %s corrupt — ignoring: %s", path, e)
        return None


def scope_hash(cfg, discovery_mode: str, nmap_extra_args: str = "", ports: Optional[List[int]] = None) -> str:
    t = cfg.targets
    scan = cfg.scan

    # Phase 72 D-19 / WR-16: include connector enable flags in the cache
    # scope hash so toggling enable_email / enable_broker / etc. invalidates
    # the cache. The `_user_set_fields` sidecar (added by D-02 in PLAN 05) is
    # a `frozenset` and not JSON-serializable, so drop it defensively — this
    # is a no-op if D-02 has not landed yet.
    connectors_dict: Dict[str, Any] = {}
    if getattr(cfg, "connectors", None) is not None and dataclasses.is_dataclass(cfg.connectors):
        connectors_dict = dataclasses.asdict(cfg.connectors)
        connectors_dict.pop("_user_set_fields", None)

    parts = {
        "discovery_mode": discovery_mode,
        "fqdns": sorted(t.fqdns or []),
        "cidrs": sorted(t.cidrs or []),
        "include_ips": sorted(t.include_ips or []),
        "exclude_ips": sorted(t.exclude_ips or []),
        "ports": sorted(ports if ports is not None else (scan.ports_tls or [])),
        "include_sni": bool(scan.include_sni),
        "nmap_extra_args": (nmap_extra_args or "").strip(),
        "connectors": connectors_dict,
    }
    raw = json.dumps(parts, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def load_cache(output_dir: str, key: str, ttl_hours: int) -> Optional[Dict[str, Any]]:
    cdir = cache_dir(output_dir)
    path = os.path.join(cdir, f"{key}.json")
    if not os.path.exists(path):
        return None

    obj = _read_json(path)
    if obj is None:
        # Phase 72 D-18: corrupt cache file → treat as cache miss.
        return None
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
