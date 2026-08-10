#!/usr/bin/env python3
"""Validate the Drive-derived hourly English course and runtime rendering."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data" / "english_hourly_cards.json"
SCRIPT = ROOT / "pomodoro_chat_original.py"
BROADCASTER = ROOT / "unified_broadcaster.py"
TZ = timezone(timedelta(hours=8))

dataset = json.loads(DATA.read_text(encoding="utf-8"))
assert dataset["version"] == 1
assert dataset["authority"] == "google-drive-folder:1awbxyfEk9sDxA5p2QQWUtn5EQxKYDXOA"
assert dataset["transcript_authority"] == "google-drive-folder:13_lazdStDY0dyj8iOras0s1UcaWQbfUe"
assert dataset["stats"] == {
    "courses": 3,
    "cards": 128,
    "provided_transcripts": 32,
    "raw_asr_crosschecked": 96,
    "word_card_structure_fallbacks": 0,
    "source_questions": 1967,
    "source_question_groups": 256,
    "raw_transcript_sections": 134,
    "raw_transcript_lesson_matches": 124,
    "structured_root_matches": 128,
    "editorial_example_corrections": 15,
}

cards = dataset["cards"]
assert len(cards) == len({card["id"] for card in cards}) == 128
assert {card["course"] for card in cards} == {
    "字根字首魔法學院",
    "字根字首魔法學院 2",
    "字根字首魔法學院 3",
}
assert all(card["root"] and card["word"] and card["prompt"] and card["answer"] for card in cards)
assert all(card["answer"] for card in cards)
assert all(card["prompt"].startswith("填空：") and "____" in card["prompt"] for card in cards)
assert all(card["decomp"] and card["example_en"] and card["example_zh"] for card in cards)
assert {card["transcript_status"] for card in cards} == {
    "provided-transcript",
    "raw-asr-crosschecked",
}
assert sum(card["transcript_status"] == "raw-asr-crosschecked" for card in cards) == 96
assert all(not Path(ref).is_absolute() for card in cards for ref in card["source_refs"])
assert all("G:/" not in ref and "G:\\" not in ref for card in cards for ref in card["source_refs"])

spec = importlib.util.spec_from_file_location("pomodoro_english_course", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

broadcaster_spec = importlib.util.spec_from_file_location("pomodoro_english_broadcaster", BROADCASTER)
assert broadcaster_spec and broadcaster_spec.loader
broadcaster = importlib.util.module_from_spec(broadcaster_spec)
broadcaster_spec.loader.exec_module(broadcaster)

loaded = mod.load_english_hourly_cards()
assert len(loaded) == 128
for card in loaded:
    rendered = mod.format_vocab_line(card)
    assert rendered.startswith("｜字｜")
    assert "答：||" in rendered and rendered.endswith("||")
    assert len(rendered) < 420, (card["id"], len(rendered), rendered)
    assert not any(noise in rendered.lower() for noise in ("abay", "abidient", "this abidient", "自根", "字為", "刪除率"))
sample = next(card for card in loaded if card["root"] == "dic, dict")
line = mod.format_vocab_line(sample)
assert line.startswith("｜字｜dic, dict＝say, speak, show / 說，指出，展現｜")
assert "｜提示：" in line
assert "答：||" in line and line.endswith("||")
assert len(line) < 360
parsed = broadcaster.parse_card_lines([line])
assert parsed["root"] == "dic, dict"
assert parsed["root_meaning"] == "say, speak, show / 說，指出，展現"
assert parsed["word"] == "diction"
assert parsed["takeaway"]
assert parsed["question"] and parsed["answer"] == "diction"
embed = broadcaster.build_discord_embed([line], datetime(2026, 8, 10, 9, tzinfo=TZ))
english_field = next(field for field in embed["embeds"][0]["fields"] if field["name"] == "📖 課程字根記憶")
assert "dic, dict" in english_field["value"]
assert "❓" in english_field["value"] and "||diction||" in english_field["value"]

for hour in range(6, 19):
    output = mod.build_message(datetime(2026, 8, 10, hour, tzinfo=TZ), test_label="qa")
    lines = output.splitlines()
    assert [line[:3] for line in lines] == ["｜行｜", "｜字｜", "｜時｜", "｜勢｜"]
    assert "答：||" in lines[1]
    assert len(output) < 1800

print("PASS english_hourly_cards courses=3 cards=128 transcripts=32 raw_asr=96 groups=256 questions=1967")
