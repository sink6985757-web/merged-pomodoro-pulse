#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import random
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 導入本機邏輯
import lunar_almanac
import pomodoro_iching_data

TZ_TAIPEI = timezone(timedelta(hours=8))
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE" # 請填入您的 Webhook URL

def get_micro_card_data():
    now = datetime.now(TZ_TAIPEI)
    
    # 1. 字 (離線單字)
    with open(DATA_DIR / "vocab_decomposition.json", "r", encoding="utf-8") as f:
        vocab_db = json.load(f)
    word, decomp = random.choice(list(vocab_db["entries"].items()))
    
    # 2. 時 (離線農曆)
    almanac = lunar_almanac.get_lunar_day_info(now)
    
    # 3. 勢 (易經)
    # 此處簡化邏輯，僅示範讀取
    iching_msg = "第12卦 天地否｜動爻：三爻｜順勢而為" 
    
    # 4. 行 (90 分鐘節奏)
    seg = ((now.hour - 9) * 60 + now.minute) // 90 + 1
    action = "先喝水、拉開窗簾；今天只定一條主線" if seg == 1 else "專注執行當前任務"

    return {
        "time_str": now.strftime("%H:%M"),
        "segment": f"S{max(0, seg)}/8",
        "action": action,
        "word": word,
        "decomp": decomp,
        "almanac": almanac,
        "iching": iching_msg
    }

def send_to_discord(card):
    embed = {
        "title": f"🍅 番茄工作脈搏 | {card['time_str']} ({card['segment']})",
        "description": f"**｜行｜** {card['action']}",
        "color": 0x2ecc71, # 綠色
        "fields": [
            {
                "name": "📖 離線單字 (字)",
                "value": f"**{card['word']}**\n{card['decomp']}",
                "inline": False
            },
            {
                "name": "🏮 離線農民曆 (時)",
                "value": f"日宜：{card['almanac']['day_yi']} / 忌：{card['almanac']['day_ji']}\n{card['almanac']['branch']}時宜：{card['almanac']['hour_yi']} / 忌：{card['almanac']['hour_ji']}\n沖{card['almanac']['chong']}·煞{card['almanac']['sha']}",
                "inline": False
            },
            {
                "name": "☯ 易經護欄 (勢)",
                "value": card['iching'],
                "inline": False
            },
            {
                "name": "📝 狀態紀錄",
                "value": f"[點此打開本機脈搏紀錄網頁](file:///{BASE_DIR.resolve()}/index.html)",
                "inline": False
            }
        ],
        "footer": {
            "text": "Hermes Offline Micro-Card System v1.0"
        }
    }
    
    payload = {"embeds": [embed]}
    req = urllib.request.Request(
        WEBHOOK_URL, 
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status

if __name__ == "__main__":
    card_data = get_micro_card_data()
    # print(json.dumps(card_data, indent=2, ensure_ascii=False))
    # send_to_discord(card_data)
    print("✅ 離線微卡片資料已產生成功。")
