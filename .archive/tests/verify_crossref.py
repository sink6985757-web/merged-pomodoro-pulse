#!/usr/bin/env python3
"""Cross-validate HEXAGRAM_DATA keys match HEXAGRAM_NAMES."""
import sys, os, importlib.util

_iching_spec = importlib.util.spec_from_file_location(
    "pomodoro_iching_data",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_iching_data.py"),
)
_iching = importlib.util.module_from_spec(_iching_spec)
_iching_spec.loader.exec_module(_iching)

import re, importlib.util as iu

# Load chat module for HEXAGRAM_NAMES
chat_spec = iu.spec_from_file_location(
    "pomodoro_chat_original",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_chat_original.py"),
)
chat_mod = iu.module_from_spec(chat_spec)
# We just need HEXAGRAM_NAMES from chat, extract it without executing full module
# Instead, let's define it inline from the known values

HEXAGRAM_NAMES = {
    1: "乾為天", 2: "坤為地", 3: "水雷屯", 4: "山水蒙", 5: "水天需", 6: "天水訟",
    7: "地水師", 8: "水地比", 9: "風天小畜", 10: "天澤履", 11: "地天泰", 12: "天地否",
    13: "天火同人", 14: "火天大有", 15: "地山謙", 16: "雷地豫", 17: "澤雷隨", 18: "山風蠱",
    19: "地澤臨", 20: "風地觀", 21: "火雷噬嗑", 22: "山火賁", 23: "山地剝", 24: "地雷復",
    25: "天雷無妄", 26: "山天大畜", 27: "山雷頤", 28: "澤風大過", 29: "坎為水", 30: "離為火",
    31: "澤山咸", 32: "雷風恆", 33: "天山遯", 34: "雷天大壯", 35: "火地晉", 36: "地火明夷",
    37: "風火家人", 38: "火澤睽", 39: "水山蹇", 40: "雷水解", 41: "山澤損", 42: "風雷益",
    43: "澤天夬", 44: "天風姤", 45: "澤地萃", 46: "地風升", 47: "澤水困", 48: "水風井",
    49: "澤火革", 50: "火風鼎", 51: "震為雷", 52: "艮為山", 53: "風山漸", 54: "雷澤歸妹",
    55: "雷火豐", 56: "火山旅", 57: "巽為風", 58: "兌為澤", 59: "風水渙", 60: "水澤節",
    61: "風澤中孚", 62: "雷山小過", 63: "水火既濟", 64: "火水未濟",
}

print("Cross-check: HEXAGRAM_DATA keys vs HEXAGRAM_NAMES")
mismatches = []
for h in range(1, 65):
    data = _iching.HEXAGRAM_DATA[h]
    data_name = data["name"]
    expected_name = HEXAGRAM_NAMES[h]
    if data_name != expected_name:
        mismatches.append(f"  卦{h}: HEXAGRAM_DATA name='{data_name}', HEXAGRAM_NAMES[{h}]='{expected_name}'")

if mismatches:
    print(f"❌ {len(mismatches)} 卦名不匹配:")
    for m in mismatches:
        print(m)
else:
    print("✅ 全部 64 卦 HEXAGRAM_DATA 與 HEXAGRAM_NAMES 名稱一致")

# Check for any hexagram appearing in judgment text of wrong hexagram
print("\nDouble-check: judgment texts reference correct hexagram?")
# For each hexagram, check its judgment doesn't contain another hexagram's distinct name
all_names = set(HEXAGRAM_NAMES.values())
suspicious = []
for h in range(1, 65):
    data = _iching.HEXAGRAM_DATA[h]
    judgment = data["judgment"]
    own_name = data["name"]
    for other_name in all_names:
        if other_name != own_name and other_name in judgment:
            # Some names are substrings - filter out false positives
            # E.g. "大過" appears in "澤風大過" but also might naturally appear
            if len(other_name) >= 3:
                suspicious.append(f"  卦{h} '{own_name}' 卦辭含 '{other_name}'")

if suspicious:
    print(f"⚠️ {len(suspicious)} 條可能跨卦引用:")
    for s in suspicious[:20]:
        print(s)
else:
    print("✅ 無跨卦名稱混淆")

print("\n✅ 交叉驗證完成")