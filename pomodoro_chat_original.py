#!/usr/bin/env python3
"""
pomodoro_chat_original.py

Script-only replacement for the original "Pomodoro Chat" LLM cron prompt.
No model calls. stdout/direct delivery is the Discord micro-card.

Original behavior encoded:
- Cron runs hourly on the hour, 06:00~18:00.
- Always output a Telegram message when triggered in that window.
- Hourly broadcast keeps a fixed four-line first-principles card:
  字（可拆解單字）/ 行（現在唯一小步）/ 時（Gooday 宜忌）/ 勢（卦象決策護欄）.
- Add a 90-minute rhythm annotation aligned to the 06:00~18:00 workday:
  06:00, 07:30, 09:00, 10:30, 12:00, 13:30, 15:00, 16:30, 18:00.
  Because cron fires hourly, whole-hour broadcasts show the current/next
  90-minute checkpoint instead of creating extra half-hour jobs.
- Traditional Chinese, compact, life-oriented, and decision-oriented.
- The chat line uses Gooday goodaytw.com day/hour 宜忌 when reachable.
- The next-step line uses a one-shot system-random I Ching reference; it is
  symbolic guidance only, not a prediction.
- Add one zero-token vocabulary line sampled from the archived 英文字根 .md corpus.
- Vocabulary is persisted: no repeated word card inside a cycle; after all cards
  are used, a new cycle begins automatically.

Inspection / reverse lookup:
  python pomodoro_chat_original.py --vocab-status
  python pomodoro_chat_original.py --list-total 20
  python pomodoro_chat_original.py --list-seen 20
  python pomodoro_chat_original.py --lookup moneyed

Manual testing:
  python pomodoro_chat_original.py --at 09:00
  python pomodoro_chat_original.py --at 10:00
  # Manual tests do NOT consume words unless --consume is passed.

Cron-run test hook:
  Write JSON to %LOCALAPPDATA%/hermes/pomodoro_chat_force_once.json:
    {"time":"09:00", "label":"測試"}
  The script consumes the file once, uses that time, prints a test-prefixed
  message, then deletes the file. Forced tests do NOT consume words unless
  --consume is also passed manually.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_lib
import json
import os
import random
import re
import secrets
import sys
import urllib.request
import time as time_module
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

# 曾仕強教授易經六十四卦辭 × 爻辭資料庫（變爻規則依曾仕強體系）
# 需與 pomodoro_iching_data.py 放在同一目錄
import importlib.util
try:
    _iching_spec = importlib.util.spec_from_file_location(
        "pomodoro_iching_data",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_iching_data.py"),
    )
    if _iching_spec is None or _iching_spec.loader is None:
        raise ImportError("pomodoro_iching_data loader unavailable")
    _iching_mod = importlib.util.module_from_spec(_iching_spec)
    _iching_spec.loader.exec_module(_iching_mod)
    _ICHING = _iching_mod
except Exception:
    # Preserve the mandatory four-line card with a neutral symbolic fallback.
    _ICHING = None

try:
    # Windows service / pythonw cron runners occasionally capture CJK+emoji
    # stdout as empty unless the child process configures its own stdio.
    # Keep this in the script, not only in cron.scheduler, so every runner
    # gets deterministic UTF-8 output.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

TZ_TAIPEI = timezone(timedelta(hours=8))

def hermes_home() -> Path:
    """Resolve the base data directory.

    Priority:
    1. POMODORO_DATA_DIR env var (for portable deployment)
    2. LOCALAPPDATA\\hermes (Windows, the default)
    3. ~/AppData/Local/hermes (fallback)
    """
    override = os.environ.get("POMODORO_DATA_DIR")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "hermes"
    return Path.home() / "AppData" / "Local" / "hermes"


def vocab_data_dir() -> Path:
    return hermes_home() / "data"
GOODAY_URL = "https://www.goodaytw.com/"
GOODAY_TIMEOUT_SECONDS = 18
GOODAY_CACHE_VERSION = 1

BRANCH_BY_TIME = [
    (23, 1, "子"), (1, 3, "丑"), (3, 5, "寅"), (5, 7, "卯"),
    (7, 9, "辰"), (9, 11, "巳"), (11, 13, "午"), (13, 15, "未"),
    (15, 17, "申"), (17, 19, "酉"), (19, 21, "戌"), (21, 23, "亥"),
]
BRANCHES = set("子丑寅卯辰巳午未申酉戌亥")

TRIGRAM_BY_LINES = {
    (True, True, True): {"name": "乾", "image": "天", "action": "主動，但先定邊界"},
    (True, True, False): {"name": "兌", "image": "澤", "action": "溝通收斂，避免口頭承諾失控"},
    (True, False, True): {"name": "離", "image": "火", "action": "看清證據，先照亮關鍵處"},
    (True, False, False): {"name": "震", "image": "雷", "action": "先動一小步，不要被驚動帶著跑"},
    (False, True, True): {"name": "巽", "image": "風", "action": "滲透推進，用小修正累積"},
    (False, True, False): {"name": "坎", "image": "水", "action": "先控風險，避開硬闖"},
    (False, False, True): {"name": "艮", "image": "山", "action": "先停一下，切清界線"},
    (False, False, False): {"name": "坤", "image": "地", "action": "承接整理，先把基礎鋪穩"},
}
TRIGRAM_ORDER = ["乾", "兌", "離", "震", "巽", "坎", "艮", "坤"]
KING_WEN_MATRIX = {
    "乾": {"乾": 1, "兌": 43, "離": 14, "震": 34, "巽": 9, "坎": 5, "艮": 26, "坤": 11},
    "兌": {"乾": 10, "兌": 58, "離": 38, "震": 54, "巽": 61, "坎": 60, "艮": 41, "坤": 19},
    "離": {"乾": 13, "兌": 49, "離": 30, "震": 55, "巽": 37, "坎": 63, "艮": 22, "坤": 36},
    "震": {"乾": 25, "兌": 17, "離": 21, "震": 51, "巽": 42, "坎": 3, "艮": 27, "坤": 24},
    "巽": {"乾": 44, "兌": 28, "離": 50, "震": 32, "巽": 57, "坎": 48, "艮": 18, "坤": 46},
    "坎": {"乾": 6, "兌": 47, "離": 64, "震": 40, "巽": 59, "坎": 29, "艮": 4, "坤": 7},
    "艮": {"乾": 33, "兌": 31, "離": 56, "震": 62, "巽": 53, "坎": 39, "艮": 52, "坤": 15},
    "坤": {"乾": 12, "兌": 45, "離": 35, "震": 16, "巽": 20, "坎": 8, "艮": 23, "坤": 2},
}
HEXAGRAM_NAMES = {
    1: "乾為天", 2: "坤為地", 3: "水雷屯", 4: "山水蒙", 5: "水天需", 6: "天水訟",
    7: "地水師", 8: "水地比", 9: "風天小畜", 10: "天澤履", 11: "地天泰", 12: "天地否",
    13: "天火同人", 14: "火天大有", 15: "地山謙", 16: "雷地豫", 17: "澤雷隨", 18: "山風蠱",
    19: "地澤臨", 20: "風地觀", 21: "火雷噬嗑", 22: "山火賁", 23: "山地剝", 24: "地雷復",
    25: "天雷無妄", 26: "山天大畜", 27: "山雷頤", 28: "澤風大過", 29: "坎為水", 30: "離為火",
    31: "澤山咸", 32: "雷風恆", 33: "天山遯", 34: "雷天大壯", 35: "火地晉", 36: "地火明夷",
    37: "風火家人", 38: "火澤睽", 39: "水山蹇", 40: "雷水解", 41: "山澤損", 42: "風雷益",
    43: "澤天夬", 44: "天風姤", 45: "澤地萃", 46: "地風升", 47: "澤水困", 48: "水風井",
    49: "澤火革", 50: "火風鼎", 51: "震為雷", 52: "艮為山", 53: "風山漸", 54: "雷澤歸妹",
    55: "雷火豐", 56: "火山旅", 57: "巽為風", 58: "兌為澤", 59: "風水渙", 60: "水澤節",
    61: "風澤中孚", 62: "雷山小過", 63: "水火既濟", 64: "火水未濟",
}
HEXAGRAM_HINTS = (
    {n: data["judgment"] for n, data in _ICHING.HEXAGRAM_DATA.items()}
    if _ICHING is not None
    else {}
)

BROADCAST_HOURS = set(range(6, 19))  # 06:00~18:00 inclusive
POMODORO_ANCHORS = [
    time(6, 0), time(7, 30), time(9, 0), time(10, 30), time(12, 0),
    time(13, 30), time(15, 0), time(16, 30), time(18, 0),
]

MORNING_ACTIONS = [
    "**確立主線**：喝水、伸展，今天只定一條核心主線。",
    "**啟動儀式**：先顧身體再開工，確認今天第一個最小成果。",
]
WORK_FOCUS_ACTIONS = [
    "**單一交付**：只推一個明確、可驗證的進度；先寫完成標準。",
    "**深度專注**：主線只留一個核心任務；過程留存紀錄與證據。",
]
WORK_CLOSE_ACTIONS = [
    "**收斂停損**：停止擴張；保存進度、記下卡點與下一步。",
    "**交接劃界**：做好進度 closure；範圍寫清楚，不默認超時。",
]
STUDY_FOCUS_ACTIONS = [
    "**拆解任務**：進修只推一題或一小節；釐清已知與未知。",
    "**輸出導向**：讀一頁或做一題；求能回想重點，不求看完。",
]
STUDY_CLOSE_ACTIONS = [
    "**保存狀態**：停止開新章；標記卡點與下回入口，方便重啟。",
    "**收斂筆記**：收攏成一個可複習單位；工具不搶走學習主線。",
]
LUNCH_ACTIONS = [
    "**離屏休息**：先吃飯、離屏走動；休息是為了走更長。",
    "**肩頸放鬆**：午休補足能量；下午只重啟一條最優先主線。",
]
DAY_END_ACTIONS = [
    "**清空大腦**：記下完成與明天第一步後停工；保留精力給自己。",
    "**關閉主線**：保存進度，留一句下一步；不把壓力拖進晚上。",
]

VOCAB_DIR = hermes_home() / "data" / "vocab_corpus"
VOCAB_SKIP_NAME_PARTS = ("index", "front_matter", "usage")
VOCAB_BAD_WORDS = {
    "adj", "adv", "prep", "pron", "conj", "interj", "noun", "verb",
    "latin", "greek", "english", "suffix", "prefix", "root",
}
VOCAB_DISPLAY_BLOCKLIST = {
    # Quarantine known damaged OCR entries from hourly delivery. They remain
    # searchable with --lookup until the source dictionary is repaired.
    "abnegate", "antobiography", "consent", "debark", "diatrics", "mju",
    "neofascism", "renegade", "subscribe",
}
VOCAB_GLOSS_OCR_NOISE_RE = re.compile(r"版教|問意|發陸|四政|法四斯")
VOCAB_PRON_FORBIDDEN_RE = re.compile(r"\d|<[^>]+>|�|\\[A-Za-z]+|[$《》]")
VOCAB_DECOMP_FORBIDDEN_RE = re.compile(
    r"<[^>]+>|�|\\[A-Za-z]+|\$|\b(?:adj|adv|prep|pron|conj|interj|noun|verb|n|v)\."
)
VOCAB_DECOMP_IPA_RE = re.compile(r"\[[^\]]*[ˈˌəɪʊʌɛɔɑɜθðʃʒŋ][^\]]*\]")
VOCAB_STATE_VERSION = 3
VOCAB_ENTRY_RE = re.compile(
    r"(?<![A-Za-z])"
    r"(?P<word>[A-Za-z][A-Za-z'\-]{2,}(?:/[A-Za-z][A-Za-z'\-]{2,})?)"
    r"(?:\s*(?P<pron>\[[^\]\n]{2,80}\]|\([^\)\n]{2,80}\))\s*|\s+)"
    r"(?P<pos>(?:adj|adv|n|v|prep|pron|conj|interj)\.?(?:\s*,\s*(?:adj|adv|n|v)\.?)*)"
    r"\s+"
    r"(?P<gloss>.{1,180}?)"
    r"(?=(?:\s+[A-Za-z][A-Za-z'\-]{2,}(?:/[A-Za-z][A-Za-z'\-]{2,})?"
    r"(?:\s*(?:\[[^\]\n]{2,80}\]|\([^\)\n]{2,80}\))\s*|\s+)"
    r"(?:adj|adv|n|v|prep|pron|conj|interj)\.?)|$)",
    re.IGNORECASE,
)

# 劉毅/學習出版社 英文字根拆解映射（惰性載入）
_DECOMP_MAP: dict[str, str] | None = None


def verified_decomp_entries(data: dict[str, Any]) -> dict[str, str]:
    """Expose only v4 source-backed entries; unverified auto splits stay out."""
    if data.get("version") != 4:
        return {}
    entries = data.get("entries") or {}
    provenance = data.get("provenance") or {}
    return {
        word: decomposition
        for word, decomposition in entries.items()
        if isinstance(word, str)
        and isinstance(decomposition, str)
        and (provenance.get(word) or {}).get("validation")
        == "source-backed+morpheme-match"
    }


def _load_decomp_map() -> dict[str, str]:
    global _DECOMP_MAP
    if _DECOMP_MAP is not None:
        return _DECOMP_MAP
    path = vocab_data_dir() / "vocab_decomposition.json"
    if not path.exists():
        _DECOMP_MAP = {}
        return _DECOMP_MAP
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _DECOMP_MAP = verified_decomp_entries(data)
    except Exception:
        _DECOMP_MAP = {}
    return _DECOMP_MAP


def force_file() -> Path:
    return hermes_home() / "pomodoro_chat_force_once.json"


def vocab_state_path() -> Path:
    override = os.environ.get("POMODORO_VOCAB_STATE")
    if override:
        return Path(override)
    # Keep state under Hermes local data so it survives workspace migrations
    return hermes_home() / "data" / "pomodoro_vocab_state.json"


def vocab_lock_path() -> Path:
    return vocab_state_path().with_suffix(".lock")


@contextmanager
def vocab_state_lock(timeout_seconds: float = 5.0):
    """Cross-process lock for the state load → reserve → save transaction."""
    path = vocab_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    if path.stat().st_size == 0:
        handle.write(b"0")
        handle.flush()

    locked = False
    deadline = time_module.monotonic() + timeout_seconds
    try:
        while not locked:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError:
                if time_module.monotonic() >= deadline:
                    raise TimeoutError(f"vocabulary state lock timeout: {path}")
                time_module.sleep(0.05)
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def parse_hhmm(value: str) -> tuple[int, int]:
    try:
        h_s, m_s = value.strip().split(":", 1)
        h, m = int(h_s), int(m_s)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except Exception as exc:
        raise argparse.ArgumentTypeError(f"invalid HH:MM: {value!r}") from exc


def load_forced_time() -> tuple[tuple[int, int] | None, str | None]:
    path = force_file()
    if not path.exists():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        forced = parse_hhmm(str(data.get("time", "09:00")))
        label = str(data.get("label", "測試"))
        return forced, label
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def minutes_of(t: time) -> int:
    return t.hour * 60 + t.minute


def format_clock(total_minutes: int) -> str:
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def pomodoro_anchor_minutes() -> list[int]:
    return [minutes_of(anchor) for anchor in POMODORO_ANCHORS]


def rhythm_mode_and_action(dt: datetime, phase: str) -> tuple[str, str]:
    """Return one life-context action; symbolic lines never override this line."""
    date_key = dt.strftime("%Y-%m-%d")
    if dt.hour <= 7:
        mode, pool = "生活", MORNING_ACTIONS
    elif dt.hour == 12:
        mode, pool = "午休", LUNCH_ACTIONS
    elif dt.hour >= 17:
        mode, pool = "收工", DAY_END_ACTIONS
    elif dt.weekday() < 5:
        mode = "工作"
        pool = WORK_CLOSE_ACTIONS if phase == "close" else WORK_FOCUS_ACTIONS
    else:
        mode = "先修"
        pool = STUDY_CLOSE_ACTIONS if phase == "close" else STUDY_FOCUS_ACTIONS
    action = choose(pool, f"life-action:{date_key}:{dt.hour}:{phase}")
    return mode, action


def build_rhythm_line(dt: datetime) -> str:
    """Annotate the hourly cron message with unified segment-based counters.

    The day is divided into 8 × 90-minute segments between 9 anchors
    (06:00, 07:30, 09:00, 10:30, 12:00, 13:30, 15:00, 16:30, 18:00).
    Cron fires on the hour, so most segments get 1-2 cards:
      - Segment-start card → "{mode} S{seg}/8"
      - Wrapping card → "{mode} S{seg}/8 收尾"
    This eliminates the N/9 vs N/90m vs 收尾 Nm inconsistency.
    """
    current = dt.hour * 60 + dt.minute
    anchors = pomodoro_anchor_minutes()
    first, last = anchors[0], anchors[-1]
    if current < first or current > last:
        return ""

    # 8 segments between 9 anchors (indices 0-7)
    for i in range(len(anchors) - 1):
        if anchors[i] <= current < anchors[i + 1]:
            seg = i  # 0-based segment number
            break
    else:
        # current == last (18:00)
        mode, action = rhythm_mode_and_action(dt, "final")
        return f"｜行｜{format_clock(current)}｜完成｜{action}"

    prev_anchor = anchors[seg]
    next_anchor = anchors[seg + 1]
    remaining = next_anchor - current
    elapsed = current - prev_anchor
    prev_label = format_clock(prev_anchor)
    next_label = format_clock(next_anchor)

    seg_display = f"S{seg + 1}/8"

    if current == prev_anchor:
        # Segment-start anchor (e.g. 06:00, 09:00, 12:00, 15:00)
        phase = "start"
        closing = ""
    elif remaining <= 30:
        # Last 30 min of segment → wrap-up
        phase = "close"
        closing = " 收尾"
    else:
        # Middle of segment
        phase = "mid"
        closing = ""

    # Use segment midpoint for mode determination, so opener and closer
    # of same segment share the same mode label. This corrects S5 (午休)
    # wrapping into 工作 and S8 (收工) starting as 工作.
    mid_pt = (prev_anchor + next_anchor) // 2
    mid_dt = dt.replace(hour=mid_pt // 60, minute=mid_pt % 60)
    mode, action = rhythm_mode_and_action(mid_dt, phase)
    return f"｜行｜{prev_label}→{next_label}｜{mode} {seg_display}{closing}｜{action}"


def choose(pool: list[str], seed: str) -> str:
    rng = random.Random(seed)
    return rng.choice(pool)


def has_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def clean_vocab_text(value: str) -> str:
    value = value.replace("\\n", " ")
    value = re.sub(r"[`*_#>]+", "", value)
    value = re.sub(r"\$+", "", value)
    value = re.sub(r"\\[a-zA-Z]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def compact_gloss(gloss: str, max_chars: int = 46) -> str:
    gloss = clean_vocab_text(gloss)
    gloss = re.split(r"\s+[A-Za-z][A-Za-z'\-]{2,}\s*(?:\[|\()", gloss, maxsplit=1)[0]
    gloss = re.sub(r"\s*(?:cf\.|參照|詳見).*", "", gloss, flags=re.IGNORECASE)
    gloss = re.sub(r"《.*?》", "", gloss)
    gloss = re.sub(r"《.*$", "", gloss)
    gloss = re.sub(r"\([^\u4e00-\u9fff)]{1,80}\)", "", gloss)
    gloss = gloss.strip(" ;；,，。")

    if len(gloss) <= max_chars:
        return gloss

    parts = [part.strip() for part in re.split(r"[;；,，]", gloss) if part.strip()]
    if not parts:
        return gloss[:max_chars].rstrip() + "…"

    selected: list[str] = []
    for part in parts:
        trial = "；".join(selected + [part])
        if len(trial) > max_chars:
            break
        selected.append(part)
        if len(selected) >= 3:
            break
    return ("；".join(selected) if selected else parts[0][:max_chars]).rstrip("；")


def source_label(path: Path) -> str:
    label = path.stem.replace("英文字根_", "").replace("_fixed", "")
    return label.replace("_", " ")


def stable_vocab_id(word: str, pron: str, pos: str, gloss: str, source: str) -> str:
    raw = f"{word}\t{pron}\t{pos}\t{gloss}\t{source}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


_VOCAB_ENTRIES_CACHE: list[dict[str, str]] | None = None


def load_vocab_entries() -> list[dict[str, str]]:
    """Parse archived 英文字根 markdown into lightweight word cards.

    Failure is intentionally non-fatal: Pomodoro delivery should never break
    just because the archive path moved or one OCR line is malformed.
    """
    global _VOCAB_ENTRIES_CACHE
    if _VOCAB_ENTRIES_CACHE is not None:
        return _VOCAB_ENTRIES_CACHE

    if not VOCAB_DIR.exists():
        return []

    entries: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for path in sorted(VOCAB_DIR.rglob("*.md")):
        lowered = path.name.lower()
        if any(part in lowered for part in VOCAB_SKIP_NAME_PARTS):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for raw in lines:
            stripped = raw.strip()
            if not stripped or stripped.startswith(("#", "*", "|", "```")):
                continue
            line = clean_vocab_text(stripped)
            if not line:
                continue

            for match in VOCAB_ENTRY_RE.finditer(line):
                word = match.group("word").strip(".,;:()[]").lower()
                pron = (match.group("pron") or "").strip()
                pos = match.group("pos").strip().rstrip(".")
                if len(word) < 3 or word in VOCAB_BAD_WORDS or not pron:
                    continue

                gloss = compact_gloss(match.group("gloss"))
                if not gloss or not has_cjk(gloss):
                    continue

                source = source_label(path)
                key = (word, pron, gloss)
                if key in seen:
                    continue
                seen.add(key)

                entry_id = stable_vocab_id(word, pron, pos, gloss, source)
                entries.append({
                    "id": entry_id,
                    "word": word,
                    "pron": pron,
                    "pos": pos,
                    "gloss": gloss,
                    "source": source,
                })

    entries.sort(key=lambda e: (e["word"], e["source"], e["id"]))
    _VOCAB_ENTRIES_CACHE = entries
    return entries


def pronunciation_is_usable(value: str) -> bool:
    inner = value.strip().strip("[]()")
    if not inner or has_cjk(inner) or VOCAB_PRON_FORBIDDEN_RE.search(value):
        return False
    # Plain OCR romanization such as "ad maia" is not a useful pronunciation.
    return re.fullmatch(r"[A-Za-z\s'.,;:\-]+", inner) is None


def decomposition_matches_word(word: str, decomposition: str) -> bool:
    """Reject obvious cross-entry spills such as misplace→pronounce."""
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


def decomposition_is_structured(decomposition: str) -> bool:
    if "+" in decomposition or "(" in decomposition:
        return True
    if "=" in decomposition:
        right = decomposition.rsplit("=", 1)[-1].strip()
        if has_cjk(right):
            return True
        return bool(re.findall(r"[A-Za-z]{4,}", right))
    return "-" in decomposition


def eligible_vocab_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep the hourly card focused on useful, non-damaged words from the 7000 common words corpus."""
    decomp_map = _load_decomp_map()
    canonical: dict[str, dict[str, str]] = {}
    for entry in entries:
        word = entry["word"].lower()
        if word in VOCAB_DISPLAY_BLOCKLIST or word in canonical:
            continue
        pron = entry.get("pron", "")
        gloss = entry.get("gloss", "")
        if not pronunciation_is_usable(pron) or VOCAB_GLOSS_OCR_NOISE_RE.search(gloss) or "+" in gloss:
            continue
        decomp = decomp_map.get(word, "")
        # Run quality gates ONLY if decomposition exists (decompositions are optional now)
        if decomp:
            if VOCAB_DECOMP_FORBIDDEN_RE.search(decomp) or VOCAB_DECOMP_IPA_RE.search(decomp):
                continue
            if decomp.count("《") != decomp.count("》"):
                continue
            if not decomposition_matches_word(word, decomp):
                continue
            if not decomposition_is_structured(decomp):
                continue
        item = dict(entry)
        item["decomp"] = decomp
        canonical[word] = item
    return list(canonical.values())


def corpus_signature(entries: list[dict[str, str]]) -> str:
    joined = "\n".join(entry["id"] for entry in entries)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def default_vocab_state(now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(TZ_TAIPEI)
    iso = now.isoformat(timespec="seconds")
    return {
        "version": VOCAB_STATE_VERSION,
        "cycle": 1,
        "cycle_started_at": iso,
        "cycle_seen_ids": [],
        "history": [],
        "last_entry_id": None,
        "last_broadcast_at": None,
        "slot_reservations": {},
        "daily_casts": {},
        "updated_at": iso,
        "corpus_signature": None,
    }


def load_vocab_state(entries: list[dict[str, str]] | None = None) -> dict[str, Any]:
    path = vocab_state_path()
    if not path.exists():
        return default_vocab_state()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default_vocab_state()

    if not isinstance(state, dict):
        return default_vocab_state()

    # Backward-compatible normalization for hand-edited or older state files.
    state.setdefault("version", VOCAB_STATE_VERSION)
    state.setdefault("cycle", 1)
    state.setdefault("cycle_started_at", datetime.now(TZ_TAIPEI).isoformat(timespec="seconds"))
    state.setdefault("cycle_seen_ids", [])
    state.setdefault("history", [])
    state.setdefault("last_entry_id", None)
    state.setdefault("last_broadcast_at", None)
    state.setdefault("slot_reservations", {})
    state.setdefault("daily_casts", {})
    state.setdefault("updated_at", None)
    state.setdefault("corpus_signature", None)

    if entries is not None:
        valid = {entry["id"] for entry in entries}
        state["cycle_seen_ids"] = [eid for eid in state.get("cycle_seen_ids", []) if eid in valid]
        # Keep historical snapshots even if the corpus changes; reverse lookup still benefits.
    return state


def save_vocab_state(state: dict[str, Any]) -> None:
    path = vocab_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state["version"] = VOCAB_STATE_VERSION
    state["updated_at"] = datetime.now(TZ_TAIPEI).isoformat(timespec="seconds")
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def history_stats(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for item in state.get("history", []):
        entry_id = item.get("id")
        if not entry_id:
            continue
        slot = stats.setdefault(entry_id, {"count": 0, "last_seen_at": None, "cycles": []})
        slot["count"] += 1
        if item.get("broadcasted_at"):
            slot["last_seen_at"] = item["broadcasted_at"]
        if item.get("cycle") not in slot["cycles"]:
            slot["cycles"].append(item.get("cycle"))
    return stats


def mark_entry_seen(state: dict[str, Any], entry: dict[str, str], dt: datetime, total: int) -> None:
    entry_id = entry["id"]
    if entry_id not in state["cycle_seen_ids"]:
        state["cycle_seen_ids"].append(entry_id)
    state["last_entry_id"] = entry_id
    state["last_broadcast_at"] = dt.isoformat(timespec="seconds")
    state.setdefault("history", []).append({
        "id": entry_id,
        "word": entry["word"],
        "pron": entry["pron"],
        "pos": entry["pos"],
        "gloss": entry["gloss"],
        "source": entry["source"],
        "cycle": state["cycle"],
        "cycle_index": len(state["cycle_seen_ids"]),
        "cycle_total": total,
        "broadcasted_at": dt.isoformat(timespec="seconds"),
        "time_hhmm": dt.strftime("%H:%M"),
    })


def generate_cast_values() -> list[int]:
    return [sum(secrets.choice((2, 3)) for _ in range(3)) for _ in range(6)]


def _choose_vocab_entry_unlocked(dt: datetime, consume: bool = False) -> dict[str, Any] | None:
    entries = eligible_vocab_entries(load_vocab_entries())
    if not entries:
        return None

    sig = corpus_signature(entries)
    state = load_vocab_state(entries)
    state["corpus_signature"] = sig

    slot_key = dt.strftime("%Y-%m-%dT%H")
    reservations = state.get("slot_reservations")
    if not isinstance(reservations, dict):
        reservations = {}
        state["slot_reservations"] = reservations

    if consume and isinstance(reservations.get(slot_key), dict):
        reservation = reservations[slot_key]
        previous = next((entry for entry in entries if entry["id"] == reservation.get("entry_id")), None)
        values = reservation.get("cast_values")
        if previous and isinstance(values, list) and len(values) == 6:
            item: dict[str, Any] = dict(previous)
            item["_cast_values"] = values
            return item
        reservations.pop(slot_key, None)

    seen_ids = set(state.get("cycle_seen_ids", []))
    remaining = [entry for entry in entries if entry["id"] not in seen_ids]

    if not remaining:
        state["cycle"] = int(state.get("cycle", 1)) + 1
        state["cycle_started_at"] = dt.isoformat(timespec="seconds")
        state["cycle_seen_ids"] = []
        seen_ids = set()
        remaining = entries[:]

    seed = f"vocab-cycle:{state['cycle']}:{len(seen_ids)}:{dt.strftime('%Y-%m-%d-%H')}:{sig}"
    entry = random.Random(seed).choice(remaining)

    if consume:
        daily_casts = state.get("daily_casts")
        if not isinstance(daily_casts, dict):
            daily_casts = {}
            state["daily_casts"] = daily_casts
        cast_values = daily_casts.get(slot_key)
        if (
            not isinstance(cast_values, list)
            or len(cast_values) != 6
            or any(value not in {6, 7, 8, 9} for value in cast_values)
        ):
            cast_values = generate_cast_values()
            daily_casts[slot_key] = cast_values
        for old_slot_key in sorted(daily_casts)[:-96]:
            daily_casts.pop(old_slot_key, None)
        mark_entry_seen(state, entry, dt, total=len(entries))
        reservations[slot_key] = {
            "entry_id": entry["id"],
            "cast_values": cast_values,
            "reserved_at": datetime.now(TZ_TAIPEI).isoformat(timespec="seconds"),
        }
        for old_slot in sorted(reservations)[:-96]:
            reservations.pop(old_slot, None)
        save_vocab_state(state)
        item: dict[str, Any] = dict(entry)
        item["_cast_values"] = cast_values
        return item

    return entry


def choose_vocab_entry(dt: datetime, consume: bool = False) -> dict[str, Any] | None:
    if consume:
        with vocab_state_lock():
            return _choose_vocab_entry_unlocked(dt, consume=True)
    return _choose_vocab_entry_unlocked(dt, consume=False)


def compact_decomposition(value: str, max_chars: int = 50) -> str:
    compact = re.sub(r"\([^)]{2,12}字[尾首]\)", "", value).strip()
    compact = re.sub(r"\s+", " ", compact)
    if len(compact) <= max_chars:
        return compact
    window = compact[: max_chars - 1]
    cuts = [window.rfind(sep) for sep in (" + ", "；", ";", "，", ",", " ")]
    cut = max(cuts)
    if cut < max_chars // 2:
        cut = max_chars - 1
    return window[:cut].rstrip(" +；;,，") + "…"


def format_vocab_line(entry: dict[str, str]) -> str:
    pron = f" {entry['pron']}" if entry.get("pron") else ""
    pos = f"{entry['pos']}." if entry.get("pos") else ""
    # Etymology decomposition removed per user request — only word, pronunciation, part of speech, definition.
    return f"｜字｜{entry['word']}{pron}｜{pos} {entry['gloss']}"


def build_vocab_line(dt: datetime, consume: bool = False) -> str:
    entry = choose_vocab_entry(dt, consume=consume)
    if not entry:
        return "｜字｜字根資料暫取不到"
    return format_vocab_line(entry)


def reserved_cast_values(dt: datetime) -> list[int] | None:
    with vocab_state_lock():
        state = load_vocab_state()
        reservations = state.get("slot_reservations", {})
        reservation = (
            reservations.get(dt.strftime("%Y-%m-%dT%H"), {})
            if isinstance(reservations, dict)
            else {}
        )
        values = reservation.get("cast_values") if isinstance(reservation, dict) else None
        if isinstance(values, list) and len(values) == 6 and all(value in {6, 7, 8, 9} for value in values):
            return list(values)
    return None


def gooday_cache_path() -> Path:
    return vocab_data_dir() / "gooday_almanac_cache.json"


def html_to_lines(raw_html: str) -> list[str]:
    """Convert Gooday's rendered HTML into compact visible text lines."""
    text = re.sub(r"<script\b[^>]*>.*?</script>", "\n", raw_html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", "\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = text.replace("<!-- -->", "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(?:div|p|li|h\d|span|a|td|th|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = html_lib.unescape(text)
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        # Drop obvious navigation/footer noise but keep one-character branches.
        if line in {"|", "好日網", "聯絡我們"}:
            lines.append(line)
            continue
        lines.append(line)
    return lines


def first_label_value(lines: list[str], label: str, start: int = 0) -> str:
    for idx in range(start, max(len(lines) - 1, 0)):
        if lines[idx] == label:
            return lines[idx + 1]
    return ""


def parse_gooday_hour_blocks(lines: list[str]) -> dict[str, dict[str, str]]:
    blocks: dict[str, dict[str, str]] = {}
    time_re = re.compile(r"^\d{2}:\d{2}$")
    i = 0
    while i < len(lines) - 3:
        if lines[i] in BRANCHES and time_re.match(lines[i + 1]) and lines[i + 2] == "|" and time_re.match(lines[i + 3]):
            branch = lines[i]
            block: dict[str, str] = {"start": lines[i + 1], "end": lines[i + 3]}
            j = i + 4
            while j < len(lines):
                if j < len(lines) - 3 and lines[j] in BRANCHES and time_re.match(lines[j + 1]) and lines[j + 2] == "|" and time_re.match(lines[j + 3]):
                    break
                if lines[j] in {"宜", "忌", "沖", "煞"} and j + 1 < len(lines):
                    block[lines[j]] = lines[j + 1]
                    j += 2
                    continue
                j += 1
            blocks[branch] = block
            i = j
            continue
        i += 1
    return blocks


def valid_gooday_data(data: Any, date_key: str) -> bool:
    if not isinstance(data, dict) or not data.get("ok") or data.get("date") != date_key:
        return False
    hours = data.get("hours")
    if not isinstance(hours, dict) or set(hours) != BRANCHES:
        return False
    if not data.get("day_yi") or not data.get("day_ji"):
        return False
    return all(isinstance(hours.get(branch), dict) for branch in BRANCHES)


def fetch_gooday_almanac(dt: datetime) -> dict[str, Any]:
    """Fetch/cache Gooday day and hour 宜忌 for the Taipei date.

    Gooday renders the current day's almanac in the HTML body. This script runs
    hourly, so cache per date to avoid hammering the site. If the network/parser
    fails, return a soft failure; Pomodoro delivery must still work.
    """
    date_key = dt.strftime("%Y-%m-%d")
    cache_path = gooday_cache_path()
    try:
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            cached_data = cached.get("data", {})
            if cached.get("version") == GOODAY_CACHE_VERSION and valid_gooday_data(cached_data, date_key):
                return cached_data
    except Exception:
        pass

    try:
        req = urllib.request.Request(GOODAY_URL, headers={"User-Agent": "Hermes-Pomodoro/1.0 Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=GOODAY_TIMEOUT_SECONDS) as resp:
            raw_html = resp.read(250_000).decode("utf-8", errors="replace")
    except Exception as exc:
        return {"ok": False, "source": GOODAY_URL, "error": f"fetch {type(exc).__name__}"}

    lines = html_to_lines(raw_html)
    day_yi = first_label_value(lines, "宜")
    day_ji = first_label_value(lines, "忌")
    day_chong = first_label_value(lines, "沖")
    day_sha = first_label_value(lines, "煞")
    hour_blocks = parse_gooday_hour_blocks(lines)
    data = {
        "ok": bool(day_yi or day_ji or hour_blocks),
        "source": GOODAY_URL,
        "date": date_key,
        "day_yi": day_yi or "資料不足",
        "day_ji": day_ji or "資料不足",
        "day_chong": day_chong or "資料不足",
        "day_sha": day_sha or "資料不足",
        "hours": hour_blocks,
        "fetched_at": datetime.now(TZ_TAIPEI).isoformat(timespec="seconds"),
    }
    if valid_gooday_data(data, date_key):
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps({"version": GOODAY_CACHE_VERSION, "date": date_key, "data": data}, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return data


def current_branch(dt: datetime) -> str:
    hour = dt.hour
    for start, end, branch in BRANCH_BY_TIME:
        if start < end and start <= hour < end:
            return branch
        if start > end and (hour >= start or hour < end):
            return branch
    return "?"


def compact_terms(value: str, max_items: int = 4, max_chars: int = 34) -> str:
    value = re.sub(r"\s+", "", value or "")
    if not value:
        return "資料不足"
    if value == "無":
        return "無"
    parts = [part for part in re.split(r"[、,，；;]", value) if part]
    if not parts:
        return value[:max_chars] + ("…" if len(value) > max_chars else "")
    selected = "、".join(parts[:max_items])
    if len(parts) > max_items or len(value) > len(selected):
        selected += "…"
    if len(selected) > max_chars:
        selected = selected[: max_chars - 1].rstrip("、") + "…"
    return selected


def build_almanac_chat_line(dt: datetime, prefix: str = "") -> str:
    almanac = fetch_gooday_almanac(dt)
    if not almanac.get("ok"):
        return f"{prefix}｜時｜Gooday 資料暫取不到｜保守：少開新坑、多留紀錄"

    branch = current_branch(dt)
    hour_info = (almanac.get("hours") or {}).get(branch, {})
    day_yi = compact_terms(str(almanac.get("day_yi", "")), max_items=2, max_chars=18)
    day_ji = compact_terms(str(almanac.get("day_ji", "")), max_items=2, max_chars=18)
    hour_yi = compact_terms(str(hour_info.get("宜", "資料不足")), max_items=2, max_chars=18)
    hour_ji = compact_terms(str(hour_info.get("忌", "資料不足")), max_items=2, max_chars=18)
    chong = almanac.get("day_chong") or "資料不足"
    sha = almanac.get("day_sha") or "資料不足"
    return (
        f"{prefix}｜時｜日宜「{day_yi}」／忌「{day_ji}」｜"
        f"{branch}宜「{hour_yi}」／忌「{hour_ji}」｜沖{chong}·煞{sha}｜現實優先"
    )


def hexagram_no_from_lines(lines: list[bool]) -> int:
    lower = TRIGRAM_BY_LINES[tuple(lines[:3])]["name"]
    upper = TRIGRAM_BY_LINES[tuple(lines[3:])]["name"]
    return KING_WEN_MATRIX[lower][upper]


def hexagram_symbol(number: int) -> str:
    """Return the Unicode Yijing glyph in King Wen order (1..64)."""
    if not 1 <= number <= 64:
        raise ValueError("hexagram number must be in 1..64")
    return chr(0x4DC0 + number - 1)


def moving_line_label(indexes: list[int]) -> str:
    labels = ["初", "二", "三", "四", "五", "上"]
    if not indexes:
        return "無"
    return "、".join(labels[i] for i in indexes)


def cast_from_values(values: list[int]) -> dict[str, Any]:
    """Build a cast from six bottom-to-top line values for deterministic tests."""
    if len(values) != 6 or any(value not in {6, 7, 8, 9} for value in values):
        raise ValueError("I Ching cast requires six values from {6,7,8,9}")
    lines = [value % 2 == 1 for value in values]  # bottom -> top; odd=yang
    moving = [idx for idx, value in enumerate(values) if value in {6, 9}]
    changed = [not line if idx in moving else line for idx, line in enumerate(lines)]
    base_no = hexagram_no_from_lines(lines)
    changed_no = hexagram_no_from_lines(changed)
    lower = TRIGRAM_BY_LINES[tuple(lines[:3])]
    upper = TRIGRAM_BY_LINES[tuple(lines[3:])]
    changed_lower = TRIGRAM_BY_LINES[tuple(changed[:3])]
    changed_upper = TRIGRAM_BY_LINES[tuple(changed[3:])]
    return {
        "values": values,
        "moving": moving,
        "base_no": base_no,
        "base_name": HEXAGRAM_NAMES[base_no],
        "changed_no": changed_no,
        "changed_name": HEXAGRAM_NAMES[changed_no],
        "lower": lower,
        "upper": upper,
        "changed_lower": changed_lower,
        "changed_upper": changed_upper,
    }


def cast_hexagram() -> dict[str, Any]:
    # Three-coin method via OS-backed system random. 6/9 are moving lines.
    return cast_from_values(generate_cast_values())


def compact_iching_text(text: str, max_chars: int = 34) -> str:
    """Prefer the modern sentence and keep the symbolic line glanceable."""
    cleaned = re.sub(r"\s+", "", text or "")
    sentences = [part for part in cleaned.split("。") if part]
    hint = sentences[-1] if len(sentences) >= 2 else (sentences[0] if sentences else "審時度勢")
    if len(hint) > max_chars:
        hint = hint[: max_chars - 1].rstrip("，、；") + "…"
    return hint


def iching_guardrail(moving_count: int) -> str:
    guardrails = [
        "守主線，只做一個可驗證小步",   # 0 靜卦
        "只改一處，做完再評估",         # 1
        "只改一處，做完再評估",         # 2
        "變數多，縮小承諾並保留退路",   # 3
        "變數多，縮小承諾並保留退路",   # 4
        "先停擴張，整理基礎與證據",     # 5
        "不做不可逆決定，先守住不變項", # 6
    ]
    return guardrails[min(max(moving_count, 0), 6)]


def build_hexagram_next_action(dt: datetime, cast_data: dict[str, Any] | None = None) -> str:
    if _ICHING is None:
        return "｜勢｜易經資料暫取不到｜只看現實優先"
    cast = cast_data or cast_hexagram()
    moving = moving_line_label(cast["moving"]) if cast["moving"] else "靜"
    base_display = f"第{cast['base_no']}卦 {hexagram_symbol(cast['base_no'])} {cast['base_name']}"
    changed = (
        f"→第{cast['changed_no']}卦 {hexagram_symbol(cast['changed_no'])} {cast['changed_name']}"
        if cast["changed_no"] != cast["base_no"]
        else ""
    )

    # 曾仕強教授變爻規則：根據變爻數量選擇對應爻辭
    text, rule = _ICHING.resolve_line_by_moving(cast["base_no"], cast["moving"])

    # 三爻以上變：需用變卦來解
    if len(cast["moving"]) >= 3:
        # 用變卦的卦辭
        changed_text = _ICHING.get_judgment(cast["changed_no"])
        if "看變卦卦辭" in text or "變卦卦辭" in text:
            text = changed_text
        elif "變卦內卦" in text:
            # 四爻變：變卦下卦（內卦）的卦辭
            changed_lower_name = cast["changed_lower"]["name"]
            essence = _ICHING.TRIGRAM_ESSENCE.get(changed_lower_name, "")
            # Extract the hint part after the description
            hint_parts = [p.strip() for p in essence.replace("——", "——").split("——") if p.strip()]
            inner_hint = hint_parts[-1] if len(hint_parts) >= 2 else (hint_parts[0] if hint_parts else "")
            text = f"{cast['changed_name']}內卦提示：{inner_hint}" if inner_hint else changed_text
        elif "不變爻" in text:
            # 五爻變：找變卦中沒變的那一爻
            unchanged = [i for i in range(6) if i not in cast["moving"]]
            if unchanged:
                uc_idx = unchanged[0]
                text = _ICHING.get_line_text(cast["changed_no"], uc_idx)
            else:
                text = changed_text

    hint = compact_iching_text(text)
    guardrail = iching_guardrail(len(cast["moving"]))
    return f"｜勢｜{base_display}{changed}｜{moving}｜{hint}"


def build_message(dt: datetime, test_label: str | None = None, consume_vocab: bool = False) -> str:
    hour = dt.hour
    if hour not in BROADCAST_HOURS:
        # Scheduled cron should never hit this. Keep manual/off-window runs silent
        # unless explicitly forced by the test hook.
        if test_label is None:
            return ""

    # Keep manual/forced tests in the same pipe-only shape as scheduled output.
    prefix = ""
    almanac_line = build_almanac_chat_line(dt, prefix=prefix)
    lines: list[str] = []

    # Reserve the slot before formatting; retries reuse both word and cast.
    vocab_line = build_vocab_line(dt, consume=consume_vocab)
    cast_data = None
    if consume_vocab:
        values = reserved_cast_values(dt)
        if values:
            cast_data = cast_from_values(values)

    # First-principles UX: the real-life action is always the first visible line.
    rhythm_line = build_rhythm_line(dt)
    if rhythm_line:
        lines.append(rhythm_line)

    lines.append(vocab_line)
    lines.append(almanac_line)
    lines.append(build_hexagram_next_action(dt, cast_data=cast_data))

    return "\n".join(lines)


def parse_limit(value: str | None, default: int = 50) -> int | None:
    if value is None:
        return default
    if str(value).strip().lower() in {"all", "全部", "*"}:
        return None
    try:
        n = int(str(value))
    except ValueError:
        return default
    return max(n, 0)


def entry_seen_suffix(entry_id: str, stats: dict[str, dict[str, Any]]) -> str:
    if entry_id not in stats:
        return "未播"
    item = stats[entry_id]
    cycles = ",".join(str(c) for c in item.get("cycles", []) if c is not None)
    return f"已播 x{item['count']}｜cycle={cycles or '?'}｜last={item.get('last_seen_at') or '?'}"


def format_entry(entry: dict[str, str], idx: int | None = None, stats: dict[str, dict[str, Any]] | None = None) -> str:
    head = f"{idx:04d}. " if idx is not None else ""
    status = f"｜{entry_seen_suffix(entry['id'], stats)}" if stats is not None else ""
    return (
        f"{head}{entry['word']} {entry['pron']}｜{entry['pos']}. {entry['gloss']}"
        f"｜src={entry['source']}｜id={entry['id']}{status}"
    )


def print_vocab_status(
    entries: list[dict[str, str]], state: dict[str, Any], corpus_total: int
) -> None:
    total = len(entries)
    current_seen = len(state.get("cycle_seen_ids", []))
    remaining = max(total - current_seen, 0)
    hist = state.get("history", [])
    print("📘 番茄鐘單字輪播狀態")
    print(f"corpus_words={corpus_total}")
    print(f"eligible_root_words={total}")
    print(f"cycle={state.get('cycle', 1)}")
    print(f"broadcasted_this_cycle={current_seen}")
    print(f"remaining_this_cycle={remaining}")
    print(f"broadcasted_history_total={len(hist)}")
    print(f"cycle_started_at={state.get('cycle_started_at')}")
    print(f"last_broadcast_at={state.get('last_broadcast_at')}")
    print(f"state_path={vocab_state_path().as_posix()}")
    if hist:
        last = hist[-1]
        print(
            "last_word="
            f"{last.get('word')} {last.get('pron', '')}｜{last.get('pos')}. {last.get('gloss')}"
        )
    print("cycle_rule=只播有字根拆解且通過品質閘門的字；cycle 內不重複")


def list_total(limit_text: str | None, as_json: bool = False) -> None:
    entries = load_vocab_entries()
    state = load_vocab_state(entries)
    stats = history_stats(state)
    limit = parse_limit(limit_text)
    rows = entries if limit is None else entries[:limit]
    if as_json:
        print(json.dumps({"total": len(entries), "shown": len(rows), "entries": rows}, ensure_ascii=False, indent=2))
        return
    print(f"total_words={len(entries)} shown={len(rows)}")
    for i, entry in enumerate(rows, 1):
        print(format_entry(entry, i, stats))


def list_seen(limit_text: str | None, as_json: bool = False) -> None:
    entries = load_vocab_entries()
    state = load_vocab_state(entries)
    hist = list(reversed(state.get("history", [])))
    limit = parse_limit(limit_text)
    rows = hist if limit is None else hist[:limit]
    if as_json:
        print(json.dumps({"history_total": len(hist), "shown": len(rows), "history": rows}, ensure_ascii=False, indent=2))
        return
    print(f"broadcasted_history_total={len(hist)} shown={len(rows)}")
    for i, item in enumerate(rows, 1):
        print(
            f"{i:04d}. {item.get('word')} {item.get('pron', '')}｜{item.get('pos')}. {item.get('gloss')}"
            f"｜cycle={item.get('cycle')}｜idx={item.get('cycle_index')}/{item.get('cycle_total')}"
            f"｜at={item.get('broadcasted_at')}｜id={item.get('id')}"
        )


def lookup(query: str, limit_text: str | None, as_json: bool = False) -> None:
    q = query.strip().lower()
    entries = load_vocab_entries()
    state = load_vocab_state(entries)
    stats = history_stats(state)
    limit = parse_limit(limit_text, default=30)

    def matches(entry: dict[str, str]) -> bool:
        hay = "\t".join([
            entry.get("id", ""), entry.get("word", ""), entry.get("pron", ""),
            entry.get("pos", ""), entry.get("gloss", ""), entry.get("source", ""),
        ]).lower()
        return q in hay

    rows = [entry for entry in entries if matches(entry)]
    shown = rows if limit is None else rows[:limit]
    if as_json:
        print(json.dumps({"query": query, "matches": len(rows), "shown": len(shown), "entries": shown}, ensure_ascii=False, indent=2))
        return
    print(f"query={query!r} matches={len(rows)} shown={len(shown)}")
    for i, entry in enumerate(shown, 1):
        print(format_entry(entry, i, stats))


def export_entries(path: str, seen_only: bool = False) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    entries = load_vocab_entries()
    state = load_vocab_state(entries)
    if seen_only:
        rows = state.get("history", [])
        fieldnames = ["id", "word", "pron", "pos", "gloss", "source", "cycle", "cycle_index", "cycle_total", "broadcasted_at", "time_hhmm"]
    else:
        stats = history_stats(state)
        rows = []
        for entry in entries:
            stat = stats.get(entry["id"], {})
            rows.append({
                **entry,
                "seen_count": stat.get("count", 0),
                "last_seen_at": stat.get("last_seen_at"),
                "cycles": ",".join(str(c) for c in stat.get("cycles", []) if c is not None),
            })
        fieldnames = ["id", "word", "pron", "pos", "gloss", "source", "seen_count", "last_seen_at", "cycles"]

    if out.suffix.lower() == ".json":
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    print(out.as_posix())


def reset_cycle() -> None:
    entries = eligible_vocab_entries(load_vocab_entries())
    state = load_vocab_state(entries)
    state["cycle"] = int(state.get("cycle", 1)) + 1
    state["cycle_started_at"] = datetime.now(TZ_TAIPEI).isoformat(timespec="seconds")
    state["cycle_seen_ids"] = []
    state["last_entry_id"] = None
    save_vocab_state(state)
    print(f"cycle_reset_ok cycle={state['cycle']} state_path={vocab_state_path().as_posix()}")


def main() -> int:
    # [CRON WORKAROUND] Always write something first so scheduler never sees
    # empty stdout when the subprocess environment differs from terminal.
    ts = datetime.now(TZ_TAIPEI)
    sys.stdout.write(f"CRON_SIGNAL:{ts.hour:02d}:{ts.minute:02d}:started\n")
    sys.stdout.flush()
    parser = argparse.ArgumentParser(description="Script-only original Pomodoro Chat cron")
    parser.add_argument("--at", type=parse_hhmm, help="test time HH:MM, e.g. 09:00")
    parser.add_argument("--consume", action="store_true", help="manual/forced test also consumes one vocabulary card")
    parser.add_argument("--vocab-status", action="store_true", help="show total/seen/remaining/cycle status")
    parser.add_argument("--list-total", nargs="?", const="50", metavar="N|all", help="list total vocabulary corpus (default 50)")
    parser.add_argument("--list-seen", nargs="?", const="50", metavar="N|all", help="list broadcast history, newest first (default 50)")
    parser.add_argument("--lookup", metavar="QUERY", help="reverse lookup total corpus by word/pron/gloss/source/id")
    parser.add_argument("--lookup-limit", default="30", metavar="N|all", help="limit lookup results")
    parser.add_argument("--json", action="store_true", help="emit JSON for list/status/lookup commands where supported")
    parser.add_argument("--export-total", metavar="PATH", help="export total corpus with seen status to CSV or JSON")
    parser.add_argument("--export-seen", metavar="PATH", help="export broadcast history to CSV or JSON")
    parser.add_argument("--reset-cycle", action="store_true", help="start a fresh cycle without destroying history")
    args = parser.parse_args()

    if args.reset_cycle:
        reset_cycle()
        return 0
    if args.export_total:
        export_entries(args.export_total, seen_only=False)
        return 0
    if args.export_seen:
        export_entries(args.export_seen, seen_only=True)
        return 0
    if args.vocab_status:
        all_entries = load_vocab_entries()
        entries = eligible_vocab_entries(all_entries)
        state = load_vocab_state(entries)
        if args.json:
            print(json.dumps({
                "corpus_words": len(all_entries),
                "eligible_root_words": len(entries),
                "cycle": state.get("cycle", 1),
                "broadcasted_this_cycle": len(state.get("cycle_seen_ids", [])),
                "remaining_this_cycle": max(len(entries) - len(state.get("cycle_seen_ids", [])), 0),
                "broadcasted_history_total": len(state.get("history", [])),
                "state_path": vocab_state_path().as_posix(),
                "state": state,
            }, ensure_ascii=False, indent=2))
        else:
            print_vocab_status(entries, state, corpus_total=len(all_entries))
        return 0
    if args.list_total is not None:
        list_total(args.list_total, as_json=args.json)
        return 0
    if args.list_seen is not None:
        list_seen(args.list_seen, as_json=args.json)
        return 0
    if args.lookup:
        lookup(args.lookup, args.lookup_limit, as_json=args.json)
        return 0

    forced, label = load_forced_time()
    tz_now = datetime.now(TZ_TAIPEI)

    if args.at:
        h, m = args.at
        dt = tz_now.replace(hour=h, minute=m, second=0, microsecond=0)
        label = label or "手動測試"
    elif forced:
        h, m = forced
        dt = tz_now.replace(hour=h, minute=m, second=0, microsecond=0)
    else:
        dt = tz_now

    # Real scheduled runs consume vocabulary; manual/forced tests do not unless --consume.
    consume_vocab = args.consume or (label is None and not args.at and not forced)
    msg = build_message(dt, test_label=label, consume_vocab=consume_vocab)
    if msg:
        # Single delivery authority: Hermes scheduler owns Telegram+Discord fan-out.
        # The script only emits UTF-8 stdout; it never posts to a platform API.
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()
    else:
        # Safety fallback: always write something so cron never sees empty stdout.
        sys.stdout.write("｜行｜排程執行中，稍後查看 Discord｜字｜無新字｜時｜現實優先｜勢｜守主線\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
