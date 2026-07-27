#!/usr/bin/env python3
"""RED/GREEN acceptance tests for vocab provenance and I Ching glyph output."""
from __future__ import annotations

import importlib.util
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


card = load_module("pomodoro_card_enhancement", SCRIPTS / "pomodoro_chat_original.py")
extractor = load_module("vocab_decomp_enhancement", SCRIPTS / "vocab_decomp_extract.py")

# Hexagram glyphs follow Unicode's King Wen order.
assert card.hexagram_symbol(1) == "䷀"
assert card.hexagram_symbol(2) == "䷁"
assert card.hexagram_symbol(64) == "䷿"
try:
    card.hexagram_symbol(0)
except ValueError:
    pass
else:
    raise AssertionError("hexagram_symbol must reject numbers outside 1..64")

static_cast = card.cast_from_values([7, 7, 7, 7, 7, 7])
static_line = card.build_hexagram_next_action(datetime(2026, 7, 14, 9, tzinfo=TZ), static_cast)
assert static_line.startswith("｜勢｜第1卦 ䷀ 乾為天｜靜｜"), static_line

moving_cast = card.cast_from_values([9, 7, 7, 7, 7, 7])
moving_line = card.build_hexagram_next_action(datetime(2026, 7, 14, 9, tzinfo=TZ), moving_cast)
expected_transition = (
    f"第{moving_cast['base_no']}卦 {card.hexagram_symbol(moving_cast['base_no'])} {moving_cast['base_name']}"
    f"→第{moving_cast['changed_no']}卦 {card.hexagram_symbol(moving_cast['changed_no'])} {moving_cast['changed_name']}"
)
assert moving_line.startswith(f"｜勢｜{expected_transition}｜初｜"), moving_line

# Multi-entry OCR lines must associate each decomposition with the nearest
# preceding dictionary entry, never the first word on the line.
fixture = [
    "audio-visual [ˌɔdiːoʊvˈɪʒuːəl] adj. 視聽的 audiphone [ˈaːdifoun] n. 助聽器《phone = sound》",
    "misplace [mɪsˈpleɪs] v. 誤置 mispronounce [ˌmɪsprəˈnaʊns] v. 發錯音《pronounce = 發音》",
    "pregnant [ˈpreɡnənt] adj. 妊娠的《pre- (before) + gnant (to bear)》",
    "cacography [kæˈkɒɡrəfi] n. 錯誤拼寫",
    "《caco = bad + graph (to write) + -y (名詞字尾)》",
]
mapping, provenance, quarantined = extractor.extract_mapping_from_lines(fixture, "fixture.md")
assert "audio-visual" not in mapping
assert mapping["audiphone"] == "phone = sound"
assert "misplace" not in mapping
assert mapping["mispronounce"] == "pronounce = 發音"
assert mapping["pregnant"] == "pre- (before) + gnant (to bear)"
assert mapping["cacography"] == "caco = bad + graph (to write) + -y (名詞字尾)"
assert provenance["audiphone"]["source_file"] == "fixture.md"
assert provenance["audiphone"]["entry_line"] == 1
assert provenance["cacography"]["decomposition_line"] == 5
assert all(item["reason"] for item in quarantined)
assert extractor.clean_decomp_text("caco - bæd") == "caco - bad"
assert extractor.clean_decomp_text("calli = bezutiful") == "calli = beautiful"
assert extractor.clean_decomp_text("dicto = to smeak") == "dicto = to speak"
assert card.decomposition_matches_word("glorious", "glory = 光榮")

verified_index_fixture = {
    "version": 4,
    "entries": {"good": "good = 良好", "bad": "bad = 不採用"},
    "provenance": {
        "good": {"validation": "source-backed+morpheme-match"},
        "bad": {"validation": "unverified-auto"},
    },
}
assert card.verified_decomp_entries(verified_index_fixture) == {"good": "good = 良好"}
assert card.verified_decomp_entries({"version": 3, "entries": {"old": "old = 舊"}}) == {}

with tempfile.TemporaryDirectory() as temp_dir:
    corpus_dir = Path(temp_dir)
    (corpus_dir / "fixture_fixed.md").write_text("\n".join(fixture), encoding="utf-8")
    backup_dir = corpus_dir / "_backup_files_20260714_000000"
    backup_dir.mkdir()
    (backup_dir / "fixture_fixed.md").write_text("\n".join(fixture), encoding="utf-8")
    index = extractor.build_index(corpus_dir)
    assert index["version"] == 4
    assert index["entries"]["audiphone"] == "phone = sound"
    assert "audio-visual" not in index["entries"]
    assert index["provenance"]["pregnant"]["validation"] == "source-backed+morpheme-match"
    assert index["stats"]["source_backed_entries"] == len(index["entries"])
    assert index["stats"]["files_scanned"] == 1

print("PASS enhancement_contracts")
