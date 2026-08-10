#!/usr/bin/env python3
"""Verify offline content generation and portable Hermes installation."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pomodoro_chat_original as core


def main() -> int:
    previous = os.environ.get("POMODORO_OFFLINE")
    os.environ["POMODORO_OFFLINE"] = "1"
    try:
        with mock.patch.object(core.urllib.request, "urlopen", side_effect=AssertionError("network call")):
            almanac = core.fetch_gooday_almanac(datetime(2026, 8, 10, 9, 0))
            assert almanac["ok"] is True
            assert almanac["source"] == "local:lunar_almanac.py"
            card = core.build_message(datetime(2026, 8, 10, 9, 0), consume_vocab=False)
            assert "｜字｜" in card and "｜時｜" in card and "｜勢｜" in card
    finally:
        if previous is None:
            os.environ.pop("POMODORO_OFFLINE", None)
        else:
            os.environ["POMODORO_OFFLINE"] = previous

    with tempfile.TemporaryDirectory(prefix="pomodoro-offline-test-") as temp_dir:
        target = Path(temp_dir) / "hermes"
        install = subprocess.run(
            [sys.executable, str(ROOT / "install_offline_runtime.py"), "--target", str(target)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        install_result = json.loads(install.stdout)
        assert install_result["ok"] is True
        assert install_result["scheduler_changed"] is False
        assert not (target / ".env").exists()
        assert not (target / "data" / "pomodoro_vocab_state.json").exists()

        check = subprocess.run(
            [sys.executable, str(ROOT / "install_offline_runtime.py"), "--target", str(target), "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        check_result = json.loads(check.stdout)
        assert check_result["ok"] is True
        assert all(row["matches"] for row in check_result["files"])

        runtime_env = os.environ.copy()
        # An explicit portable root must win even when LOCALAPPDATA points
        # somewhere unrelated to the installed runtime.
        runtime_env["LOCALAPPDATA"] = str(Path(temp_dir) / "unrelated-local-app-data")
        runtime_env["POMODORO_DATA_DIR"] = str(target)
        runtime_env.pop("DISCORD_WEBHOOK_URL", None)
        runtime = subprocess.run(
            [
                sys.executable,
                str(target / "scripts" / "unified_broadcaster.py"),
                "--at",
                "09:00",
                "--dry-run",
            ],
            cwd=target / "scripts",
            env=runtime_env,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert "｜字｜" in runtime.stdout
        assert "｜提示：" in runtime.stdout
        assert '"name": "📖 課程字根記憶"' in runtime.stdout
        assert "答：||" in runtime.stdout

    print(f"PASS offline_source={almanac['source']} runtime_files={len(check_result['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
