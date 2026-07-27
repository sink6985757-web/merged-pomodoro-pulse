#!/usr/bin/env python3
"""
Audit script for the 曾仕強教授 I Ching hexagram interpretation system.
Checks KING_WEN_MATRIX, trigram mappings, hexagram data integrity, etc.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util
_iching_spec = importlib.util.spec_from_file_location(
    "pomodoro_iching_data",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_iching_data.py"),
)
_iching_mod = importlib.util.module_from_spec(_iching_spec)
_iching_spec.loader.exec_module(_iching_mod)

# Also load the chat module's constants
_chat_spec = importlib.util.spec_from_file_location(
    "pomodoro_chat_original",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_chat_original.py"),
)
_chat_mod = importlib.util.module_from_spec(_chat_spec)
_chat_spec.loader.exec_module(_chat_mod)

HEXAGRAM_DATA = _iching_mod.HEXAGRAM_DATA
KING_WEN_MATRIX = _chat_mod.KING_WEN_MATRIX
HEXAGRAM_NAMES = _chat_mod.HEXAGRAM_NAMES
TRIGRAM_ORDER = _chat_mod.TRIGRAM_ORDER

# Standard King Wen hexagram compositions (upper trigram, lower trigram)
# Format: hex_number: (upper_trigram_name, lower_trigram_name, hexagram_name)
# Based on standard I Ching references
STANDARD_COMPOSITION = {
    1:  ("乾", "乾", "乾為天"),
    2:  ("坤", "坤", "坤為地"),
    3:  ("坎", "震", "水雷屯"),
    4:  ("艮", "坎", "山水蒙"),
    5:  ("坎", "乾", "水天需"),
    6:  ("乾", "坎", "天水訟"),
    7:  ("坤", "坎", "地水師"),
    8:  ("坎", "坤", "水地比"),
    9:  ("巽", "乾", "風天小畜"),
    10: ("乾", "兌", "天澤履"),
    11: ("坤", "乾", "地天泰"),
    12: ("乾", "坤", "天地否"),
    13: ("乾", "離", "天火同人"),
    14: ("離", "乾", "火天大有"),
    15: ("坤", "艮", "地山謙"),
    16: ("震", "坤", "雷地豫"),
    17: ("兌", "震", "澤雷隨"),
    18: ("艮", "巽", "山風蠱"),
    19: ("坤", "兌", "地澤臨"),
    20: ("巽", "坤", "風地觀"),
    21: ("離", "震", "火雷噬嗑"),
    22: ("艮", "離", "山火賁"),
    23: ("艮", "坤", "山地剝"),
    24: ("坤", "震", "地雷復"),
    25: ("乾", "震", "天雷無妄"),
    26: ("艮", "乾", "山天大畜"),
    27: ("艮", "震", "山雷頤"),
    28: ("兌", "巽", "澤風大過"),
    29: ("坎", "坎", "坎為水"),
    30: ("離", "離", "離為火"),
    31: ("兌", "艮", "澤山咸"),
    32: ("震", "巽", "雷風恆"),
    33: ("乾", "艮", "天山遯"),
    34: ("震", "乾", "雷天大壯"),
    35: ("離", "坤", "火地晉"),
    36: ("坤", "離", "地火明夷"),
    37: ("巽", "離", "風火家人"),
    38: ("離", "兌", "火澤睽"),
    39: ("坎", "艮", "水山蹇"),
    40: ("震", "坎", "雷水解"),
    41: ("艮", "兌", "山澤損"),
    42: ("巽", "震", "風雷益"),
    43: ("兌", "乾", "澤天夬"),
    44: ("乾", "巽", "天風姤"),
    45: ("兌", "坤", "澤地萃"),
    46: ("坤", "巽", "地風升"),
    47: ("兌", "坎", "澤水困"),
    48: ("坎", "巽", "水風井"),
    49: ("兌", "離", "澤火革"),
    50: ("離", "巽", "火風鼎"),
    51: ("震", "震", "震為雷"),
    52: ("艮", "艮", "艮為山"),
    53: ("巽", "艮", "風山漸"),
    54: ("震", "兌", "雷澤歸妹"),
    55: ("震", "離", "雷火豐"),
    56: ("離", "艮", "火山旅"),
    57: ("巽", "巽", "巽為風"),
    58: ("兌", "兌", "兌為澤"),
    59: ("巽", "坎", "風水渙"),
    60: ("坎", "兌", "水澤節"),
    61: ("巽", "兌", "風澤中孚"),
    62: ("震", "艮", "雷山小過"),
    63: ("坎", "離", "水火既濟"),
    64: ("離", "坎", "火水未濟"),
}

print("=" * 80)
print("1. KING_WEN_MATRIX 正確性檢查")
print("=" * 80)

errors = []
for hex_no, (std_upper, std_lower, std_name) in STANDARD_COMPOSITION.items():
    matrix_value = KING_WEN_MATRIX.get(std_upper, {}).get(std_lower)
    if matrix_value != hex_no:
        errors.append(
            f"  ERROR: 卦{hex_no} {std_name} (上{std_upper}下{std_lower}) → "
            f"KING_WEN_MATRIX[{std_upper}][{std_lower}] = {matrix_value}, 應為 {hex_no}"
        )

if errors:
    print(f"\n發現 {len(errors)} 個錯誤:\n")
    for e in errors:
        print(e)
else:
    print("\n✓ 所有64卦的 KING_WEN_MATRIX 映射完全正確")

print("\n" + "=" * 80)
print("2. HEXAGRAM_NAMES 與 HEXAGRAM_DATA name 一致性檢查")
print("=" * 80)

name_mismatches = []
for hex_no in range(1, 65):
    names_name = HEXAGRAM_NAMES.get(hex_no, "?")
    data_name = HEXAGRAM_DATA.get(hex_no, {}).get("name", "?")
    if names_name != data_name:
        name_mismatches.append(f"  卦{hex_no}: HEXAGRAM_NAMES='{names_name}' ≠ HEXAGRAM_DATA='{data_name}'")

if name_mismatches:
    print(f"\n發現 {len(name_mismatches)} 個名稱不一致:\n")
    for m in name_mismatches:
        print(m)
else:
    print("\n✓ 名稱完全一致")

print("\n" + "=" * 80)
print("3. HEXAGRAM_DATA 完整性檢查")
print("=" * 80)

missing_hexagrams = [n for n in range(1, 65) if n not in HEXAGRAM_DATA]
if missing_hexagrams:
    print(f"\n  缺卦: {missing_hexagrams}")
else:
    print("\n✓ 64卦全部存在")

print("\n檢查每卦是否有6條爻辭:")
line_count_errors = []
for hex_no in range(1, 65):
    data = HEXAGRAM_DATA[hex_no]
    lines = data.get("lines", [])
    if len(lines) != 6:
        line_count_errors.append(f"  卦{hex_no} {data['name']}: 有 {len(lines)} 條爻辭 (應為6)")

if line_count_errors:
    for e in line_count_errors:
        print(e)
else:
    print("✓ 所有64卦均有6條爻辭")

print("\n" + "=" * 80)
print("4. 卦辭/爻辭重複檢查 (copy-paste errors)")
print("=" * 80)

judgments = {}
line_map = {}  # (hex_no, line_idx) -> text

for hex_no in range(1, 65):
    data = HEXAGRAM_DATA[hex_no]
    j = data["judgment"]
    judgments.setdefault(j, []).append(hex_no)
    for idx, line in enumerate(data["lines"]):
        key = line.strip()
        line_map.setdefault(key, []).append((hex_no, idx))

# Check for duplicate judgments
dup_judgments = {j: hexes for j, hexes in judgments.items() if len(hexes) > 1}
if dup_judgments:
    print(f"\n⚠ 發現 {len(dup_judgments)} 組重複卦辭:\n")
    for j, hexes in sorted(dup_judgments.items()):
        print(f"  '{j[:40]}...' 出現在卦: {hexes}")
else:
    print("\n✓ 卦辭無重複")

# Check for duplicate line texts across different hexagrams
dup_lines = {k: v for k, v in line_map.items() if len(v) > 1}
if dup_lines:
    print(f"\n⚠ 發現 {len(dup_lines)} 組重複爻辭:\n")
    for k, v in sorted(dup_lines.items(), key=lambda x: -len(x[1]))[:20]:
        if len(v) > 2:
            print(f"  '{k[:50]}...' 出現在: {v}")
else:
    print("\n✓ 爻辭無跨卦重複")

# Check for duplicate line texts within same hexagram
print("\n檢查同一卦內爻辭是否有重複:")
intra_dups = []
for hex_no in range(1, 65):
    data = HEXAGRAM_DATA[hex_no]
    lines = data["lines"]
    seen = {}
    for idx, line in enumerate(lines):
        text = line.strip()
        if text in seen:
            intra_dups.append(f"  卦{hex_no} {data['name']}: 爻{seen[text]}/{idx} 重複: {text[:40]}...")
        seen[text] = idx

if intra_dups:
    for d in intra_dups:
        print(d)
else:
    print("✓ 無卦內爻辭重複")

print("\n" + "=" * 80)
print("5. 爻辭格式檢查 (初/二/三/四/五/上 及 六/九)")
print("=" * 80)

position_labels = ["初", "二", "三", "四", "五", "上"]
format_errors = []
for hex_no in range(1, 65):
    data = HEXAGRAM_DATA[hex_no]
    lines = data["lines"]
    for idx, line in enumerate(lines):
        expected_prefix = position_labels[idx]
        if not line.startswith(expected_prefix):
            format_errors.append(f"  卦{hex_no} {data['name']} 爻{idx}: 開頭不是'{expected_prefix}' → '{line[:15]}...'")

if format_errors:
    print(f"\n發現 {len(format_errors)} 個格式錯誤:\n")
    for e in format_errors:
        print(e)
else:
    print("\n✓ 爻辭格式正確")

print("\n" + "=" * 80)
print("6. 變爻規則測試 (resolve_line_by_moving)")
print("=" * 80)

resolve_fn = _iching_mod.resolve_line_by_moving

test_cases = [
    # (hex_no, moving_indexes, expected_rule_desc)
    # 0 變爻
    (1, [], "靜卦"),
    (15, [], "靜卦"),
    # 1 變爻
    (1, [0], "一爻變"),
    (1, [4], "一爻變"),
    (64, [5], "一爻變"),
    # 2 變爻
    (3, [0, 2], "二爻變"),
    (7, [1, 4], "二爻變"),
    # 3 變爻
    (11, [0, 1, 2], "三爻變"),
    # 4 變爻
    (23, [0, 1, 2, 3], "四爻變"),
    # 5 變爻
    (24, [0, 1, 2, 3, 4], "五爻變"),
    # 6 變爻
    (1, [0, 1, 2, 3, 4, 5], "六爻全變"),
    (2, [0, 1, 2, 3, 4, 5], "六爻全變"),
    (3, [0, 1, 2, 3, 4, 5], "六爻全變"),
]

rule_errors = []
for hex_no, moving, expected in test_cases:
    text, rule = resolve_fn(hex_no, moving)
    if expected not in rule:
        rule_errors.append(f"  卦{hex_no} 變爻{moving}: rule='{rule}' 不包含 '{expected}'")

if rule_errors:
    print(f"\n發現 {len(rule_errors)} 個規則錯誤:\n")
    for e in rule_errors:
        print(e)
else:
    print(f"\n✓ 所有 {len(test_cases)} 個變爻測試案例通過")

# Test that 2變爻 uses the upper (max index) line
print("\n2變爻取上爻測試:")
for hex_no in [1, 11, 30, 64]:
    moving = [0, 2]  # 初 and 三, upper should be 三 (index 2)
    text, rule = resolve_fn(hex_no, moving)
    upper_line = HEXAGRAM_DATA[hex_no]["lines"][2]
    match = upper_line[:20] in text
    print(f"  卦{hex_no}: moving={moving}, 上爻=index2, {'✓ 正確' if match else '✗ 錯誤' if match else '✗'} text[:40]={text[:40]}")

print("\n" + "=" * 80)
print("7. 三錢筮法 casting 測試 (cast_hexagram)")
print("=" * 80)

cast_fn = _chat_mod.cast_hexagram

# Run 100 casts and check validity
print("\n執行100次 cast_hexagram 統計:")
moving_counts = {i: 0 for i in range(7)}
valid_results = 0
hexagram_freq = {i: 0 for i in range(1, 65)}

for trial in range(100):
    result = cast_fn()
    values = result["values"]
    moving = result["moving"]
    base_no = result["base_no"]
    changed_no = result["changed_no"]
    
    # Check values are in valid range
    if not all(v in {6, 7, 8, 9} for v in values):
        print(f"  錯誤: trial {trial} values={values} 含無效值")
        continue
    if len(values) != 6:
        print(f"  錯誤: trial {trial} 只有 {len(values)} 個值")
        continue
    if base_no not in HEXAGRAM_NAMES:
        print(f"  錯誤: trial {trial} base_no={base_no} 不在1-64")
        continue
    if changed_no not in HEXAGRAM_NAMES:
        print(f"  錯誤: trial {trial} changed_no={changed_no} 不在1-64")
        continue
    
    moving_counts[len(moving)] += 1
    hexagram_freq[base_no] += 1
    valid_results += 1

print(f"  有效結果: {valid_results}/100")
print(f"  變爻數量分布: {dict(sorted(moving_counts.items()))}")
print(f"  觸及卦數: {len([k for k, v in hexagram_freq.items() if v > 0])}/64")

print("\n" + "=" * 80)
print("8. 白話語言檢查")
print("=" * 80)

# Check for classical-only phrases that might be hard to understand
classical_markers = [
    "元亨利貞", "匪寇婚媾", "童蒙求我", 
]
# Check that judgments contain practical guidance (not just classical text)
non_baihua_count = 0
for hex_no in range(1, 65):
    j = HEXAGRAM_DATA[hex_no]["judgment"]
    # Must have modern interpretation (。後有現代白話)
    if "。" not in j:
        non_baihua_count += 1
        print(f"  卦{hex_no}: 卦辭無句號分隔 '{j[:40]}...'")

print(f"\n  卦辭無現代白話註解: {non_baihua_count}/64")

# Check for school-style explanations (曾仕強 style: practical, decision-oriented)
print("\n抽查10個重點卦的卦辭白話程度:")
key_hexagrams = [1, 2, 3, 11, 12, 15, 29, 30, 63, 64]
for hex_no in key_hexagrams:
    j = HEXAGRAM_DATA[hex_no]["judgment"]
    name = HEXAGRAM_DATA[hex_no]["name"]
    print(f"  卦{hex_no} {name}: {j[:60]}...")

print("\n" + "=" * 80)
print("9. 重點卦辭內容與曾仕強教授風格對照")
print("=" * 80)

# 曾仕強 key teachings to check:
checks = {
    1: "乾卦應有'自強不息'、'不可傲慢'",
    2: "坤卦應有'厚德載物'、'順勢'",
    3: "屯卦應講'初生艱難'、'最小可行啟動'",
    11: "泰卦應講'通泰'、'不可得意忘形'",
    12: "否卦應講'閉塞'、'止損'",
    15: "謙卦應講'謙虛'、'六爻皆吉'",
    63: "既濟應講'完成'、'慎終如始'",
    64: "未濟應講'未完成'、'補缺口'",
}

for hex_no, expected in checks.items():
    j = HEXAGRAM_DATA[hex_no]["judgment"]
    name = HEXAGRAM_DATA[hex_no]["name"]
    print(f"  卦{hex_no} {name}: {j}")

print("\n" + "=" * 80)
print("10. 隨機抽查30條爻辭")
print("=" * 80)

import random
random.seed(42)
check_indices = random.sample([(h, l) for h in range(1, 65) for l in range(6)], 30)
for hex_no, line_idx in sorted(check_indices, key=lambda x: (x[0], x[1])):
    name = HEXAGRAM_DATA[hex_no]["name"]
    line = HEXAGRAM_DATA[hex_no]["lines"][line_idx]
    pos = position_labels[line_idx]
    # Check the line label matches
    is_ok = line.startswith(pos)
    flag = "✓" if is_ok else "✗"
    print(f"  {flag} 卦{hex_no:02d} {name} {pos}爻: {line[:55]}")

# Summary
print("\n" + "=" * 80)
print("總結")
print("=" * 80)
total_issues = len(errors) + len(name_mismatches) + len(missing_hexagrams) + \
               len(line_count_errors) + len(format_errors) + len(rule_errors) + \
               len(dup_judgments) + len(dup_lines) + len(intra_dups) + non_baihua_count

print(f"\n發現問題總數: {total_issues}")
if total_issues == 0:
    print("狀態: 所有檢查通過 ✓")
else:
    print("狀態: 需要修正 ✗")
    print(f"\n細節:")
    print(f"  KING_WEN_MATRIX 錯誤: {len(errors)}")
    print(f"  名稱不一致: {len(name_mismatches)}")
    print(f"  缺卦: {len(missing_hexagrams)}")
    print(f"  爻辭數量錯誤: {len(line_count_errors)}")
    print(f"  格式錯誤: {len(format_errors)}")
    print(f"  變爻規則錯誤: {len(rule_errors)}")
    print(f"  重複卦辭: {len(dup_judgments)}")
    print(f"  重複爻辭(跨卦): {len(dup_lines)}")
    print(f"  重複爻辭(同卦): {len(intra_dups)}")
    print(f"  卦辭無白話: {non_baihua_count}")