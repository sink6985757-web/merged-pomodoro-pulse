# 🍅 番茄工作脈搏系統 · Merged Pomodoro Pulse

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)

一個 **內容生成完全離線、零 Token 消耗、極致隱私** 的個人時間管理與決策護欄系統。只有 Hermes 將結果送到 Discord（或選用 webhook 直送）時需要網路。
整合「番茄鐘微卡片（Discord）」與「整點工作脈搏（本機紀錄）」，協助開發者建立高效的專注與回顧循環。

## 部署狀態（2026-08-10）

| 層級 | 狀態 | 說明 |
|---|---|---|
| 本機工作樹 | `VERIFIED_LOCAL` | 定案四區模板、128 單元／384 核心字與十年記憶節點已通過完整回歸 |
| GitHub `master` | `VERIFIED_REMOTE` | 定案十年版已推送為 `cbe57d2` 並完成遠端 ref 回讀 |
| 另一台 Hermes | `DEPLOYED_PREVIOUS` | 使用者已安裝上一版；本次十年版尚未更新 |

本次定案版已完成 GitHub delivery；Hermes 仍需重跑 installer 與 dry-run，才會從上一版升級。

---

## 🌟 系統架構

系統由兩個高度互補的模組構成：
1. **📢 播報中樞 (`unified_broadcaster.py`)**：整點依「紀錄、英文、農民曆、易經 × 斯多葛」權重發送 Discord 卡片；90 分鐘時段放在標題，不另設「行」。
2. **💓 紀錄中樞 (`index.html`)**：單檔 Web App，10 秒內快速登記整點狀態，累積精力數據，內建一鍵複製 AI 回顧 Prompt。

```text
merged-pomodoro-pulse/
├── unified_broadcaster.py      # 🚀 播報主程式 (Discord 卡片生成)
├── pomodoro_chat_original.py   # 🧠 核心計算引擎 (單字、易經、農民曆)
├── lunar_almanac.py            # 🏮 備用離線農民曆 (干支推算)
├── pomodoro_iching_data.py     # ☯ 64 卦反思摘要、384 爻位與朱熹變爻選取規則
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
│   ├── english_transcript_crosscheck.json # 離線逐字稿段落交叉驗證清單
│   ├── stoic_daily_quotes.json     # 可攜式 366 日行動輔助摘要
│   ├── vocab_decomposition_v5.json # V5 11,464 單字大字庫 (本機、忽略追蹤)
│   └── vocab_decomposition.json    # V4 離線字根資料庫 (本機、忽略追蹤)
└── tests/                      # 🚦 自動化測試套件 (100% 綠燈驗證)
    ├── verify_english_hourly_cards.py   # Drive 課程卡來源與顯示合約
    ├── verify_english_content_accuracy.py # 英文拼字、構詞、提示與例句校驗
    ├── verify_stoic_daily_quotes.py     # 366 日日期覆蓋、字形與 schema 校驗
    ├── verify_spaced_repetition.py      # 60 日導入、長期節點、年度維護與重試冪等
    ├── verify_offline_runtime.py        # 禁網路內容生成與可攜部署驗證
    ├── verify_pomodoro_final.py         # 生產路徑與時段覆蓋
    ├── verify_pomodoro_enhancements.py  # 增強版合約與單字庫
    ├── verify_vocab_decomposition.py    # 字根重複性校驗
    ├── verify_iching.py                 # 易經結構與變爻校驗
    └── ...                              # 其他番茄鐘與易經迴歸測試
```

---

## 🚀 核心特色

### 🎴 定案整點微卡片 (Discord)
每小時播報一次，90 分鐘區段只放在卡片標題；正文固定四區，權重由高到低：
- **📊 紀錄**：使用原本的公開紀錄儀表板連結，永遠排第一。
- **📖 英文**：固定顯示 `課程 › 章節`、正式單元、記憶節點、字根定義與三個核心字家族；有例句的節點直接顯示答案。3 套課程共 128 單元、3,261 張來源字卡，離線衍生 384 個核心字；15 句窄範圍文法／用字校正保留 editorial note。只有課程資料不存在時才回退本機 V5 11,464 字庫。
- **🗓️ 農民曆**：預設只用 `lunar_almanac.py` 本機推算；只有明確加上 `--online-almanac` 才抓 Gooday。
- **☯️ 易經 × 斯多葛**：三錢法起卦；變爻機械選取採朱熹《易學啟蒙》通行規則，反思語氣參考曾仕強教授重視的變易、時位、中道與自省，並與每日斯多葛摘要分行呈現。它是反思參考，不代替現實判斷。

四爻變的校正依古籍所載「以之卦二不變爻占，仍以下爻為主」；來源見 [Chinese Text Project《周易函書別集》卷七](https://ctext.org/wiki.pl?chapter=427773&if=zh)。

### 📊 輕量脈搏紀錄器 (`index.html`)
- **極速登記**：10 秒快速記錄感受（−2 ~ +2）、精力（1 ~ 5）與活動。
- **絕對隱私**：100% 儲存於瀏覽器 `localStorage`，數據不落雲端。
- **AI 賦能**：內建「30 天回顧 Prompt」，一鍵生成深度精力與軌跡分析。

### 十年英文學習邏輯

90 天只是第一輪建構期，不是循環或重置點。正常每次整點都有播報時，前 60 天依每週 15 單元（六天各 2 單元、一天 3 單元）完成 128 單元首次接觸；第 61 天起不再塞新課，只消化既有複習。較晚加入的單元，其 D90 會自然延伸到約第 150 天。

每單元保留三個核心字，依下列節點 merge 顯示：

| 節點 | 顯示重點 |
|---|---|
| 首次、約 3 小時 | 核心字 1；再帶核心字 2＋3 |
| D1、D3、D7、D14 | 三字家族、來源例句與交錯辨識 |
| D30、D60、D90 | 壓縮摘要與長期喚回 |
| D180、D365 | 半年與年度喚回 |
| D365 之後 | 每 365 天一個正式年度節點，可持續十年以上；其他整點用已學單元輕量輪播 |

未執行的播報保留為到期工作，之後每小時只取最早一筆，不會一次補發整串。既有 `pomodoro_vocab_state.json` 會相容升級到 v5；保留歷史、已學單元、reservation 與舊 review queue，不會在第 91 天歸零。

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
# 有新的完整逐字稿時才設定；否則使用 repository 的離線交叉驗證清單
$env:POMODORO_ENGLISH_TRANSCRIPT_FILE = '<字根字首魔法學院_20260406.txt>'
py -3.11 build_english_hourly_cards.py
py -3.11 build_english_hourly_cards.py --check
py -3.11 tests/verify_english_hourly_cards.py
py -3.11 tests/verify_english_content_accuracy.py
```

逐字稿是 ASR 原始證據層，可能含同音錯字、簡繁混用、重複句與非課程雜訊。`data/english_transcript_crosscheck.json` 只保存 Drive 檔案身分與 96 個已匹配段落，不保存 848 KB 全文；正式卡片的拼字、定義與構詞仍以課程目錄、逐課摘要和 `cards.json` 為準。影片與音訊本體不複製進 repository。課程記憶家族是教學助記分組，不代表每個形式都已通過嚴格歷史語源認證。

### 5. 部署到另一台 Hermes 電腦

保留既有 Hermes `no_agent` cron，只更新它呼叫的純 Python runtime：

```powershell
git pull
py -3.11 install_offline_runtime.py
py -3.11 install_offline_runtime.py --check
py -3.11 "$env:LOCALAPPDATA\hermes\scripts\unified_broadcaster.py" --at 09:00 --dry-run
```

安裝器只複製 5 個 runtime 檔與 2 個精簡資料檔，不複製 `.env`、原始影音、逐字稿或既有學習狀態，也不新增或修改 Hermes 排程。搬到新電腦並要延續十年進度時，需另行安全複製舊機的 `pomodoro_vocab_state.json`。完整交接見 [`DEPLOY_OFFLINE_HERMES.md`](DEPLOY_OFFLINE_HERMES.md)。

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

- **學習冪等性**：消耗狀態紀錄於 `pomodoro_vocab_state.json`；同一時段重跑會重用 reservation，128 單元首次完成後轉入長期維護，不自動歸零循環。
- **併發防護**：內建**檔案鎖 (File Lock)** 避免多行程衝突與重複發送。
- **免責聲明**：易經占卜僅作決策符號學引導，不構成投資/職涯建議。英文課程資料來自使用者提供的私人 Drive 來源；repository 僅保留個人學習用的精簡衍生卡片，不含原始影音。

---

MIT License © 2026 sink6

## Agent workflow 與版本紀錄

- GitHub canonical：`sink6985757-web/merged-pomodoro-pulse`；`data/vocab_corpus/` 是已登記專案資料來源。
- 本 README 是人類與 Agent／Tool 的安裝、使用、版本與公開文案；近期變更見 [`CHANGELOG.md`](CHANGELOG.md)。
- 每次收工更新 CHANGELOG 與 handoff；GitHub delivery 前更新本 README。
- 外部知識庫為 `ON_DEMAND_ONLY`，不屬於 initial／startup／shutdown。
