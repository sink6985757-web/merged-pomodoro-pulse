---
name: pomodoro-micro-card
description: "Maintain and troubleshoot the zero-token Pomodoro micro-card cron system — vocabulary word with pronunciation, 曾仕強 I Ching hexagram divination, Gooday almanac, and Discord-only scheduler delivery."
---

# Pomodoro Micro-Card System (Merged Pomodoro Pulse)

Zero-token `no_agent` cron script (`pomodoro_chat_original.py`) that delivers one compact micro-card to Discord #英文字根 every hour 06:00–18:00. The final-converged card has exactly four one-character axes in action-first order: `行` (the user's one real-life action now), `字` (vocabulary word with pronunciation and definition), `時` (Gooday day/hour rhythm), and `勢` (I Ching numbered glyph, uncertainty prompt, and interpretation). Reality and the `行` line always outrank symbolic lines.

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

### 3. 配置環境變數
在克隆下來的專案根目錄下，建立一個 `.env` 檔案（或寫入宿主全域 `.env`）：
```env
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

### 4. 建立自動化定時任務 (Cron Job)
使用以下命令，在 Hermes 中建立完全相容、格式一致的自動消耗播報任務：
```bash
hermes cron create "0 6-18 * * *" \
  --name "每日無為天機｜life-pomodoro micro-card" \
  --prompt "Run the Python script at ~/AppData/Local/hermes/scripts/unified_broadcaster.py with --consume using the terminal tool, timeout 60s. Output its stdout EXACTLY as-is — raw text, no markdown wrapping, no code fences, no extra formatting, no commentary. Never use triple backticks or any other wrapper. The raw text IS the final message." \
  --deliver "discord:1521867388440543316"
```
*(注意：路徑請根據宿主實際克隆或安裝的 `unified_broadcaster.py` 絕對路徑進行替換)*

### 5. 一鍵執行全套自動化驗證
執行自動化測試套件，確保起卦亂數、生肖干支、詞彙過濾與路徑相容性全數綠燈通過：
```bash
python tests/verify_pomodoro_final.py
```
若輸出 `PASS casts_4moving=960 eligible=6180 cards=130 concurrent_outputs=1`，代表部署 100% 成功。

---

## 🛠️ 系統架構 (Architecture)

```
unified_broadcaster.py      ← 播報主腳本（當 Dry-run 時會直接格式化輸出 CJK 繁體中文卡片）
├── pomodoro_chat_original.py   ← 計算核心與狀態引擎（計算週期、易經起卦、農民曆抓取）
│   ├── data/
│   │   ├── vocab_decomposition.json # 離線字根拆解資料庫
│   │   └── vocab_corpus/            # 字根 markdown 原始語料庫
│   ├── pomodoro_iching_data.py  # 曾仕強教授 64 卦、384 爻辭、變爻規則數據庫
│   ├── Gooday almanac cache    # 每日/每時辰宜忌快取
│   └── pomodoro_vocab_state.json # 狀態記錄檔（含鎖、目前 Cycle 與消耗進度）
├── lunar_almanac.py        # 🏮 備用離線農民曆：干支沖煞算法
├── pomodoro_focus.py       # 🔧 專注 90 分鐘番茄鐘與休息提示變體邏輯
└── index.html              # 📊 脈搏紀錄儀表板：單檔 Web App，使用 LocalStorage 儲存
```

---

## 📐 輸出卡片規範 (Output Contract)

### 1. 純文字模式（單一 authority 播報）
```text
｜行｜<90m 時段>｜<mode> <S{N}/8[ 收尾]|完成>｜<action>
｜字｜<word> [pron]｜<pos>. <gloss>
｜時｜<day 宜忌>｜<hour 宜忌>｜<沖煞>｜現實優先
｜勢｜第<N>卦 <glyph> <name>[→第<M>卦 <glyph> <changed_name>]｜<moving|靜>｜<hint>
```

### 2. 播報卡片格式細節與規範
- **行計數系統統一**：每日劃分為 8 個 90 分鐘區段。首小時卡片顯示 `S{N}/8`（例如：`S1/8`），次小時（收尾小時）顯示 `S{N}/8 收尾`，18:00 卡片則顯示 `完成`。
- **勢 決策提示**：刪除了原尾部的 `｜守主線…｜只改一處…` 等決策護欄提示文字（2026-07-20 移去），此行在 interpretation hint 處結束。
- **勢 四爻變規則**：依曾仕強教授體系，四爻變時需擷取**變卦下卦（內卦）**之卦德提示，並以前綴 `{changed_name}內卦提示：` 呈現，避免長篇幅文字溢出。
- **字 詞彙 pool 品質門檻**：表面文字不重複，僅讀取經過 v4 結構化比對與 Morpheme-match 驗證之有效詞彙，移除了對 Morpheme Decomposition 欄位的強制要求（Decomposition 變為可選），使可用 pool 大幅擴增至 6,180 筆優質常用單字。
- **時 宜忌基準**：抓取 Gooday 官網為優先；斷線時自動切換至 `lunar_almanac` 基於傳統干支的本機推算算法。

---

## 🧪 核心開發與驗證指令 (Commands)

### 手動測試與除錯
```bash
python pomodoro_chat_original.py --at 14:00             # 全卡片模擬（不消耗進度）
python pomodoro_chat_original.py --vocab-status          # 檢視單字庫消耗統計
python pomodoro_chat_original.py --lookup abandon        # 快速查詢特定單字
python pomodoro_chat_original.py --reset-cycle           # 重設並開啟全新 Cycle
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
   曾仕強教授體系的卦象查表順序為 `KING_WEN_MATRIX[lower_trigram][upper_trigram]`（下卦在左，上卦在頂）。**若顛倒為 `[upper][lower]`，64 卦中會有 56 卦傳回錯誤的卦號與爻辭**，僅 8 個八純卦（上下卦相同）能倖免。
2. **路徑跨平台相容性**：
   在 Git-bash/MSYS 等 Windows 模擬 bash 環境中，`Path(__file__).resolve()` 會展開為 POSIX 風格路徑（`/c/Users/...`）。若將此路徑寫入 Python 的 `POMODORO_DATA_DIR` 環境變數中，原生 Windows `python.exe` 解譯器將無法識別而導致資料庫載入失敗（單字顯示為 "無"）。在 live 環境中，請直接刪除或不設置 `POMODORO_DATA_DIR`，讓其自然回退至由驅動器識別的 `LOCALAPPDATA/hermes`。
3. **Cron 播報 stdout 污染**：
   在 headless/no_agent 定時排程中，所有的 `sys.stderr` 警告或除錯訊息（如 `⚠️ 警告: 目前使用預設 Webhook...`）會與 stdout 混合。務必將非必要的 debug print 全部關閉或導流，保持 stdout 輸出的純淨。
4. **字根提取空行跳脫陷阱**：
   在 `vocab_decomp_extract.py` 提取字根時，遇到空行必須使用 `continue` 繼續向下掃描，而非 `break`。因為劉毅的語料 markdown 中，單字定義與 `《...》` 拆解公式之間常有空行，使用 `break` 將導致超過 576 筆字根定義遺失。
5. **雙重提交一致性**：
   在收工（Shutdown）或同步時，如果修改了核心邏輯，務必在 **本機實體 `AppData/Local/hermes/scripts/`** 與 **本倉庫 `merged-pomodoro-pulse/`** 兩個目錄中同時進行 patch 修改，保持兩側代碼 100% 同步與乾淨。
