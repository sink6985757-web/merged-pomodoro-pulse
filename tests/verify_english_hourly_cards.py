#!/usr/bin/env python3
"""Validate the Drive-derived course database and finalized four-section card."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data" / "english_hourly_cards.json"
MANIFEST = ROOT / "data" / "english_transcript_crosscheck.json"
TZ = timezone(timedelta(hours=8))

import pomodoro_chat_original as core
import unified_broadcaster as broadcaster


dataset = json.loads(DATA.read_text(encoding="utf-8"))
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
assert manifest["authority"] == "google-drive-folder:13_lazdStDY0dyj8iOras0s1UcaWQbfUe"
assert manifest["source_file"]["id"] == "1Gg-H5a9aHTPraXuEX39SstOtZjbt00D3"
assert manifest["raw_transcript_sections"] == 134 and len(manifest["sections"]) == 96
assert dataset["version"] == 2
assert dataset["authority"] == "google-drive-folder:1awbxyfEk9sDxA5p2QQWUtn5EQxKYDXOA"
assert dataset["transcript_authority"] == "google-drive-folder:13_lazdStDY0dyj8iOras0s1UcaWQbfUe"
assert dataset["stats"] == {
    "courses": 3,
    "cards": 128,
    "source_word_cards": 3261,
    "core_words": 384,
    "provided_transcripts": 32,
    "raw_asr_crosschecked": 96,
    "word_card_structure_fallbacks": 0,
    "source_questions": 1967,
    "source_question_groups": 256,
    "raw_transcript_sections": 134,
    "raw_transcript_lesson_matches": 96,
    "structured_root_matches": 128,
    "editorial_example_corrections": 15,
}

cards = dataset["cards"]
assert len(cards) == len({card["id"] for card in cards}) == 128
assert all(card["course"] and card["chapter"] and card["lesson"] for card in cards)
assert all(card["source_word_count"] >= 3 and len(card["core_words"]) == 3 for card in cards)
assert all(len({word["word"] for word in card["core_words"]}) == 3 for card in cards)
assert all(
    word["decomp"] and word["example_en"] and word["answer"]
    for card in cards
    for word in card["core_words"]
)
assert all(not Path(ref).is_absolute() for card in cards for ref in card["source_refs"])

path_card = next(card for card in cards if card["root"] == "path")
assert [word["word"] for word in path_card["core_words"]] == ["sympathy", "apathy", "empathy"]

for stage in (
    "new_anchor", "same_day", "day_1", "day_3", "day_7", "day_14",
    "day_30", "day_60", "day_90", "day_180", "day_365", "annual", "refresh",
):
    staged = dict(path_card)
    staged["_review_stage"] = stage
    rendered = core.format_vocab_line(staged)
    assert rendered.startswith("｜字｜path＝feeling / 感情")
    assert all(label in rendered for label in ("｜課：", "｜章：", "｜單元：", "｜節點：", "｜族："))
    assert "||" not in rendered
    parsed = broadcaster.parse_card_lines([rendered])
    assert parsed["course"] == path_card["course"]
    assert parsed["chapter"] == path_card["chapter"]
    assert parsed["lesson"] == path_card["lesson"]
    assert parsed["family"]

for card in cards:
    for stage in ("new_anchor", "same_day", "day_3", "day_7", "day_90", "annual", "refresh"):
        staged = dict(card)
        staged["_review_stage"] = stage
        rendered = core.format_vocab_line(staged)
        field_value = broadcaster.build_english_display(broadcaster.parse_card_lines([rendered]))
        assert len(field_value) <= 1024, (card["id"], stage, len(field_value))

first = dict(path_card)
first["_review_stage"] = "new_anchor"
line = core.format_vocab_line(first)
assert "**sympathy**" in line and "｜答：sympathy" in line
assert "sympathy＝同情 · apathy＝冷漠；淡漠 · empathy＝移情作用；同感、共鳴" in line

now = datetime(2026, 8, 10, 9, tzinfo=TZ)
raw = core.build_message(now).splitlines()
raw.append(f"｜記｜[點此開啟紀錄儀表板]({broadcaster.PUBLIC_RECORD_URL})")
data = broadcaster.parse_card_lines(raw)
markdown = broadcaster.build_markdown_fallback(data, now)
assert [markdown.index(label) for label in ("**📊 紀錄**", "**📖 英文**", "**🗓️ 農民曆**", "**☯️ 易經 × 斯多葛**")] == sorted(
    markdown.index(label) for label in ("**📊 紀錄**", "**📖 英文**", "**🗓️ 農民曆**", "**☯️ 易經 × 斯多葛**")
)
assert "**行**" not in markdown and "讀一次" not in markdown
assert broadcaster.PUBLIC_RECORD_URL in markdown

payload = broadcaster.build_discord_embed(raw, now)
embed = payload["embeds"][0]
assert [field["name"] for field in embed["fields"]] == [
    "📊 紀錄", "📖 英文", "🗓️ 農民曆", "☯️ 易經 × 斯多葛"
]
assert "09:00→10:30" in embed["description"]
assert all(len(field["value"]) <= 1024 for field in embed["fields"])
assert "課程" not in embed["fields"][0]["name"]
assert "反思參考，不代替現實判斷" in embed["footer"]["text"]

print("PASS english_course units=128 source_words=3261 core_words=384 layout=record-english-almanac-reflection")
