# Handoff

## 目前狀態

- 整體：`VERIFIED`（本機 Hermes 部署完成並實際播報驗證；歷史 reflog 缺失 tree 未修復）。
- GitHub：`VERIFIED_REMOTE`。新版已提交至 `master`，README、installer、英文資料與本 handoff 回讀一致。
- Hermes／Discord：本機 Hermes 已安裝（`install_offline_runtime.py` 7 檔同步、`--check` 全綠）；未修改 cron／頻道；2026-08-10 08:00–13:00 每小時實際播報驗證通過。
- 收工時間：2026-08-10（Asia/Taipei）。
- Agent／電腦：Hermes／`DESKTOP-P5NQS9D`（部署與驗證）。

## 本輪完成

1. 英文資料完整性與正確度
   - 3 套課程、128/128 正式單元；32 份逐課乾淨逐字稿加 96 份合併 ASR 交叉證據，另讀取 256 題組／1,967 題來源題目。
   - 代表字現在必須匹配結構化 `word_roots`；修正 27 個把 `foot`、`star`、`mind` 等英譯詞誤當代表字的單元，結果為 128/128 結構化匹配。
   - 18 個來源例句的複數、過去式或分詞答案已保留實際詞形；128/128 均為來源例句填空。
   - 15 句英文作窄範圍文法、用字或事實修正，衍生卡保留 `example_editorial_note` 與來源 reference。
   - 課程分組改稱「課程字根記憶」：保留教學助記價值，不把整組宣稱成嚴格歷史語源同源。

2. 其他離線資料
   - `data/stoic_daily_quotes.json` 完整覆蓋閏年 366 天；62 個 PDF／Markdown 轉錄字形、漏字或標點問題已正規化。
   - 只有 2 筆曾夾帶長引文、其餘 364 筆沒有；現已統一為 `{MM-DD: {title}}`，避免 runtime schema 不一致。
   - 原始 `Hui Dao Zi Ji De Nei Xin ... Ryan Holiday_20260405.md` 只作唯讀核對，未修改、未納入 installer、仍保持 untracked。

3. 離線 Hermes runtime 與文件
   - 修正明確 `POMODORO_DATA_DIR` 被覆寫的可攜路徑 bug；臨時 Hermes 安裝在錯誤 `LOCALAPPDATA` 下仍可依指定資料根目錄正確執行。
   - Python 需求由錯誤的 3.8+ 修正為 3.10+（建議 3.11）。
   - README 已明示本機／GitHub／目標 Hermes 三層部署狀態；部署文件收斂成先 delivery、再 installer、再 dry-run、最後核准觀察既有 cron。
   - installer 只同步 7 個必要檔案，不複製 `.env`、webhook、原始課程／影音／逐字稿或 `pomodoro_vocab_state.json`，也不建立排程。

## 驗證證據

- 英文 builder `--check`：PASS（courses=3、cards=128、transcripts=32、raw_asr=96、questions=1967）。
- `verify_english_hourly_cards.py`：PASS（groups=256）。
- `verify_english_content_accuracy.py`：PASS（structured_roots=128、fill_prompts=128、editorial_corrections=15、V5 spelling cross-check=123、reviewed exceptions=5）。
- Stoic normalizer `--check` 與 `verify_stoic_daily_quotes.py`：PASS（dates=366、curated=62）。
- `verify_offline_runtime.py`：PASS（offline local almanac、runtime_files=7、portable explicit data root）。
- `verify_pomodoro_enhancements.py`、`verify_vocab_decomposition.py`、`verify_pomodoro_final.py`、`verify_iching.py`、`verify_casting.py`、`verify_crossref.py`：全部 PASS。
- `py_compile`、`git diff --check`、變更範圍 secret scan、可攜資料絕對路徑 scan：PASS。
- Git active refs：`HEAD`、`master`、`origin/master` 均指向 `42cdc87424dae1eb2d257520df271278dbde0b41`；active-ref object walk PASS。
- Git 完整物件庫：`git fsck --full` 非零。歷史 reflog 的 commit `d04405b88c1c74070f242928461af602c1f2035f` 指向缺失 tree `09f93e7589edaaa0b7a91254e51dfd647dc39e54`，另有 dangling objects；不在目前 branch／remote 可達歷史，本輪未做破壞性修復。

## 安全與工作樹邊界

- 本機 `unified_broadcaster.py` 已移除硬編碼 webhook；變更範圍未檢出 credential。
- 遠端舊版曾含 webhook 字串；新版來源已移除，但使用者仍需在 Discord 端輪替，不要把新 webhook 寫進 Git。
- 本次只提交新版程式、精簡資料、測試與交接文件；原始 Ryan Holiday Markdown 保持 untracked。未修復 Git object database、未安裝目標 Hermes，也未修改外部排程。

## 回復方式

- Repository 新版已提交；若需回復，另做可追蹤的 revert，不使用 `git reset --hard` 覆蓋未知檔案。
- 本機 Hermes 已部署。日後安裝若需回復，從最近的 `%LOCALAPPDATA%\hermes\backups\offline-runtime-*` 複製原檔回 `scripts/` 與 `data/`；installer 不改 cron。

## 唯一續跑點

剩餘續跑：① 使用者輪替 Discord webhook（遠端舊版曾含 webhook 字串）；② 如需在其他電腦部署，執行：

```powershell
git pull
py -3.11 install_offline_runtime.py
py -3.11 install_offline_runtime.py --check
py -3.11 "$env:LOCALAPPDATA\hermes\scripts\unified_broadcaster.py" --at 09:00 --dry-run
```

確認「課程字根記憶」、例句填空與 spoiler 答案後，只觀察既有 Hermes `no_agent` cron；不要另建 Windows 排程或第二個 cron。
