# Merged Pomodoro Pulse

## 目標
整合番茄鐘、微卡片與脈搏紀錄，提供全離線 Discord 播報與本機狀態追蹤系統。

## 路線圖
- [x] 核心邏輯整合 (Pomodoro, Micro Card, Hour Pulse)
- [x] 離線單字與農曆資料庫建立
- [x] Discord Webhook 播報腳本撰寫
- [x] V5 7000 單字庫校正驗證與 V5 專屬測試建置
- [ ] 設定第二台 Hermes 自動化排程

## 專案結構
- `unified_broadcaster.py`：Discord 播報主腳本
- `lunar_almanac.py`：本機農曆與宜忌邏輯
- `build_vocab_db.py`：V5 單字庫建置／修補腳本 (Vertex AI Gemini-2.5-flash)
- `data/vocab_decomposition_v5.json`：V5 7000 單字庫 (本機核心，5805 筆)
- `data/vocab_decomposition.json`：V4 離線字根資料庫 (本機備用)
- `tests/verify_vocab_decomposition.py`：V5 JSON 結構與欄位完整性驗證
- `tests/verify_pomodoro_final.py`：全面回歸測試 (易經／單字池／卡片／並發)
- `index.html`：本機脈搏紀錄儀表板

## 共用規則
1. 每個 Agent 開工先讀本檔與 `handoff.md`。
2. 保留既有修改；不提交 secret、credential 或未知檔案。
3. 所有 canonical 路徑使用專案相對路徑。
4. 開工只讀；收工才更新交接、GitHub 與 Obsidian。

## 整合
- GitHub：https://github.com/sink6985757-web/merged-pomodoro-pulse.git
- Obsidian：merged-pomodoro-pulse/README.md
