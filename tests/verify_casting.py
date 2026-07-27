#!/usr/bin/env python3
"""
Comprehensive cast testing: verify all 7 moving-line resolution cases.
"""
import sys, os, importlib.util, collections, secrets

_this_dir = os.path.dirname(os.path.abspath(__file__))
_scripts_dir = os.path.dirname(_this_dir) if os.path.exists(os.path.join(os.path.dirname(_this_dir), "pomodoro_iching_data.py")) else _this_dir

_iching_spec = importlib.util.spec_from_file_location(
    "pomodoro_iching_data",
    os.path.join(_scripts_dir, "pomodoro_iching_data.py"),
)
_iching = importlib.util.module_from_spec(_iching_spec)
_iching_spec.loader.exec_module(_iching)

TRIGRAM_BY_LINES = {
    (True, True, True): {"name": "乾"}, (True, True, False): {"name": "兌"},
    (True, False, True): {"name": "離"}, (True, False, False): {"name": "震"},
    (False, True, True): {"name": "巽"}, (False, True, False): {"name": "坎"},
    (False, False, True): {"name": "艮"}, (False, False, False): {"name": "坤"},
}
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

def hexagram_no_from_lines(lines):
    lower = TRIGRAM_BY_LINES[tuple(lines[:3])]["name"]
    upper = TRIGRAM_BY_LINES[tuple(lines[3:])]["name"]
    return KING_WEN_MATRIX[lower][upper]

def cast_one():
    values = [sum(secrets.choice((2, 3)) for _ in range(3)) for _ in range(6)]
    lines = [v % 2 == 1 for v in values]
    moving = [i for i, v in enumerate(values) if v in {6, 9}]
    changed = [not line if i in moving else line for i, line in enumerate(lines)]
    base_no = hexagram_no_from_lines(lines)
    changed_no = hexagram_no_from_lines(changed)
    return base_no, changed_no, moving, values

def test_resolution(base_no, moving, changed_no):
    text, rule = _iching.resolve_line_by_moving(base_no, moving)
    count = len(moving)
    
    if count == 0:
        assert "卦辭" in rule, f"0變應回卦辭, got {rule}"
        assert "爻" not in rule, f"0變不應有爻, got {rule}"
    elif count == 1:
        assert "一爻變" in rule, f"1變應為一爻變, got {rule}"
        assert "爻爻辭" in rule, f"1變應有爻爻辭, got {rule}"
    elif count == 2:
        assert "二爻變" in rule, f"2變應為二爻變, got {rule}"
    elif count == 3:
        assert "三爻變" in rule or "變卦卦辭" in rule, f"3變應為三爻變或變卦卦辭, got {rule}"
    elif count == 4:
        assert "四爻變" in rule or "變卦內卦" in rule, f"4變應為四爻變或變卦內卦, got {rule}"
    elif count == 5:
        assert "五爻變" in rule or "不變爻" in rule, f"5變應為五爻變或不變爻, got {rule}"
    elif count == 6:
        assert "六爻全變" in rule or "用九" in rule or "用六" in rule, f"6變應為六爻全變, got {rule}"
    return True

N = 5000
print(f"模擬 {N} 次占卦，驗證所有變爻案例...")
counts = collections.Counter()
issues = []
for i in range(N):
    base_no, changed_no, moving, values = cast_one()
    count = len(moving)
    counts[count] += 1
    try:
        test_resolution(base_no, moving, changed_no)
    except AssertionError as e:
        issues.append((i, base_no, moving, changed_no, str(e)))

print(f"\n變爻數量分布 (N={N}):")
for count in range(7):
    pct = counts[count] / N * 100
    print(f"  {count}變爻: {counts[count]:5d} ({pct:5.1f}%)")

if issues:
    print(f"\n❌ 發現 {len(issues)} 個錯誤:")
    for i, base, mov, chg, err in issues[:20]:
        print(f"  cast #{i}: base={base}, moving={mov}, changed={chg}, error={err}")
else:
    print(f"\n✅ 全部 {N} 次占卦的變爻規則正確")

# Verify each moving index outputs the right position name
print(f"\n個別變爻位驗證:")
line_pos_names = ["初", "二", "三", "四", "五", "上"]
for idx in range(6):
    text, rule = _iching.resolve_line_by_moving(1, [idx])
    expected_pos = line_pos_names[idx]
    if expected_pos in rule:
        print(f"  ✅ 動爻 idx={idx}: rule='{rule}'")
    else:
        print(f"  ❌ 動爻 idx={idx}: rule='{rule}', expected '{expected_pos}'")

print("\n✅ 全部驗證通過")