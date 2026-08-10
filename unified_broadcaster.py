#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unified_broadcaster.py

Unified Discord Broadcaster for Merged Pomodoro Pulse.
Integrates full dynamic calculations from pomodoro_chat_original.py
and lunar_almanac.py, outputting a highly structured and aesthetic CJK
Discord Embed. Content generation is offline by default; Hermes can deliver
stdout without invoking a model, while direct webhook delivery remains optional.
"""
import sys
import os
import json
import argparse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 1. Resolve the adjacent workspace/Hermes data root without discarding an
# explicit portable override.
BASE_DIR = Path(__file__).parent.resolve()
if not os.environ.get("POMODORO_DATA_DIR"):
    if (BASE_DIR / "data").is_dir():
        os.environ["POMODORO_DATA_DIR"] = str(BASE_DIR)
    elif BASE_DIR.name.lower() == "scripts" and (BASE_DIR.parent / "data").is_dir():
        os.environ["POMODORO_DATA_DIR"] = str(BASE_DIR.parent)

# Import the core logic (now that POMODORO_DATA_DIR is set)
try:
    import pomodoro_chat_original
except ImportError as e:
    print(f"❌ 無法載入核心模組 pomodoro_chat_original: {e}", file=sys.stderr)
    sys.exit(1)

TZ_TAIPEI = timezone(timedelta(hours=8))
PUBLIC_RECORD_URL = "https://htmlpreview.github.io/?https://github.com/sink6985757-web/merged-pomodoro-pulse/blob/master/index.html"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Merged Pomodoro Pulse Discord Broadcaster")
    parser.add_argument("--at", type=str, help="設定特定時間 (格式 HH:MM，例 --at 09:00)")
    parser.add_argument("--consume", action="store_true", help="是否消耗單字庫中的單字 (Cron 執行時請啟用)")
    parser.add_argument("--webhook", type=str, help="指定自訂 Discord Webhook URL")
    parser.add_argument("--dry-run", action="store_true", help="預覽 Embed Payload，不實際發送到 Discord")
    parser.add_argument(
        "--online-almanac",
        action="store_true",
        help="明確允許抓取 Gooday；預設內容完全使用本機資料",
    )
    return parser.parse_args()


def load_webhook_url(args_webhook=None) -> str:
    """Resolve Webhook URL following hierarchical priority:
    1. Command line --webhook argument
    2. Environment variable DISCORD_WEBHOOK_URL
    3. Local .env file (DISCORD_WEBHOOK_URL=...)
    No webhook is bundled in source control or portable packages.
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

    return ""


def parse_card_lines(final_lines: list) -> dict:
    """Parse the raw pipe-delimited card lines into a structured dict.
    
    Expected format from build_message:
    ｜行｜HH:MM→HH:MM｜segment｜action
    ｜字｜root＝meaning｜word gloss｜課：course｜章：chapter｜單元：lesson｜節點：phase｜音：pron｜詞：pos｜拆：decomp｜族：family｜答：answer｜例：example｜譯：translation
    舊版相容：｜字｜word [pron]｜pos gloss｜decomp
    ｜時｜hour_yi_ji ｜ day_yi_ji ｜ chong_sha ｜ priority
    ｜勢｜hexagrams｜moving_lines｜hint
    """
    data = {
        "time_range": "無", "segment": "無", "action": "無", "stoic_quote": "",
        "word": "無", "pron": "", "pos": "", "gloss": "無", "decomp": "",
        "course": "", "chapter": "", "lesson": "", "family": "",
        "root": "", "root_meaning": "", "takeaway": "", "question": "", "answer": "",
        "example": "", "memory_cue": "",
        "translation": "",
        "review_stage": "輪播·輕量複現",
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
            parts = [p.strip() for p in line.split("｜") if p.strip()]
            if len(parts) >= 3 and "＝" in parts[1]:
                # New root-family course card.
                data["root"], data["root_meaning"] = (
                    value.strip() for value in parts[1].split("＝", 1)
                )
                word_gloss = parts[2].split(maxsplit=1)
                data["word"] = word_gloss[0]
                data["gloss"] = word_gloss[1] if len(word_gloss) > 1 else "無"
                for part in parts[3:]:
                    if part.startswith(("提示：", "聯想：")):
                        data["takeaway"] = part.split("：", 1)[1].strip()
                    elif part.startswith("答："):
                        data["answer"] = part[len("答：") :].strip().strip("|")
                    elif part.startswith("例："):
                        data["example"] = part[len("例：") :].strip()
                    elif part.startswith("讀："):
                        data["memory_cue"] = part[len("讀：") :].strip()
                    elif part.startswith(("階段：", "節點：")):
                        data["review_stage"] = part.split("：", 1)[1].strip()
                    elif part.startswith("課："):
                        data["course"] = part[len("課：") :].strip()
                    elif part.startswith("章："):
                        data["chapter"] = part[len("章：") :].strip()
                    elif part.startswith("單元："):
                        data["lesson"] = part[len("單元：") :].strip()
                    elif part.startswith("族："):
                        data["family"] = part[len("族：") :].strip()
                    elif part.startswith("音："):
                        data["pron"] = part[len("音：") :].strip()
                    elif part.startswith("詞："):
                        data["pos"] = part[len("詞：") :].strip()
                    elif part.startswith("譯："):
                        data["translation"] = part[len("譯：") :].strip()
                    elif part.startswith("問："):
                        qa = part[len("問：") :].strip()
                        match = __import__("re").match(r"(.+?)\s+答：\|\|(.+?)\|\|$", qa)
                        if match:
                            data["question"] = match.group(1).strip()
                            data["answer"] = match.group(2).strip()
                        else:
                            data["question"] = qa
                    elif part.startswith("拆："):
                        data["decomp"] = part[len("拆：") :].strip()
                    elif not data["decomp"]:
                        data["decomp"] = part
            elif len(parts) >= 4:
                # Legacy single-word card.
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


def build_english_display(data: dict) -> str:
    """Render the finalized compact course-unit card with no hidden answer."""
    lines: list[str] = []
    course_path = " › ".join(value for value in (data["course"], data["chapter"]) if value)
    if course_path:
        lines.append(f"🎓 **{course_path}**")
    if data["lesson"]:
        lines.append(f"📍 {data['lesson']}　`{data['review_stage']}`")
    else:
        lines.append(f"🔁 `{data['review_stage']}`")
    if data["root"]:
        lines.append(f"🧠 **{data['root']}＝{data['root_meaning']}**")
    word = f"🧩 **{data['word']}**"
    if data["pron"]:
        word += f" `{data['pron']}`"
    if data["pos"]:
        word += f" *{data['pos']}.*"
    if data["gloss"] != "無":
        word += f" {data['gloss']}"
    lines.append(word)
    if data["decomp"]:
        lines.append(f"`{data['decomp']}`")
    if data["family"]:
        lines.append(f"🌿 {data['family']}")
    if data["takeaway"]:
        lines.append(f"🔗 {data['takeaway']}")
    if data["answer"]:
        lines.append(f"✅ **答案：{data['answer']}**")
    if data["example"]:
        lines.append(f"🗣️ {data['example']}")
    if data["translation"]:
        lines.append(f"🌏 {data['translation']}")
    return "\n".join(lines)


def build_markdown_fallback(data: dict, now: datetime) -> str:
    """Build the same four-section card used by Discord Embed delivery."""
    time_seg = f"{data['time_range']}　{data['segment']}" if data["segment"] != "無" else data["time_range"]
    almanac = f"⏰ {data['hour_yi_ji']}"
    if data["day_yi_ji"] != "無":
        almanac += f"\n📅 {data['day_yi_ji']}"
    almanac += f"\n⚠️ {data['chong_sha']}"
    reflection = f"☯ {data['hexagrams']}"
    if data["moving_lines"] != "靜":
        reflection += f"　🎴 {data['moving_lines']}"
    reflection += f"\n🪞 易經反思：{data['hint']}"
    if data.get("stoic_quote"):
        reflection += f"\n💡 斯多葛：{data['stoic_quote']}"
    return (
        f"🍅 **番茄工作脈搏 · {now.strftime('%H:%M')}**\n"
        f"🕐 `{time_seg}`\n\n"
        f"**📊 紀錄**\n[📈 開啟紀錄儀表板]({PUBLIC_RECORD_URL})\n\n"
        f"**📖 英文**\n{build_english_display(data)}\n\n"
        f"**🗓️ 農民曆**\n{almanac}\n\n"
        f"**☯️ 易經 × 斯多葛**\n{reflection}\n\n"
        "`反思參考，不代替現實判斷 · 零 Token`"
    )


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

    if not args.online_almanac:
        os.environ["POMODORO_OFFLINE"] = "1"
    
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
    final_lines.append(f"｜記｜[點此開啟紀錄儀表板]({PUBLIC_RECORD_URL})")
    data = parse_card_lines(final_lines)
    final_output = build_markdown_fallback(data, now)
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
        # Existing zero-token Hermes contract: stdout is the single delivery
        # payload and Hermes performs the configured Discord fan-out.
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
    time_seg = f"{data['time_range']}　{data['segment']}" if data['segment'] != "無" else data['time_range']
    word_line = build_english_display(data)

    time_line = f"⏰ {data['hour_yi_ji']}"
    if data['day_yi_ji'] != "無":
        time_line += f"\n📅 {data['day_yi_ji']}"
    time_line += f"\n⚠️ {data['chong_sha']}"
    
    hex_line = f"☯ {data['hexagrams']}"
    if data['moving_lines'] != "靜":
        hex_line += f"　🎴 {data['moving_lines']}"
    hex_line += f"\n🪞 **易經反思：**{data['hint']}"
    if data.get("stoic_quote"):
        hex_line += f"\n💡 **斯多葛：**{data['stoic_quote']}"

    embed = {
        "title": f"🍅 番茄工作脈搏 · {time_str}",
        "description": f"🕐 `{time_seg}`",
        "color": color,
        "fields": [
            {
                "name": "📊 紀錄",
                "value": f"[📈 開啟紀錄儀表板]({PUBLIC_RECORD_URL})",
                "inline": False
            },
            {
                "name": "📖 英文",
                "value": word_line,
                "inline": False
            },
            {
                "name": "🗓️ 農民曆",
                "value": time_line,
                "inline": False
            },
            {
                "name": "☯️ 易經 × 斯多葛",
                "value": hex_line,
                "inline": False
            }
        ],
        "footer": {
            "text": "反思參考，不代替現實判斷 · 零 Token · Merged Pomodoro Pulse"
        }
    }
    return {"embeds": [embed]}


if __name__ == "__main__":
    main()
