# Merged Pomodoro Pulse

## 目標
整合番茄鐘、微卡片與脈搏紀錄，提供全離線 Discord 播報與本機狀態追蹤系統。

## 路線圖
- [x] 核心邏輯整合 (Pomodoro, Micro Card, Hour Pulse)
- [x] 離線單字與農曆資料庫建立
- [x] Discord Webhook 播報腳本撰寫
- [ ] 設定第二台 Hermes 自動化排程

## 專案結構
- `unified_broadcaster.py`：Discord 播報主腳本
- `lunar_almanac.py`：本機農曆與宜忌邏輯
- `data/vocab_decomposition.json`：離線單字拆解庫
- `index.html`：本機脈搏紀錄儀表板

## 共用規則
1. 每個 Agent 開工先讀本檔與 `handoff.md`。
2. 保留既有修改；不提交 secret、credential 或未知檔案。
3. 所有 canonical 路徑使用專案相對路徑。
4. 開工只讀；收工才更新交接、GitHub 與 Obsidian。

## 整合
- GitHub：https://github.com/sink6985757-web/merged-pomodoro-pulse.git
- Obsidian：merged-pomodoro-pulse/README.md
