import os
import json
import re
import time
from pathlib import Path
from google import genai
from google.genai import types

# 設定 Vertex AI
CREDENTIALS_PATH = r"C:\Users\sink6\gcp-vertex-sa.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

# 使用 google-genai 介面
client = genai.Client(vertexai=True, project="aiagent-503607", location="us-central1")
model_id = "gemini-2.5-flash"

PROMPT_TEMPLATE = """
請將以下「英文單字與其翻譯」的清單進行整理與字根語源拆解（類似劉毅字典風格）。
如果單字有字首、字根或字尾，請清楚標示出來。過於簡單的單字請將 decomp 設為 null。

請輸出 JSON 格式的字典 (Dictionary)，key 為英文單字，value 為一個物件包含：
- pron: K.K.音標（若不確定請補上，不含中括號）
- pos: 詞性縮寫（如 v., n., adj. 等，若有多個以逗號隔開）
- gloss: 中文解釋
- decomp: 語源拆解字串，格式如 `prefix (意思) + root (意思) + suffix (意思)`，若無則為 null

例如：
"abbreviation": {
  "pron": "əˌbriviˈeʃən",
  "pos": "n.",
  "gloss": "縮略語",
  "decomp": "ab- (加強語氣) + brev (短) + -ation (名詞字尾)"
},
"boy": {
  "pron": "bɔɪ",
  "pos": "n.",
  "gloss": "男孩",
  "decomp": null
}

請只輸出純 JSON，不要 Markdown：
{lines}
"""

def get_vocab_lines():
    lines = []
    # 支援專案相對路徑與上層目錄路徑的相容性
    src_paths = [Path("7000_vocab_utf8.txt"), Path("../7000_vocab_utf8.txt")]
    src_path = None
    for p in src_paths:
        if p.exists():
            src_path = p
            break
            
    if not src_path:
        raise FileNotFoundError("無法找到 7000_vocab_utf8.txt 檔案！")
        
    print(f"正在從 {src_path.resolve()} 讀取字源...")
    with open(src_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("大學") and len(line) > 1:
                # 只收集真的有單字的行
                if line[0].isalpha() or line.startswith("*"):
                    lines.append(line)
    return lines


def expand_word_part(word_part: str) -> list[str]:
    """展開複合單字格式：achieve(ment) → [achieve, achievement]; adviser/advisor → [adviser, advisor]"""
    word_part = word_part.replace("*", "").strip().lower()
    # 清除中文註解或標點
    word_part = re.split(r'[、，,；;]', word_part)[0]
    word_part = re.sub(r'[^\w\-\/\(\)]', '', word_part)

    if '(' in word_part and ')' in word_part:
        # achieve(ment) → achieve, achievement
        m = re.match(r'^([a-z\-]+)\(([a-z\-]+)\)$', word_part)
        if m:
            base, suffix = m.groups()
            return [base, base + suffix]
        # v(i)olent → violent, volent
        m = re.match(r'^([a-z\-]+)\(([a-z\-]+)\)([a-z\-]*)$', word_part)
        if m:
            base, opt, tail = m.groups()
            return [base + tail, base + opt + tail]

    if '/' in word_part:
        return [w.strip() for w in word_part.split('/') if w.strip()]

    return [word_part]


def _word_exists(word: str, results: dict) -> bool:
    """Case-insensitive check if word exists in results as a valid dict."""
    # Direct match first (fast path)
    if word in results and isinstance(results[word], dict):
        return True
    # Case-insensitive fallback
    for k in results:
        if k.lower() == word.lower() and isinstance(results[k], dict):
            return True
    return False

def main():
    lines = get_vocab_lines()
    print(f"找到 {len(lines)} 個單字條目。")
    
    checkpoint_file = Path("data/vocab_decomposition_v5.json")
    if not checkpoint_file.parent.exists():
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
    if checkpoint_file.exists():
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            results = json.load(f)
        print(f"從 checkpoint 載入 {len(results)} 筆已處理紀錄。")
    else:
        results = {}

    # 1. 精密診斷與主動清理非 dictionary 結構或缺欄位的臟資料 (如 'abandon', 'ability', 'side' 等)
    cleaned_count = 0
    for k in list(results.keys()):
        v = results[k]
        if not isinstance(v, dict):
            print(f"【清理】發現非字典格式臟資料: '{k}' = {repr(v)}")
            results.pop(k)
            cleaned_count += 1
        else:
            # 檢查關鍵欄位是否缺失
            if not v.get("pron") or not v.get("pos") or not v.get("gloss"):
                print(f"【清理】發現遺漏關鍵欄位: '{k}' = {v}")
                results.pop(k)
                cleaned_count += 1
                
    if cleaned_count > 0:
        print(f"共清理了 {cleaned_count} 筆不合規或有缺損的單字條目，準備重新補件。")
        # 立即寫入一次，確保清理後的 checkpoint 與硬碟同步
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    batch_size = 30
    lines_to_process = []
    for line in lines:
        # 提取單字並展開複合格式
        raw_word = line.split()[0]
        sub_words = expand_word_part(raw_word)
        # 只有全部展開子字都已存在時才跳過
        all_exist = all(_word_exists(w, results) for w in sub_words)
        if not all_exist:
            lines_to_process.append(line)

    print(f"尚有 {len(lines_to_process)} 個單字待處理（包含修補件）。")

    if not lines_to_process:
        print("全部處理完成！單字庫狀態已符合 100% 合規要求。")
        return

    max_batches_for_test = 240
    processed_batches = 0

    for i in range(0, len(lines_to_process), batch_size):
        if processed_batches >= max_batches_for_test:
            print("批次已達上限，暫停執行。")
            break
            
        batch = lines_to_process[i:i+batch_size]
        prompt = PROMPT_TEMPLATE.replace("{lines}", "\n".join(batch))
        
        max_retries = 3
        retry_delay = 30
        success = False
        
        for attempt in range(max_retries):
            try:
                print(f"正在處理批次 {processed_batches+1} (嘗試 {attempt+1}): {batch[0].split()[0]} ~ {batch[-1].split()[0]}...")
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                    ),
                )
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:-3].strip()
                elif text.startswith("```"):
                    text = text[3:-3].strip()
                    
                batch_result = json.loads(text)
                
                for k, v in batch_result.items():
                    # 再次防呆：寫入前確保為 dictionary
                    if isinstance(v, dict):
                        results[k] = v
                    else:
                        print(f"警告：API 回傳的 '{k}' 不是 dict 物件，跳過寫入。")
                    
                # 寫入專案內的 data 目錄
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                    
                # 同步更新到 Hermes AppData 目錄
                dest_file = Path(r"C:\Users\sink6\AppData\Local\hermes\data\vocab_decomposition_v5.json")
                if dest_file.parent.exists():
                    with open(dest_file, "w", encoding="utf-8") as f:
                        json.dump(results, f, ensure_ascii=False, indent=2)
                    print(f"已同步更新至 AppData: {dest_file}")
                    
                processed_batches += 1
                print(f"批次處理成功！目前已累積 {len(results)} 筆單字。")
                success = True
                time.sleep(1) # 局部重修，僅需短暫休眠
                break
                
            except Exception as e:
                err_str = str(e)
                print(f"處理異常: {err_str}")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"遇到 Rate Limit，暫停 {retry_delay} 秒後重試...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    break
        
        if not success:
            print(f"批次 {processed_batches+1} 徹底失敗，中止腳本。")
            break

if __name__ == "__main__":
    main()
