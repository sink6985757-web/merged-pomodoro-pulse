---
name: pomodoro-micro-card
description: "Maintain and troubleshoot the zero-token Pomodoro micro-card cron system — long-term offline English course units, local almanac, I Ching and Stoic reflection, and Hermes Discord delivery."
---

# Pomodoro Micro-Card System (Merged Pomodoro Pulse)

Zero-token `no_agent` cron runtime that uses pure Python to produce one compact micro-card every hour 06:00–18:00. Hermes owns stdout delivery; the runtime never calls a language model. The finalized priority is fixed: `紀錄 → 英文 → 農民曆 → 易經 × 斯多葛`. The 90-minute segment stays in the header; there is no separate `行` field. Symbolic material is reflection only and never overrides reality.

---

## 🤖 AI Agent 快速部署與安裝指南 (AI Agent Direct Installation)

如果您是新喚醒的 AI 協作 Agent，請依據以下步驟在宿主（Host）環境中直接下載、安裝、配置並驗證本系統：

### 1. 安裝本專案 Skill 到本機 Hermes 環境
直接在終端機（bash）執行以下命令，將本專案的系統指南與知識庫載入到本機 Hermes 中：
```bash
hermes skills install https://raw.githubusercontent.com/sink6985757-web/merged-pomodoro-pulse/master/SKILL.md --name pomodoro-micro-card
```

### 2. 檢索與克隆專案倉庫
在宿主指定的工作目錄下複製本專案：
```bash
git clone https://github.com/sink6985757-web/merged-pomodoro-pulse.git
cd merged-pomodoro-pulse
```

### 3. 安裝精簡離線 runtime
將 repository 內的純 Python 程式與兩個精簡資料檔複製到 Hermes 既有路徑；不修改 cron、`.env` 或消耗狀態：
```bash
python install_offline_runtime.py
python install_offline_runtime.py --check
```
需要 Python 3.10 以上，建議 Python 3.11。
使用 Hermes `--deliver` 時不需要 Discord webhook。只有選用 Python 直送時，才在本機 `.env` 設定 `DISCORD_WEBHOOK_URL`。

### 4. 沿用自動化定時任務 (Cron Job)
既有任務不需改排程架構。確認它仍以零 Token `no_agent` 方式呼叫 `<LOCALAPPDATA>/hermes/scripts/unified_broadcaster.py --consume`，並由 Hermes `--deliver` 原樣傳送 stdout。安裝器不建立 cron；全新主機的排程與 Discord 頻道須由使用者另行授權設定。

### 5. 一鍵執行全套自動化驗證
執行自動化測試套件，確保離線資料、英文字根卡、起卦亂數與路徑相容性全數綠燈通過：
```bash
python tests/verify_english_hourly_cards.py
python tests/verify_english_content_accuracy.py
python tests/verify_stoic_daily_quotes.py
python tests/verify_spaced_repetition.py
python tests/verify_offline_runtime.py
python tests/verify_pomodoro_final.py
```

---

## 🛠️ 系統架構 (Architecture)

```
unified_broadcaster.py      ← 播報主腳本（當 Dry-run 時會直接格式化輸出 CJK 繁體中文卡片）
├── pomodoro_chat_original.py   ← 計算核心與狀態引擎（計算週期、易經起卦、農民曆抓取）
│   ├── data/
│   │   ├── english_hourly_cards.json # 128 單元、384 核心字的精簡衍生卡
│   │   └── stoic_daily_quotes.json   # 366 日行動輔助摘要
│   ├── pomodoro_iching_data.py  # 64 卦反思摘要、384 爻位、朱熹變爻選取規則
│   └── pomodoro_vocab_state.json # v5 狀態檔（128 單元與十年複習節點）
├── lunar_almanac.py        # 🏮 備用離線農民曆：干支沖煞算法
├── pomodoro_focus.py       # 🔧 專注 90 分鐘番茄鐘與休息提示變體邏輯
└── index.html              # 📊 脈搏紀錄儀表板：單檔 Web App，使用 LocalStorage 儲存
```

---

## 📐 輸出卡片規範 (Output Contract)

### 1. Hermes stdout（單一 authority 播報）
```text
🍅 番茄工作脈搏 · <HH:MM>  <90m 時段 / S{N}/8>
📊 紀錄：<原本的公開紀錄連結>
📖 英文：<課程 › 章節> / <正式單元> / <記憶節點> / <三字家族> / <直接答案與例句>
🗓️ 農民曆：<時辰宜忌> / <日宜忌> / <沖煞>
☯️ 易經 × 斯多葛：<卦象與變爻> / <易經反思> / <當日斯多葛摘要>
```

### 2. 播報卡片格式細節與規範
- **時段計數系統統一**：每日劃分為 8 個 90 分鐘區段。首小時顯示 `S{N}/8`，次小時顯示 `S{N}/8 收尾`，18:00 顯示 `完成`；只放在標題描述。
- **勢 決策提示**：刪除了原尾部的 `｜守主線…｜只改一處…` 等決策護欄提示文字（2026-07-20 移去），此行在 interpretation hint 處結束。
- **勢 判讀分層**：變爻的機械選取採朱熹通行規則；四爻變看變卦兩個不變爻並以下爻為主。曾仕強教授只作「變易、時位、中道、自省」的反思框架參考，不把摘要冒充教授原文或現實判決。
- **字 課程 authority**：優先使用 3 套課程的 128 個正式單元；字根拼法、定義和拆解由課程資料與逐課摘要交叉校正，合併 ASR 逐字稿只作證據層，不直接成為顯示文字。課程家族是助記分組，不等於逐項歷史語源認證。舊 V5 字庫僅在本機存在且課程卡不存在時回退。
- **字 快速記憶格式**：不使用 Discord spoiler，也不播「請念一次／問自己」等提示詞。答案直接加粗顯示；每卡固定顯示課程、章節、單元與節點。
- **字 十年排程**：每週導入 15 單元，正常約 60 天完成 128 單元首次接觸。節點為首次、3 小時、D1、D3、D7、D14、D30、D60、D90、D180、D365，之後每 365 天年度喚回；其他整點只做已學單元輕量輪播。v3/v4 狀態相容升級為 v5，不在第 91 天重置。
- **時 宜忌基準**：`unified_broadcaster.py --consume` 預設只用 `lunar_almanac.py`；只有明確傳入 `--online-almanac` 才允許抓取 Gooday。

---

## 🧪 核心開發與驗證指令 (Commands)

### 手動測試與除錯
```bash
python pomodoro_chat_original.py --at 14:00             # 全卡片模擬（不消耗進度）
python pomodoro_chat_original.py --vocab-status          # 檢視單字庫消耗統計
python pomodoro_chat_original.py --lookup abandon        # 快速查詢特定單字
```
*注意：手動測試時請勿傳遞 `--consume` 參數，以免污染正式的單字消耗進度。*

### 重建字根資料庫
當修改了 `data/vocab_corpus/` 下的 Markdown 原始語料後，需重新執行提取與驗證：
```bash
python vocab_decomp_extract.py
python tests/verify_vocab_decomposition.py
```

### 清理快取並執行全面驗證
```bash
# 清理 __pycache__ 防止編譯位元組碼污染
find . -name "__pycache__" -exec rm -rf {} +
# 執行全套易經與番茄鐘迴歸測試
python tests/verify_pomodoro_final.py
python tests/verify_iching.py
python tests/verify_casting.py
python tests/verify_crossref.py
```

---

## ⚠️ 關鍵踩坑與防護機制 (Critical Pitfalls)

1. **易經矩陣查表順序**：
   卦象查表順序為 `KING_WEN_MATRIX[lower_trigram][upper_trigram]`（下卦在左，上卦在頂）。**若顛倒為 `[upper][lower]`，64 卦中會有 56 卦傳回錯誤的卦號與爻辭**，僅 8 個八純卦能倖免。
2. **路徑跨平台相容性**：
   明確設定的 `POMODORO_DATA_DIR` 具有最高優先權，必須是目前 Python 可辨識且包含 `data/` 的 Hermes 根目錄。未設定時，程式會自動尋找腳本同層的 `data/`，或 `scripts/` 的上一層 `data/`；不要把 Git-bash/MSYS 的 `/c/Users/...` 路徑傳給原生 Windows `python.exe`。
3. **Cron 播報 stdout 污染**：
   在 headless/no_agent 定時排程中，所有的 `sys.stderr` 警告或除錯訊息（如 `⚠️ 警告: 目前使用預設 Webhook...`）會與 stdout 混合。務必將非必要的 debug print 全部關閉或導流，保持 stdout 輸出的純淨。
4. **字根提取空行跳脫陷阱**：
   在 `vocab_decomp_extract.py` 提取字根時，遇到空行必須使用 `continue` 繼續向下掃描，而非 `break`。因為劉毅的語料 markdown 中，單字定義與 `《...》` 拆解公式之間常有空行，使用 `break` 將導致超過 576 筆字根定義遺失。
5. **Repository 與 runtime 一致性**：
   核心邏輯只在 repository 維護。取得 GitHub／Hermes 部署授權後，使用 `install_offline_runtime.py` 同步至目標，再以 `--check` 的 SHA-256 回讀驗證；不要在收工時手動雙邊 patch。
