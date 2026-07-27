import os
import json
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
    with open("7000_vocab_utf8.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("大學") and len(line)>1:
                # 只收集真的有單字的行
                if line[0].isalpha() or line.startswith("*"):
                    lines.append(line)
    return lines

def main():
    lines = get_vocab_lines()
    print(f"找到 {len(lines)} 個單字條目。")
    
    checkpoint_file = Path("vocab_decomposition_v5.json")
    if checkpoint_file.exists():
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            results = json.load(f)
        print(f"從 checkpoint 載入 {len(results)} 筆已處理紀錄。")
    else:
        results = {}

    batch_size = 30
    lines_to_process = []
    for line in lines:
        # Extract just word to check if it's in results
        word_part = line.split()[0].replace("*", "").lower()
        if word_part not in results:
            lines_to_process.append(line)

    print(f"尚有 {len(lines_to_process)} 個單字待處理。")

    if not lines_to_process:
        print("全部處理完成！")
        return

    max_batches_for_test = 240 # 足夠跑完 7000 單 (7000 / 30 = 233 批)
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
                    results[k] = v
                    
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                    
                # 同步更新到 Hermes data 目錄
                dest_file = Path(r"C:\Users\sink6\AppData\Local\hermes\data\vocab_decomposition_v5.json")
                with open(dest_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                    
                processed_batches += 1
                print(f"批次處理成功！目前已累積 {len(results)} 筆單字。")
                success = True
                time.sleep(15) # 基礎暫停
                break # 成功則跳出 retry 迴圈
                
            except Exception as e:
                err_str = str(e)
                print(f"處理異常: {err_str}")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"遇到 Rate Limit，暫停 {retry_delay} 秒後重試...")
                    time.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                else:
                    break # 非 429 錯誤不重試
        
        if not success:
            print(f"批次 {processed_batches+1} 徹底失敗，中止腳本。")
            break

if __name__ == "__main__":
    main()
