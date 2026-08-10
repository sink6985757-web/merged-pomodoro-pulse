#!/usr/bin/env python3
"""Verify the 128-unit onboarding plan and ten-year maintenance state."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pomodoro_chat_original as core


TZ = timezone(timedelta(hours=8))
previous_state = os.environ.get("POMODORO_VOCAB_STATE")

try:
    with tempfile.TemporaryDirectory(prefix="pomodoro-ten-year-test-") as temp_dir:
        state_path = Path(temp_dir) / "pomodoro_vocab_state.json"
        os.environ["POMODORO_VOCAB_STATE"] = str(state_path)
        start = datetime(2026, 8, 10, 6, tzinfo=TZ)
        learned = []
        for offset in range(60):
            day = start + timedelta(days=offset)
            target = 3 if (offset + 1) % 7 == 0 else 2
            anchors = core.NEW_UNIT_ANCHORS[target]
            daily = [
                core.choose_vocab_entry(day.replace(hour=hour), consume=True)
                for hour in anchors
            ]
            assert all(card and card["_review_stage"] == "new_anchor" for card in daily)
            learned.extend(card for card in daily if card)

        assert len(learned) == 128
        assert len({card["id"] for card in learned}) == 128
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["version"] == 5
        assert len(state["cycle_seen_ids"]) == 128
        assert len(state["review_queue"]) == 128 * len(core.REVIEW_DELAYS)
        assert {item["stage"] for item in state["review_queue"]} == set(core.REVIEW_DELAYS)

        day_61 = start + timedelta(days=60)
        review = core.choose_vocab_entry(day_61.replace(hour=6), consume=True)
        assert review and review["_review_stage"] != "new_anchor"
        retry = core.choose_vocab_entry(day_61.replace(hour=6), consume=True)
        assert retry and retry["id"] == review["id"]
        assert retry["_review_stage"] == review["_review_stage"]

        maintenance_state = core.default_vocab_state(start)
        job = {
            "first_learned_at": start.isoformat(timespec="seconds"),
            "created_at": start.isoformat(timespec="seconds"),
        }
        core.schedule_maintenance_review(maintenance_state, job, learned[0], start + timedelta(days=365))
        annual = maintenance_state["review_queue"][0]
        assert annual["stage"] == "annual"
        annual_due = core.parse_state_datetime(annual["due_at"])
        assert annual_due and annual_due.date() == (start + timedelta(days=730)).date()

        first_line = core.format_vocab_line(learned[0])
        assert "｜課：" in first_line and "｜章：" in first_line and "｜單元：" in first_line
        assert "｜節點：首次·核心 1" in first_line
        assert "｜族：" in first_line and "｜答：" in first_line

    with tempfile.TemporaryDirectory(prefix="pomodoro-state-v4-test-") as temp_dir:
        state_path = Path(temp_dir) / "pomodoro_vocab_state.json"
        os.environ["POMODORO_VOCAB_STATE"] = str(state_path)
        entries = core.load_english_hourly_cards()
        preserved_id = entries[0]["id"]
        historical_id = entries[1]["id"]
        migration_now = datetime.now(TZ).replace(microsecond=0)
        old_state = {
            "version": 4,
            "cycle": 1,
            "cycle_started_at": "2026-08-01T06:00:00+08:00",
            "cycle_seen_ids": [preserved_id],
            "history": [{
                "id": historical_id,
                "word": entries[1]["word"],
                "broadcasted_at": migration_now.isoformat(timespec="seconds"),
                "review_stage": "new",
            }],
            "slot_reservations": {},
            "daily_casts": {},
            "review_queue": [
                {"entry_id": preserved_id, "stage": "short", "due_at": "2026-08-01T09:00:00+08:00"},
                {"entry_id": preserved_id, "stage": "next_day", "due_at": "2026-08-02T06:00:00+08:00"},
            ],
        }
        state_path.write_text(json.dumps(old_state, ensure_ascii=False), encoding="utf-8")
        migrated = core.load_vocab_state(entries)
        assert migrated["learning_plan_started_at"] == old_state["cycle_started_at"]
        assert migrated["cycle_seen_ids"] == [preserved_id, historical_id]
        assert [item["stage"] for item in migrated["review_queue"][:2]] == ["same_day", "day_1"]
        assert {item["stage"] for item in migrated["review_queue"] if item["entry_id"] == historical_id} == set(core.REVIEW_DELAYS)
        core.save_vocab_state(migrated)
        assert json.loads(state_path.read_text(encoding="utf-8"))["version"] == 5
finally:
    if previous_state is None:
        os.environ.pop("POMODORO_VOCAB_STATE", None)
    else:
        os.environ["POMODORO_VOCAB_STATE"] = previous_state

print("PASS ten_year_learning units=128 intake_days=60 nodes=11 annual=365 v4_migration=1")
