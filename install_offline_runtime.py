#!/usr/bin/env python3
"""Install the zero-token micro-card runtime into a Hermes data directory.

The installer copies only the Python runtime and compact offline datasets. It
does not create a cron job, configure Discord, copy .env files, or call a model.
Existing vocabulary state is preserved. Replaced runtime files are backed up.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNTIME_FILES = {
    "unified_broadcaster.py": "scripts/unified_broadcaster.py",
    "pomodoro_chat_original.py": "scripts/pomodoro_chat_original.py",
    "pomodoro_iching_data.py": "scripts/pomodoro_iching_data.py",
    "lunar_almanac.py": "scripts/lunar_almanac.py",
    "index.html": "scripts/index.html",
    "data/english_hourly_cards.json": "data/english_hourly_cards.json",
    "data/stoic_daily_quotes.json": "data/stoic_daily_quotes.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_target() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise SystemExit("LOCALAPPDATA is unavailable; pass --target explicitly")
    return Path(local_app_data) / "hermes"


def expected_manifest(target: Path) -> list[dict[str, object]]:
    rows = []
    for source_rel, target_rel in RUNTIME_FILES.items():
        source = ROOT / source_rel
        if not source.is_file():
            raise SystemExit(f"missing source file: {source}")
        rows.append(
            {
                "source": source_rel,
                "target": target_rel,
                "bytes": source.stat().st_size,
                "sha256": sha256(source),
                "target_path": str(target / target_rel),
            }
        )
    return rows


def verify(target: Path) -> tuple[bool, list[dict[str, object]]]:
    rows = expected_manifest(target)
    ok = True
    for row in rows:
        deployed = Path(str(row["target_path"]))
        row["present"] = deployed.is_file()
        row["matches"] = deployed.is_file() and sha256(deployed) == row["sha256"]
        ok = ok and bool(row["matches"])
    return ok, rows


def install(target: Path) -> Path | None:
    rows = expected_manifest(target)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = target / "backups" / f"offline-runtime-{stamp}"
    backed_up = False

    for row in rows:
        source = ROOT / str(row["source"])
        deployed = Path(str(row["target_path"]))
        if deployed.is_file() and sha256(deployed) != row["sha256"]:
            backup = backup_root / str(row["target"])
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(deployed, backup)
            backed_up = True
        deployed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, deployed)

    manifest_path = target / "offline_runtime_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "installed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "zero_token": True,
                "scheduler_changed": False,
                "files": [{k: v for k, v in row.items() if k != "target_path"} for row in rows],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return backup_root if backed_up else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the offline zero-token Hermes runtime")
    parser.add_argument("--target", type=Path, help="Hermes root; default: LOCALAPPDATA/hermes")
    parser.add_argument("--check", action="store_true", help="verify only; copy nothing")
    return parser.parse_args()


def main() -> int:
    if sys.version_info < (3, 10):
        print("Python 3.10+ is required; Python 3.11 is recommended.")
        return 2
    args = parse_args()
    target = (args.target or default_target()).expanduser().resolve()
    if args.check:
        ok, rows = verify(target)
        print(json.dumps({"ok": ok, "target": str(target), "files": rows}, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    backup = install(target)
    ok, rows = verify(target)
    print(
        json.dumps(
            {
                "ok": ok,
                "target": str(target),
                "backup": str(backup) if backup else None,
                "scheduler_changed": False,
                "files": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
