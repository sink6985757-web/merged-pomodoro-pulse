# 🍅 番茄工作脈搏系統 · Merged Pomodoro Pulse

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)

一個 **100% 離線、零 Token 消耗、極致隱私** 的個人時間管理與決策護欄系統。
整合「番茄鐘微卡片（Discord）」與「整點工作脈搏（本機紀錄）」，協助開發者建立高效的專專注與回顧循環。

---

## 🌟 系統架構

系統由兩個高度互補的模組構成：
1. **📢 播報中樞 (`unified_broadcaster.py`)**：整點發送「行、字、時、勢」四維 Discord 卡片，整合字根學習、農民曆與易經決策。
2. **💓 紀錄中樞 (`index.html`)**：單檔 Web App，10 秒內快速登記整點狀態，累積精力數據，內建一鍵複製 AI 回顧 Prompt。

```text
merged-pomodoro-pulse/
├── unified_broadcaster.py      # 🚀 播報主程式 (Discord 卡片生成)
├── pomodoro_chat_original.py   # 🧠 核心計算引擎 (單字、易經、農民曆)
├── lunar_almanac.py            # 🏮 備用離線農民曆 (干支推算)
├── pomodoro_iching_data.py     # ☯ 易經資料庫 (曾仕強教授 64 卦、384 爻辭與變爻)
├── pomodoro_focus.py           # 🔧 專注 90 分鐘番茄鐘邏輯
├── vocab_decomp_extract.py     # 📖 離線字根拆解核心工具
├── index.html                  # 📊 脈搏紀錄儀表板 (LocalStorage 單檔)
├── requirements.txt            # 📦 相依性清單 (僅 Python 標準函式庫)
├── AGENTS.md                   # 🤖 專案 Agent 協作共用設定
├── handoff.md                  # 📝 專案開發交接紀錄
├── data/                       # 🔒 本機資料夾 (已列入 .gitignore，存於 LOCALAPPDATA\hermes\data)
│   ├── vocab_decomposition_v5.json # V5 11,464 單字大字庫 (本機核心，全離線字根權威校正)
│   └── vocab_decomposition.json    # V4 離線字根資料庫 (本機備用)
└── tests/                      # 🚦 自動化測試套件 (100% 綠燈驗證)
    ├── verify_pomodoro_final.py         # 生產路徑與時段覆蓋
    ├── verify_pomodoro_enhancements.py  # 增強版合約與單字庫
    ├── verify_vocab_decomposition.py    # 字根重複性校驗
    ├── verify_iching.py                 # 易經結構與變爻校驗
    └── ... (共 6 項測試校驗檔案)
```

---

## 🚀 核心特色

### 🎴 四維整點微卡片 (Discord)
每小時播報一次，完美對齊 90 分鐘專注節奏（06:00 ~ 18:00 共 8 區段）：
- **｜ 行 ｜**：當前時段具體、可驗證的工作指引 ＋ 融合《每天讀點斯多噶》366 天每日精髓哲思（單行精簡，兼具執行力與心法）。
- **｜ 字 ｜**：精選 **11,464** 個 CEFR/學測指考大考核心單字與離線字根拆解，權威字典級釋義校正。
- **｜ 時 ｜**：網路優先抓取 Gooday 官網宜忌；斷線自動切換本機干支推算。
- **｜ 勢 ｜**：模擬「三錢法」起卦，支援完整變爻規則，提供專屬決策建議。

### 📊 輕量脈搏紀錄器 (`index.html`)
- **極速登記**：10 秒快速記錄感受（−2 ~ +2）、精力（1 ~ 5）與活動。
- **絕對隱私**：100% 儲存於瀏覽器 `localStorage`，數據不落雲端。
- **AI 賦能**：內建「30 天回顧 Prompt」，一鍵生成深度精力與軌跡分析。

---

## ⚙️ 快速開始

### 1. 安裝與設定
```bash
git clone https://github.com/sink6985757-web/merged-pomodoro-pulse.git
cd merged-pomodoro-pulse
```
建立 `.env` 檔案並填入 Discord Webhook：
```env
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

### 2. 測試播報
```bash
# 模擬 09:00 播報（不發送且不消耗單字庫）
python unified_broadcaster.py --at 09:00 --dry-run

# 真正消耗一個單字並發送至 Discord
python unified_broadcaster.py --consume
```

### 3. 設定自動化排程 (Cron)
建議在工作日 06:00 ~ 18:00 的整點執行：
```cron
0 6-18 * * * cd /path/to/merged-pomodoro-pulse && python unified_broadcaster.py --consume
```

---

## 🤖 Hermes Agent 快速部署

如果您使用 **Hermes Agent**，可透過以下指令一鍵裝載：

1. **安裝 Skill 指引**：
   ```bash
   hermes skills install https://raw.githubusercontent.com/sink6985757-web/merged-pomodoro-pulse/master/SKILL.md --name pomodoro-micro-card
   ```
2. **建立排程 (Cron)**：
   ```bash
   hermes cron create "0 6-18 * * *" \
     --name "merged-pomodoro-pulse" \
     --prompt "Run the Python script at <絕對路徑>/unified_broadcaster.py with --consume using the terminal tool, timeout 60s. Output its stdout EXACTLY as-is." \
     --deliver "discord:<頻道ID>"
   ```
3. **自動化驗證**：
   ```bash
   python tests/verify_pomodoro_final.py
   ```

---

## 🔒 系統安全與免責聲明

- **單字冪等性**：消耗狀態紀錄於 `pomodoro_vocab_state.json`，同一個 Cycle 內單字絕不重複，自動循環。
- **併發防護**：內建**檔案鎖 (File Lock)** 避免多行程衝突與重複發送。
- **免責聲明**：易經占卜僅作決策符號學引導，不構成投資/職涯建議。農民曆與字根語料皆取自公開來源。

---

MIT License © 2026 sink6

## Agent workflow 與版本紀錄

- GitHub canonical：`sink6985757-web/merged-pomodoro-pulse`；`data/vocab_corpus/` 是已登記專案資料來源。
- 本 README 是人類與 Agent／Tool 的安裝、使用、版本與公開文案；近期變更見 [`CHANGELOG.md`](CHANGELOG.md)。
- 每次收工更新 CHANGELOG 與 handoff；GitHub delivery 前更新本 README。
- 外部知識庫為 `ON_DEMAND_ONLY`，不屬於 initial／startup／shutdown。
