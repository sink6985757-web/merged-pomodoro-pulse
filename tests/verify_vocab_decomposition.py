#!/usr/bin/env python3
"""Verify that the production decomposition index is reproducible and source-backed."""
from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent if (Path(__file__).resolve().parent.parent / "pomodoro_chat_original.py").exists() else Path(__file__).resolve().parent
DATA = SCRIPTS / "data" if (SCRIPTS / "data").exists() else SCRIPTS.parent / "data"
INDEX_PATH = DATA / "vocab_decomposition.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extractor = load_module("vocab_index_extractor", SCRIPTS / "vocab_decomp_extract.py")
card = load_module("vocab_index_card", SCRIPTS / "pomodoro_chat_original.py")
stored = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
rebuilt = extractor.build_index(extractor.CORPUS_DIR)

assert stored["version"] == 4
assert stored["entries"] == rebuilt["entries"]
assert stored["provenance"] == rebuilt["provenance"]
assert stored["stats"] == rebuilt["stats"]
assert len(stored["entries"]) == len(stored["provenance"])
assert card.verified_decomp_entries(stored) == stored["entries"]
assert all(
    meta.get("validation") == "source-backed+morpheme-match"
    for meta in stored["provenance"].values()
)
assert all(
    extractor.decomposition_matches_entry(word, decomposition)
    for word, decomposition in stored["entries"].items()
)

source_cache: dict[str, list[str]] = {}
for word, meta in stored["provenance"].items():
    source_file = meta["source_file"]
    if source_file not in source_cache:
        source_path = extractor.CORPUS_DIR / source_file
        assert source_path.exists(), source_path
        source_cache[source_file] = source_path.read_text(
            encoding="utf-8", errors="ignore"
        ).splitlines()
    lines = source_cache[source_file]
    entry_line = int(meta["entry_line"])
    decomposition_line = int(meta["decomposition_line"])
    assert 1 <= entry_line <= len(lines)
    assert 1 <= decomposition_line <= len(lines)
    assert word.lower() in lines[entry_line - 1].lower(), (word, meta)

# Regression cases from multi-entry OCR lines and targeted source repairs.
assert "audio-visual" not in stored["entries"]
assert "misplace" not in stored["entries"]
assert stored["entries"]["audiphone"] == "phone = sound"
assert stored["entries"]["pregnant"] == "pre- (before) + gnant (to bear 生產)"
assert stored["entries"]["cacography"] == "caco- = bad + -graphy = writing"
assert stored["entries"]["calligraphy"] == "calli- = beautiful + -graphy = writing"
assert not any(
    part.lower().startswith("_backup_files_")
    for meta in stored["provenance"].values()
    for part in Path(meta["source_file"]).parts
)

eligible = card.eligible_vocab_entries(card.load_vocab_entries())
reasons = Counter(item["reason"] for item in stored["quarantined"])
print(
    "PASS "
    f"source_backed={len(stored['entries'])} "
    f"eligible={len(eligible)} "
    f"quarantined={len(stored['quarantined'])} "
    f"reasons={dict(sorted(reasons.items()))}"
)
