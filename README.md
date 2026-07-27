# 🍅 番茄工作脈搏系統 · Merged Pomodoro Pulse

一個 **零 Token 消耗**、純 Python 核心與 HTML 雙重架構的**個人時間管理與決策護欄系統**。本專案完美整合了「番茄鐘微卡片（Discord 播報）」與「整點工作脈搏（本機紀錄儀表板）」，為開發者與工程師提供 100% 離線、極致隱私、無 API 成本的深度自我管理體驗。

---

## 🌟 系統定位：您的時間雙中樞

本系統由兩個高度互補的模組構成，協同運作：

1. **📢 播報中樞 (`unified_broadcaster.py`)**：定時發送「行 / 字 / 時 / 勢」四維 Discord Embed 或純文字微卡片，提供即時字根單字學習、農民曆沖煞、易經卦象決策護欄與 90 分鐘專注節奏計數。
2. **💓 紀錄中樞 (`index.html`)**：透過播報卡片底部的網址連結，開啟本機單檔 Web App，在 10 秒內快速登記當前感受（−2 ~ +2）、精力（1 ~ 5）與主要活動，累積職涯樣本，提供 AI 回顧 Prompt 範本。

---

## 🛠️ 專案架構與檔案清單

```text
merged-pomodoro-pulse/
├── unified_broadcaster.py      # 🚀 播報主程式：產出豐富的 Discord 卡片訊息
├── pomodoro_chat_original.py   # 🧠 核心計算引擎：處理單字循環、易經擲卦、農民曆抓取
├── lunar_almanac.py            # 🏮 備用離線農民曆：基於干支基準點推算宜忌與沖煞
├── pomodoro_iching_data.py     # ☯ 易經資料庫：曾仕強教授 64 卦、384 爻辭、變爻規則
├── index.html                  # 📊 脈搏紀錄儀表板：單檔網頁，使用 LocalStorage 儲存
├── pomodoro_focus.py           # 🔧 專注 90 分鐘番茄鐘與休息提示變體邏輯
├── requirements.txt            # 📦 相依性清單（純 Python 標準函式庫，無需安裝外部依賴）
├── LICENSE                     # MIT 授權條款
├── data/
│   ├── vocab_decomposition.json # 📖 離線字根拆解資料庫核心索引
│   └── vocab_corpus/            # 📚 劉毅/學習出版社風格字根 md 原始語料庫目錄
```

---

## 🚀 核心特色功能

### 1. ⚡ 零 Token 消耗、零外部 API 成本
全系統採用純 Python 標準函式庫與離線索引，完全不呼叫大型語言模型（LLM），不產生任何 API 帳單。

### 2. 🎴 四維微卡片（Discord Rich Embed / Markdown）
每小時或定時播報一次，微卡片欄位包含：
- **｜ 行 ｜ 專注行動**：對齊 90 分鐘（1.5 小時）工作節奏（06:00 ~ 18:00 共 8 個 S 區段），提供具體、可驗證的工作提示，防止在繁雜的日常中迷失焦點。
- **｜ 字 ｜ 英文字根**：直接顯示「單字、音標、詞性、字義」，無痛累積字彙量。
- **｜ 時 ｜ 農民曆宜忌**：優先抓取 Gooday 官網當日/當值時辰之宜忌與生肖沖煞；若網路斷線，則自動切換至本機干支基準算法，確保播報不中斷。
- **｜ 勢 ｜ 易經決策護欄**：採用系統時間亂數種子模擬「三錢法」起卦。支援完整 64 卦、384 爻辭，並嚴格實作變爻規則，自動對應決策護欄與決策建議。

### 3. 💓 單檔輕量本機工作脈搏紀錄器 (`index.html`)
- **極速登記**：每小時只需花 10 秒鐘即可點選完成主要活動、感受、精力與文字/語音備註。
- **隱私至上**：所有紀錄存在瀏覽器的 `localStorage` 中，不會上傳任何雲端，絕對安全。
- **資料搬移**：支援完整的 JSON 檔案匯入、匯出與合併功能，靈活交換數據。
- **AI 整合**：內建「一鍵複製 30 天 AI 回顧 Prompt」，將累積的脈搏數據直接貼給 AI 進行深度的週/月/年軌跡與精力回顧。

---

## ⚙️ 快速開始指南

### 1. 下載與準備
確保本機或環境中已安裝 Python 3.8+ 且可正常執行。
```bash
git clone https://github.com/sink6985757-web/merged-pomodoro-pulse.git
cd merged-pomodoro-pulse
```

### 2. 設定 Discord Webhook 網址
本專案支援多種 Discord Webhook URL 設定方式，優先順序如下：
1. **指令引數**：`--webhook "https://discord.com/api/webhooks/..."`
2. **環境變數**：`DISCORD_WEBHOOK_URL`
3. **本機環境檔案**：在專案根目錄下建立一個 `.env` 檔案，內容如下：
   ```env
   DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
   ```
4. **程式碼內嵌**：在 `unified_broadcaster.py` 中的 `DEFAULT_WEBHOOK` 變數填入網址。

### 3. 手動測試播報
您可以利用 `--at` 指令引數模擬在特定時間點的播報（不消耗單字庫）：
```bash
# 預覽 Embed JSON Payload 或 Markdown（不發送，適合除錯）
python unified_broadcaster.py --at 09:00 --dry-run

# 測試當前時間播報並真正消耗一個單字（會將進度記入狀態檔）
python unified_broadcaster.py --consume
```

### 4. 設定自動化排程（Cron）
建議在工作日（06:00 ~ 18:00）的每個整點設定排程執行。

#### 一般伺服器 Cron 排程：
```cron
0 6-18 * * * cd /path/to/merged-pomodoro-pulse && python unified_broadcaster.py --consume
```

---

## 🤖 AI Agent 快速部署與安裝指南 (For Hermes Agent)

如果您是協作 AI Agent（如 Hermes Agent），請依照以下步驟直接進行全套安裝與配置：

### 1. 安裝 Skill
在終端機中執行以下命令，直接將本專案的 `SKILL.md` 安裝為本機的技能，裝載所有開發、維護與踩坑稽核指引：
```bash
hermes skills install https://raw.githubusercontent.com/sink6985757-web/merged-pomodoro-pulse/master/SKILL.md --name pomodoro-micro-card
```

### 2. 建立播報排程 (Cron Job)
在 Hermes 環境中建立定時播報任務（自動調用終端機執行並抓取 stdout 輸出，**不依賴獨立背景進程，因此需設為 no_agent: false**）：
```bash
hermes cron create "0 6-18 * * *" \
  --name "merged-pomodoro-pulse" \
  --prompt "Run the Python script at <您的腳本絕對路徑>/unified_broadcaster.py with --consume using the terminal tool, timeout 60s. Output its stdout EXACTLY as-is — raw text, no markdown wrapping, no commentary." \
  --deliver "discord:<你的目標頻道ID>"
```

### 3. 一鍵自動化驗證
執行自動化測試，確保 100% 綠燈通過：
```bash
python tests/verify_pomodoro_final.py
```

---

## 🔒 數據庫維護與冪等安全

- **單字循環防重複機制**：播報單字保存在 `pomodoro_vocab_state.json` 中，同一 Cycle 內已被消耗的單字絕不重複播報。當精選單字消耗完畢後，自動開展下個 Cycle。
- **跨行程安全鎖**：本程式具備檔案鎖（File Lock）機制。在多行程或定時排程衝突時，能保證「讀取 ➔ 消耗單字 ➔ 儲存狀態」的交易性（Transactional），防止重複發送與競態條件。

---

## ⚖️ 免責聲明與版權

1. **易經占卜**：內容源於曾仕強教授之著述與數位化整理，純屬符號學引導與決策護欄提示，不構成任何形式之未來預測或實質投資/職涯建議。
2. **字根字典**：英文字根字典語料庫來自公開學習資料，本專案僅提供提取、索引與拆解學習工具模組。
3. **農民曆**：日/時宜忌與沖煞資訊來自網路公開農民曆演算法與 [Gooday 官網](https://www.goodaytw.com/)，請在使用時遵守其相關使用條款。

---

MIT License © 2026 sink6