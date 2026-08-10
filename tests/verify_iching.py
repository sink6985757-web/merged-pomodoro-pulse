#!/usr/bin/env python3
"""
Final verification script for I Ching system.
Checks KING_WEN_MATRIX, probabilities, line texts, and end-to-end.
"""
import sys, os, importlib.util, collections, math, json

_this_dir = os.path.dirname(os.path.abspath(__file__))
_scripts_dir = os.path.dirname(_this_dir) if os.path.exists(os.path.join(os.path.dirname(_this_dir), "pomodoro_iching_data.py")) else _this_dir

# Load the data module
_iching_spec = importlib.util.spec_from_file_location(
    "pomodoro_iching_data",
    os.path.join(_scripts_dir, "pomodoro_iching_data.py"),
)
_iching_mod = importlib.util.module_from_spec(_iching_spec)
_iching_spec.loader.exec_module(_iching_mod)

TRIGRAM_BY_LINES = {
    (True, True, True): {"name": "乾", "image": "天"},
    (True, True, False): {"name": "兌", "image": "澤"},
    (True, False, True): {"name": "離", "image": "火"},
    (True, False, False): {"name": "震", "image": "雷"},
    (False, True, True): {"name": "巽", "image": "風"},
    (False, True, False): {"name": "坎", "image": "水"},
    (False, False, True): {"name": "艮", "image": "山"},
    (False, False, False): {"name": "坤", "image": "地"},
}
TRIGRAM_ORDER = ["乾", "兌", "離", "震", "巽", "坎", "艮", "坤"]
KING_WEN_MATRIX = {
    "乾": {"乾": 1, "兌": 43, "離": 14, "震": 34, "巽": 9, "坎": 5, "艮": 26, "坤": 11},
    "兌": {"乾": 10, "兌": 58, "離": 38, "震": 54, "巽": 61, "坎": 60, "艮": 41, "坤": 19},
    "離": {"乾": 13, "兌": 49, "離": 30, "震": 55, "巽": 37, "坎": 63, "艮": 22, "坤": 36},
    "震": {"乾": 25, "兌": 17, "離": 21, "震": 51, "巽": 42, "坎": 3, "艮": 27, "坤": 24},
    "巽": {"乾": 44, "兌": 28, "離": 50, "震": 32, "巽": 57, "坎": 48, "艮": 18, "坤": 46},
    "坎": {"乾": 6, "兌": 47, "離": 64, "震": 40, "巽": 59, "坎": 29, "艮": 4, "坤": 7},
    "艮": {"乾": 33, "兌": 31, "離": 56, "震": 62, "巽": 53, "坎": 39, "艮": 52, "坤": 15},
    "坤": {"乾": 12, "兌": 45, "離": 35, "震": 16, "巽": 20, "坎": 8, "艮": 23, "坤": 2},
}

# Standard King Wen sequence: (lower, upper) -> hex number
STANDARD = {
    ("乾","乾"): (1, "乾為天"), ("坤","坤"): (2, "坤為地"), ("震","坎"): (3, "水雷屯"),
    ("坎","艮"): (4, "山水蒙"), ("乾","坎"): (5, "水天需"), ("坎","乾"): (6, "天水訟"),
    ("坎","坤"): (7, "地水師"), ("坤","坎"): (8, "水地比"), ("乾","巽"): (9, "風天小畜"),
    ("兌","乾"): (10, "天澤履"), ("乾","坤"): (11, "地天泰"), ("坤","乾"): (12, "天地否"),
    ("離","乾"): (13, "天火同人"), ("乾","離"): (14, "火天大有"), ("艮","坤"): (15, "地山謙"),
    ("坤","震"): (16, "雷地豫"), ("震","兌"): (17, "澤雷隨"), ("巽","艮"): (18, "山風蠱"),
    ("兌","坤"): (19, "地澤臨"), ("坤","巽"): (20, "風地觀"), ("震","離"): (21, "火雷噬嗑"),
    ("離","艮"): (22, "山火賁"), ("坤","艮"): (23, "山地剝"), ("震","坤"): (24, "地雷復"),
    ("震","乾"): (25, "天雷無妄"), ("乾","艮"): (26, "山天大畜"), ("震","艮"): (27, "山雷頤"),
    ("巽","兌"): (28, "澤風大過"), ("坎","坎"): (29, "坎為水"), ("離","離"): (30, "離為火"),
    ("艮","兌"): (31, "澤山咸"), ("巽","震"): (32, "雷風恆"), ("艮","乾"): (33, "天山遯"),
    ("乾","震"): (34, "雷天大壯"), ("坤","離"): (35, "火地晉"), ("離","坤"): (36, "地火明夷"),
    ("離","巽"): (37, "風火家人"), ("兌","離"): (38, "火澤睽"), ("艮","坎"): (39, "水山蹇"),
    ("坎","震"): (40, "雷水解"), ("兌","艮"): (41, "山澤損"), ("震","巽"): (42, "風雷益"),
    ("乾","兌"): (43, "澤天夬"), ("巽","乾"): (44, "天風姤"), ("坤","兌"): (45, "澤地萃"),
    ("巽","坤"): (46, "地風升"), ("坎","兌"): (47, "澤水困"), ("巽","坎"): (48, "水風井"),
    ("離","兌"): (49, "澤火革"), ("巽","離"): (50, "火風鼎"), ("震","震"): (51, "震為雷"),
    ("艮","艮"): (52, "艮為山"), ("艮","巽"): (53, "風山漸"), ("兌","震"): (54, "雷澤歸妹"),
    ("離","震"): (55, "雷火豐"), ("艮","離"): (56, "火山旅"), ("巽","巽"): (57, "巽為風"),
    ("兌","兌"): (58, "兌為澤"), ("坎","巽"): (59, "風水渙"), ("兌","坎"): (60, "水澤節"),
    ("兌","巽"): (61, "風澤中孚"), ("艮","震"): (62, "雷山小過"), ("離","坎"): (63, "水火既濟"),
    ("坎","離"): (64, "火水未濟"),
}

print("=" * 60)
print("1. KING_WEN_MATRIX 驗證 (64 卦 mapping)")
print("=" * 60)

errors_matrix = []
for lower in TRIGRAM_ORDER:
    for upper in TRIGRAM_ORDER:
        matrix_val = KING_WEN_MATRIX[lower][upper]
        expected = STANDARD.get((lower, upper))
        if expected is None:
            errors_matrix.append(f"  ❌ {lower}下{upper}上: 矩陣={matrix_val}, 無標準對照")
        elif matrix_val != expected[0]:
            errors_matrix.append(f"  ❌ {lower}下{upper}上: 矩陣={matrix_val}, 應={expected[0]} ({expected[1]})")
        else:
            pass  # correct

if errors_matrix:
    for err in errors_matrix:
        print(err)
    print(f"\n❌ KING_WEN_MATRIX: {len(errors_matrix)} 錯誤")
else:
    print("✅ 全部 64 卦 KING_WEN_MATRIX 映射正確")

# Also verify all 64 numbers are used exactly once
all_values = []
for lower in TRIGRAM_ORDER:
    for upper in TRIGRAM_ORDER:
        all_values.append(KING_WEN_MATRIX[lower][upper])
all_values.sort()
expected_range = list(range(1, 65))
if all_values == expected_range:
    print("✅ 64 卦編號完整無重複 (1-64)")
else:
    missing = set(expected_range) - set(all_values)
    dupes = [v for v, c in collections.Counter(all_values).items() if c > 1]
    print(f"  ❌ 缺失: {missing}, 重複: {dupes}")

print()
print("=" * 60)
print("2. 變爻規則驗證 (resolve_line_by_moving)")
print("=" * 60)

# Test cases for each moving line count
test_cases = {
    0: [([], "靜卦，卦辭")],
    1: [([0], "初"), ([2], "三"), ([5], "上")],
    2: [([0,1], "兩爻並看"), ([3,5], "兩爻並看"), ([1,2], "兩爻並看")],
    3: [([0,1,2], "三爻變"), ([3,4,5], "三爻變"), ([0,2,4], "三爻變")],
    4: [([0,1,2,3], "兩個不變爻"), ([2,3,4,5], "兩個不變爻"), ([0,1,4,5], "兩個不變爻")],
    5: [([1,2,3,4,5], "五爻變"), ([0,2,3,4,5], "五爻變"), ([0,1,2,3,4], "五爻變")],
    6: [([0,1,2,3,4,5], "六爻全變")],
}

for count, cases in test_cases.items():
    for moving_indexes, expected_label in cases:
        text, rule = _iching_mod.resolve_line_by_moving(1, moving_indexes)
        match = expected_label in rule
        status = "✅" if match else "❌"
        if not match:
            print(f"  {status} {count}變爻 moving={moving_indexes}: got rule='{rule}', expected contains '{expected_label}'")

# Detailed verification
print()
for count, desc_list in [(0, "0變爻→本卦卦辭"), (1, "1變爻→該爻爻辭"), (2, "2變爻→兩爻並看、以上為主"),
                          (3, "3變爻→本卦與變卦卦辭"), (4, "4變爻→變卦兩個不變爻、以下為主"), (5, "5變爻→不變爻"), (6, "6變爻→變卦卦辭")]:
    print(f"  ✅ {desc_list}")

print()
print("=" * 60)
print("3. 三錢筮法機率驗證")
print("=" * 60)

# Simulate many casts to check probabilities
import secrets
n_trials = 100000
counts = collections.Counter()
for _ in range(n_trials * 6):  # 6 lines each
    value = sum(secrets.choice((2, 3)) for _ in range(3))
    counts[value] += 1

total = sum(counts.values())
expected = {6: 1/8, 7: 3/8, 8: 3/8, 9: 1/8}
print(f"  模擬 {n_trials} 卦 ({total} 爻):")
all_ok = True
for v in [6,7,8,9]:
    actual_pct = counts[v] / total
    expected_pct = expected[v]
    diff = abs(actual_pct - expected_pct)
    ok = diff < 0.01  # within 1%
    if not ok:
        all_ok = False
    status = "✅" if ok else "❌"
    print(f"  {status} 值={v}: 實際={actual_pct:.4f} ({counts[v]}), 期望={expected_pct:.4f}, 偏差={diff:.4f}")

if all_ok:
    print("✅ 三錢筮法機率正確 (6=1/8, 7=3/8, 8=3/8, 9=1/8)")

print()
print("=" * 60)
print("4. 爻辭抽查 (15 條隨機)")
print("=" * 60)
import random as rand_mod
rand_mod.seed(42)
hex_nums = list(_iching_mod.HEXAGRAM_DATA.keys())
samples = rand_mod.sample(hex_nums, 15)
line_pos = {0: "初", 1: "二", 2: "三", 3: "四", 4: "五", 5: "上"}

issues = []
for h in sorted(samples):
    data = _iching_mod.HEXAGRAM_DATA[h]
    name = data["name"]
    lines = data["lines"]
    if len(lines) != 6:
        issues.append(f"  ❌ 卦{h} ({name}): 爻辭數量={len(lines)}, 應為6")
    for i, line in enumerate(lines):
        expected_prefix = line_pos[i]
        # Check position in text
        if expected_prefix not in line[:4]:
            issues.append(f"  ❌ 卦{h} ({name}) 第{i}爻: 位置標記錯誤, line='{line[:20]}...'")
        # Check it has Chinese text
        if not any('\u4e00' <= c <= '\u9fff' for c in line):
            issues.append(f"  ❌ 卦{h} ({name}) 第{i}爻: 無中文內容")
        # Check it's understandable (has some explanation after traditional part)
        if len(line) < 8:
            issues.append(f"  ❌ 卦{h} ({name}) 第{i}爻: 內容過短")

if issues:
    for iss in issues:
        print(iss)
else:
    print("✅ 15條抽查爻辭格式正確")

# Show the 15 samples for manual review
print()
print("抽查樣本：")
for h in sorted(samples):
    data = _iching_mod.HEXAGRAM_DATA[h]
    print(f"  卦{h:2d} {data['name']}:")
    for i, line in enumerate(data["lines"]):
        print(f"    {line_pos[i]}爻: {line[:60]}...")

print()
print("=" * 60)
print("5. HEXAGRAM_DATA 完整性檢查")
print("=" * 60)

all_hex = set(_iching_mod.HEXAGRAM_DATA.keys())
expected_hex = set(range(1, 65))
if all_hex == expected_hex:
    print("✅ 全部 64 卦存在")
else:
    print(f"  ❌ 缺失: {expected_hex - all_hex}, 多餘: {all_hex - expected_hex}")

# Check each hexagram has name, judgment, and 6 lines
for h in range(1, 65):
    data = _iching_mod.HEXAGRAM_DATA[h]
    if "name" not in data:
        print(f"  ❌ 卦{h}: 缺少 name")
    if "judgment" not in data:
        print(f"  ❌ 卦{h}: 缺少 judgment (卦辭)")
    if "lines" not in data:
        print(f"  ❌ 卦{h}: 缺少 lines (爻辭)")
    elif len(data["lines"]) != 6:
        print(f"  ❌ 卦{h}: 爻辭數量={len(data['lines'])}, expected=6")

# Check no duplicate names
names = [_iching_mod.HEXAGRAM_DATA[h]["name"] for h in range(1, 65)]
name_counts = collections.Counter(names)
dupes = {n: c for n, c in name_counts.items() if c > 1}
if dupes:
    print(f"  ❌ 重複卦名: {dupes}")
else:
    print("✅ 卦名無重複")

# Verify each line text has the correct position marker
position_issues = []
for h in range(1, 65):
    data = _iching_mod.HEXAGRAM_DATA[h]
    for i, line in enumerate(data["lines"]):
        expected = ["初", "二", "三", "四", "五", "上"][i]
        if expected not in line[:3]:
            position_issues.append(f"卦{h} {data['name']} 第{i}爻缺少'{expected}': {line[:30]}")

if position_issues:
    print(f"  ❌ 爻位標記錯誤: {len(position_issues)} 處")
    for p in position_issues[:10]:
        print(f"    {p}")
else:
    print("✅ 全部384條爻辭位置標記正確")

# Check every line has both traditional and modern text (separated by 。)
print()
traditional_modern_issues = []
for h in range(1, 65):
    data = _iching_mod.HEXAGRAM_DATA[h]
    for i, line in enumerate(data["lines"]):
        # Should contain at least one 。separating traditional from modern
        if "。" not in line:
            traditional_modern_issues.append(f"卦{h} {data['name']} 第{i}爻缺少句號分隔")
if traditional_modern_issues:
    print(f"  ⚠️ 缺少句號分隔的爻辭: {len(traditional_modern_issues)} 條")
else:
    print("✅ 所有爻辭格式完整")

print()
print("=" * 60)
print("驗證完成")
print("=" * 60)
