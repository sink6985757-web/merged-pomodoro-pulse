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
DEFAULT_WEBHOOK = "https://discord.com/api/webhooks/1532019963735314555/ZBIrVwPz_zd7aUkuLjBECMZyorjyB9YQ-e9kYvq0i0ITUmKzA1grXsKEnc43Hsc4r8k_"


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


def parse_card_lines(final_lines: list) -> dict:
    """Parse the raw pipe-delimited card lines into a structured dict.
    
    Expected format from build_message:
    ｜行｜HH:MM→HH:MM｜segment｜action
    ｜字｜word [pron]｜pos gloss ｜decomp
    ｜時｜hour_yi_ji ｜ day_yi_ji ｜ chong_sha ｜ priority
    ｜勢｜hexagrams｜moving_lines｜hint
    """
    data = {
        "time_range": "無", "segment": "無", "action": "無", "stoic_quote": "",
        "word": "無", "pron": "", "pos": "", "gloss": "無", "decomp": "",
        "day_yi_ji": "無", "hour_yi_ji": "無", "chong_sha": "無",
        "priority": "現實優先",
        "hexagrams": "無", "moving_lines": "靜", "hint": "無"
    }

    for line in final_lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("｜行｜"):
            # ｜行｜09:00→10:30｜工作 S3/8｜行動描述 💡 斯多噶：xxx
            parts = [p.strip() for p in line.split("｜") if p.strip()]
            if len(parts) >= 4:
                data["time_range"] = parts[1]
                data["segment"] = parts[2]
                raw_action = parts[3]
                # Strip Stoic quote suffix from action, save separately
                import re as _re
                m = _re.search(r'(.+?)\s*💡\s*斯多噶[：:]\s*(.+)$', raw_action)
                if m:
                    data["action"] = m.group(1).strip()
                    data["stoic_quote"] = m.group(2).strip()
                else:
                    data["action"] = raw_action

        elif line.startswith("｜字｜"):
            # ｜字｜word [pron]｜pos gloss ｜decomp
            parts = [p.strip() for p in line.split("｜") if p.strip()]
            if len(parts) >= 4:
                # parts[1] = "word [pron]" or just "word"
                wp = parts[1]
                if "[" in wp:
                    data["word"] = wp.split("[")[0].strip()
                    data["pron"] = "[" + wp.split("[", 1)[1]
                else:
                    data["word"] = wp
                # parts[2] = "pos gloss"  (e.g. "v 調查", "adv 快樂地")
                pg = parts[2]
                m = __import__("re").match(r'^([^0-9]\S+(?:,\s*\S+)*)\s+(.+)$', pg)
                if m:
                    data["pos"] = m.group(1)
                    data["gloss"] = m.group(2)
                else:
                    data["gloss"] = pg
                # parts[3] = decomp
                data["decomp"] = parts[3]
            elif len(parts) >= 3:
                data["word"] = parts[1]
                data["gloss"] = parts[2]

        elif line.startswith("｜時｜"):
            # ｜時｜巳時 宜.../忌... ｜ 日宜.../忌... ｜ 沖(戊戌)狗煞南方 ｜ 現實優先
            parts = [p.strip() for p in line.split("｜") if p.strip()]
            if len(parts) >= 4:
                data["hour_yi_ji"] = parts[1]   # 巳時 宜出行...
                data["day_yi_ji"] = parts[2]     # 日宜納採...
                data["chong_sha"] = parts[3]      # 沖(戊戌)...
            if len(parts) >= 5:
                data["priority"] = parts[4]

        elif line.startswith("｜勢｜"):
            # ｜勢｜第10卦 ䷉ 天澤履｜靜｜護欄提示
            parts = [p.strip() for p in line.split("｜") if p.strip()]
            if len(parts) >= 4:
                data["hexagrams"] = parts[1]
                data["moving_lines"] = parts[2]
                data["hint"] = parts[3]
            elif len(parts) >= 3:
                data["hexagrams"] = parts[1]
                data["hint"] = parts[2]

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
    test_label = None
    
    # 0. Check for forced time backdoor
    forced_hhmm, loaded_label = pomodoro_chat_original.load_forced_time()
    if forced_hhmm:
        now = now.replace(hour=forced_hhmm[0], minute=forced_hhmm[1], second=0, microsecond=0)
        test_label = loaded_label

    if args.at:
        try:
            hh, mm = pomodoro_chat_original.parse_hhmm(args.at)
            now = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        except Exception as e:
            print(f"❌ 設定時間失敗 (格式應為 HH:MM): {e}", file=sys.stderr)
            sys.exit(1)

    # 1. Build the raw message text from the core engine
    raw_message = pomodoro_chat_original.build_message(now, test_label=test_label, consume_vocab=args.consume)
    if not raw_message:
        sys.exit(0)

    # 2. Split into lines (build_message already includes full decomp from consumed entry)
    final_lines = raw_message.splitlines()
    
    # 3. Append the working URL
    public_index_url = "https://htmlpreview.github.io/?https://github.com/sink6985757-web/merged-pomodoro-pulse/blob/master/index.html"
    final_lines.append(f"｜記｜[點此開啟紀錄儀表板]({public_index_url})")
    
    final_output = "\n".join(final_lines)
    payload = build_discord_embed(final_lines, now)

    if args.dry_run:
        print("🔍 [Dry Run] 產生的 Markdown 卡片預覽:")
        print(final_output)
        print("\n🎨 [Dry Run] 產生的 Discord Rich Embed JSON (iPhone 12 專屬一頁式卡片):")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 4. Resolve webhook and send
    webhook_url = load_webhook_url(args.webhook)
    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        print(final_output)
        sys.exit(0)

    print(f"🚀 正在傳送番茄工作脈搏 Rich Embed 卡片 ({now.strftime('%H:%M')}) 至 Discord...")
    status = send_to_discord(webhook_url, payload)
    if status == 204 or status == 200:
        print("✅ 播報傳送成功！")
    else:
        print(f"❌ 傳送失敗，HTTP 狀態碼: {status}", file=sys.stderr)
        sys.exit(1)


def build_discord_embed(final_lines: list, now: datetime) -> dict:
    """Build a concise, structured Discord Embed from parsed card lines."""
    time_str = now.strftime("%H:%M")
    hour = now.hour
    
    # Theme color based on time of day
    if 6 <= hour < 9:
        color = 0x2ecc71  # Emerald Green
    elif 9 <= hour < 15:
        color = 0x3498db  # Bright Blue
    elif 15 <= hour < 18:
        color = 0xe67e22  # Amber Gold
    else:
        color = 0x9b59b6  # Royal Purple

    data = parse_card_lines(final_lines)
    public_index_url = "https://htmlpreview.github.io/?https://github.com/sink6985757-web/merged-pomodoro-pulse/blob/master/index.html"
    
    # 行: compact time + action
    time_seg = f"{data['time_range']}　{data['segment']}" if data['segment'] != "無" else data['time_range']
    
    # 字: single compact line
    word_line = f"**{data['word']}**"
    if data['pron']:
        word_line += f" `{data['pron']}`"
    if data['pos'] or data['gloss'] != "無":
        word_line += f"　*{data['pos']}.* {data['gloss']}" if data['pos'] else f"　{data['gloss']}"
    if data['decomp']:
        word_line += f"\n`{data['decomp']}`"
    
    # 時: trim labels, use slash compact
    time_line = f"⏰ {data['hour_yi_ji']}"
    if data['day_yi_ji'] != "無":
        time_line += f"\n📅 {data['day_yi_ji']}"
    time_line += f"\n⚠️ {data['chong_sha']}"
    if data['priority'] != "現實優先":
        time_line += f"\n🎯 {data['priority']}"
    
    # 勢: compact
    hex_line = f"☯ {data['hexagrams']}"
    if data['moving_lines'] != "靜":
        hex_line += f"　🎴 {data['moving_lines']}"
    hex_line += f"\n🛡️ {data['hint']}"

    embed = {
        "title": f"🍅 番茄工作脈搏 · {time_str}",
        "color": color,
        "fields": [
            {
                "name": "🎯 行·專注",
                "value": f"🕐 {time_seg}\n🚀 {data['action']}",
                "inline": False
            },
            {
                "name": "📖 單字",
                "value": word_line,
                "inline": False
            },
            {
                "name": "🗓️ 宜忌",
                "value": time_line,
                "inline": False
            },
            {
                "name": "☯️ 卦勢",
                "value": hex_line,
                "inline": False
            },
            {
                "name": "📊 紀錄",
                "value": f"[📈 開啟]({public_index_url})",
                "inline": False
            }
        ],
        "footer": {
            "text": "零 Token · Merged Pomodoro Pulse"
        }
    }
    # Add Stoic quote as bottom field if present
    stoic_val = data.get("stoic_quote", "").strip()
    if stoic_val:
        embed["fields"].append({
            "name": "💡 斯多噶",
            "value": f"*{stoic_val}*",
            "inline": False
        })
    return {"embeds": [embed]}


if __name__ == "__main__":
    main()
