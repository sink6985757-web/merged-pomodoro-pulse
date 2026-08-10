# Changelog

## [Unreleased] - 2026-08-10

### Added
- 新增 `data/english_hourly_cards.json`：3 套「字根字首魔法學院」、128 個正式單元的精簡離線課程卡，含字根定義、代表字拆解、影片重點與回想 Q&A。
- 新增 `build_english_hourly_cards.py`，以課程 `cards.json`、逐課摘要和合併 ASR 逐字稿交叉建置課程卡；輸出不含來源電腦絕對路徑。
- 新增 `install_offline_runtime.py`，把 5 個純 Python/runtime 檔與 2 個精簡資料檔同步到 Hermes，保留既有排程、`.env` 與學習狀態並在覆寫前備份。
- 新增 `normalize_stoic_daily_quotes.py`，將 PDF／Markdown 提取的 366 日標題正規化為一致的日期＋標題 schema，修正 62 個轉錄字形、漏字或標點問題。
- 新增 `tests/verify_english_hourly_cards.py`、`tests/verify_english_content_accuracy.py`、`tests/verify_stoic_daily_quotes.py`、`tests/verify_offline_runtime.py` 與 `DEPLOY_OFFLINE_HERMES.md`。

### Changed
- 英文播報改為每小時一個字根家族，顯示代表字、構詞拆解、影片提示與 Discord spoiler 答案；舊 V5 字庫只作資料不存在時的回退。
- 代表字選擇改為優先匹配結構化 `word_roots`，修正 27 個把英譯詞誤當代表字的單元；128/128 單元均有結構化字根匹配。
- 回想題依來源例句保留實際屈折詞形，修正 18 個複數、過去式或分詞答案；128/128 均為來源例句填空。另對 15 句英文作窄範圍文法、用字或事實校正並保留 editorial note。
- 將英文分組明確標示為「課程字根記憶」；這是課程助記家族，不宣稱每個變體均已完成嚴格歷史語源認證。
- `POMODORO_DATA_DIR` 明確設定時不再被啟動程式覆寫；未設定時可自動辨識 repository 根目錄或 Hermes `scripts/../data`。Python 最低版本修正為 3.10。
- README、SKILL 與 Hermes 部署文件改成明確的 `LOCAL_ONLY → GitHub delivery → 目標安裝 → dry-run → 核准後觀察` 流程，不建立第二個 cron 或 Windows 排程。
- `unified_broadcaster.py --consume` 的內容生成預設完全離線，農民曆使用 `lunar_almanac.py`；`--online-almanac` 才明確允許 Gooday。
- 保留既有 Hermes `no_agent` stdout delivery 契約，不建立 Windows 排程、不修改 Hermes cron。
- 移除程式碼內硬編碼的 Discord webhook fallback；Hermes `--deliver` 不需 webhook，Python 直送只接受本機環境變數或 `.env`。
- README 與 SKILL 更新為新版資料 authority、離線部署與播報格式。

### Validation
- `verify_english_hourly_cards.py`：PASS（3 courses、128 cards、32 provided transcripts、96 raw ASR cross-check、256 question groups、1,967 questions）。
- `verify_english_content_accuracy.py`：PASS（128 structured roots、128 fill prompts、15 editorial corrections、123 V5 spelling cross-check、5 reviewed common exceptions）。
- `verify_stoic_daily_quotes.py` 與 normalizer `--check`：PASS（366/366 日期、62 個 curated corrections、一致 title-only schema、無 CJK radical 異體）。
- `verify_offline_runtime.py`：PASS（封鎖內容網路呼叫、local almanac、7-file temporary Hermes install/readback，且明確資料根目錄不依賴 `LOCALAPPDATA`）。
- `verify_pomodoro_enhancements.py`、`verify_vocab_decomposition.py`、`verify_pomodoro_final.py`、`verify_iching.py`、`verify_casting.py`、`verify_crossref.py`：PASS。
- `py_compile`、資料庫 `--check`、`git diff --check` 與變更範圍 secret scan：PASS。
- `HEAD`、`master`、`origin/master` 與 active-ref object walk：PASS；`git fsck --full` 仍因歷史 reflog commit 指向缺失 tree 而非零結束，未經 Git 修復閘門不清理或重寫。

### Delivery
- GitHub：`VERIFIED_REMOTE`。新版已 commit／push 至 `master`，並回讀 README、installer、英文資料與 handoff。
- 目標電腦：`VERIFIED`（2026-08-10 本機 Hermes 部署完成）。`install_offline_runtime.py` 安裝 7 檔並回讀 `--check` 全綠；`scripts/.env` 含 `DISCORD_WEBHOOK_URL`，`load_webhook_url()` 解析 OK；今日 08:00–13:00 每小時實際播報正常（`daily_casts`／`slot_reservations` 逐時消耗、`last_broadcast_at` 更新）。
- 安全續跑：遠端舊版曾含 webhook 字串；新版已移除，使用者仍需在 Discord 端輪替該 webhook。

## [Governance] - 2026-08-09

### Changed
- 明確定義 `data/vocab_corpus/` 為本專案登記資料來源，而非獨立發布 repository。
- 對齊四檔生命週期與外部知識庫邊界。

### Validation
- 本輪只更新治理文件；既有未知 untracked Markdown 保留且不 stage。

### Delivery
- GitHub：`VERIFIED`，治理 commit `4a266be1ab4ceb7a9ddd7e4c598809e48c730ad9` 已推送 `master` 並回讀一致。
