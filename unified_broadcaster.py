#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unified_broadcaster.py

Unified Discord Broadcaster for Merged Pomodoro Pulse.
Integrates full dynamic calculations from pomodoro_chat_original.py
and lunar_almanac.py, outputting a highly structured and aesthetic CJK
Discord Embed. Supports portability, custom webhooks, and manual testing.
"""
import sys
import os
import json
import argparse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 1. Force the database and state directories to be self-contained in this workspace
BASE_DIR = Path(__file__).parent.resolve()
if (BASE_DIR / "data").exists():
    os.environ["POMODORO_DATA_DIR"] = str(BASE_DIR)
else:
    # If running in Hermes live scripts directory, let it fall back to standard
    # LOCALAPPDATA/hermes native Windows pathing (clear any override)
    if "POMODORO_DATA_DIR" in os.environ:
        del os.environ["POMODORO_DATA_DIR"]

# Import the core logic (now that POMODORO_DATA_DIR is set)
try:
    import pomodoro_chat_original
except ImportError as e:
    print(f"❌ 無法載入核心模組 pomodoro_chat_original: {e}", file=sys.stderr)
    sys.exit(1)

TZ_TAIPEI = timezone(timedelta(hours=8))
DEFAULT_WEBHOOK = "YOUR_DISCORD_WEBHOOK_URL_HERE"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Merged Pomodoro Pulse Discord Broadcaster")
    parser.add_argument("--at", type=str, help="設定特定時間 (格式 HH:MM，例 --at 09:00)")
    parser.add_argument("--consume", action="store_true", help="是否消耗單字庫中的單字 (Cron 執行時請啟用)")
    parser.add_argument("--webhook", type=str, help="指定自訂 Discord Webhook URL")
    parser.add_argument("--dry-run", action="store_true", help="預覽 Embed Payload，不實際發送到 Discord")
    return parser.parse_args()


def load_webhook_url(args_webhook=None) -> str:
    """Resolve Webhook URL following hierarchical priority:
    1. Command line --webhook argument
    2. Environment variable DISCORD_WEBHOOK_URL
    3. Local .env file (DISCORD_WEBHOOK_URL=...)
    4. Hardcoded constant
    """
    if args_webhook:
        return args_webhook

    env_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if env_webhook:
        return env_webhook

    # Check local .env file
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.split("=", 1)
                    if key.strip() == "DISCORD_WEBHOOK_URL":
                        return val.strip().strip("'\"")
        except Exception:
            pass

    return DEFAULT_WEBHOOK


def parse_card_lines(msg_text: str, now: datetime) -> dict:
    """Parse the raw four-line text output from build_message into structured dict."""
    lines = msg_text.splitlines()
    data = {
        "time_range": "無",
        "segment": "無",
        "action": "無",
        "word": "無",
        "pron": "",
        "pos": "",
        "gloss": "無",
        "decomp": "",
        "day_yi_ji": "無",
        "hour_yi_ji": "無",
        "chong_sha": "無",
        "priority": "現實優先",
        "hexagrams": "無",
        "moving_lines": "靜",
        "hint": "無"
    }

    # Fetch vocabulary details directly from the dictionary to get root-decomposition
    vocab_entry = pomodoro_chat_original.choose_vocab_entry(now, consume=False)
    if vocab_entry:
        data["word"] = vocab_entry.get("word", "")
        data["pron"] = vocab_entry.get("pron", "")
        data["pos"] = vocab_entry.get("pos", "")
        data["gloss"] = vocab_entry.get("gloss", "")
        data["decomp"] = vocab_entry.get("decomp", "")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("｜行｜"):
            # Format: ｜行｜09:00→10:30｜先修 S3/8｜只讀一頁...
            parts = [p.strip() for p in line.split("｜") if p.strip()]
            if len(parts) >= 4:
                data["time_range"] = parts[1]
                data["segment"] = parts[2]
                data["action"] = parts[3]

        elif line.startswith("｜字｜") and not vocab_entry:
            # Fallback parsing if dict was not retrieved
            parts = [p.strip() for p in line.split("｜") if p.strip()]
            if len(parts) >= 3:
                data["word"] = parts[1]
                data["gloss"] = parts[2]

        elif line.startswith("｜時｜"):
            # Format: ｜時｜日宜...｜巳宜...｜沖...｜現實優先
            parts = [p.strip() for p in line.split("｜") if p.strip()]
            if len(parts) >= 5:
                data["day_yi_ji"] = parts[1]
                data["hour_yi_ji"] = parts[2]
                data["chong_sha"] = parts[3]
                data["priority"] = parts[4]

        elif line.startswith("｜勢｜"):
            # Format: ｜勢｜第25卦 ䷘...｜初、四｜守正可保無災
            parts = [p.strip() for p in line.split("｜") if p.strip()]
            if len(parts) >= 4:
                data["hexagrams"] = parts[1]
                data["moving_lines"] = parts[2]
                data["hint"] = parts[3]

    return data


def build_discord_payload(data: dict, now: datetime) -> dict:
    """Build a rich, beautiful Discord Embed payload from structured data."""
    # Build title with time and segment
    time_str = now.strftime("%H:%M")
    segment_str = data["segment"] if data["segment"] != "無" else "日常"
    
    # Pre-calculate file path URL to avoid backslashes inside f-string (Python 3.8-3.11 compatibility)
    local_index_path = str(BASE_DIR / 'index.html').replace('\\', '/')

    # Emojis and CJK format
    embed = {
        "title": f"🍅 番茄工作脈搏 | {time_str} ({segment_str})",
        "color": 15158332,  # Tomato Red (#E74C3C)
        "timestamp": now.isoformat(),
        "fields": [
            {
                "name": "｜ 行 ｜ 專注行動 (90 分鐘節奏)",
                "value": f"🕒 **時段**: `{data['time_range']}`\n🚀 **行動**: {data['action']}",
                "inline": False
            },
            {
                "name": "｜ 字 ｜ 零 Token 英文字根",
                "value": f"📝 **單字**: **{data['word']}**  `{data['pron']}`\n"
                         f"🏷️ **釋義**: *{data['pos']}.* {data['gloss']}" +
                         (f"\n📖 **字根**: `{data['decomp']}`" if data['decomp'] else ""),
                "inline": False
            },
            {
                "name": "｜ 時 ｜ 離線農民曆宜忌",
                "value": f"📅 **今日宜忌**: {data['day_yi_ji']}\n"
                         f"⏰ **時辰宜忌**: {data['hour_yi_ji']}\n"
                         f"⚠️ **沖煞提示**: `{data['chong_sha']}`\n"
                         f"🎯 **決策導向**: {data['priority']}",
                "inline": False
            },
            {
                "name": "｜ 勢 ｜ 易經決策護欄",
                "value": f"☯ **卦象**: {data['hexagrams']}\n"
                         f"🎴 **變爻**: `{data['moving_lines']}`\n"
                         f"🛡️ **決策護欄**: {data['hint']}",
                "inline": False
            },
            {
                "name": "📝 本機狀態紀錄",
                "value": f"[開啟本機工作脈搏紀錄儀表板](file:///{local_index_path})",
                "inline": False
            }
        ],
        "footer": {
            "text": "Hermes Offline Micro-Card System v2.0"
        }
    }
    return {"embeds": [embed]}


def build_markdown_fallback(data: dict, now: datetime) -> str:
    """Build a rich, beautiful Discord Markdown fallback message (without Embed)
    when no Webhook URL is configured.
    """
    time_str = now.strftime("%H:%M")
    segment_str = data["segment"] if data["segment"] != "無" else "日常"
    
    # Use GitHack to serve the repository's index.html as a web page, 
    # making it clickable on Discord across mobile and desktop.
    public_index_url = "https://raw.githack.com/sink6985757-web/merged-pomodoro-pulse/master/index.html"
    
    decomp_str = f" `{data['decomp']}`" if data['decomp'] else ""
    
    md = f"""🍅 **番茄工作脈搏 | {time_str} ({segment_str})**
> **行**｜`{data['time_range']}` {data['action']}
> **字**｜**{data['word']}** `{data['pron']}` (*{data['pos']}.*) {data['gloss']}{decomp_str}
> **時**｜**日**: {data['day_yi_ji']}／**時**: {data['hour_yi_ji']}／`{data['chong_sha']}`
> **勢**｜{data['hexagrams']} (變爻: `{data['moving_lines']}`)
> **護**｜{data['hint']}
> 
> 🔗 [記]({public_index_url})"""
    return md


def send_to_discord(webhook_url: str, payload: dict) -> int:
    """Send payload to Discord webhook and return HTTP status code."""
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except Exception as e:
        print(f"❌ 傳送至 Discord 失敗: {e}", file=sys.stderr)
        return 500


def main():
    args = parse_arguments()
    
    # Setup correct local timezone datetime
    now = datetime.now(TZ_TAIPEI)
    if args.at:
        try:
            hh, mm = pomodoro_chat_original.parse_hhmm(args.at)
            now = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        except Exception as e:
            print(f"❌ 設定時間失敗 (格式應為 HH:MM): {e}", file=sys.stderr)
            sys.exit(1)

    # 1. Build the raw message text from the core engine
    raw_message = pomodoro_chat_original.build_message(now, consume_vocab=args.consume)
    if not raw_message:
        sys.exit(0)

    # 2. Parse out the vocab entry so we can restore the decomp to the string
    vocab_entry = pomodoro_chat_original.choose_vocab_entry(now, consume=False)
    
    # Reconstruct the strict 5-line format
    lines = raw_message.splitlines()
    final_lines = []
    for line in lines:
        if line.startswith("｜字｜") and vocab_entry and vocab_entry.get("decomp"):
            # Restore the decomp (etymology) data to the end of the line
            line = f"{line}｜{vocab_entry['decomp']}"
        final_lines.append(line)
    
    # 3. Append the working URL
    public_index_url = "https://htmlpreview.github.io/?https://github.com/sink6985757-web/merged-pomodoro-pulse/blob/master/index.html"
    final_lines.append(f"｜記｜[點此開啟紀錄儀表板]({public_index_url})")
    
    final_output = "\n".join(final_lines)

    if args.dry_run:
        print("🔍 [Dry Run] 產生的本機 Markdown 卡片預覽如下:")
        print(final_output)
        sys.exit(0)

    # 4. Resolve webhook and send
    webhook_url = load_webhook_url(args.webhook)
    if webhook_url == DEFAULT_WEBHOOK:
        print(final_output)
        sys.exit(0)

    print(f"🚀 正在傳送番茄工作脈搏 ({now.strftime('%H:%M')}) 至 Discord...")
    status = send_to_discord(webhook_url, payload)
    if status == 204 or status == 200:
        print("✅ 播報傳送成功！")
    else:
        print(f"❌ 傳送失敗，HTTP 狀態碼: {status}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
