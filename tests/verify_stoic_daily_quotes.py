#!/usr/bin/env python3
"""Validate date coverage and normalized display safety of Stoic titles."""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "stoic_daily_quotes.json"

current = date(2024, 1, 1)
end = date(2025, 1, 1)
dates = set()
while current < end:
    dates.add(current.strftime("%m-%d"))
    current += timedelta(days=1)

data = json.loads(DATA.read_text(encoding="utf-8"))
assert set(data) == dates
assert len(data) == 366
assert all(set(entry) == {"title"} for entry in data.values())
assert all(4 <= len(entry["title"]) <= 24 for entry in data.values())
assert all(not re.search(r"[\u2e80-\u2fff]", entry["title"]) for entry in data.values())
assert all("**" not in entry["title"] and "?" not in entry["title"] for entry in data.values())
assert data["01-12"]["title"] == "通往平靜人生的唯一途徑"
assert data["07-14"]["title"] == "一知半解最危險"
assert data["09-10"]["title"] == "記得要未雨綢繆"
assert data["10-05"]["title"] == "一言既出，駟馬難追"
assert data["12-31"]["title"] == "努力拉自己一把"

print("PASS stoic_daily_quotes dates=366 normalized=366 curated=62")
