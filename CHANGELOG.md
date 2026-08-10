# Changelog

## [Unreleased] - 2026-08-10

### Added
- 新增 `data/english_hourly_cards.json`：3 套「字根字首魔法學院」、128 個正式單元的精簡離線課程卡，含字根定義、代表字拆解、影片重點與回想 Q&A。
- 新增 `build_english_hourly_cards.py`，以課程 `cards.json`、逐課摘要和合併 ASR 逐字稿交叉建置課程卡；輸出不含來源電腦絕對路徑。
- 新增 `install_offline_runtime.py`，把 5 個純 Python/runtime 檔與 2 個精簡資料檔同步到 Hermes，保留既有排程、`.env` 與學習狀態並在覆寫前備份。
- 新增 `normalize_stoic_daily_quotes.py`，將 PDF／Markdown 提取的 366 日標題正規化為一致的日期＋標題 schema，修正 62 個轉錄字形、漏字或標點問題。
- 新增 `tests/verify_english_hourly_cards.py`、`tests/verify_english_content_accuracy.py`、`tests/verify_stoic_daily_quotes.py`、`tests/verify_offline_runtime.py` 與 `DEPLOY_OFFLINE_HERMES.md`。
- 新增 `data/english_transcript_crosscheck.json`：只保存 Drive 合併逐字稿的檔案身分、134 段統計與 96 個單元匹配，不納入 848 KB ASR 全文。

### Changed
- 定案播報模板依權重改為「紀錄 → 英文 → 農民曆 → 易經 × 斯多葛」；90 分鐘節點留在標題，不再顯示獨立「行」欄，也移除「請念／問自己」類提示詞。
- 每個正式單元由一個代表字擴為三個來源核心字，共 3,261 張來源字卡 → 128 單元 → 384 核心字；Discord 固定顯示課程、章節、單元與記憶節點。
- 依實際 Hermes 使用回饋，英文卡由 spoiler 填空改成直接答案版：答案加粗填回完整來源例句。
- 將冗長或重複的「影片重點」改為逐課 `formation_note` 的第一句來源聯想；保留零 Token、純 Python 與既有卡片輪替方式。
- 零 Token 記憶排程改為十年單向累積：每週 15 單元、正常約 60 天完成首次接觸；正式節點為首次、3 小時、D1、D3、D7、D14、D30、D60、D90、D180、D365，之後每 365 天年度喚回。第 91 天不重置，漏播工作每小時只補最早一筆。
- 學習狀態升級為 v5，相容保留 v3/v4 cycle、history、reservation、已學單元與舊 short/next-day queue；同時段重跑維持冪等。
- 易經變爻機械判讀改正為朱熹通行規則：二爻變兩爻並看、以上為主；三爻變並看本卦與變卦；四爻變看變卦兩個不變爻、以下為主。曾仕強教授定位為變易、時位、中道、自省的反思參考，不冒充原文或現實決策。
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
- 定案版 `verify_english_hourly_cards.py`：PASS（3 courses、128 units、3,261 source words、384 core words、固定四區順序、直接答案、無 spoiler）。
- `verify_spaced_repetition.py`：PASS（60 日完成 128 首次單元、11 個長期節點、年度 365 日續排、same-slot retry idempotent、v4 migration）。
- 英文 builder `--check`：PASS（32 provided transcripts、96 raw ASR cross-check、256 question groups、1,967 questions）。
- `verify_english_content_accuracy.py`：PASS（128 structured roots、128 fill prompts、15 editorial corrections、123 V5 spelling cross-check、5 reviewed common exceptions）。
- `verify_stoic_daily_quotes.py` 與 normalizer `--check`：PASS（366/366 日期、62 個 curated corrections、一致 title-only schema、無 CJK radical 異體）。
- `verify_offline_runtime.py`：PASS（封鎖內容網路呼叫、local almanac、7-file temporary Hermes install/readback，且明確資料根目錄不依賴 `LOCALAPPDATA`）。
- `verify_pomodoro_enhancements.py`、`verify_vocab_decomposition.py`、`verify_pomodoro_final.py`、`verify_iching.py`、`verify_casting.py`、`verify_crossref.py`：PASS。
- `py_compile`、資料庫 `--check`、`git diff --check` 與變更範圍 secret scan：PASS。
- `HEAD`、`master`、`origin/master` 與 active-ref object walk：PASS；`git fsck --full` 仍因歷史 reflog commit 指向缺失 tree 而非零結束，未經 Git 修復閘門不清理或重寫。

### Delivery
- 本次定案十年版：`VERIFIED_REMOTE`，功能 commit `cbe57d2` 已推送至 `master`。
- GitHub：已回讀遠端 ref 與功能 commit；上一版 Hermes 部署證據 `fb914e2` 已保留在歷史。
- 目標 Hermes：`DEPLOYED_PREVIOUS`。`DESKTOP-P5NQS9D` 已安裝上一版並於 2026-08-10 08:00–13:00 實際播報正常；本次定案版需 GitHub delivery 後再執行 installer。
- 安全續跑：遠端舊版曾含 webhook 字串；新版已移除，使用者仍需在 Discord 端輪替該 webhook。

## [Governance] - 2026-08-09

### Changed
- 明確定義 `data/vocab_corpus/` 為本專案登記資料來源，而非獨立發布 repository。
- 對齊四檔生命週期與外部知識庫邊界。

### Validation
- 本輪只更新治理文件；既有未知 untracked Markdown 保留且不 stage。

### Delivery
- GitHub：`VERIFIED`，治理 commit `4a266be1ab4ceb7a9ddd7e4c598809e48c730ad9` 已推送 `master` 並回讀一致。
