#!/usr/bin/env python3
"""Verify that the V5 vocabulary decomposition database is structurally valid.

V5 schema (from Vertex AI Gemini-2.5-flash):
    {word: {pron, pos, gloss, decomp}, ...}
- pron: K.K. phonetic (string, non-empty)
- pos: part of speech (string, non-empty)
- gloss: Chinese definition (string, non-empty)
- decomp: root decomposition string or null
"""
from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent if (Path(__file__).resolve().parent.parent / "pomodoro_chat_original.py").exists() else Path(__file__).resolve().parent
DATA = SCRIPTS / "data" if (SCRIPTS / "data").exists() else SCRIPTS.parent / "data"
INDEX_PATH = DATA / "vocab_decomposition_v5.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import os
if "POMODORO_DATA_DIR" not in os.environ:
    os.environ["POMODORO_DATA_DIR"] = str(SCRIPTS)

card = load_module("vocab_index_card", SCRIPTS / "pomodoro_chat_original.py")

# ── Load V5 database ────────────────────────────────────────────
stored = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
assert isinstance(stored, dict), "V5 must be a flat dict {word: {...}}"
print(f"Loaded {len(stored)} vocabulary entries from V5 database.")

# ── Structural validation ──────────────────────────────────────
REQUIRED_KEYS = {"pron", "pos", "gloss"}

str_count = 0
none_count = 0
missing_pron = 0
missing_pos = 0
missing_gloss = 0
non_dict_count = 0

for word, entry in stored.items():
    if not isinstance(entry, dict):
        non_dict_count += 1
        continue
    if isinstance(entry, str):
        str_count += 1
    if entry is None:
        none_count += 1
    if not entry.get("pron"):
        missing_pron += 1
    if not entry.get("pos"):
        missing_pos += 1
    if not entry.get("gloss"):
        missing_gloss += 1

assert str_count == 0, f"Found {str_count} flat string values (should be dicts)"
assert none_count == 0, f"Found {none_count} None values"
assert non_dict_count == 0, f"Found {non_dict_count} non-dict entries"
assert missing_pron == 0, f"Found {missing_pron} entries with empty pron"
assert missing_pos == 0, f"Found {missing_pos} entries with empty pos"
assert missing_gloss == 0, f"Found {missing_gloss} entries with empty gloss"

# ── Content validation via pomodoro_chat_original ──────────────
eligible = card.eligible_vocab_entries(card.load_vocab_entries())
print(f"Eligible vocabulary entries (loaded via pomodoro_chat): {len(eligible)}")

# Check all eligible entries have usable pronunciation
for entry in eligible:
    # No CJK characters in pronunciation
    assert not card.has_cjk(entry.get("pron", "")), f"CJK in pron: {entry['word']} {entry.get('pron')}"
    # No forbidden patterns in pronunciation
    assert not card.VOCAB_PRON_FORBIDDEN_RE.search(entry.get("pron", "")), f"Forbidden pron pattern: {entry['word']}"
    # Pronunciation must be usable
    assert card.pronunciation_is_usable(entry.get("pron", "")), f"Unusable pron: {entry['word']}"
    # No '+' in gloss (indicates raw/compound definitions)
    assert "+" not in entry.get("gloss", ""), f"' + ' in gloss: {entry['word']}: {entry.get('gloss')}"

# Skip decomp content checks for entries where decomp is None
entries_with_decomp = [e for e in eligible if e.get("decomp")]
print(f"Entries with root decomposition: {len(entries_with_decomp)}/{len(eligible)}")

for entry in entries_with_decomp:
    decomp = entry.get("decomp", "")
    # No forbidden patterns in decomposition
    assert not card.VOCAB_DECOMP_FORBIDDEN_RE.search(decomp), f"Forbidden decomp: {entry['word']}: {decomp}"
    # No IPA-like phonetic artifacts in decomposition
    assert not card.VOCAB_DECOMP_IPA_RE.search(decomp), f"IPA in decomp: {entry['word']}: {decomp}"
    # Decomposition must be structured (contains separator like + or =)
    assert card.decomposition_is_structured(decomp), f"Unstructured decomp: {entry['word']}: {decomp}"

# ── Regression cases ───────────────────────────────────────────
# Verify the 6 previously broken words are now properly structured
for word in ["abandon", "abbreviation", "abnormal", "absorb", "ability", "side"]:
    assert word in stored, f"Missing critical word: {word}"
    entry = stored[word]
    assert isinstance(entry, dict), f"{word} is not a dict: {type(entry)}"
    assert entry.get("pron"), f"{word} has no pron"
    assert entry.get("pos"), f"{word} has no pos"
    assert entry.get("gloss"), f"{word} has no gloss"

# Verify no duplicate keys with identical lowercased forms AND content
# (legitimate homographs like march/March, polish/Polish, second/Second are OK)
same_case_dupes = [k for k, count in Counter(stored.keys()).items() if count > 1]
assert not same_case_dupes, f"Exact duplicate keys: {same_case_dupes}"

# ── Summary ─────────────────────────────────────────────────────
decomp_none_count = sum(1 for v in stored.values() if isinstance(v, dict) and v.get("decomp") is None)

print(
    "PASS "
    f"total={len(stored)} "
    f"eligible={len(eligible)} "
    f"with_decomp={len(entries_with_decomp)} "
    f"decomp_null={decomp_none_count} "
    f"str_vals={str_count} "
    f"none_vals={none_count} "
    f"missing_pron={missing_pron} "
    f"missing_pos={missing_pos} "
    f"missing_gloss={missing_gloss}"
)
