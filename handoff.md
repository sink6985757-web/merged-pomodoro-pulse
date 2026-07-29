# Handoff

## 目前做到哪
1. **V5 7000 單字庫校正與修補完成**：修復 `build_vocab_db.py` 的複合字展開與大小寫匹配邏輯，經 Vertex AI Gemini-2.5-flash 重新補件 76 筆缺失單字（含 side），`vocab_decomposition_v5.json` 從 5,786→5,805 筆，全庫 zero flat string/None/empty gloss。
2. **V5 驗證測試建置**：重寫 `tests/verify_vocab_decomposition.py` 為 V5 專用驗證（字典結構、非空欄位、品質閘門、regression case），與 `tests/verify_pomodoro_final.py` 雙測 100% PASS。
3. **雙路徑同步完成**：project 與 AppData 雙檔 md5 一致，播報核心 `pomodoro_chat_original.py` 讀取無誤。

## 目前狀態
- 可執行：是
- 已驗證：是 (verify_vocab_decomposition.py + verify_pomodoro_final.py 雙 PASS)
- 未完成：無

## 下一步
1. 每小時番茄鐘自動從 V5 5805 筆單字庫抽取播報。
2. 若需新增單字或修補，執行 `python build_vocab_db.py`（支援複合格式 + case-insensitive）。
3. CI 或開工時執行 `python tests/verify_vocab_decomposition.py` 驗證單字庫完整性。

## 注意事項
- `build_vocab_db.py` 已放回專案根目錄（從 .archive/ 移出並更新邏輯）。
- `README.md.bak` 為本次清理的備份，下次開工可視情況移入 .archive/ 或刪除。
- `data/` 目錄仍受 .gitignore 保護，不推送 GitHub。
- backup 檔：`data/vocab_decomposition_v5.json.bak` + `AppData/.../vocab_decomposition_v5.json.bak`。

## 最近更新
- 時間：2026-07-29 08:30 (GMT+8)
- 更新者：deepseek/deepseek-v4-pro (Nous)
- 電腦：DESKTOP-P5NQS9D
- 成果 commit：ea82a5d
- Git push：VERIFIED
- Obsidian：NOT_CONFIGURED