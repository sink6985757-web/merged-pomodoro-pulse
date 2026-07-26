#!/usr/bin/env python3
"""Deterministic production-path verification for the life-pomodoro micro-card."""
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).with_name("pomodoro_chat_original.py")
TZ = timezone(timedelta(hours=8))

spec = importlib.util.spec_from_file_location("pomodoro_final", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
real_fetch = mod.fetch_gooday_almanac
mod.fetch_gooday_almanac = lambda dt: {"ok": False}

print("Starting I Ching casts verification...")
# Exhaust all 4,096 production casts and assert final 0–6 moving semantics.
four_count = 0
moving_counts = set()
for values_tuple in itertools.product((6, 7, 8, 9), repeat=6):
    values = list(values_tuple)
    cast = mod.cast_from_values(values)
    count = len(cast["moving"])
    moving_counts.add(count)
    if count == 0:
        expected_text = mod._ICHING.get_judgment(cast["base_no"])
    elif count == 1:
        expected_text = mod._ICHING.get_line_text(cast["base_no"], cast["moving"][0])
    elif count == 2:
        expected_text = mod._ICHING.get_line_text(cast["base_no"], max(cast["moving"]))
    elif count == 3:
        expected_text = mod._ICHING.get_judgment(cast["changed_no"])
    elif count == 4:
        four_count += 1
        changed = [not (value % 2 == 1) if value in {6, 9} else (value % 2 == 1) for value in values]
        expected_lower = mod.TRIGRAM_BY_LINES[tuple(changed[:3])]["name"]
        assert cast["changed_lower"]["name"] == expected_lower
        essence = mod._ICHING.TRIGRAM_ESSENCE[expected_lower]
        hint_parts = [p.strip() for p in essence.replace("——", "——").split("——") if p.strip()]
        inner_hint = hint_parts[-1] if len(hint_parts) >= 2 else (hint_parts[0] if hint_parts else "")
        expected_text = f"{cast['changed_name']}內卦提示：{inner_hint}"
    elif count == 5:
        unchanged = next(index for index in range(6) if index not in cast["moving"])
        expected_text = mod._ICHING.get_line_text(cast["changed_no"], unchanged)
    elif cast["base_no"] == 1:
        expected_text = "群龍無首，吉。用九：見群龍無首，天則也。"
    elif cast["base_no"] == 2:
        expected_text = "利永貞。用六：利永貞，以終也。"
    else:
        expected_text = mod._ICHING.get_judgment(cast["changed_no"])
    expected_hint = mod.compact_iching_text(expected_text)
    output = mod.build_hexagram_next_action(datetime(2026, 7, 14, 9, tzinfo=TZ), cast)
    assert f"｜{expected_hint}" in output, (values, output, expected_hint)
    base_display = f"第{cast['base_no']}卦 {mod.hexagram_symbol(cast['base_no'])} {cast['base_name']}"
    assert f"｜勢｜{base_display}" in output, (values, output)
    assert ord(mod.hexagram_symbol(cast["base_no"])) == 0x4DC0 + cast["base_no"] - 1
    if cast["changed_no"] != cast["base_no"]:
        changed_display = (
            f"→第{cast['changed_no']}卦 "
            f"{mod.hexagram_symbol(cast['changed_no'])} {cast['changed_name']}"
        )
        assert changed_display in output, (values, output)
    else:
        assert "→第" not in output, (values, output)
assert four_count == 960
assert moving_counts == set(range(7))

print("Starting vocabulary pool checks...")
# Vocabulary pool: unique visible words and no forbidden OCR artifacts.
eligible = mod.eligible_vocab_entries(mod.load_vocab_entries())
words = [entry["word"].lower() for entry in eligible]
decomp_index = json.loads(
    (mod.vocab_data_dir() / "vocab_decomposition.json").read_text(encoding="utf-8")
)
assert decomp_index["version"] == 4
assert len(decomp_index["entries"]) == len(decomp_index["provenance"])
assert mod.verified_decomp_entries(decomp_index) == decomp_index["entries"]
assert len(words) == len(set(words))
assert all(not mod.has_cjk(entry["pron"]) for entry in eligible)
assert all(not mod.VOCAB_PRON_FORBIDDEN_RE.search(entry["pron"]) for entry in eligible)
assert all(not mod.VOCAB_DECOMP_FORBIDDEN_RE.search(entry["decomp"]) for entry in eligible if entry.get("decomp"))
assert all(not mod.VOCAB_DECOMP_IPA_RE.search(entry["decomp"]) for entry in eligible if entry.get("decomp"))
assert all(mod.pronunciation_is_usable(entry["pron"]) for entry in eligible)
assert all(mod.decomposition_matches_word(entry["word"], entry["decomp"]) for entry in eligible if entry.get("decomp"))
assert all(mod.decomposition_is_structured(entry["decomp"]) for entry in eligible if entry.get("decomp"))
assert all("+" not in entry["gloss"] for entry in eligible)

print("Starting scheduled hours card generation checks (130 cards)...")
# All 13 scheduled hours: action-first, four lines, Discord-safe size.
cards = []
for hour in range(6, 19):
    for _ in range(10):
        card = mod.build_message(datetime(2026, 7, 14, hour, tzinfo=TZ), test_label="qa", consume_vocab=False)
        assert [line[:3] for line in card.splitlines()] == ["｜行｜", "｜字｜", "｜時｜", "｜勢｜"]
        assert len(card) < 1800
        cards.append(card)

print("Starting neutral data-source fallback checks...")
# Neutral data-source fallbacks.
original_fetch = real_fetch
mod.fetch_gooday_almanac = lambda dt: {"ok": False}
assert mod.build_almanac_chat_line(datetime(2026, 7, 14, 9, tzinfo=TZ)).startswith("｜時｜Gooday 資料暫取不到")
mod.fetch_gooday_almanac = original_fetch
original_iching = mod._ICHING
mod._ICHING = None
assert mod.build_hexagram_next_action(datetime(2026, 7, 14, 9, tzinfo=TZ)).startswith("｜勢｜易經資料暫取不到")
mod._ICHING = original_iching
assert not mod.valid_gooday_data({"ok": True, "date": "2026-07-14", "hours": {}}, "2026-07-14")

print("Starting concurrent same-slot run checks...")
# Same-slot concurrent runs: one reservation, one word, one byte-identical card.
with tempfile.TemporaryDirectory() as td:
    state_path = Path(td) / "pomodoro_state.json"
    env = os.environ.copy()
    env["POMODORO_VOCAB_STATE"] = str(state_path)

    def run_at(hhmm: str) -> tuple[int, str, str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--at", hhmm, "--consume"],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        return result.returncode, result.stdout.replace("\r\n", "\n"), result.stderr

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: run_at("09:00"), range(8)))
    assert all(code == 0 for code, _, _ in results), results
    assert len({stdout for _, stdout, _ in results}) == 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert len(state["history"]) == 1
    assert len(state["slot_reservations"]) == 1

    code, _, error = run_at("10:00")
    assert code == 0, error
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert len(state["history"]) == 2
    assert len(state["slot_reservations"]) == 2
    assert len(state["daily_casts"]) == 2
    for slot_key, reservation in state["slot_reservations"].items():
        assert state["daily_casts"][slot_key] == reservation["cast_values"]
    assert state["history"][0]["word"].lower() != state["history"][1]["word"].lower()
    print("Starting manual run checks (non-consuming 11:00)...")

    before = hashlib.sha256(state_path.read_bytes()).hexdigest()
    manual = subprocess.run(
        [sys.executable, str(SCRIPT), "--at", "11:00"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert manual.returncode == 0, manual.stderr
    assert before == hashlib.sha256(state_path.read_bytes()).hexdigest()

print(f"PASS casts_4moving={four_count} eligible={len(eligible)} cards={len(cards)} concurrent_outputs=1")
