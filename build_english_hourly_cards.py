#!/usr/bin/env python3
"""Build compact hourly English learning cards from the synced Drive courses.

The source tree is expected to contain the three ``字根字首魔法學院``
folders exported from Google Drive.  Only lightweight teaching text is copied:
root definitions, three source-backed core words per unit, morpheme notes, and
answerable source examples.  Audio, video, and full ASR binaries are never copied.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "english_hourly_cards.json"
DEFAULT_TRANSCRIPT_MANIFEST = PROJECT_ROOT / "data" / "english_transcript_crosscheck.json"

# Source cards remain untouched. These narrowly scoped edits correct clear
# grammar, usage, or factual phrasing in the portable derivative.
CURATED_EXAMPLE_CORRECTIONS: dict[str, tuple[str, str, str]] = {
    "diction": (
        "Children's authors must closely watch their diction to ensure they use easily understandable words.",
        "兒童讀物作者必須留意措辭，確保使用容易理解的字詞。",
        "removed incorrect -ly compound hyphenation",
    ),
    "version": (
        "The classic board game Monopoly is available in a wide range of versions and languages around the world.",
        "經典桌遊《大富翁》在世界各地有許多版本與語言。",
        "clarified global availability",
    ),
    "press": (
        "In a democracy, freedom of the press helps hold the government accountable.",
        "在民主制度中，新聞自由有助於監督政府並要求其負責。",
        "corrected the role of press freedom",
    ),
    "sign": (
        "Normally, equations include an equals sign.",
        "一般而言，方程式會包含等號。",
        "used the standard term equals sign",
    ),
    "depend": (
        "The financial crisis made clear how much we depend on international cooperation.",
        "金融危機顯示我們有多麼依賴國際合作。",
        "replaced non-idiomatic international society",
    ),
    "order": (
        "You can change the order of the list if need be.",
        "如有必要，你可以更改清單的順序。",
        "corrected the idiom if need be",
    ),
    "section": (
        "Insects have six legs and three sections of their bodies: the head, thorax, and abdomen.",
        "昆蟲有六條腿，身體分成頭部、胸部與腹部三個部分。",
        "corrected plural agreement",
    ),
    "linguist": (
        "Working as a linguist is difficult, and you need a good ear to distinguish different sound patterns.",
        "語言學家的工作並不容易，而且需要敏銳的聽力來分辨不同的聲音模式。",
        "corrected the subject-complement relationship",
    ),
    "ambition": (
        "When James got his new job, he believed his ambition would lead to him becoming the company's CEO one day.",
        "James 得到新工作時，相信自己的抱負終有一天會使他成為公司的執行長。",
        "corrected the lead to construction",
    ),
    "monologue": (
        "The president delivered a monologue at the United Nations while asking other world leaders for assistance.",
        "這位總統在聯合國發表長篇獨白，並向其他國家領袖尋求協助。",
        "normalized title capitalization and verb choice",
    ),
    "similar": (
        "The colorful scarlet kingsnake is similar to the venomous coral snake, but it is not venomous at all.",
        "色彩鮮豔的猩紅王蛇與有毒的珊瑚蛇相似，但猩紅王蛇本身完全沒有毒液。",
        "corrected venomous versus poisonous usage",
    ),
    "center": (
        "Central Park lies near the center of Manhattan and is one of the most famous parks in the world.",
        "中央公園位於曼哈頓中部附近，是世界上最著名的公園之一。",
        "corrected geographic scope",
    ),
    "minister": (
        "Calvin majored in theology in college to become a minister in the Presbyterian Church, just like his father.",
        "Calvin 在大學主修神學，希望像父親一樣成為長老教會的牧師。",
        "normalized common-noun capitalization",
    ),
    "plain": (
        "Every morning, I prefer a cup of latte, while my co-worker prefers plain black coffee with no cream or sugar.",
        "每天早上我喜歡喝拿鐵，而同事喜歡不加奶精或糖的純黑咖啡。",
        "corrected latte spelling and adjective punctuation",
    ),
    "democracy": (
        "In a democracy, citizens choose their representatives through elections.",
        "在民主制度中，公民透過選舉選出代表。",
        "replaced an overgeneralized causal claim",
    ),
}
COURSE_PREFIX = "字根字首魔法學院"
COURSE_AUTHORITY = "google-drive-folder:1awbxyfEk9sDxA5p2QQWUtn5EQxKYDXOA"
TRANSCRIPT_AUTHORITY = "google-drive-folder:13_lazdStDY0dyj8iOras0s1UcaWQbfUe"
NUMBER_PREFIX_RE = re.compile(r"^\d+[_\s]*")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: Any, max_chars: int | None = None) -> str:
    text = html.unescape(str(value or ""))
    text = TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|\t\r\n")
    if max_chars and len(text) > max_chars:
        text = text[: max_chars - 1].rstrip(" ,;，；。") + "…"
    return text


def discover_source_root(explicit: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("POMODORO_ENGLISH_SOURCE_DIR"):
        candidates.append(Path(os.environ["POMODORO_ENGLISH_SOURCE_DIR"]))
    candidates.extend(
        [
            PROJECT_ROOT.parent / "字根自首",
            PROJECT_ROOT.parent / "字根字首",
        ]
    )
    for candidate in candidates:
        if candidate.is_dir() and any(
            child.is_dir() and child.name.startswith(COURSE_PREFIX)
            for child in candidate.iterdir()
        ):
            return candidate.resolve()
    shown = "\n".join(f"- {candidate}" for candidate in candidates)
    raise FileNotFoundError(f"找不到同步課程來源。已檢查：\n{shown}")


def parse_lesson_title(title: str) -> tuple[str, str, str]:
    title = NUMBER_PREFIX_RE.sub("", title).strip()
    if "=" in title:
        roots, meaning = (part.strip() for part in title.split("=", 1))
    else:
        match = CJK_RE.search(title)
        if match:
            roots = title[: match.start()].strip(" ,，")
            meaning = title[match.start() :].strip()
        else:
            roots, meaning = title, ""

    match = CJK_RE.search(meaning)
    if match:
        meaning_en = meaning[: match.start()].strip(" ,，")
        meaning_zh = meaning[match.start() :].strip(" ,，")
    else:
        meaning_en, meaning_zh = meaning.strip(" ,，"), ""
    return clean_text(roots), clean_text(meaning_en), clean_text(meaning_zh)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def first_explanation(card: dict[str, Any]) -> dict[str, Any]:
    explanations = (card.get("text_content") or {}).get("explanations") or []
    return next((item for item in explanations if isinstance(item, dict)), {})


def card_sentence(card: dict[str, Any]) -> tuple[str, str]:
    for explanation in (card.get("text_content") or {}).get("explanations") or []:
        sentences = explanation.get("sentences") or []
        if not sentences:
            continue
        english = clean_text(sentences[0])
        chinese = clean_text(sentences[1]) if len(sentences) > 1 else ""
        if english:
            return english, chinese
    return "", ""


def editorially_correct_example(word: str, english: str, chinese: str) -> tuple[str, str, str]:
    correction = CURATED_EXAMPLE_CORRECTIONS.get(word.lower())
    if correction:
        return correction
    return english, chinese, ""


def root_forms(root_label: str) -> list[str]:
    values = [clean_text(value).lower().strip("-") for value in re.split(r"[,/]", root_label)]
    return [value for value in values if value]


def normalized_morpheme(value: str) -> str:
    """Normalize a displayed root/word part for structured matching."""
    return re.sub(r"[^a-z]", "", clean_text(value).lower())


def representative_root_match(card: dict[str, Any], roots: list[str]) -> bool:
    """Return whether course metadata actually marks a lesson root in the word.

    Many decks begin with a translation card such as ``foot`` for ``ped``.
    That card is useful vocabulary, but it is not a good morpheme-decomposition
    example. Prefer a later card such as ``pedal`` whose structured ``part``
    explicitly contains the taught root.
    """
    normalized_roots = [normalized_morpheme(root) for root in roots]
    normalized_roots = [root for root in normalized_roots if root]
    for item in card.get("word_roots") or []:
        if not isinstance(item, dict):
            continue
        part = normalized_morpheme(str(item.get("part") or ""))
        if not part:
            continue
        if any(
            part == root
            or (len(root) >= 2 and part.startswith(root))
            or (len(part) >= 2 and root.startswith(part))
            for root in normalized_roots
        ):
            return True
    return False


def breakdown_root_match(breakdown: str, roots: list[str]) -> bool:
    """Check the compact rendered decomposition against the lesson roots."""
    normalized_roots = [normalized_morpheme(root) for root in roots]
    normalized_roots = [root for root in normalized_roots if root]
    for segment in breakdown.split(" + "):
        part = normalized_morpheme(segment.split("(", 1)[0])
        if part and any(
            part == root
            or (len(root) >= 2 and part.startswith(root))
            or (len(part) >= 2 and root.startswith(part))
            for root in normalized_roots
        ):
            return True
    return False


def normalized_root_key(title: str) -> str:
    root_label, _, _ = parse_lesson_title(title)
    return re.sub(r"[^a-z]", "", root_label.lower())


def parse_raw_transcript(
    path: Path | None, course_dirs: list[Path]
) -> tuple[dict[tuple[str, str], dict[str, str]], dict[str, int]]:
    """Index the combined ASR transcript by course and root-family lesson.

    The ASR body is retained only as evidence.  Runtime teaching text remains
    grounded in the structured course/card data because the transcript contains
    known spelling, script-conversion, repetition, and homophone errors.
    """
    if path is None:
        return {}, {"raw_transcript_sections": 0, "raw_transcript_lesson_matches": 0}
    raw = path.read_text(encoding="utf-8", errors="replace")
    course_by_code = {code: course.name for code, course in zip("abc", course_dirs)}
    sections: dict[tuple[str, str], dict[str, str]] = {}
    total_sections = 0
    current_name: str | None = None
    current_lines: list[str] = []

    def store() -> None:
        nonlocal current_name, current_lines
        if not current_name:
            return
        stem = current_name.rsplit(".", 1)[0]
        parts = stem.split("_")
        if len(parts) < 4:
            return
        code = parts[1][:1].lower()
        course = course_by_code.get(code)
        if not course:
            return
        lesson_title = "_".join(parts[3:])
        key = normalized_root_key(lesson_title)
        if key:
            sections[(course, key)] = {
                "file": path.name,
                "section": current_name,
                "body": "\n".join(current_lines).strip(),
            }

    for line in raw.splitlines():
        if line.startswith("### [") and line.rstrip().endswith(".mp4") and ": " in line:
            store()
            total_sections += 1
            current_name = line.split(": ", 1)[1].strip()
            current_lines = []
        elif current_name:
            current_lines.append(line)
    store()
    return sections, {"raw_transcript_sections": total_sections, "raw_transcript_lesson_matches": 0}


def load_transcript_manifest(
    path: Path = DEFAULT_TRANSCRIPT_MANIFEST,
) -> tuple[dict[tuple[str, str], dict[str, str]], dict[str, int]]:
    """Load the compact offline record of the previously parsed Drive transcript."""
    if not path.is_file():
        return {}, {"raw_transcript_sections": 0, "raw_transcript_lesson_matches": 0}
    data = load_json(path)
    if data.get("version") != 1 or data.get("authority") != TRANSCRIPT_AUTHORITY:
        raise ValueError(f"逐字稿交叉驗證清單格式不符：{path}")
    sections: dict[tuple[str, str], dict[str, str]] = {}
    for item in data.get("sections") or []:
        if not isinstance(item, dict):
            continue
        course = clean_text(item.get("course"))
        lesson_key = clean_text(item.get("lesson_key"))
        file_name = clean_text(item.get("file"))
        section = clean_text(item.get("section"))
        if course and lesson_key and file_name and section:
            sections[(course, lesson_key)] = {"file": file_name, "section": section, "body": ""}
    return sections, {
        "raw_transcript_sections": int(data.get("raw_transcript_sections") or len(sections)),
        "raw_transcript_lesson_matches": 0,
    }


def choose_representative(cards: list[dict[str, Any]], roots: list[str]) -> dict[str, Any]:
    def score(card: dict[str, Any]) -> tuple[int, int, int, int, str]:
        word = clean_text(card.get("word")).lower()
        has_sentence = int(bool(card_sentence(card)[0]))
        has_roots = int(bool(card.get("word_roots")))
        structured_match = int(representative_root_match(card, roots))
        exact_root = int(word.strip("-") in roots)
        position = int(card.get("position") or 9999)
        return (
            -structured_match,
            -exact_root,
            -has_sentence,
            -has_roots,
            f"{position:05d}:{word}",
        )

    valid = [card for card in cards if isinstance(card, dict) and clean_text(card.get("word"))]
    if not valid:
        raise ValueError("cards.json 沒有可用單字")
    return sorted(valid, key=score)[0]


def leading_family_signature(card: dict[str, Any], roots: list[str]) -> str:
    """Return a compact prefix signature used only to diversify core words."""
    normalized_roots = {root.strip("-").casefold() for root in roots}
    prefix_parts: list[str] = []
    for item in card.get("word_roots") or []:
        if not isinstance(item, dict):
            continue
        part = clean_text(item.get("part")).strip("-").casefold()
        if not part:
            continue
        if part in normalized_roots:
            break
        prefix_parts.append(part)
    return "+".join(prefix_parts)


def choose_core_words(
    cards: list[dict[str, Any]], roots: list[str], limit: int = 3
) -> list[dict[str, Any]]:
    """Choose three source-backed words with examples and varied word families."""
    representative = choose_representative(cards, roots)
    chosen = [representative]
    used_words = {clean_text(representative.get("word")).casefold()}
    used_signatures = {leading_family_signature(representative, roots)}

    def score(card: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
        word = clean_text(card.get("word")).casefold()
        signature = leading_family_signature(card, roots)
        sentence = card_sentence(card)[0]
        return (
            -int(representative_root_match(card, roots)),
            -int(bool(sentence)),
            -int(bool(signature) and signature not in used_signatures),
            len(word),
            int(card.get("position") or 9999),
            word,
        )

    candidates = [
        card
        for card in cards
        if isinstance(card, dict)
        and clean_text(card.get("word")).casefold() not in used_words
        and representative_root_match(card, roots)
        and card_sentence(card)[0]
    ]
    while candidates and len(chosen) < limit:
        selected = sorted(candidates, key=score)[0]
        chosen.append(selected)
        word = clean_text(selected.get("word")).casefold()
        used_words.add(word)
        used_signatures.add(leading_family_signature(selected, roots))
        candidates = [
            card for card in candidates if clean_text(card.get("word")).casefold() not in used_words
        ]

    if len(chosen) < limit:
        fallback = [
            card
            for card in cards
            if isinstance(card, dict)
            and clean_text(card.get("word")).casefold() not in used_words
        ]
        for card in sorted(fallback, key=score):
            chosen.append(card)
            used_words.add(clean_text(card.get("word")).casefold())
            if len(chosen) >= limit:
                break
    return chosen


def extract_gloss_and_pos(card: dict[str, Any]) -> tuple[str, str]:
    explanation = first_explanation(card)
    translations = [clean_text(item) for item in explanation.get("translations") or []]
    word_types = [clean_text(item) for item in explanation.get("word_types") or []]
    return clean_text("；".join(item for item in translations if item), 48), ",".join(
        item for item in word_types if item
    )


def extract_phonetic(card: dict[str, Any]) -> str:
    phonetics = card.get("phonetics") or {}
    for locale in ("us", "uk"):
        values = phonetics.get(locale) or []
        if values and isinstance(values[0], dict):
            value = clean_text(values[0].get("phonetic"))
            if value:
                return value
    return ""


def extract_breakdown(card: dict[str, Any], root_label: str) -> tuple[str, str]:
    parts: list[str] = []
    notes: list[str] = []
    for item in card.get("word_roots") or []:
        if not isinstance(item, dict):
            continue
        part = clean_text(item.get("part"))
        note = clean_text(item.get("note"))
        if part:
            parts.append(f"{part}({note})" if note else part)
        elif note:
            notes.append(note)
    breakdown = " + ".join(parts) or root_label
    return clean_text(breakdown, 90), clean_text(notes[0] if notes else "", 180)


def safe_video_takeaway(
    root_label: str,
    meaning_en: str,
    meaning_zh: str,
    formation_note: str,
) -> str:
    meaning = " / ".join(value for value in (meaning_en, meaning_zh) if value)
    root_definition = f"{root_label} 表示 {meaning}" if meaning else root_label
    if formation_note:
        return clean_text(f"{root_definition}；{formation_note}", 180)
    return clean_text(root_definition, 180)


def extract_takeaway(
    lesson_dir: Path,
    root_label: str,
    meaning_en: str,
    meaning_zh: str,
    formation_note: str,
    raw_section: dict[str, str] | None,
) -> tuple[str, str, str | None]:
    transcripts = sorted(lesson_dir.rglob("transcript.txt"))
    if transcripts:
        transcript = transcripts[0]
        lines = [clean_text(line) for line in transcript.read_text(encoding="utf-8", errors="ignore").splitlines()]
        candidates = [
            line.lstrip("- ")
            for line in lines
            if "用來表示" in line or (line.startswith("-") and "表示" in line)
        ]
        takeaway = candidates[0] if candidates else safe_video_takeaway(
            root_label, meaning_en, meaning_zh, formation_note
        )
        return clean_text(takeaway, 180), "provided-transcript", transcript.name
    if raw_section:
        # Do not copy ASR wording into the user-facing card.  The section match
        # proves video coverage; spellings and explanations come from the
        # structured lesson title and word-root notes.
        return (
            safe_video_takeaway(root_label, meaning_en, meaning_zh, formation_note),
            "raw-asr-crosschecked",
            raw_section["section"],
        )
    return (
        safe_video_takeaway(root_label, meaning_en, meaning_zh, formation_note),
        "word-card-structure",
        None,
    )


def extract_source_question(lesson_dir: Path) -> tuple[str, list[str], int, int, list[str]]:
    question = ""
    options: list[str] = []
    count = 0
    refs: list[str] = []
    for path in sorted(lesson_dir.rglob("group.json")):
        refs.append(path.as_posix())
        try:
            group = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        questions = group.get("questions") or []
        count += len(questions)
        if not question and questions:
            first = questions[0]
            question = clean_text((first.get("attributes") or {}).get("text"), 220)
            options = [
                clean_text(option.get("text"), 80)
                for option in first.get("options") or []
                if isinstance(option, dict) and clean_text(option.get("text"))
            ]
    return question, options, count, len(refs), refs


def inflected_word_pattern(word: str) -> re.Pattern[str]:
    """Match the source word or common English inflections in its example."""
    alternatives = [re.escape(word)]
    if word.endswith("e") and len(word) > 2:
        alternatives.extend(
            [
                re.escape(word + "s"),
                re.escape(word + "d"),
                re.escape(word[:-1] + "ing"),
            ]
        )
    else:
        alternatives.extend(
            [
                re.escape(word + "s"),
                re.escape(word + "ed"),
                re.escape(word + "ing"),
            ]
        )
    if word.endswith("y") and len(word) > 2 and word[-2].lower() not in "aeiou":
        alternatives.extend([re.escape(word[:-1] + "ies"), re.escape(word[:-1] + "ied")])
    alternatives.sort(key=len, reverse=True)
    return re.compile(rf"\b(?:{'|'.join(alternatives)})\b", re.IGNORECASE)


def build_prompt(word: str, gloss: str, sentence: str) -> tuple[str, str]:
    if sentence:
        pattern = inflected_word_pattern(word)
        match = pattern.search(sentence)
        if match:
            answer = match.group(0)
            prompt = pattern.sub("____", sentence, count=1)
            return f"填空：{clean_text(prompt, 110)}", answer
    if gloss:
        return f"「{gloss}」的英文是？", word
    return f"看到這個字根時，先回想代表字：{word[0]}____", word


def relative_ref(path: Path, source_root: Path) -> str:
    return path.relative_to(source_root).as_posix()


def build_card(
    cards_path: Path,
    source_root: Path,
    raw_transcripts: dict[tuple[str, str], dict[str, str]],
) -> dict[str, Any]:
    lesson_dir = cards_path.parents[1]
    chapter_dir = lesson_dir.parent
    course_dir = chapter_dir.parent
    root_label, meaning_en, meaning_zh = parse_lesson_title(lesson_dir.name)
    cards = load_json(cards_path)
    if not isinstance(cards, list):
        raise ValueError(f"cards.json 不是陣列：{cards_path}")
    roots = root_forms(root_label)
    core_source_cards = choose_core_words(cards, roots)
    representative = core_source_cards[0]
    word = clean_text(representative.get("word")).lower()
    gloss, pos = extract_gloss_and_pos(representative)
    sentence_en, sentence_zh = card_sentence(representative)
    sentence_en, sentence_zh, editorial_note = editorially_correct_example(
        word, sentence_en, sentence_zh
    )
    breakdown, formation_note = extract_breakdown(representative, root_label)
    raw_section = raw_transcripts.get((course_dir.name, normalized_root_key(lesson_dir.name)))
    takeaway, transcript_status, transcript_name = extract_takeaway(
        lesson_dir,
        root_label,
        meaning_en,
        meaning_zh,
        formation_note,
        raw_section,
    )
    (
        source_question,
        source_options,
        source_question_count,
        source_question_group_count,
        question_refs,
    ) = extract_source_question(lesson_dir)
    prompt, answer = build_prompt(word, gloss, sentence_en)

    core_words: list[dict[str, Any]] = []
    for source_card in core_source_cards:
        core_word = clean_text(source_card.get("word")).lower()
        core_gloss, core_pos = extract_gloss_and_pos(source_card)
        core_sentence_en, core_sentence_zh = card_sentence(source_card)
        core_sentence_en, core_sentence_zh, core_editorial_note = editorially_correct_example(
            core_word, core_sentence_en, core_sentence_zh
        )
        core_breakdown, core_formation_note = extract_breakdown(source_card, root_label)
        core_prompt, core_answer = build_prompt(core_word, core_gloss, core_sentence_en)
        core_words.append({
            "word": core_word,
            "pron": extract_phonetic(source_card),
            "pos": core_pos,
            "gloss": core_gloss,
            "decomp": core_breakdown,
            "formation_note": core_formation_note,
            "prompt": core_prompt,
            "answer": core_answer,
            "example_en": clean_text(core_sentence_en, 180),
            "example_zh": clean_text(core_sentence_zh, 180),
            "example_editorial_note": core_editorial_note,
        })

    source_refs = [relative_ref(cards_path, source_root)]
    if transcript_name:
        provided = sorted(lesson_dir.rglob(transcript_name))
        if provided:
            source_refs.append(relative_ref(provided[0], source_root))
    source_refs.extend(relative_ref(Path(ref), source_root) for ref in question_refs)
    source_refs = sorted(dict.fromkeys(source_refs))

    source = "/".join((course_dir.name, chapter_dir.name, lesson_dir.name))
    stable_id = hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]
    return {
        "id": stable_id,
        "course": course_dir.name,
        "chapter": NUMBER_PREFIX_RE.sub("", chapter_dir.name),
        "lesson": NUMBER_PREFIX_RE.sub("", lesson_dir.name),
        "source_word_count": len(cards),
        "core_words": core_words,
        "root": root_label,
        "root_meaning_en": meaning_en,
        "root_meaning_zh": meaning_zh,
        "word": word,
        "pron": extract_phonetic(representative),
        "pos": pos,
        "gloss": gloss,
        "decomp": breakdown,
        "formation_note": formation_note,
        "takeaway": takeaway,
        "prompt": prompt,
        "answer": answer,
        "example_en": clean_text(sentence_en, 180),
        "example_zh": clean_text(sentence_zh, 180),
        "example_editorial_note": editorial_note,
        "source_quiz_prompt": source_question,
        "source_quiz_options": source_options,
        "source_question_count": source_question_count,
        "source_question_group_count": source_question_group_count,
        "transcript_status": transcript_status,
        "transcript_ref": (
            {
                "authority": TRANSCRIPT_AUTHORITY,
                "file": raw_section["file"],
                "section": raw_section["section"],
            }
            if transcript_status == "raw-asr-crosschecked" and raw_section
            else None
        ),
        "source": source,
        "source_refs": source_refs,
    }


def build_dataset(source_root: Path, transcript_file: Path | None = None) -> dict[str, Any]:
    course_dirs = sorted(
        child for child in source_root.iterdir() if child.is_dir() and child.name.startswith(COURSE_PREFIX)
    )
    if transcript_file:
        raw_transcripts, raw_stats = parse_raw_transcript(transcript_file, course_dirs)
    else:
        raw_transcripts, raw_stats = load_transcript_manifest()
    cards: list[dict[str, Any]] = []
    for course_dir in course_dirs:
        for cards_path in sorted(course_dir.rglob("cards.json")):
            cards.append(build_card(cards_path, source_root, raw_transcripts))
    if not cards:
        raise ValueError(f"來源內找不到 cards.json：{source_root}")

    transcript_count = sum(card["transcript_status"] == "provided-transcript" for card in cards)
    raw_crosschecked_count = sum(card["transcript_status"] == "raw-asr-crosschecked" for card in cards)
    raw_lesson_matches = sum(
        (card["course"], normalized_root_key(card["lesson"])) in raw_transcripts for card in cards
    )
    source_question_count = sum(int(card["source_question_count"]) for card in cards)
    source_question_group_count = sum(int(card["source_question_group_count"]) for card in cards)
    structured_root_matches = sum(
        breakdown_root_match(card["decomp"], root_forms(card["root"])) for card in cards
    )
    editorial_example_corrections = sum(bool(card["example_editorial_note"]) for card in cards)
    return {
        "version": 2,
        "authority": COURSE_AUTHORITY,
        "transcript_authority": TRANSCRIPT_AUTHORITY if raw_transcripts else None,
        "description": "Hourly course-defined root-family mnemonic cards extracted from the synced Google Drive courses; not a claim that every displayed variant shares one strict historical etymology.",
        "stats": {
            "courses": len({card["course"] for card in cards}),
            "cards": len(cards),
            "source_word_cards": sum(int(card["source_word_count"]) for card in cards),
            "core_words": sum(len(card["core_words"]) for card in cards),
            "provided_transcripts": transcript_count,
            "raw_asr_crosschecked": raw_crosschecked_count,
            "word_card_structure_fallbacks": len(cards) - transcript_count - raw_crosschecked_count,
            "source_questions": source_question_count,
            "source_question_groups": source_question_group_count,
            "raw_transcript_sections": raw_stats["raw_transcript_sections"],
            "raw_transcript_lesson_matches": raw_lesson_matches,
            "structured_root_matches": structured_root_matches,
            "editorial_example_corrections": editorial_example_corrections,
        },
        "cards": cards,
    }


def serialized(dataset: dict[str, Any]) -> str:
    return json.dumps(dataset, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", help="包含三套課程資料夾的同步 Drive 目錄")
    parser.add_argument(
        "--transcript-file",
        default=os.environ.get("POMODORO_ENGLISH_TRANSCRIPT_FILE"),
        help="合併 ASR 逐字稿；只作交叉驗證，不直接覆寫結構化拼字",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="輸出 JSON 路徑")
    parser.add_argument("--check", action="store_true", help="只驗證輸出是否與來源一致")
    args = parser.parse_args()

    try:
        source_root = discover_source_root(args.source_root)
        transcript_file = Path(args.transcript_file).resolve() if args.transcript_file else None
        if transcript_file is not None and not transcript_file.is_file():
            raise FileNotFoundError(f"逐字稿不存在：{transcript_file}")
        dataset = build_dataset(source_root, transcript_file)
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output)
    rendered = serialized(dataset)
    if args.check:
        if not output.exists():
            print(f"ERROR: 輸出不存在：{output}", file=sys.stderr)
            return 1
        if output.read_text(encoding="utf-8") != rendered:
            print(f"ERROR: 輸出已落後來源，請重建：{output}", file=sys.stderr)
            return 1
        print(
            "PASS "
            f"courses={dataset['stats']['courses']} cards={dataset['stats']['cards']} "
            f"transcripts={dataset['stats']['provided_transcripts']} "
            f"raw_asr={dataset['stats']['raw_asr_crosschecked']} "
            f"questions={dataset['stats']['source_questions']}"
        )
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8", newline="\n")
    print(
        f"WROTE {output} courses={dataset['stats']['courses']} cards={dataset['stats']['cards']} "
        f"transcripts={dataset['stats']['provided_transcripts']} "
        f"raw_asr={dataset['stats']['raw_asr_crosschecked']} "
        f"questions={dataset['stats']['source_questions']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
