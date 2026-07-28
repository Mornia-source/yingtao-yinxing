# -*- coding: utf-8 -*-
import io, os
from shape import ShapeEncoder
from zrm import encode_zrm
from tier_boost import boosted_weight

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(_HERE, "..", "sources")

SRC = os.path.join(_SOURCES, "base.dict.yaml")
SRC_CHENGYU = os.path.join(_SOURCES, "chengyu.dict.yaml")
OUT = os.path.join(_HERE, "yingtao_words.dict.yaml")

_shape_cache = {}


def get_shape(enc, ch):
    if ch not in _shape_cache:
        code, mode = enc.shape(ch)
        _shape_cache[ch] = code
    return _shape_cache[ch]


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
    enc = ShapeEncoder()
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

        zrms = []
        firsts = []
        ok = True
        for ch, syl in zip(text, syls):
            z = encode_zrm(syl)
            if len(z) != 2:
                ok = False
                break
            zrms.append(z)
            firsts.append(z[0])
        if not ok:
            skipped += 1
            continue

        if n == 2:
            # 全码：前字前两位+后字前两位；简码：前字前两位+后字首位（3位）。
            # 2位编码专属于单字双拼(见gen_chars.py)，词组一律从3位起，
            # 避免和"双拼2位打完优先显示单字"的规则冲突。
            full = zrms[0] + zrms[1]
            short = zrms[0][0] + zrms[0][1] + firsts[1]
            out.append((text, full, weight))
            out.append((text, short, weight))
        elif n == 3:
            full = firsts[0] + firsts[1] + zrms[2]
            short = firsts[0] + firsts[1] + firsts[2]
            out.append((text, full, weight))
            out.append((text, short, weight))
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
            f.write("%s\t%s\t%d\n" % (text, code, boosted_weight(code, weight)))

    print("source rows:", len(rows), "skipped:", skipped, "written:", len(out))


if __name__ == "__main__":
    main()
