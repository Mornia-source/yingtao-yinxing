# -*- coding: utf-8 -*-
# 词组编码完全不涉及形码(见下方 n==2/3/4/5+ 分支)，只需要自然码双拼，
# 所以这里不需要、也不引入 shape.ShapeEncoder。
import io, os
from zrm import encode_zrm, encode_zrm_variants
from tier_boost import boosted_weight

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(_HERE, "..", "sources")

SRC = os.path.join(_SOURCES, "base.dict.yaml")
SRC_CHENGYU = os.path.join(_SOURCES, "chengyu.dict.yaml")
OUT = os.path.join(_HERE, "yingtao_words.dict.yaml")


def parse_rows(path):
    rows = []
    with io.open(path, encoding="utf-8") as f:
        started = False
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "...":
                started = True
                continue
            if not started:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            text, packed, weight = parts[0], parts[1], parts[2]
            try:
                weight = int(weight)
            except ValueError:
                continue
            rows.append((text, packed, weight))
    return rows


def syllables_of(text, packed):
    blocks = packed.split("; ")
    if len(blocks) != len(text):
        return None
    syls = []
    for b in blocks:
        syl = b.split(";")[0].strip()
        if not syl or not syl.isalpha():
            return None
        syls.append(syl)
    return syls


def main():
    rows = parse_rows(SRC)
    try:
        rows += parse_rows(SRC_CHENGYU)
    except IOError:
        pass

    out = []  # list of (text, code, weight)
    skipped = 0
    for text, packed, weight in rows:
        n = len(text)
        if n < 2:
            continue
        syls = syllables_of(text, packed)
        if syls is None:
            skipped += 1
            continue

        zrm_variants = []
        zrms = []  # 每个字的"主"双拼(取variants[0])，firsts一律从这个来，
                   # ü用u/v哪个拼写都不影响声母首字母，不需要变体
        firsts = []
        ok = True
        for ch, syl in zip(text, syls):
            variants = encode_zrm_variants(syl)
            if any(len(v) != 2 for v in variants):
                ok = False
                break
            zrm_variants.append(variants)
            zrms.append(variants[0])
            firsts.append(variants[0][0])
        if not ok:
            skipped += 1
            continue

        if n == 2:
            # 全码：前字前两位+后字前两位；简码：前字前两位+后字首位（3位）。
            # 2位编码专属于单字双拼(见gen_chars.py)，词组一律从3位起，
            # 避免和"双拼2位打完优先显示单字"的规则冲突。
            for z0 in zrm_variants[0]:
                for z1 in zrm_variants[1]:
                    out.append((text, z0 + z1, weight))
                out.append((text, z0 + firsts[1], weight))
        elif n == 3:
            short = firsts[0] + firsts[1] + firsts[2]
            out.append((text, short, weight))
            for z2 in zrm_variants[2]:
                out.append((text, firsts[0] + firsts[1] + z2, weight))
        elif n == 4:
            code = "".join(firsts)
            out.append((text, code, weight))
        else:
            code = firsts[0] + firsts[1] + firsts[2] + firsts[-1]
            out.append((text, code, weight))

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Rime dictionary\n# encoding: utf-8\n#\n")
        f.write("# 樱桃音形 - 词组码表（二字词/三字词/四字词/多字词）\n")
        f.write("# 词库来源: rime-ice base.dict.yaml, chengyu.dict.yaml\n")
        f.write("#\n---\nname: yingtao_words\nversion: \"1.0\"\nsort: by_weight\n...\n")
        for text, code, weight in out:
            f.write("%s\t%s\t%d\n" % (text, code, boosted_weight(code, weight, text)))

    print("source rows:", len(rows), "skipped:", skipped, "written:", len(out))


if __name__ == "__main__":
    main()
