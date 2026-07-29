import os
import re
import json
import time
import sys
import sqlite3
from pathlib import Path
from google import genai
from google.genai import types

# Force stdout/stderr to use UTF-8 encoding to avoid Windows CP950 console errors
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 1. Paths configuration
project_dir = Path(__file__).resolve().parent
corpus_dir = project_dir / "data" / "vocab_corpus"
db_path = corpus_dir / "英文字根字典_Canonical.sqlite3"
txt_path = project_dir / "data" / "7000_vocab_utf8.txt"
v5_local_path = project_dir / "data" / "vocab_decomposition_v5.json"
v5_bak_path = project_dir / "data" / "vocab_decomposition_v5.json.bak"

# Set up Vertex AI credentials
if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    sa_path = Path(r"C:\Users\Yulin\gcp-vertex-sa.json")
    if sa_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(sa_path)

# Mapped filename map for corrupted names in source_ref
filename_map = {
    "01_Prefix": "英文字根_01_Prefix_字首_fixed.md",
    "02A_Suffix_Noun": "英文字根_02A_Suffix_Noun_名詞字尾_fixed.md",
    "02B_Suffix_Adjective": "英文字根_02B_Suffix_Adjective_形容詞字尾_fixed.md",
    "02C_Suffix_Adverb": "英文字根_02C_Suffix_Adverb_副詞字尾_fixed.md",
    "02D_Suffix_Verb": "英文字根_02D_Suffix_Verb_動詞字尾_fixed.md",
    "02_Suffix": "英文字根_02_Suffix_字尾_fixed.md",
    "03_Root": "英文字根_03_Root_字根_fixed.md",
    "04_Appendix": "英文字根_04_Appendix_附錄_fixed.md",
    "05_Index": "英文字根_05_Index_索引_fixed.md"
}

def resolve_filename(corrupted_name):
    for key, correct_name in filename_map.items():
        if key in corrupted_name:
            return correct_name
    return None

def parse_source_ref(ref_str):
    if not ref_str:
        return None, None
    parts = ref_str.split(";")
    for part in parts:
        part = part.strip()
        m = re.search(r"([^:]+\.md):(\d+)", part)
        if m:
            corrupted_fn = m.group(1)
            ln = int(m.group(2))
            correct_fn = resolve_filename(corrupted_fn)
            if correct_fn:
                return correct_fn, ln
    return None, None

file_lines_cache = {}
def get_line_from_file(filename, line_num):
    if filename not in file_lines_cache:
        path = corpus_dir / filename
        if not path.exists():
            for p in corpus_dir.rglob(filename):
                path = p
                break
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_lines_cache[filename] = f.readlines()
        except Exception:
            return None
            
    lines = file_lines_cache.get(filename)
    if lines and 1 <= line_num <= len(lines):
        return lines[line_num - 1]
    return None

def extract_definition_from_line(word, line_text):
    if not line_text:
        return None
    escaped_word = re.escape(word)
    pattern = (
        r"(?:\b|(?<=^))" + escaped_word + r"\b"
        r"\s*(?:\[(?P<pron>[^\]]+)\]|\((?P<pron2>[^\)]+)\))?"
        r"\s*(?P<pos>(?:adj|adv|n|v|prep|pron|conj|interj)\.?\s+)?"
        r"\s*(?P<gloss>[^《\n]+?)"
        r"(?:《(?P<decomp>[^》]+)》)?"
        r"(?=\s+[a-zA-Z][a-zA-Z'\-]{2,}\s*(?:\[|\()|\s*$)"
    )
    m = re.search(pattern, line_text)
    if m:
        pron = m.group("pron") or m.group("pron2")
        pos = m.group("pos")
        gloss = m.group("gloss")
        decomp = m.group("decomp")
        
        if gloss:
            gloss = re.sub(r"^=\s*[^=]+\s*=\s*", "", gloss)
            gloss = gloss.strip(" ;，、")
            
        return {
            "pron": pron.strip() if pron else None,
            "pos": pos.strip() if pos else None,
            "gloss": gloss.strip() if gloss else None,
            "decomp": clean_decomp_text(decomp)
        }
    return None

def clean_decomp_text(decomp):
    if not decomp:
        return None
    decomp = re.sub(r"\b10\b", "to", decomp)
    decomp = re.sub(r"\s*\+\s*", " + ", decomp)
    decomp = re.sub(r"\s*=\s*", " = ", decomp)
    decomp = re.sub(r"\s+", " ", decomp)
    return decomp.strip()

def get_hermes_home():
    override = os.environ.get("POMODORO_DATA_DIR")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "hermes"
    return Path.home() / "AppData" / "Local" / "hermes"

def clean_record_gloss(gloss):
    if not gloss:
        return ""
    gloss = re.sub(r"^(?:adj|adv|n|v|prep|pron|conj|interj)\.?\s*", "", gloss).strip()
    gloss = gloss.replace("\ufffd", "")
    return gloss.strip(" ;，、")

def has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))

def decomposition_is_structured(decomposition: str) -> bool:
    if not decomposition:
        return False
    if "+" in decomposition or "(" in decomposition:
        return True
    if "=" in decomposition:
        right = decomposition.rsplit("=", 1)[-1].strip()
        if has_cjk(right):
            return True
        return bool(re.findall(r"[A-Za-z]{2,}", right))
    return "-" in decomposition

def is_valid_word(word):
    if word.startswith("-") or word.endswith("-"):
        return False
    if "$$" in word or "\\" in word or "*" in word:
        return False
    if len(word) < 2 and word.lower() not in ["a", "i"]:
        return False
    return True

def expand_word_part(word_part: str) -> list[str]:
    word_part = word_part.replace("*", "").strip().lower()
    word_part = re.split(r'[、，,；;]', word_part)[0]
    word_part = re.sub(r'[^\w\-\/\(\)]', '', word_part)
    if '(' in word_part and ')' in word_part:
        m = re.match(r'^([a-z\-]+)\(([a-z\-]+)\)$', word_part)
        if m:
            base, suffix = m.groups()
            return [base, base + suffix]
        m = re.match(r'^([a-z\-]+)\(([a-z\-]+)\)([a-z\-]*)$', word_part)
        if m:
            base, opt, tail = m.groups()
            return [base + tail, base + opt + tail]
    if '/' in word_part:
        return [w.strip() for w in word_part.split('/') if w.strip()]
    return [word_part]

# Prompt template for Gemini API
PROMPT_TEMPLATE = """
請校正與補全以下可能含有 OCR 損壞或編碼錯誤的英文單字。
請輸出 JSON 格式的字典 (Dictionary)，key 為英文單字，value 為一個物件包含：
- pron: 正確的 K.K.音標（不含中括號，例如: əˈbændən）
- pos: 詞性縮寫（如 v., n., adj., adv., prep. 等，若有多個以逗號隔開）
- gloss: 正確的中文釋義（去除任何 LaTeX、HTML、問號、空括號或損壞字元）
- decomp: 語源字根拆解字串，格式如 `prefix (意思) + root (意思) + suffix (意思)`。如果該單字沒有字首字尾或字根拆解，請設為 null

重要規則：
1. 如果傳入的單字拼寫有明顯的 OCR 錯誤（例如 "apporHon" 正確應為 "apportion"），請在輸出的 JSON 中將 key 修正為正確的英文單字。
2. 請確保輸出是標準的 JSON 格式。

輸入資料：
{lines}
"""

def main():
    # 1. Gather all word keys from 3 sources
    txt_words = set()
    if txt_path.exists():
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("大學") and len(line) > 1:
                    if line[0].isalpha() or line.startswith("*"):
                        parts = line.split()
                        if parts:
                            for w in expand_word_part(parts[0]):
                                if is_valid_word(w):
                                    txt_words.add(w)
                                    
    sqlite_words = {}
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT headword, source_ipa, source_pos, source_meaning_zh, source_ref FROM words")
        for r in cursor.fetchall():
            w = r[0].lower()
            if is_valid_word(w):
                sqlite_words[w] = {
                    "ipa": r[1],
                    "pos": r[2],
                    "sm_zh": r[3],
                    "ref": r[4]
                }
        conn.close()
        
    v5_current = {}
    if v5_local_path.exists():
        try:
            with open(v5_local_path, "r", encoding="utf-8") as f:
                v5_current = json.load(f)
        except Exception:
            pass
            
    v5_bak = {}
    if v5_bak_path.exists():
        try:
            with open(v5_bak_path, "r", encoding="utf-8") as f:
                v5_bak = json.load(f)
        except Exception:
            pass
            
    # Combine keys
    all_keys = set(txt_words) | set(sqlite_words.keys()) | set(v5_current.keys()) | set(v5_bak.keys())
    print(f"三路合併後的單字鍵總量: {len(all_keys)}")
    
    clean_records = {}
    words_needing_llm = {}
    
    for hw in all_keys:
        hw_lower = hw.lower()
        
        # Determine base record using fallbacks
        record = None
        
        # Option A: already processed high quality record in current v5
        if hw in v5_current and isinstance(v5_current[hw], dict):
            record = dict(v5_current[hw])
        elif hw_lower in v5_current and isinstance(v5_current[hw_lower], dict):
            record = dict(v5_current[hw_lower])
            
        # Option B: fallback to SQLite and local MD extraction
        if not record or not record.get("gloss"):
            sql_data = sqlite_words.get(hw_lower)
            if sql_data:
                fn, ln = parse_source_ref(sql_data["ref"])
                extracted = None
                if fn and ln:
                    line_text = get_line_from_file(fn, ln)
                    extracted = extract_definition_from_line(hw_lower, line_text)
                    if not extracted or not extracted.get("decomp"):
                        next_line = get_line_from_file(fn, ln + 1)
                        if next_line and next_line.strip().startswith("《"):
                            m_next = re.search(r"《([^》]+)》", next_line)
                            if m_next:
                                decomp = m_next.group(1).strip()
                                if extracted:
                                    extracted["decomp"] = clean_decomp_text(decomp)
                                else:
                                    extracted = {"pron": None, "pos": None, "gloss": None, "decomp": clean_decomp_text(decomp)}
                
                record = {
                    "pron": sql_data["ipa"],
                    "pos": sql_data["pos"],
                    "gloss": None,
                    "decomp": None
                }
                if extracted:
                    if extracted.get("pron"): record["pron"] = extracted["pron"]
                    if extracted.get("pos"): record["pos"] = extracted["pos"]
                    if extracted.get("gloss"): record["gloss"] = extracted["gloss"]
                    if extracted.get("decomp"): record["decomp"] = extracted["decomp"]
                    
                if not record["gloss"]:
                    gloss = sql_data["sm_zh"] if sql_data["sm_zh"] else ""
                    m_bracket = re.search(r"《([^》]+)》", gloss)
                    if m_bracket:
                        if not record["decomp"]:
                            record["decomp"] = clean_decomp_text(m_bracket.group(1))
                        gloss = gloss.replace(m_bracket.group(0), "").strip()
                    record["gloss"] = clean_record_gloss(gloss)
                    
        # Option C: fallback to legacy V5 backup JSON
        if not record or not record.get("gloss"):
            if hw in v5_bak and isinstance(v5_bak[hw], dict):
                record = dict(v5_bak[hw])
            elif hw_lower in v5_bak and isinstance(v5_bak[hw_lower], dict):
                record = dict(v5_bak[hw_lower])
                
        # Option D: empty shell
        if not record:
            record = {
                "pron": None,
                "pos": None,
                "gloss": None,
                "decomp": None
            }
            
        # Clean pos and decomp formatting
        if record.get("pos"):
            record["pos"] = re.sub(r"[^\w\.,\s]", "", record["pos"]).strip()
        if record.get("decomp"):
            record["decomp"] = clean_decomp_text(record["decomp"])
            
        # Quality gates check
        has_corruption = "\ufffd" in (record.get("gloss") or "") or "\ufffd" in (record.get("pron") or "")
        has_empty = not record.get("gloss") or not record.get("pron") or not record.get("pos")
        has_plus_in_gloss = "+" in (record.get("gloss") or "")
        
        has_decomp_damage = False
        if record.get("decomp"):
            if any(char in record["decomp"] for char in ["τ", "ω", "$$", "\\", "●"]):
                has_decomp_damage = True
            elif re.search(r"\b\d+\b", record["decomp"]):
                has_decomp_damage = True
            elif not decomposition_is_structured(record["decomp"]):
                has_decomp_damage = True
                
        if has_corruption or has_empty or has_decomp_damage or has_plus_in_gloss:
            words_needing_llm[hw] = record
        else:
            clean_records[hw] = record
            
    print(f"三路彙總分析結果:")
    print(f"  直接無損合格: {len(clean_records)} 筆")
    print(f"  需要 LLM 修復或補全: {len(words_needing_llm)} 筆")
    
    # 2. Invoke Gemini for repairs
    repaired_records = {}
    if words_needing_llm:
        print("正在初始化 Vertex AI...")
        client = genai.Client(vertexai=True, project="aiagent-503607", location="us-central1")
        model_id = "gemini-2.5-flash"
        
        batch_size = 25
        need_list = list(words_needing_llm.items())
        
        for i in range(0, len(need_list), batch_size):
            batch = need_list[i:i+batch_size]
            batch_dict = {k: v for k, v in batch}
            
            prompt = PROMPT_TEMPLATE.format(lines=json.dumps(batch_dict, ensure_ascii=False, indent=2))
            
            max_retries = 3
            retry_delay = 10
            success = False
            
            for attempt in range(max_retries):
                try:
                    print(f"正在處理 LLM 批次 {i//batch_size + 1} (嘗試 {attempt+1}): {batch[0][0]} ~ {batch[-1][0]}...")
                    response = client.models.generate_content(
                        model=model_id,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json"
                        ),
                    )
                    text = response.text.strip()
                    batch_result = json.loads(text)
                    
                    for k, v in batch_result.items():
                        if isinstance(v, dict):
                            repaired_records[k] = v
                            print(f"  [修復] {k} -> {v['gloss']}")
                        else:
                            print(f"  警告：LLM 回傳 {k} 的值非字典，跳過。")
                    success = True
                    break
                except Exception as e:
                    print(f"  API 呼叫出錯: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    
            if not success:
                print(f"批次 {i//batch_size + 1} 重試失敗，跳過此批次...")
                
            time.sleep(0.5)
            
    # 3. Merge and Save
    final_records = {}
    final_records.update(clean_records)
    final_records.update(repaired_records)
    
    # Final filter: delete non-word keys if they sneaked in
    final_keys = list(final_records.keys())
    for k in final_keys:
        if not is_valid_word(k):
            final_records.pop(k)
            
    sorted_records = {k: final_records[k] for k in sorted(final_records.keys())}
    
    # Save V5 local database
    v5_local_path.parent.mkdir(parents=True, exist_ok=True)
    with open(v5_local_path, "w", encoding="utf-8") as f:
        json.dump(sorted_records, f, ensure_ascii=False, indent=2)
    print(f"V5 本機資料庫已更新並寫入: {v5_local_path} (共 {len(sorted_records)} 筆單字)")
    
    # Dynamic sync to AppData
    hermes_data_dir = get_hermes_home() / "data"
    try:
        hermes_data_dir.mkdir(parents=True, exist_ok=True)
        v5_appdata_path = hermes_data_dir / "vocab_decomposition_v5.json"
        with open(v5_appdata_path, "w", encoding="utf-8") as f:
            json.dump(sorted_records, f, ensure_ascii=False, indent=2)
        print(f"同步成功！AppData 資料庫已寫入: {v5_appdata_path}")
        
        # Also copy V4 database (vocab_decomposition.json) to AppData for verification support
        v4_local_path = project_dir / "data" / "vocab_decomposition.json"
        if v4_local_path.exists():
            v4_appdata_path = hermes_data_dir / "vocab_decomposition.json"
            import shutil
            shutil.copy2(v4_local_path, v4_appdata_path)
            print(f"同步成功！V4 AppData 資料庫已複製: {v4_appdata_path}")
    except Exception as e:
        print(f"提示：同步到 AppData 時出錯: {e}")

if __name__ == "__main__":
    main()
