#!/usr/bin/env python3
"""Audit spelling, source-grounded decomposition, examples, and recall answers."""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "english_hourly_cards.json"
V5 = ROOT / "data" / "vocab_decomposition_v5.json"


def normalize(value: str) -> str:
    return re.sub(r"[^a-z]", "", value.lower())


def root_matches_decomposition(card: dict[str, object]) -> bool:
    roots = [normalize(value) for value in re.split(r"[,/]", str(card["root"]))]
    roots = [value for value in roots if value]
    for segment in str(card["decomp"]).split(" + "):
        part = normalize(segment.split("(", 1)[0])
        if part and any(
            part == root
            or (len(root) >= 2 and part.startswith(root))
            or (len(part) >= 2 and root.startswith(part))
            for root in roots
        ):
            return True
    return False


dataset = json.loads(DATA.read_text(encoding="utf-8"))
cards = dataset["cards"]
required = {
    "id", "course", "chapter", "lesson", "root", "root_meaning_zh",
    "word", "pron", "pos", "gloss", "decomp", "takeaway", "prompt",
    "answer", "example_en", "example_zh", "transcript_status", "source",
    "source_refs", "example_editorial_note",
}

assert len(cards) == 128
assert dataset["stats"]["structured_root_matches"] == 128
assert "course-defined root-family mnemonic" in dataset["description"]
assert all(required.issubset(card) for card in cards)
assert all(re.fullmatch(r"[a-z][a-z'-]*", card["word"]) for card in cards)
assert all(card["pron"] and card["pos"] and card["gloss"] for card in cards)
assert all(card["root_meaning_en"] or card["root_meaning_zh"] for card in cards)
assert all(card["decomp"] and root_matches_decomposition(card) for card in cards)
assert all(card["example_en"] and card["example_zh"] for card in cards)
assert sum(bool(card["example_editorial_note"]) for card in cards) == 15
assert dataset["stats"]["editorial_example_corrections"] == 15
assert all(card["prompt"].startswith("填空：") and "____" in card["prompt"] for card in cards)
assert all(card["answer"] for card in cards)
assert all(not Path(ref).is_absolute() for card in cards for ref in card["source_refs"])

# Guard the representative-selection regression: use a genuine source-marked
# derivative instead of the deck's opening translation-equivalent flashcard.
expected_representatives = {
    "ped, pod, pus": "pedal",
    "ple, plex, plic, ply": "simple",
    "ment": "mental",
    "pater, patr": "paternal",
    "astro, aster": "asterisk",
    "son": "sonic",
    "voc, vok": "vocal",
    "rod, ros, rad, raz": "corrode",
    "ly": "analyze",
    "sim, simil, sembl, homo": "similar",
}
by_root = {card["root"]: card for card in cards}
assert all(by_root[root]["word"] == word for root, word in expected_representatives.items())

# V5 is a useful spelling cross-check, not the course authority. The five
# exceptions are common, correctly spelled course words absent from that file.
if V5.is_file():
    v5 = json.loads(V5.read_text(encoding="utf-8"))
    not_in_v5 = {card["word"] for card in cards if card["word"] not in v5}
    assert not_in_v5 == {"asterisk", "clarity", "lavatory", "monologue", "order"}
    spelling_crosscheck = len(cards) - len(not_in_v5)
else:
    # The portable GitHub/Hermes runtime intentionally omits the 1.6 MB legacy
    # V5 file. The course dataset remains self-contained and fully testable.
    not_in_v5 = set()
    spelling_crosscheck = 0

noise = ("abay", "abidient", "this abidient", "自根", "字為", "刪除率", "請記得點讚訂閱")
rendered = json.dumps(dataset, ensure_ascii=False).lower()
assert not any(item.lower() in rendered for item in noise)

print(
    "PASS english_content_accuracy "
    f"cards={len(cards)} structured_roots=128 fill_prompts=128 "
    f"editorial_corrections=15 v5_spelling_crosscheck={spelling_crosscheck} "
    f"exceptions={len(not_in_v5)}"
)
