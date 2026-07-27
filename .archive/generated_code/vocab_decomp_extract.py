#!/usr/bin/env python3
"""
vocab_decomp_extract.py — 從劉毅/學習出版社 style 語料庫提取單字拆解
產生 mapping: word.lower() → decomposition string

v3.0 — 全格式 + 寬鬆策略 + OCR 修正
支援格式:
  1. 《...》                      — 標準中文書名號（主要格式）
  2. \langle ... \rangle         — LaTeX 角括號
  3. (prefix + root + suffix)     — 括號分解（含 + 號）
  4. $$...$$ 數學區塊             — 含分解資訊的數學塊
  5. 殘缺 》格式                  — OCR 漏掉開頭《 的情況
"""

import json, os, re
from pathlib import Path

def _data_dir() -> Path:
    d = os.environ.get("POMODORO_DATA_DIR")
    if d:
        return Path(d) / "data"
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "hermes" / "data"
    return Path.home() / "AppData" / "Local" / "hermes" / "data"

CORPUS_DIR = _data_dir() / "vocab_corpus"
OUTPUT_PATH = _data_dir() / "vocab_decomposition.json"
SKIP_NAME_PARTS = ("index", "front_matter", "usage", "appendix")

# ─── Regex patterns ──────────────────────────────────────────────

# Word entry line: word [pron] or word (pron)
WORD_LINE_RE = re.compile(
    r"(?<![A-Za-z])"
    r"(?P<word>[A-Za-z][A-Za-z'\-]{2,}(?:/[A-Za-z][A-Za-z'\-]{2,})?)"
    r"(?:\s*(?P<pron>\[[^\]\n]{2,80}\]|\([^\)\n]{2,80}\))\s*)"
)

# A real dictionary entry must include pronunciation and part of speech.
# This prevents decomposition fragments such as ``bandon(order)`` from being
# mistaken for independent words.
FULL_ENTRY_RE = re.compile(
    r"(?<![A-Za-z])"
    r"(?P<word>[A-Za-z][A-Za-z'\-]{2,}(?:/[A-Za-z][A-Za-z'\-]{2,})?)"
    r"\s*(?P<pron>\[[^\]\n]{2,80}\]|\([^\)\n]{2,80}\))\s*"
    r"(?P<pos>(?:adj|adv|n|v|prep|pron|conj|interj)\.?)(?=\s)",
    re.IGNORECASE,
)

# Standard 《...》
DECOMP_BOOK_RE = re.compile(r"《([^》]+)》")

# LaTeX \langle ... \rangle (with optional $ delimiters, inline or block)
LANGLE_RE = re.compile(
    r"(?:\$\$?\s*)?\\langle\s+(.+?)\s+\\rangle(?:\s*\$?\$?)?",
    re.DOTALL
)

# $$...$$ math blocks — extract content inside
MATH_BLOCK_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)

# Bare parenthetical decomposition: ( ... + ... + ... ) with at least one +
# Avoid matching pronunciations like [prɒn]
PAREN_DECOMP_RE = re.compile(
    r"\(([^()]*?[A-Za-z][^()]*?\+[^()]*?)\)"
)

# HTML/LaTeX cleanup
LATEX_CLEAN_RE = re.compile(r"\$\$[^$]+\$\$")
HTML_TAG_RE = re.compile(r"<[^>]+>")

# ─── OCR fix tables ──────────────────────────────────────────────

# OCR misreads: wrong → correct
OCR_CHAR_FIXES = [
    ("hrief", "brief"),
    ("bæd", "bad"),
    ("bezutiful", "beautiful"),
    ("smeak", "speak"),
    ("bottow", "bottom"),
    ("bortom", "bottom"),
    ("機骨", "肋骨"),
    ("thorought", "thorough"),
    ("throught", "through"),
    ("wcond", "second"),
    ("Tirst", "first"),
    ("to wonder at", "to wonder at"),  # already correct, just document
]

# '10' → 'to' fixes (only apply in decomposition context)
OCR_10_PATTERNS = [
    (re.compile(r"\b10\s+wonder\b"), "to wonder"),
    (re.compile(r"\b10\s+come\b"), "to come"),
    (re.compile(r"\b10\s+touch\b"), "to touch"),
    (re.compile(r"\b10\s+show\b"), "to show"),
    (re.compile(r"ad-\(10\)"), "ad-(to)"),
    (re.compile(r"\(10\)"), "(to)"),
    (re.compile(r"\b10\s+"), "to "),
    (re.compile(r"\b10$"), "to"),  # 10 at end of string
]

# LaTeX artifact removal (inside decomposition text)
LATEX_GARBAGE = [
    (re.compile(r"\\cdot\s*"), " "),
    (re.compile(r"\\bullet\s*"), " "),
    (re.compile(r"_\{\\bullet\}"), ""),
    (re.compile(r"_\{\\Omega\}"), ""),
    (re.compile(r"_\{\\omega\}"), ""),
    (re.compile(r"_\{\\cup\s*\d+\}"), ""),
    (re.compile(r"_\{\\square\}"), ""),
    (re.compile(r"_\{\s*\}"), ""),           # _{ } → remove
    (re.compile(r"_\{\s*\\bullet"), ""),     # _{\bullet → remove
    (re.compile(r"_\{0\}"), ""),             # _{0} → remove
    (re.compile(r"\\mid\s*"), " + "),
    (re.compile(r"\\ell\s+"), ""),
    (re.compile(r"\\overline\{[^}]*\}"), ""),
    (re.compile(r"\\circ\s+f\.\s*.*$"), ""),
    (re.compile(r"\+\s*\\Omega_\{\\bullet\}"), ""),
    (re.compile(r"\+\s*\\\\Omega"), ""),
    (re.compile(r"\\mathbf\{([^}]*)\}"), r"\1"),
    (re.compile(r"\\boxed\{[^}]*\}"), " "),
    (re.compile(r"\|\s*[|]+\s*"), " "),
    (re.compile(r"\\\\"), " "),
    (re.compile(r"&\s*"), " "),
    (re.compile(r"\$+"), " "),
    (re.compile(r"\\begin\{[^}]*\}.*?\\end\{[^}]*\}", re.DOTALL), " "),
    (re.compile(r"\\(?=[^a-zA-Z])"), " "),
    # OCR: t_0, t_{\Omega} → to
    (re.compile(r"\bt_0\b"), "to"),
    (re.compile(r"\bt_\{\\Omega\}\b"), "to"),
    (re.compile(r"\bt_\{\\omega\}\b"), "to"),
    (re.compile(r"\bt_\{0\}\b"), "to"),
    (re.compile(r"\(t_0\)"), "(to)"),
    (re.compile(r"\(t_\{\\Omega\}\)"), "(to)"),
]


# ─── Cleaning functions ──────────────────────────────────────────

def clean_line(text: str) -> str:
    """Basic line cleanup: remove HTML and normalize whitespace.
    Does NOT strip $$ blocks — they may contain decomposition info."""
    text = HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_decomp_text(decomp: str) -> str:
    """Apply OCR fixes and clean up a decomposition string."""
    decomp = decomp.strip()

    # Strip leading/trailing garbage
    decomp = re.sub(r"^[\s\.\,\;\:\!\?\|\\•·]+", "", decomp)
    decomp = re.sub(r"[\s\.\,\;\:\!\?\|\\•·]+$", "", decomp)

    # Fix doubled hyphens from OCR: -- → - (but keep = patterns)
    decomp = re.sub(r"(?<!=)-(?!=)", "-", decomp)  # normalize single hyphens
    decomp = re.sub(r"--+", "-", decomp)           # collapse multiple hyphens

    # Remove LaTeX artifacts
    for pattern, replacement in LATEX_GARBAGE:
        decomp = pattern.sub(replacement, decomp)

    # Character-level OCR fixes
    for wrong, right in OCR_CHAR_FIXES:
        decomp = decomp.replace(wrong, right)

    # Fix '10' → 'to' (only in decomposition context with English parts)
    if re.search(r'[A-Za-z]', decomp):
        for pattern, replacement in OCR_10_PATTERNS:
            decomp = pattern.sub(replacement, decomp)

    # Normalize whitespace
    decomp = re.sub(r"\s+", " ", decomp).strip()

    # Fix common spacing: ensure single space around +
    decomp = re.sub(r"\s*\+\s*", " + ", decomp)

    # Fix " = = " → " = "
    decomp = re.sub(r"\s*=\s*=\s*", " = ", decomp)

    # Remove trailing cf./參照
    decomp = re.sub(r"\s*cf\..*$", "", decomp).strip()
    decomp = re.sub(r"\s*參照.*$", "", decomp).strip()

    # Clean doubled spaces
    decomp = re.sub(r"  +", " ", decomp)

    return decomp.strip()


def is_skip_decomp(text: str) -> bool:
    """Check if decomposition text should be skipped (non-decomposition metadata)."""
    t = text.strip()
    if not t or len(t) < 2:
        return True
    if t.startswith(("解說", "參照", "cf.", "see ", "p.", "pp.")):
        return True
    if re.match(r'^[\d\s,;\-]+$', t):  # purely numeric/page ref
        return True
    if re.match(r'^[a-z]{2,6}\s*=\s*[a-z]{2,15}$', t.strip(), re.IGNORECASE):
        return False  # simple root=meaning is valid
    if not re.search(r'[A-Za-z]', t):
        return True  # no English letters = not useful
    return False


def extract_decomps_from_text(text: str) -> list[tuple[str, str]]:
    """Extract all decomposition candidates from text. Returns [(source, text), ...]."""
    results = []

    # Pattern 1: 《...》 — primary format
    for m in DECOMP_BOOK_RE.finditer(text):
        d = m.group(1).strip()
        if not is_skip_decomp(d):
            results.append(("book", d))

    # Pattern 2: \langle ... \rangle — LaTeX angle brackets
    for m in LANGLE_RE.finditer(text):
        d = m.group(1).strip()
        if not is_skip_decomp(d):
            # Capture all \langle content — both complex (a + b) and simple (x = y)
            results.append(("langle", d))

    # Pattern 3: $$...$$ math blocks — look for \langle inside
    for block_m in MATH_BLOCK_RE.finditer(text):
        block_content = block_m.group(1)
        # Skip large layout arrays (page decorations)
        if len(block_content) > 300:
            continue
        for lm in LANGLE_RE.finditer(block_content):
            d = lm.group(1).strip()
            if not is_skip_decomp(d):
                results.append(("math_block", d))

    # Pattern 4: Bare parenthetical (xxx + xxx)
    # Pre-clean: strip LaTeX artifacts from the text for paren matching
    paren_clean = text
    for pattern, replacement in LATEX_GARBAGE[:10]:  # only simple patterns
        paren_clean = pattern.sub(replacement, paren_clean)
    # Remove inner nested parentheses: (foo(bar)) → (foo bar) — crude but functional
    paren_clean = re.sub(r'\(([^()]*?)\)', r' \1 ', paren_clean)
    
    for m in PAREN_DECOMP_RE.finditer(paren_clean):
        d = m.group(1).strip()
        if len(d) > 6 and re.search(r'[A-Za-z]{3,}', d):
            if re.search(r'[a-z]+-[a-z]*\s*[=＋]\s*[a-z]', d, re.IGNORECASE):
                results.append(("paren", d))

    return results


def decomposition_matches_entry(word: str, decomposition: str) -> bool:
    """Require at least one visible morpheme to match the target word."""
    normalized_word = re.sub(r"[^a-z]", "", word.lower())
    outside_notes = re.sub(r"\([^)]*\)", " ", decomposition.lower())
    candidates = re.findall(r"[a-z]{2,}", outside_notes)
    for candidate in candidates:
        variants = {candidate}
        if candidate.endswith("y"):
            variants.add(candidate[:-1] + "i")
        if candidate.endswith("e"):
            variants.add(candidate[:-1])
        if any(variant and variant in normalized_word for variant in variants):
            return True
    return False


def decomposition_candidates_with_spans(text: str) -> list[tuple[int, str, str]]:
    """Return ``(start, format, text)`` candidates without losing positions."""
    candidates: list[tuple[int, str, str]] = []
    for match in DECOMP_BOOK_RE.finditer(text):
        candidates.append((match.start(), "book", match.group(1)))
    for match in LANGLE_RE.finditer(text):
        candidates.append((match.start(), "langle", match.group(1)))
    return sorted(candidates, key=lambda item: item[0])


def extract_mapping_from_lines(
    lines: list[str], source_file: str
) -> tuple[dict[str, str], dict[str, dict], list[dict]]:
    """Extract source-backed decompositions with line-level provenance."""
    mapping: dict[str, str] = {}
    provenance: dict[str, dict] = {}
    quarantined: list[dict] = []

    def register(word: str, raw_decomp: str, entry_line: int, decomp_line: int, fmt: str) -> None:
        decomp = clean_decomp_text(raw_decomp)
        if is_skip_decomp(decomp) or len(decomp) < 3:
            quarantined.append({
                "word": word,
                "reason": "invalid decomposition text",
                "source_file": source_file,
                "decomposition_line": decomp_line,
            })
            return
        if not decomposition_matches_entry(word, decomp):
            quarantined.append({
                "word": word,
                "reason": "decomposition morpheme does not match visible word",
                "source_file": source_file,
                "decomposition_line": decomp_line,
                "decomposition": decomp,
            })
            return
        if word in mapping:
            return
        mapping[word] = decomp
        provenance[word] = {
            "source_file": source_file,
            "entry_line": entry_line,
            "decomposition_line": decomp_line,
            "format": fmt,
            "validation": "source-backed+morpheme-match",
        }

    for index, raw in enumerate(lines):
        entries = list(FULL_ENTRY_RE.finditer(raw))
        candidates = decomposition_candidates_with_spans(raw)
        assigned_words: set[str] = set()

        for start, fmt, decomposition in candidates:
            preceding = [entry for entry in entries if entry.start() < start]
            if not preceding:
                continue
            entry = max(preceding, key=lambda item: item.start())
            word = entry.group("word").lower()
            register(word, decomposition, index + 1, index + 1, fmt)
            assigned_words.add(word)

        # Only a single-entry line may own a following standalone decomposition.
        # Multi-entry lines are ambiguous and remain unassigned.
        if len(entries) == 1:
            word = entries[0].group("word").lower()
            if word not in assigned_words and word not in mapping:
                for lookahead in (1, 2):
                    next_index = index + lookahead
                    if next_index >= len(lines):
                        break
                    next_raw = lines[next_index].strip()
                    if not next_raw:
                        continue
                    if FULL_ENTRY_RE.search(next_raw) or should_stop_lookahead(next_raw):
                        break
                    next_candidates = decomposition_candidates_with_spans(next_raw)
                    if next_candidates:
                        _, fmt, decomposition = next_candidates[0]
                        register(word, decomposition, index + 1, next_index + 1, fmt)
                        break

    return mapping, provenance, quarantined


def is_word_entry_line(text: str) -> bool:
    """Check if a line looks like a new word entry (stop lookahead).
    Excludes decomposition-only lines starting with 《 or \\langle."""
    s = text.strip()
    # Decomposition lines are NOT word entries
    if s.startswith(("《", "\\langle", "$$\\langle")):
        return False
    if WORD_LINE_RE.search(text):
        return True
    if len(text) <= 25 and re.match(r'^[A-Za-z]{1,3}\s', text):
        return True
    return False


def should_stop_lookahead(line: str) -> bool:
    """Check if we should stop looking ahead for decomposition."""
    s = line.strip()
    if not s:
        return False  # empty lines are OK to skip
    if s.startswith(("```", "$$", "---", "===", "![")):
        return True
    if re.match(r'^#{2,}', s):  # ## or more
        return True
    if is_word_entry_line(s):
        return True
    # Section headers like "5 acid, acr = sour (酸的)"
    if re.match(r'^\d+\s+[a-z]+.*=', s, re.IGNORECASE):
        return True
    return False


# ─── Main extraction ─────────────────────────────────────────────

def build_index(corpus_dir: Path) -> dict:
    """Build a provenance-carrying, source-backed decomposition index."""
    entries: dict[str, str] = {}
    provenance: dict[str, dict] = {}
    quarantined: list[dict] = []
    total_lines = 0
    files_scanned = 0

    for path in sorted(corpus_dir.rglob("*.md")):
        lowered_name = path.name.lower()
        if any(part.lower().startswith("_backup_files_") for part in path.parts):
            continue
        if any(skip in lowered_name for skip in SKIP_NAME_PARTS):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        files_scanned += 1
        total_lines += len(lines)
        file_entries, file_provenance, file_quarantine = extract_mapping_from_lines(
            lines, path.name
        )
        quarantined.extend(file_quarantine)
        for word, decomposition in file_entries.items():
            if word in entries:
                if entries[word] != decomposition:
                    quarantined.append({
                        "word": word,
                        "reason": "conflicting source decomposition; kept first source",
                        "kept": entries[word],
                        "rejected": decomposition,
                        "source_file": path.name,
                    })
                continue
            entries[word] = decomposition
            provenance[word] = file_provenance[word]

    by_format: dict[str, int] = {}
    for item in provenance.values():
        fmt = str(item.get("format", "unknown"))
        by_format[fmt] = by_format.get(fmt, 0) + 1
    return {
        "version": 4,
        "source": "劉毅/學習出版社 英文字根字典",
        "total_entries": len(entries),
        "stats": {
            "files_scanned": files_scanned,
            "total_lines": total_lines,
            "source_backed_entries": len(entries),
            "quarantined_candidates": len(quarantined),
            "by_format": by_format,
        },
        "entries": entries,
        "provenance": provenance,
        "quarantined": quarantined,
    }

def extract() -> dict:
    index = build_index(CORPUS_DIR)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    stats = index["stats"]
    print(f"✅ 已提取 {index['total_entries']} 筆來源可追溯字根拆解")
    print(f"   掃描檔案: {stats['files_scanned']}")
    print(f"   掃描行數: {stats['total_lines']}")
    print(f"   格式分布: {stats['by_format']}")
    print(f"   隔離候選: {stats['quarantined_candidates']}")
    print(f"   輸出至: {OUTPUT_PATH}")
    return index


if __name__ == "__main__":
    extract()