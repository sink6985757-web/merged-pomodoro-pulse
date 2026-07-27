#!/usr/bin/env python3
"""
pomodoro_focus.py — 專注 90 分鐘番茄鐘與休息提示
設計導向：專注深度、量化產出、休息補充、思維沉澱與專注力高原。
休息動作刻意具體（離螢幕/喝水/伸展），避免「繼續窩在椅子上滑手機」。
區段切換提醒：聚焦深度工作與學習的思維錨點。
"""
import random
from datetime import datetime, timezone, timedelta

# ── 休息動作庫（IC 工程師友善，必有「具體行動」）──
BREAK_ACTIONS = [
    "離開座位，走到茶水間倒一杯溫水。眼睛看 3 公尺外的東西 20 秒。",
    "站起來甩手 30 秒 + 轉肩 5 次 + 深呼吸 4-7-8 兩輪。",
    "走去洗手間，順便讓眼睛看看窗外綠色。回來前洗把臉。",
    "離開電腦 5 分鐘，做 10 個深蹲 + 10 個小腿伸展。",
    "起身走動 3 分鐘，順便拿下一區段要用的工具/資料。"
]

# ── 設計導向金句（專業工程師視角，非雞湯）──
DESIGN_QUOTES = [
    "工程不是追求完美的藝術，是處理限制與取捨的科學。",
    "修正錯誤的累積速度，是技術熟練度的最佳指標。",
    "你在賣的是『讓別人能放心交辦的能力』，這比技術本身值錢。",
    "不懂業務邏輯的工程師是操作者，懂的才是合作者。",
    "硬體極限與物理瓶頸是現實，不是誰的錯——接受它，再繞過它。",
    "測試跑出來的數字與 Log 會說真話。",
    "工具切換是基本技能，但『判斷該用哪個工具』才是核心設計能力。",
    "你現在修的每一個困難 Bug，都會變成未來面試的精彩故事。",
    "標準作業流程 (SOP) 是資產，能帶著走的那種——這比人際關係重要。",
    "防禦性設計的價值在於 Margin，你花的時間都是在買 Margin。",
    "不要只會解 Bug，要會『預測哪裡會有 Bug』——那才是架構師思維。",
    "實作與架構的距離，是閱讀規格書與原始碼的日積月累。",
    "過往學到的不只是特定領域知識，是『如何在壓力下維持穩定產出』——這個能力移植性極高。",
]

# ── 時段主訊息 ──
MESSAGES = {
    "morning": [
        "☀️ 第{seg}段啟動。",
        "早班思緒最清——這段留給最硬的架構審查或核心決策。",
        "打開工具前先想 30 秒：這 90 分鐘的單一最重要產出是什麼？寫下來。",
    ],
    "late_morning": [
        "⚡ 第{seg}段，深度工作高原。",
        "這段適合做需要連貫性的事——測試迴圈、重構收斂、複雜邏輯推演。",
        "關閉通訊軟體，專注產出。90 分鐘純專注，勝過 3 小時被打斷的對話。",
    ],
    "noon": [
        "🍱 午間衝刺段。",
        "完成這段再去吃飯——午餐會更香，下午也更有底氣。",
        "把今天的第一個里程碑設在這段，做完就是今天的 50%。",
    ],
    "afternoon": [
        "🍵 午後重置，第{seg}段。",
        "飯後專注會下滑是生理事實——用 25 分鐘小衝刺當暖機，再進入大任務。",
        "下午適合做審視型任務（Code Review、驗證報告、文件化 SOP）。",
    ],
    "late_afternoon": [
        "⚙️ 第{seg}段，體力管理時間。",
        "選一個『完成就能畫句點』的任務。不要再開新主題。",
        "數一下今天已完成的 — 你會發現比感覺中多。這是事實不是安慰。",
    ],
    "evening": [
        "🌙 第{seg}段，收尾模式。",
        "與其追進度，不如把今天的發現、SOP、未解題目沉澱進筆記。",
        "最後一段，做『讓明天上班第一分鐘更輕鬆』的事——這就是 90 分鐘最大的槓桿。",
    ],
    "after_six": [
        "🛑 已過 18:00，進入交棒模式。",
        "剩下能關的事 30 分鐘內關，關不掉的就寫 1 行交接註記。",
        "今天的最後一個工作，是確認明天的開始是輕的；準備登出。",
    ],
}


def pick_tone(hour: int) -> str:
    """Map hour-of-day to message-pool tone key (IC Layout variant)."""
    if hour < 10:
        return "morning"
    if hour < 12:
        return "late_morning"
    if hour < 13:
        return "noon"
    if hour < 15:
        return "afternoon"
    if hour < 17:
        return "late_afternoon"
    if hour < 18:
        return "evening"
    return "after_six"


def compute_segment(hour: int, minute: int) -> int:
    """Estimate today's pomodoro segment number (09:00 = segment 1)."""
    if hour < 9:
        return 0
    return ((hour - 9) * 60 + minute) // 90 + 1


def build_output() -> str:
    """Compose the full IC Layout pomodoro push message."""
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    hour = now.hour
    minute = now.minute
    time_str = f"{hour:02d}:{minute:02d}"

    segment = compute_segment(hour, minute)
    tone = pick_tone(hour)
    pool = MESSAGES.get(tone, MESSAGES["morning"])
    main_msg = random.choice(pool).format(seg=segment)
    break_action = random.choice(BREAK_ACTIONS)
    design_quote = random.choice(DESIGN_QUOTES)

    if 17 <= hour < 19:
        closing = (
            "\n\n🏁 **收工提醒**：明天連假，把今天做到 80%+ 的狀態交出去。"
            "剩下的讓它存在，明天的你會感謝今天願意停手的你。"
        )
    else:
        closing = ""

    return (
        f"🍅 **第{segment}段 | {time_str}**\n\n"
        f"{main_msg}\n\n"
        f"💧 **休息 5 分鐘**：{break_action}\n\n"
        f"🔧 **設計導向**：{design_quote}"
        f"{closing}"
    )


def main() -> None:
    """Build and print the IC Layout pomodoro push notification."""
    print(build_output())


if __name__ == "__main__":
    main()
