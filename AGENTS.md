# Merged Pomodoro Pulse

## 目標

整合番茄鐘、微卡片、脈搏紀錄、離線資料與 Discord 播報。

## 專案結構

- `unified_broadcaster.py`：Discord 播報主程式。
- `data/`：離線字根與其他本機資料。
- `tests/`：資料結構與整合回歸測試。
- `README.md`：人類與 Agent／Tool 安裝、使用、版本與公開文案。
- `CHANGELOG.md`：每次收工的近期修改與 delivery 狀態。
- `handoff.md`：目前排程、驗證與唯一續跑點。

## 共用規則

1. 開工只讀本檔、`handoff.md` 與 Git 狀態。
2. 保留既有修改；不提交 webhook、secret、credential 或未知檔案。
3. canonical 路徑使用專案相對路徑。
4. `data/vocab_corpus/` 是專案內登記資料來源，不是另一個待發布 repository。
5. 每次收工更新 `CHANGELOG.md` 與 `handoff.md`；GitHub delivery 前更新 README。
6. Discord、排程、commit、push、發布與權限須由工作單／ReadyGate 放行。
7. 外部知識庫一律 `ON_DEMAND_ONLY`，不屬於 initial／startup／shutdown。

## 整合

- GitHub：private `sink6985757-web/merged-pomodoro-pulse`
- Discord／Hermes：外部執行閘門
- 外部知識庫：`ON_DEMAND_ONLY`
