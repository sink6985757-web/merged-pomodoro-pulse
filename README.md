# 🍅 番茄工作脈搏系統 · Merged Pomodoro Pulse

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)

一個 **內容生成完全離線、零 Token 消耗、極致隱私** 的個人時間管理與決策護欄系統。只有 Hermes 將結果送到 Discord（或選用 webhook 直送）時需要網路。
整合「番茄鐘微卡片（Discord）」與「整點工作脈搏（本機紀錄）」，協助開發者建立高效的專注與回顧循環。

## 部署狀態（2026-08-10）

| 層級 | 狀態 | 說明 |
|---|---|---|
| 本機工作樹 | `VERIFIED_LOCAL` | 新版英文資料、離線 runtime 與完整迴歸測試已通過 |
| GitHub `master` | `VERIFIED_REMOTE` | 新版程式、README、英文資料與 installer 已完成 delivery 並回讀 |
| 另一台 Hermes | `PENDING` | 尚未安裝新版；既有 `no_agent` cron 與 Discord delivery 未變更 |

這份 README 可作為 GitHub 新版交付證據；Hermes 目標機部署仍須依交接文件另外執行與驗證。

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
├── build_english_hourly_cards.py # 🎓 Drive 課程 → 每小時英文卡資料庫
├── normalize_stoic_daily_quotes.py # 🧹 正規化 366 日標題與資料結構
├── install_offline_runtime.py  # 📦 複製精簡 runtime 到 Hermes，不更動排程
├── index.html                  # 📊 脈搏紀錄儀表板 (LocalStorage 單檔)
├── requirements.txt            # 📦 相依性清單 (僅 Python 標準函式庫)
├── AGENTS.md                   # 🤖 專案 Agent 協作共用設定
├── handoff.md                  # 📝 專案開發交接紀錄
├── data/
│   ├── english_hourly_cards.json   # 可攜式 128 單元課程卡（不含影片/音訊）
│   ├── stoic_daily_quotes.json     # 可攜式 366 日行動輔助摘要
│   ├── vocab_decomposition_v5.json # V5 11,464 單字大字庫 (本機、忽略追蹤)
│   └── vocab_decomposition.json    # V4 離線字根資料庫 (本機、忽略追蹤)
└── tests/                      # 🚦 自動化測試套件 (100% 綠燈驗證)
    ├── verify_english_hourly_cards.py   # Drive 課程卡來源與顯示合約
    ├── verify_english_content_accuracy.py # 英文拼字、構詞、提示與例句校驗
    ├── verify_stoic_daily_quotes.py     # 366 日日期覆蓋、字形與 schema 校驗
    ├── verify_offline_runtime.py        # 禁網路內容生成與可攜部署驗證
    ├── verify_pomodoro_final.py         # 生產路徑與時段覆蓋
    ├── verify_pomodoro_enhancements.py  # 增強版合約與單字庫
    ├── verify_vocab_decomposition.py    # 字根重複性校驗
    ├── verify_iching.py                 # 易經結構與變爻校驗
    └── ...                              # 其他番茄鐘與易經迴歸測試
```

---

## 🚀 核心特色

### 🎴 四維整點微卡片 (Discord)
每小時播報一次，完美對齊 90 分鐘專注節奏（06:00 ~ 18:00 共 8 區段）：
- **｜ 行 ｜**：當前時段具體、可驗證的工作指引 ＋ 融合《每天讀點斯多噶》366 天每日精髓哲思（單行精簡，兼具執行力與心法）。
- **｜ 字 ｜**：每小時一個「課程字根記憶家族」：字根定義、代表字拆解、影片重點與一題可揭曉答案的回想題。課程庫含 3 套課程、128 個正式單元；128/128 代表字都有結構化字根對應，128/128 回想題使用來源例句填空，另有 15 句窄範圍文法／用字校正。只有本機另有舊 V5 字庫且課程資料不可用時，才會回退到 11,464 字庫。
- **｜ 時 ｜**：預設只用 `lunar_almanac.py` 的本機干支推算；只有明確加上 `--online-almanac` 才會抓取 Gooday。
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
需要 Python 3.10 以上，建議 Python 3.11；runtime 只使用標準函式庫。
若由 Hermes `--deliver` 發送 Discord，不需要 webhook。只有選擇讓 Python 直接送 Discord 時，才在未納入 Git 的 `.env` 填入：
```env
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

### 2. 測試播報
```bash
# 模擬 09:00 播報（不發送且不消耗單字庫）
python unified_broadcaster.py --at 09:00 --dry-run

# 消耗一張課程卡；有 webhook 時直送，否則輸出 stdout 給 Hermes
python unified_broadcaster.py --consume
```

### 3. 非 Hermes 主機的選用排程

只有沒有既有 Hermes 排程時，才可選擇一般 cron。既有 Hermes 主機必須沿用原本的 `no_agent` cron，不要重建或改成 Windows 工作排程：
```cron
0 6-18 * * * cd /path/to/merged-pomodoro-pulse && python unified_broadcaster.py --consume
```

### 4. 重新產生英文課程卡

來源是 Google Drive Desktop 同步後的三套「字根字首魔法學院」資料夾。合併逐字稿可作交叉驗證，但不會直接覆寫 `cards.json` 的正確拼字與拆解：

```powershell
$env:POMODORO_ENGLISH_SOURCE_DIR = '<包含三套課程的資料夾>'
$env:POMODORO_ENGLISH_TRANSCRIPT_FILE = '<字根字首魔法學院_20260406.txt>'
py -3.11 build_english_hourly_cards.py
py -3.11 build_english_hourly_cards.py --check
py -3.11 tests/verify_english_hourly_cards.py
py -3.11 tests/verify_english_content_accuracy.py
```

逐字稿是 ASR 原始證據層，可能含同音錯字、簡繁混用、重複句與非課程雜訊。正式卡片的字根拼法、定義與構詞規則以課程目錄、逐課摘要和 `cards.json` 交叉校正；影片與音訊本體不複製進 repository。課程把部分形式放在同一記憶家族，這是教學助記法，不代表每個形式都已通過嚴格歷史語源認證。

### 5. 部署到另一台 Hermes 電腦

保留既有 Hermes `no_agent` cron，只更新它呼叫的純 Python runtime：

```powershell
git pull
py -3.11 install_offline_runtime.py
py -3.11 install_offline_runtime.py --check
py -3.11 "$env:LOCALAPPDATA\hermes\scripts\unified_broadcaster.py" --at 09:00 --dry-run
```

安裝器只複製 5 個 runtime 檔與 2 個精簡資料檔，不複製 `.env`、原始影音、逐字稿或既有消耗狀態，也不新增或修改 Hermes 排程。完整交接見 [`DEPLOY_OFFLINE_HERMES.md`](DEPLOY_OFFLINE_HERMES.md)。

---

## 🤖 Hermes Agent 快速部署

如果您使用 **Hermes Agent**，可透過以下指令一鍵裝載：

1. **安裝 Skill 指引（GitHub delivery 完成後）**：
   ```bash
   hermes skills install https://raw.githubusercontent.com/sink6985757-web/merged-pomodoro-pulse/master/SKILL.md --name pomodoro-micro-card
   ```
2. **沿用既有零 Token 排程 (Cron)**：確認既有任務仍呼叫 `<LOCALAPPDATA>/hermes/scripts/unified_broadcaster.py --consume`，且由 Hermes `--deliver` 傳送原始 stdout。此部署不建立或修改排程。
3. **自動化驗證**：
   ```bash
   python tests/verify_english_hourly_cards.py
   python tests/verify_english_content_accuracy.py
   python tests/verify_stoic_daily_quotes.py
   python tests/verify_offline_runtime.py
   python tests/verify_pomodoro_final.py
   ```

---

## 🔒 系統安全與免責聲明

- **單字冪等性**：消耗狀態紀錄於 `pomodoro_vocab_state.json`，同一個 Cycle 內單字絕不重複，自動循環。
- **併發防護**：內建**檔案鎖 (File Lock)** 避免多行程衝突與重複發送。
- **免責聲明**：易經占卜僅作決策符號學引導，不構成投資/職涯建議。英文課程資料來自使用者提供的私人 Drive 來源；repository 僅保留個人學習用的精簡衍生卡片，不含原始影音。

---

MIT License © 2026 sink6

## Agent workflow 與版本紀錄

- GitHub canonical：`sink6985757-web/merged-pomodoro-pulse`；`data/vocab_corpus/` 是已登記專案資料來源。
- 本 README 是人類與 Agent／Tool 的安裝、使用、版本與公開文案；近期變更見 [`CHANGELOG.md`](CHANGELOG.md)。
- 每次收工更新 CHANGELOG 與 handoff；GitHub delivery 前更新本 README。
- 外部知識庫為 `ON_DEMAND_ONLY`，不屬於 initial／startup／shutdown。
