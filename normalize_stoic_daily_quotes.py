#!/usr/bin/env python3
"""Normalize the 366 compact Stoic titles extracted from the user's Markdown."""
from __future__ import annotations

import argparse
import json
import unicodedata
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "data" / "stoic_daily_quotes.json"
RADICAL_REPLACEMENTS = str.maketrans({"⺠": "民", "⻑": "長"})

# The PDF-to-Markdown source drops some occurrences of 一 and most title
# punctuation. These corrections were reviewed against the dated source
# headings; the source Markdown itself remains untouched.
TITLE_CORRECTIONS = {
    "01-05": "沒有目標，就不可能出擊致勝",
    "01-06": "人、事、地、原因很重要",
    "01-12": "通往平靜人生的唯一途徑",
    "01-15": "想要平靜，就要堅定不移",
    "01-18": "像詩人和藝術家一樣看世界",
    "01-25": "最有價值的事",
    "02-15": "一切只是惡夢一場",
    "02-25": "一切終究歸於塵土",
    "02-27": "別人激動，你要保持平常心",
    "03-25": "少點慾望，多點富足和自由",
    "03-30": "理智主宰一切",
    "04-03": "不要自欺欺人、三心二意",
    "04-05": "就算信了，也要檢驗",
    "04-17": "放下痛苦，少點鬱悶",
    "04-18": "想法其實只是……",
    "05-07": "如何度過美好的一天",
    "05-10": "與其效法別人，不如讓別人效法",
    "05-19": "學習、實踐、鍛鍊",
    "05-29": "工作就是一種療癒",
    "05-31": "人生唯一的任務",
    "06-06": "該留就留，該退就退",
    "06-10": "你一定辦得到",
    "06-18": "做好準備，積極進取",
    "07-14": "一知半解最危險",
    "07-17": "不要放棄別人，也不要放棄自己",
    "07-23": "面對榮辱，心態一致",
    "08-04": "少埋怨，多專心",
    "08-07": "腳踏實地，堅持原則",
    "08-11": "面對現實，少鑽理論",
    "08-12": "言行合一最重要",
    "08-13": "多動腦，麻煩就少",
    "08-17": "與其怪東怪西，不如認真自省",
    "08-25": "胸懷過去，心向未來",
    "08-29": "減少慾望就能擁有一切",
    "09-02": "哲學課堂就是一座醫院",
    "09-04": "沒吃過苦，就沒有領悟",
    "09-10": "記得要未雨綢繆",
    "09-22": "沒有付出，哪來收穫",
    "09-23": "最安全的堡壘",
    "10-04": "人人為我，我為人人",
    "10-05": "一言既出，駟馬難追",
    "10-09": "設定標準，努力實踐",
    "10-14": "多拉人一把，少生點悶氣",
    "10-18": "捅人一刀的朋友",
    "10-26": "三個層面，目標一致",
    "10-27": "種瓜得瓜，種豆得豆",
    "11-08": "人生如戲，你就是演員",
    "11-10": "千年如一日",
    "11-11": "天下本無事，庸人自擾之",
    "11-13": "不抱怨，不多言",
    "11-20": "看，當下不就是永恆嗎？",
    "11-21": "感受一次等於感受一輩子",
    "11-24": "不屬於你的，就不要操心",
    "11-26": "走到最後，大家都一樣",
    "11-28": "少怪別人，多怪自己",
    "11-29": "一切都會安然無恙",
    "11-30": "順著 logos 走",
    "12-01": "把今天當作人生最後一天",
    "12-11": "果敢堅強，維護尊嚴",
    "12-12": "世事運作始終如一",
    "12-26": "好好利用人生，你就能長壽了",
    "12-31": "努力拉自己一把",
}


def expected_dates() -> set[str]:
    current = date(2024, 1, 1)
    end = date(2025, 1, 1)
    values = set()
    while current < end:
        values.add(current.strftime("%m-%d"))
        current += timedelta(days=1)
    return values


def normalize_title(value: str) -> str:
    title = unicodedata.normalize("NFKC", value).translate(RADICAL_REPLACEMENTS)
    return " ".join(title.split()).replace("?", "？").strip()


def normalize_dataset(data: dict[str, object]) -> dict[str, object]:
    if set(data) != expected_dates():
        missing = sorted(expected_dates() - set(data))
        extra = sorted(set(data) - expected_dates())
        raise ValueError(f"date coverage mismatch missing={missing} extra={extra}")
    normalized = {}
    for key in sorted(data):
        entry = data[key]
        if not isinstance(entry, dict):
            raise ValueError(f"invalid entry: {key}")
        title = TITLE_CORRECTIONS.get(key, normalize_title(str(entry.get("title") or "")))
        if not title:
            raise ValueError(f"empty title: {key}")
        # The compact runtime dataset intentionally exposes one stable field.
        # Two source records contained long quotes while the other 364 did not;
        # retaining those partial extras would make the offline schema uneven.
        normalized[key] = {"title": title}
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    rendered = json.dumps(normalize_dataset(data), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if args.data.read_text(encoding="utf-8") != rendered:
            print(f"ERROR stale normalization: {args.data}")
            return 1
        print(f"PASS stoic_normalization titles={len(data)} curated={len(TITLE_CORRECTIONS)}")
        return 0
    args.data.write_text(rendered, encoding="utf-8")
    print(f"WROTE {args.data} titles={len(data)} curated={len(TITLE_CORRECTIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
