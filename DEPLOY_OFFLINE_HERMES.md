# Hermes 離線零 Token 部署

## 現況與執行契約

- 本機十年版與 GitHub `master`（功能 commit `cbe57d2`）已驗證；另一台 Hermes 仍是上一版，尚未重裝本次 runtime。
- 保留目前穩定的 Hermes `no_agent` cron 與 Discord `--deliver`，不建立 Windows 工作排程，也不另建第二個 cron。
- Hermes 執行 `unified_broadcaster.py --consume`；Python 只產生 stdout，沒有模型呼叫，因此內容生成使用 0 token。
- Discord 傳輸仍需要網路；「離線」是指內容生成不依賴 Google Drive、Gooday、影音、逐字稿或模型 API。
- Python 需求是 3.10 以上，建議 3.11。

## 放行後的唯一部署順序

1. 使用者在 Discord 輪替舊 webhook。Hermes `--deliver` 路線不需要把 webhook 寫回程式或 Git。
2. 在另一台電腦更新 repository，再安裝精簡 runtime：

   ```powershell
   git pull
   py -3.11 install_offline_runtime.py
   py -3.11 install_offline_runtime.py --check
   ```

3. 在不消耗卡片、不傳 Discord 的情況下預覽：

   ```powershell
   py -3.11 "$env:LOCALAPPDATA\hermes\scripts\unified_broadcaster.py" --at 09:00 --dry-run
   ```

4. 確認輸出依序為「紀錄 → 英文 → 農民曆 → 易經 × 斯多葛」，英文含課程／章節／單元／記憶節點與直接答案，且沒有獨立「行」、spoiler、提示詞或額外 debug 文字。
5. 只在使用者核准後觀察一次既有 `no_agent` cron 的正式播報；不要另外建立 cron 或 Windows 排程。

若目標 repository 尚未存在，步驟 2 的 `git pull` 改為：

```powershell
git clone https://github.com/sink6985757-web/merged-pomodoro-pulse.git
Set-Location merged-pomodoro-pulse
```

## 安裝與驗證範圍

安裝器複製 7 個檔案：

- `unified_broadcaster.py`
- `pomodoro_chat_original.py`
- `pomodoro_iching_data.py`
- `lunar_almanac.py`
- `index.html`
- `data/english_hourly_cards.json`
- `data/stoic_daily_quotes.json`

不會複製或修改：

- Hermes cron 與 Discord channel 設定
- `.env`、webhook 或任何憑證
- `pomodoro_vocab_state.json` 與既有學習進度
- Google Drive 原始課程、影片、音訊、逐字稿與未追蹤 Markdown

若目標檔案內容不同，安裝器先備份到 `%LOCALAPPDATA%\hermes\backups\offline-runtime-<timestamp>`。`--check` 會逐檔比對 SHA-256，並以非零結束碼表示不一致。

### 十年進度搬機

安裝器刻意不覆寫狀態。若要在新電腦延續原本進度，先停止舊機播報，確認兩端實際 `POMODORO_DATA_DIR`，再把舊機的 `data\pomodoro_vocab_state.json` 複製到新機相同資料位置。保留一份原檔備份後才啟動新機，且同一時間只能有一台使用 `--consume`，避免兩份進度分叉。這是部署時的獨立人工步驟，不由 installer 自動執行。

Repository 端在交付前執行：

```powershell
py -3.11 build_english_hourly_cards.py --check
py -3.11 normalize_stoic_daily_quotes.py --check
py -3.11 tests/verify_english_hourly_cards.py
py -3.11 tests/verify_english_content_accuracy.py
py -3.11 tests/verify_stoic_daily_quotes.py
py -3.11 tests/verify_spaced_repetition.py
py -3.11 tests/verify_offline_runtime.py
py -3.11 tests/verify_pomodoro_final.py
```

## 既有排程與回復

既有排程應維持呼叫：

```text
<LOCALAPPDATA>/hermes/scripts/unified_broadcaster.py --consume
```

不必增加 `--offline`；離線內容已是預設。只有人工除錯且明確需要 Gooday 時才使用 `--online-almanac`。使用 Hermes `--deliver "discord:<頻道ID>"` 時不要再設 webhook，以免雙重播報。

若新版有問題，停止後續正式播報並從最近的 `backups/offline-runtime-*` 將對應檔案複製回 `scripts/` 與 `data/`。排程從未被 installer 變更，因此不需要重建 cron。
