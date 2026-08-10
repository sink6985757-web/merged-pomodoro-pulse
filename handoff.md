# Handoff

## 目前狀態

- 整體：`PARTIAL`。定案十年版與 GitHub delivery 已完成；Hermes 正式播報仍是上一版。
- 本機：`VERIFIED_LOCAL`，分支 `master`，功能 commit `cbe57d2`。
- GitHub：`VERIFIED_REMOTE`，`master` 已含 `cbe57d2` 並完成 ref 回讀。
- Hermes／Discord：`DESKTOP-P5NQS9D` 已安裝上一版並於 2026-08-10 08:00–13:00 每小時實際播報驗證通過；本次定案版尚未重裝，未修改既有 `no_agent` cron／頻道。
- 收工日期：2026-08-10（Asia/Taipei）；Agent／電腦：Codex／`YULIN-SFG16-72`。

## 本輪完成

1. 定案播報模板
   - 正文固定依權重顯示：`紀錄 → 英文 → 農民曆 → 易經 × 斯多葛`。
   - 原紀錄儀表板公開連結保留並排第一；90 分鐘時段／S 段只放標題，不再有獨立「行」。
   - Hermes stdout 與 Discord Embed 使用同一份結構化資料與相同順序。
   - 移除「讀一次／問自己」等提示詞；有例句的節點直接顯示答案。

2. 英文課程資料與十年記憶
   - 3 套課程、128 個正式單元、3,261 張來源字卡；每單元選 3 個不同且有來源例句的核心字，共 384 字。
   - 卡片固定顯示 `課程 › 章節`、正式單元、字根定義、記憶節點與三字家族。
   - `path = feeling 感情` 實例為 `sympathy / apathy / empathy`。
   - 60 日導入規則：每週 15 單元（六天各 2、一天 3）；未看時不一次補發整串。
   - 每單元節點：首次、3 小時、D1、D3、D7、D14、D30、D60、D90、D180、D365；之後每 365 天年度喚回，可持續十年以上。
   - 狀態升級 v5，保留 v3/v4 history、reservation、已學單元與舊 review queue；不在第 91 天歸零。
   - 新增 `data/english_transcript_crosscheck.json`，記錄 Drive 合併逐字稿檔案 `1Gg-H5a9aHTPraXuEX39SstOtZjbt00D3`、134 段與 96 個單元匹配；不保存 ASR 全文。

3. 易經與斯多葛
   - 易經保留三錢法、64 卦、384 爻位與完整 0–6 變爻處理。
   - 修正舊四爻變「變卦內卦」錯法；現採朱熹通行規則：四爻變看變卦兩個不變爻並以下爻為主。
   - 二爻變改為兩爻並看、以上為主；三爻變改為本卦與變卦卦辭並看。
   - 曾仕強教授的定位限定為變易、時位、中道、自省的反思框架，不把摘要冒充教授原文或現實判決。
   - 斯多葛與易經在同一區分行顯示，兩者不混成同一判讀。

4. 離線與搬機
   - 內容生成仍為純 Python、零模型 token；農民曆預設本機，Discord 傳輸本身仍需網路。
   - installer 仍只同步 7 個 runtime 檔，不碰 cron、`.env`、credential 或 `pomodoro_vocab_state.json`。
   - 十年進度搬機需在舊機停播後，人工備份並複製 `data/pomodoro_vocab_state.json`；同時只能一台使用 `--consume`。

## 驗證證據

- `py_compile`：核心、builder、broadcaster、易經資料均 PASS。
- 英文 builder `--check`：PASS（courses=3、cards=128、transcripts=32、raw_asr=96、questions=1967）。
- `verify_english_hourly_cards.py`：PASS（units=128、source_words=3261、core_words=384、四區模板順序）。
- `verify_english_content_accuracy.py`：PASS（structured_roots=128、fill_prompts=128、editorial_corrections=15、V5 spelling cross-check=123）。
- `verify_spaced_repetition.py`：PASS（128 單元／60 日、11 節點、annual=365、v4 migration）。
- `verify_offline_runtime.py`：PASS（local almanac、7-file temporary Hermes install/readback）。
- `verify_pomodoro_final.py`：PASS（4,096 起卦組合、960 個四爻變案例、併發冪等）。
- `verify_iching.py`、`verify_casting.py`、`verify_crossref.py`、`verify_pomodoro_enhancements.py`、`verify_vocab_decomposition.py`、`verify_stoic_daily_quotes.py`：PASS。
- `git diff --check`、變更範圍 secret scan、衍生資料絕對路徑 scan：PASS。
- Git active refs：功能 push 後 `HEAD`、`master`、`origin/master` 均為 `cbe57d2`；`git fsck --full --no-reflogs` exit 0（只有 dangling objects）。
- `git fsck --full` exit 2：歷史 reflog commit `d04405b88c1c74070f242928461af602c1f2035f` 仍缺 tree `09f93e7589edaaa0b7a91254e51dfd647dc39e54`；不在 active refs，本輪不做破壞性修復。

## 安全與工作樹邊界

- 保留未追蹤 `.codex-remote-attachments/` 與 Ryan Holiday Markdown；不納入本輪交付範圍。
- 不提交 webhook、token、credential、原始課程影片或完整逐字稿。
- 遠端舊版曾含 webhook 字串；新版來源不保存 credential，使用者仍需自行輪替舊 webhook。

## 回復方式

- Repository 變更若需回復，另做可追蹤的 revert，不使用 `git reset --hard` 覆蓋未知檔案。
- Hermes 上一版已部署；未來更新若需回復，從最近的 `%LOCALAPPDATA%\hermes\backups\offline-runtime-*` 複製原檔回 `scripts/` 與 `data/`，installer 不改 cron。

## 唯一續跑點

在 Hermes 電腦執行：

```powershell
git pull
py -3.11 install_offline_runtime.py
py -3.11 install_offline_runtime.py --check
py -3.11 "$env:LOCALAPPDATA\hermes\scripts\unified_broadcaster.py" --at 09:00 --dry-run
```

確認畫面依序為「紀錄、英文、農民曆、易經 × 斯多葛」，再由使用者核准觀察既有 `no_agent` cron；不要另建 Windows 排程或第二個 cron。
