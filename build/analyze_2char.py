# -*- coding: utf-8 -*-
"""双字词扩展编码方案的重码率实测。

对比几种「4码全码之后再加2位形码」的取码方式，看哪种把重码压得最狠：
  A) 字1首根 + 字2首根
  B) 字1首根 + 字2末根
  C) 字1末根 + 字2末根
同时给出当前 4 码全码的重码基线，以及词表扩大到雾凇全量双字词后的情况。
"""
import io, os, sys
from collections import Counter, defaultdict

from pypinyin import lazy_pinyin, Style
from shape import ShapeEncoder
from zrm import encode_zrm_variants

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(_HERE, "..", "sources")


def _is_cjk(ch):
    o = ord(ch)
    return 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF


def load_openfly_2char():
    words = set()
    for name in ("openfly.primary.dict.yaml", "openfly.secondary.dict.yaml"):
        path = os.path.join(_SOURCES, name)
        started = False
        for line in io.open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.strip() == "...":
                started = True
                continue
            if not started:
                continue
            p = line.split("\t")
            if len(p) != 2:
                continue
            t = p[0]
            if len(t) == 2 and all(_is_cjk(c) for c in t):
                words.add(t)
    return words


def load_ricime_2char():
    words = set()
    for name in ("base.dict.yaml", "chengyu.dict.yaml"):
        path = os.path.join(_SOURCES, name)
        started = False
        for line in io.open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.strip() == "...":
                started = True
                continue
            if not started:
                continue
            p = line.split("\t")
            if len(p) < 3:
                continue
            t = p[0]
            if len(t) == 2 and all(_is_cjk(c) for c in t):
                words.add(t)
    return words


def build(words, enc):
    """返回 [(词, 双拼4码, 字1首根, 字1末根, 字2首根, 字2末根)]"""
    out = []
    for w in sorted(words):
        syls = lazy_pinyin(w, style=Style.NORMAL, v_to_u=False, errors="ignore")
        if len(syls) != 2:
            continue
        z = []
        ok = True
        for s in syls:
            v = encode_zrm_variants(s)
            if len(v[0]) != 2:
                ok = False
                break
            z.append(v[0])
        if not ok:
            continue
        s1, _ = enc.shape(w[0])
        s2, _ = enc.shape(w[1])
        if not s1 or not s2:
            continue
        out.append((w, z[0] + z[1], s1[0], s1[1], s2[0], s2[1]))
    return out


def stats(rows, keyfunc, label):
    groups = defaultdict(list)
    for r in rows:
        groups[keyfunc(r)].append(r[0])
    sizes = Counter(len(v) for v in groups.values())
    total = len(rows)
    unique = sizes[1]
    worst = max((len(v), k) for k, v in groups.items())
    # 打完该编码后仍需翻页(第10位之后)的词数
    beyond_page = sum(len(v) - 9 for v in groups.values() if len(v) > 9)
    print("%-28s 词数=%-6d 唯一码=%-6d (%5.1f%%)  最大重码=%-3d  10位开外=%d"
          % (label, total, unique, 100.0 * unique / total, worst[0], beyond_page))
    return groups


def main():
    enc = ShapeEncoder()

    for name, words in (("openfly 双字词", load_openfly_2char()),
                        ("雾凇全量双字词", load_ricime_2char())):
        rows = build(words, enc)
        print("\n=== %s ===" % name)
        stats(rows, lambda r: r[1], "现状：4码全码")
        stats(rows, lambda r: r[1] + r[2] + r[4], "A) 6码 字1首根+字2首根")
        stats(rows, lambda r: r[1] + r[2] + r[5], "B) 6码 字1首根+字2末根")
        stats(rows, lambda r: r[1] + r[3] + r[5], "C) 6码 字1末根+字2末根")
        # 5码方案：只加1位
        stats(rows, lambda r: r[1] + r[2], "D) 5码 只加字1首根")
        stats(rows, lambda r: r[1] + r[4], "E) 5码 只加字2首根")

    # 形码分布均匀度：越均匀区分力越强
    print("\n=== 字根码分布均匀度(8105字) ===")
    first = Counter()
    last = Counter()
    for line in io.open(os.path.join(_SOURCES, "wubi98_noident_8105.txt"), encoding="utf-8"):
        p = line.rstrip("\r\n").split("\t")
        if len(p) != 2:
            continue
        first[p[1][0]] += 1
        last[p[1][-1]] += 1
    for label, c in (("首根", first), ("末根", last)):
        tot = sum(c.values())
        top = c.most_common(3)
        share = 100.0 * sum(v for _, v in top) / tot
        print("%s: 用到%d个键, 最集中的3个键 %s 占 %.1f%%"
              % (label, len(c), top, share))


if __name__ == "__main__":
    main()
