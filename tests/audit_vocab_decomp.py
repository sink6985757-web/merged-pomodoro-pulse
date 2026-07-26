#!/usr/bin/env python3
"""Comprehensive audit of vocab decomposition system."""
import json
import re
import random
from pathlib import Path

# NOTE: Update these paths for your environment, or set POMODORO_DATA_DIR env var.
import os
_HOME = os.environ.get("POMODORO_DATA_DIR",
    str(Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "hermes"))
DECOMP_PATH = Path(_HOME) / "data" / "vocab_decomposition.json"
CORPUS_DIR = Path(_HOME) / "data" / "vocab_corpus"

# Load JSON
data = json.loads(DECOMP_PATH.read_text(encoding="utf-8"))
entries = data["entries"]
print(f"=== 基本統計 ===")
print(f"Total entries in JSON: {len(entries)}")
print(f"Stats from extraction: {data['stats']}")

# -------------------------------------------------------
# BUG 1: Check for "ghost words" — words that appear to be roots/parts 
# extracted from WITHIN 《...》 decomposition text
# -------------------------------------------------------
print(f"\n=== BUG 分析 1: 幽靈單字 (從拆解文字中誤提取的單字) ===")

# These look like they're from within decompositions, not real vocabulary entries
# Let's check known problematic patterns
suspicious_patterns = [
    # Keys that are phonetic/prefix fragments
    ("byss", "part of 'abyss' decomposition"),
    ("chromat", "part of 'achromatic' decomposition"),
    ("bene-", "looks like prefix, not a word"),
    ("ambi-", "prefix, not a word"),
    ("amb-", "prefix variant"),
    ("auto-", "prefix"),
    ("cata-", "prefix"),
    ("circum-", "prefix"),
    ("contra-", "prefix"),
    ("counter", "could be real word but check"),
    ("deca-", "prefix (decade key?)"),
    ("di-", "prefix"),
    ("dis-", "prefix"),
    ("en-", "prefix"),
    ("ex-", "prefix"),
    ("extra-", "prefix"),
    ("for-", "prefix"),
    ("hexa-", "prefix"),
    ("in-", "prefix"),
    ("inter-", "prefix"),
    ("intro-", "prefix"),
    ("iso-", "prefix"),
    ("macro-", "prefix"),
    ("mal-", "prefix"),
    ("mega-", "prefix"),
    ("mono-", "prefix"),
    ("multi-", "prefix"),
    ("mult-", "prefix variant"),
    ("ne-", "prefix"),
    ("necro-", "prefix?"),
    ("ob-", "prefix"),
    ("ob--", "prefix double dash"),
    ("omni-", "prefix"),
    ("pan-", "prefix"),
    ("per-", "prefix?"),
    ("poly-", "prefix?"),
    ("post-", "prefix?"),
    ("pre-", "prefix?"),
    ("pro-", "prefix?"),
    ("re-", "prefix?"),
    ("se-", "prefix?"),
    ("sub-", "prefix?"),
    ("super-", "prefix?"),
    ("syn-", "prefix?"),
    ("trans-", "prefix?"),
    ("ultra-", "prefix?"),
    ("un-", "prefix?"),
    ("under-", "prefix?"),
    ("with-", "prefix?"),
    # Words that look semantically wrong
    ("ad-", "should be 'approbate', not prefix key"),
    ("comb--com-", "nonsense key from OCR/formula line"),
]

ghost_entries = []
for key in entries:
    if key.endswith("-") and key not in {"counter"}:
        ghost_entries.append((key, entries[key], "hyphenated key (likely prefix, not word)"))
    if key in {"byss", "chromat", "comb--com-"}:
        ghost_entries.append((key, entries[key], "extracted from WITHIN decomposition text"))

print(f"Found {len(ghost_entries)} suspected ghost entries (hyphenated keys or known extraction errors):")
for key, val, reason in ghost_entries[:30]:
    print(f"  [{key}] → {val[:60]} | {reason}")

# -------------------------------------------------------
# BUG 2: Decompositions that don't match their word
# -------------------------------------------------------
print(f"\n=== BUG 分析 2: 拆解與單字不匹配 ===")
mismatches = []

# Check: atom → "a- (not) + typical (典型的)" — "typical" is wrong
known_wrong = {
    "atom": "應為 a-(not) + tom(cut)，非 typical",
    "accumulate": "應為 ad-(to) + cumul(heap) + -ate，非 custom",
    "archangel": "應為 arch-(chief) + angel，非 bishop = 主教",
    "advance": "adv- = ab-(from) + ance(before) 存疑(ab- from 非正統分析)",
    "abbreviate": "brev 拼成 hrief，OCR 錯誤",
    "accelerate": "ac--ad- 雙 dash，格式錯誤",
    "accost": "ec- 應為 ac- ( OCR 錯誤)，機骨→肋骨",
    "acknowledge": "使用 em dash (–) 而非 regular dash",
    "alloy": "allude 的拆解混入 alloy (alloy ≠ al+lude)",
    "bene-": "key 是字根 'bene-'，非完整單字",
    "ambi-": "key 是字首，非完整單字",
    "amb-": "key 是字首變體",
    "comb--com-": "來自 OCR 殘留公式行，非有效單字",
    "ob--": "雙連字號，OCR 錯誤",
    "bel": "應為 embellish，誤取 fragment",
    "emia": "應為 anemia 或 leukemia，誤取 fragment",
    "fari": "來自 nefarious 拆解 fragment，非單字",
    "via": "應為 obvious，誤取部分",
    "struct": "應為 obstruct，誤取部分",
    "enact": "act = 法令 (拆解無字根解釋)",
    "encourage": "en-(in) + croach(to hook) → 這是 encroach 的拆解！",
    "enfold": "en-(in) + gage → 這是 engage 的拆解！",
    "enrich": "roll = 名冊 → 這是 enroll 的拆解！",
    "emharrass": "bar=棒 → 這是 embarrass 的拆解，且拼錯",
    "hyperacidity": "acid - 酸 (無字根拆解，僅釋義)",
    "hyperactive": "active - 活動的 (無字根拆解)",
    "hypersensitive": "sensitive = 敏感的 (無拆解)",
    "hypertension": "tension = 張力 (無拆解)",
    "hypotension": "tension=壓力 (無拆解)",
    "foredoom": "doom = 命運 (無拆解)",
    "counterattack": "attack = 攻擊 (無拆解)",
    "countermeasure": "measure = 手段 (無拆解)",
    "newclassicism": "classicism - 古典主義 (無拆解)",
    "neocolonialism": "colonialism - 殖民主義 (無拆解)",
    "neofascism": "fascism - 法西斯主義 (無拆解)",
    "neoimpressionism": "impressionism - 印象主義 (無拆解)",
    "macrometeorology": "engineering = 工程學 (完全無關的拆解！)",
    "macromolecule": "molecule = 分子 (無拆解)",
    "microbiology": "biology = 生物學 (無拆解)",
    "microeconomics": "economics = 經濟學 (無拆解)",
    "misapply": "apprehend = 了解 (完全錯誤的拆解)",
    "misarrange": "behave = 行為 (完全錯誤的拆解)",
    "mischief": "conduct = 行為 (錯誤拆解)",
    "misplace": "pronounce - 發音 (錯誤拆解)",
    "escape": "cape = 無袖的短外套 (無字根解釋)",
    "vapor": "應為 evaporate，key 只有 vapor (半個字)",
    "spend": "應為 dispend/dispense 拆解，非 spend",
    "stain": "應為 distain 拆解，非 stain",
    "neuter": "ne- + uter 拆解應屬 neuter 本身但 uther 拼錯",
    "exit": "it(togs) → it(goes) 的 OCR 錯誤",
    "inbeing": "in-(into)·breathe(呼吸) → key 與 decompose 不一致",
    "inaccessible": "僅 in + accessible，無深層拆解",
    "infamous": "in- (not) + nutrition → nutrition 應為 famous!",
    "invulnerable": "en- = in- (not) + em (friend) → 應為 in- + vulnerable!",
    "intra-school": "intra-(within) + ven(vein) → key 是 intra-school 但拆解是 intravenous!",
    "intellect": "inter-(between) + lect → 應為 intel-(inter-) + lect",
    "entertain": "inter- = inter-(between) + tain → key 是 entertain 但拆解寫 inter-",
    "eloquent": "e-ex-(out) + lope(to run) → 這是 elope 的拆解！",
    "habit": "in-(into) + ject → 這是 inject 的拆解！",
    "implant": "im-(in) + ple(fill) + -ment → 這是 implement 的拆解！",
    "microscope": "wave = 波 → 這是 microwave 的拆解！",
    "inherit": "in-(in) + hibit(to have) → 這是 inhibit 的拆解!",
    "pentachord": "pentagen(five) + gon(angle) → 這是五角形 pentagon 拆解!",
    "pentarchy": "went = penta-(five) → 這是 pentarchy 拆解但 went 是誤植",
    "hexad": "hexa-(six) + gon(angle) → 這是 hexagon 拆解!",
    "hexangular": "hexa-(six) + pod(foot) → 這是 hexapod 拆解!",
    "hemicycle": "hemi-(half) + sphere → 這是 hemisphere 拆解!",
    "decade": "deca-(ten) + gon(angle) → 這是 decagon 拆解!",
    "dodecagon": "do- = duo-(two) + zen(ten) → 這是 dozen 拆解!",
    "duodecimal": "duo-(two) + decimal → 正確，但非標準拆解格式",
    "double": "dou- = duo-(two) + -ble(to fold) → 合理但非標準",
    "dual": "du-(two) + -al → 合理但過度拆解",
}

for key, reason in known_wrong.items():
    if key in entries:
        mismatches.append((key, entries[key][:80], reason))

print(f"Known problematic entries: {len(mismatches)}")
for key, val, reason in mismatches[:40]:
    print(f"  [{key}] → {val} | {reason}")

# -------------------------------------------------------
# BUG 3: Check for entries where word IS in decomposition text (self-referential loop)
# -------------------------------------------------------
print(f"\n=== BUG 分析 3: 拆解中出現 OCR/格式錯誤 ===")
ocr_errors = []
for key, val in entries.items():
    # Check for common OCR errors
    if "10" in val and not val.startswith("dec") and "ten" not in val.lower():
        # "10" is likely OCR misread of "to"
        if re.search(r'\(10\b', val) or re.search(r'\b10\b', val):
            ocr_errors.append((key, val, "OCR: '10' 應為 'to'"))
    if "機骨" in val:
        ocr_errors.append((key, val, "OCR: '機骨' 應為 '肋骨'"))
    if "hrief" in val.lower():
        ocr_errors.append((key, val, "OCR: 'hrief' 應為 'brief'"))
    if "剝谷" in val:
        ocr_errors.append((key, val, "OCR: '剝谷' 應為 '剝奪'"))
    if re.search(r'[a-z]--[a-z]', val):
        ocr_errors.append((key, val, "OCR: 雙連字號 (--)"))

print(f"OCR/格式錯誤: {len(ocr_errors)}")
for key, val, reason in ocr_errors[:20]:
    print(f"  [{key}] → {val[:60]} | {reason}")

# -------------------------------------------------------
# BUG 4: Missing entries - words in source with decompositions
# that were NOT extracted (e.g., abyss)
# -------------------------------------------------------
print(f"\n=== BUG 分析 4: 抽樣交叉比對 (從原始語料庫中取樣) ===")

# Let's read the source files and find all 《...》 decompositions
all_source_decomps = {}
word_decomp_pairs = []

SKIP_NAME_PARTS = ("index", "front_matter", "usage", "appendix")
WORD_LINE_RE = re.compile(
    r"(?<![A-Za-z])"
    r"(?P<word>[A-Za-z][A-Za-z'\-]{2,}(?:/[A-Za-z][A-Za-z'\-]{2,})?)"
    r"(?:\s*(?P<pron>\[[^\]\n]{2,80}\]|\([^\)\n]{2,80}\))\s*)"
)
DECOMP_RE = re.compile(r"《([^》]+)》")

for path in sorted(CORPUS_DIR.rglob("*.md")):
    lowered_name = path.name.lower()
    if any(skip in lowered_name for skip in SKIP_NAME_PARTS):
        continue
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        continue
    
    i = 0
    while i < len(lines):
        raw = lines[i].strip()
        if not raw or raw.startswith(("#", "*", "|", "```", "$$")):
            i += 1
            continue
        
        # Find decompositions
        decomps = DECOMP_RE.findall(raw)
        
        if decomps:
            # Look backwards for the nearest word entry
            # (max 5 lines back, since decompositions are usually right after)
            found_word = None
            j = i - 1
            while j >= max(0, i-6):
                prev_raw = lines[j].strip()
                if prev_raw and not prev_raw.startswith(("#", "```")):
                    prev_clean = re.sub(r"\$\$[^$]+\$\$", " ", prev_raw)
                    prev_clean = re.sub(r"<[^>]+>", " ", prev_clean)
                    prev_clean = re.sub(r"\s+", " ", prev_clean).strip()
                    wm = WORD_LINE_RE.search(prev_clean)
                    if wm:
                        found_word = wm.group("word").strip(".,;:()[]").lower()
                        break
                j -= 1
            
            # Also check current line for inline word
            wm = WORD_LINE_RE.search(raw)
            if wm:
                found_word = wm.group("word").strip(".,;:()[]").lower()
            
            if found_word:
                for d in decomps:
                    if not d.startswith("解說") and not d.startswith("參照"):
                        d_clean = d.strip()
                        d_clean = re.sub(r"\s*cf\..*$", "", d_clean).strip()
                        d_clean = re.sub(r"\s*參照.*$", "", d_clean).strip()
                        word_decomp_pairs.append((found_word, d_clean))
                        if found_word not in all_source_decomps:
                            all_source_decomps[found_word] = d_clean
        i += 1

print(f"Source decompositions found: {len(word_decomp_pairs)}")
print(f"Unique words with decomps in source: {len(all_source_decomps)}")

# Check which source entries are MISSING from the JSON
missing = {}
for word, decomp in all_source_decomps.items():
    if word not in entries:
        missing[word] = decomp

print(f"Words in source but MISSING from JSON: {len(missing)}")
for word, decomp in list(missing.items())[:30]:
    print(f"  [{word}] → {decomp[:60]}")

# Check which JSON entries are NOT in the source
extra = {}
for word, decomp in entries.items():
    if word not in all_source_decomps:
        extra[word] = decomp

print(f"\nWords in JSON but NOT in source (possibly propagated from nearby lines): {len(extra)}")
for word, decomp in list(extra.items())[:30]:
    print(f"  [{word}] → {decomp[:60]}")

# -------------------------------------------------------
# RANDOM SPOT CHECK: 20 random entries
# -------------------------------------------------------
print(f"\n=== 隨機抽樣 20 筆交叉比對 ===")
sample_keys = random.sample(list(entries.keys()), min(20, len(entries)))
correct = 0
incorrect = 0
for key in sample_keys:
    json_decomp = entries[key]
    source_decomp = all_source_decomps.get(key, "NOT IN SOURCE")
    status = "✓" if json_decomp == source_decomp else "✗"
    if json_decomp == source_decomp:
        correct += 1
    else:
        incorrect += 1
    print(f"  {status} [{key}]")
    print(f"     JSON: {json_decomp[:80]}")
    print(f"   SOURCE: {source_decomp[:80] if source_decomp != 'NOT IN SOURCE' else 'NOT FOUND'}")

print(f"\nRandom spot check: {correct} correct, {incorrect} incorrect out of {len(sample_keys)}")

# -------------------------------------------------------
# FINAL SUMMARY
# -------------------------------------------------------
print(f"\n{'='*60}")
print(f"=== 最終摘要 ===")
print(f"JSON total entries: {len(entries)}")
print(f"Source total unique decomps: {len(all_source_decomps)}")
print(f"Missing from JSON: {len(missing)}")
print(f"Extra in JSON (not in source): {len(extra)}")
print(f"Ghost entries (hyphenated/non-word keys): {len(ghost_entries)}")
print(f"Known wrong decompositions: {len(mismatches)}")
print(f"OCR errors: {len(ocr_errors)}")
print(f"Random spot check: {correct}/{len(sample_keys)} correct")