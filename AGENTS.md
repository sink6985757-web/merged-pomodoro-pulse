# AGENTS.md - 專案狀態紀錄

## 專案名稱：Merged Pomodoro Pulse (整合番茄脈搏系統)
**目標**：將 Pomodoro、Micro Card 與 Hour Work Plus 整合為全離線、自動化播報的 Windows/Discord 輔助系統。

### 當前狀態 (2026-07-26)
- **整合進度**：核心邏輯已遷移至 `merged-pomodoro-pulse/`。
- **離線單字**：已產生 `data/vocab_decomposition.json` (2,357 筆)。
- **離線農曆**：`lunar_almanac.py` 已完成，提供基本宜忌、沖煞。
- **播報系統**：`unified_broadcaster.py` 已完成，支援 Discord Embed 推送與本機脈搏網頁連結。

### 待辦事項 (Pending)
1. [ ] 填寫 `unified_broadcaster.py` 中的 Discord Webhook URL。
2. [ ] 在第二台 Hermes 機器上設定 Cron 排程 (`0 6-18 * * *`)。
3. [ ] (選選) 將紀錄資料庫從 localStorage 遷移至 SQLite (目前仍使用原本的 index.html)。

---
*最後更新者：Gemini-3-Flash @ Yulin-SFG16-72*
