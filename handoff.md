# Handoff

## 目前做到哪

易經起卦頻率改為「一天一卦」並已部署至本機 Hermes、同步 GitHub master：`daily_casts` 的 key 從小時（`%Y-%m-%dT%H`）改為日期（`%Y-%m-%d`），全天 13 個整點時段（06:00～18:00）共用同一卦；`slot_reservations` 維持小時 key，同 slot 重試仍重用同一字＋同一卦（冪等不變）。

## 目前狀態

- 可執行：是（本機已部署、cron `3ca5ac1b5479` 契約不變，無需改排程）
- 已驗證：同一天 06/09/12/18 四時段實測同一卦（第19卦 地澤臨→第24卦 地雷復｜二，爻值全同）；跨天 key miss 自動重抽；`verify_pomodoro_final.py` PASS（960 四爻變／5571 字／130 卡／併發冪等）；py_compile OK；repo==live IDENTICAL
- 未完成：無

## 下一步

1. 明天起觀察每日 06:00～18:00 的 13 張卡是否全天同一卦（跨天自動換卦）。
2. 若日後要改回每小時一卦：把 `_choose_vocab_entry_unlocked` 中 `daily_casts` 的 `day_key` 換回 `slot_key`，並同步更新 `tests/verify_pomodoro_final.py` 的 daily_casts 斷言（同天兩 slot → 1 key）。

## 注意事項

- 今天 06:00～09:00 的卡是舊邏輯（每小時一卦）；10:00 起為新邏輯，今天的「今日卦」從 10:00 那張開始。
- 改動前備份在 `%LOCALAPPDATA%\hermes\backups\daily-cast-20260811-092652\`（live + repo + test 三份）。
- 不提交 webhook、token、credential；遠端舊版曾含 webhook 字串，使用者仍需自行輪替舊 webhook。

## 最近更新

- 時間：2026-08-11 09:31 +08:00
- 更新者：Hermes
- 電腦：DESKTOP-P5NQS9D
- 成果 commit：`59d5528`
- Git push：VERIFIED（`master`，LOCAL = REMOTE `59d5528`）
- Obsidian：NOT_CONFIGURED（本專案未登記 Obsidian 筆記）
