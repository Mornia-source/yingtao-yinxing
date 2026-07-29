# -*- coding: utf-8 -*-
"""平均按键数对比：樱桃音形(词频加权，取每词最短可用码) vs 全拼 vs 纯双拼。

用于 README「平均按键数」一节的数据支撑，可重新运行验证。
"""
import io, os

_HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(_HERE, "yingtao_words.dict.yaml")
R = os.path.join(_HERE, "..", "sources", "rime-ice.base.dict.yaml")

# 每个词最短的樱桃音形编码（简码/全码/6码里取最短的那个）
best_code_len = {}
started = False
for line in io.open(W, encoding="utf-8"):
    line = line.rstrip("\n")
    if line.strip() == "...":
        started = True
        continue
    if not started:
        continue
    p = line.split("\t")
    if len(p) != 3:
        continue
    text, code = p[0], p[1]
    L = len(code)
    if text not in best_code_len or L < best_code_len[text]:
        best_code_len[text] = L

freq = {}
started = False
for line in io.open(R, encoding="utf-8"):
    line = line.rstrip("\n")
    if line.strip() == "...":
        started = True
        continue
    if not started or not line or line.startswith("#"):
        continue
    p = line.split("\t")
    if len(p) < 3:
        continue
    try:
        w = int(p[2])
    except ValueError:
        continue
    if w > freq.get(p[0], 0):
        freq[p[0]] = w

total_w = 0
sum_yt = 0.0
sum_sp = 0.0  # 纯双拼：每字固定2键
sum_py_min = 0.0  # 全拼：按字符数*3(平均拼音音节长度约2.9，取3做保守估计)

for text, w in freq.items():
    n = len(text)
    if text not in best_code_len:
        continue
    total_w += w
    sum_yt += best_code_len[text] * w
    sum_sp += 2 * n * w
    sum_py_min += 3 * n * w

print("加权词条数(有樱桃音形编码的):", len(best_code_len))
print("覆盖词频总权重:", total_w)
print("平均按键数/词  樱桃音形=%.2f  纯双拼(2键/字)=%.2f  全拼(约3键/字估计)=%.2f"
      % (sum_yt / total_w, sum_sp / total_w, sum_py_min / total_w))

# 分词长看
from collections import defaultdict
by_len = defaultdict(lambda: [0, 0.0, 0.0])
for text, w in freq.items():
    if text not in best_code_len:
        continue
    n = len(text)
    by_len[n][0] += w
    by_len[n][1] += best_code_len[text] * w
    by_len[n][2] += 2 * n * w
print("\n词长  加权平均樱桃音形按键  纯双拼按键(2/字)")
for n in sorted(by_len):
    tw, yt, sp = by_len[n]
    if n > 6:
        break
    print("%d字   %.2f   %.2f" % (n, yt / tw, sp / tw))
