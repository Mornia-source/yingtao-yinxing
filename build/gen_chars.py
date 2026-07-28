# -*- coding: utf-8 -*-
import io, os
from shape import ShapeEncoder
from zrm import encode_zrm
from tier_boost import boosted_weight

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(_HERE, "..", "sources")

SRC = os.path.join(_SOURCES, "8105.dict.yaml")
OUT = os.path.join(_HERE, "yingtao_chars.dict.yaml")


def load_rows():
    rows = []
    with io.open(SRC, encoding="utf-8") as f:
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
            char, packed, weight = parts[0], parts[1], parts[2]
            pinyin = packed.split(";")[0]
            if len(char) != 1:
                continue
            rows.append((char, pinyin, int(weight)))
    return rows


def main():
    enc = ShapeEncoder()
    rows = load_rows()
    out_lines = []
    stats = {"decomp": 0, "own-full": 0, "own1": 0, "fail": 0}
    missing = []
    for char, pinyin, weight in rows:
        # pinyin field may contain multiple syllables separated by space for a single 'char'? For single chars it's one syllable.
        py = pinyin.strip()
        if not py or not py.isalpha():
            continue
        zrm = encode_zrm(py)
        if len(zrm) != 2:
            # some rare finals (e.g. 'ng', 'm', 'hm') won't reduce to exactly 2 letters; skip gracefully
            missing.append((char, pinyin, "badzrm:" + zrm))
            continue
        shp, mode = enc.shape(char)
        stats[mode] = stats.get(mode, 0) + 1
        if not shp:
            missing.append((char, pinyin, "noshape"))
            continue
        code = zrm + shp
        out_lines.append("%s\t%s\t%d" % (char, code, boosted_weight(code, weight)))
        # 双拼码打完(2位)即可作为同音字候选出现，权重按字频排序，
        # 不必非要把形码也打完才能看到这个字；形码留给需要精确选字的时候用。
        out_lines.append("%s\t%s\t%d" % (char, zrm, boosted_weight(zrm, weight)))

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Rime dictionary\n# encoding: utf-8\n#\n")
        f.write("# 樱桃音形 - 单字全码表\n")
        f.write("# 自然码双拼(2位) + 98五笔首末字根形码(2位)\n")
        f.write("# 数据来源: rime-ice(拼音/字频), lotem/rime-wubi98(官方五笔全码), hanzi-chai/pychai(汉字结构拆分)\n")
        f.write("#\n---\nname: yingtao_chars\nversion: \"1.0\"\nsort: by_weight\n...\n")
        for l in out_lines:
            f.write(l + "\n")

    print("total rows:", len(rows))
    print("written:", len(out_lines))
    print("missing:", len(missing))
    print("shape stats:", stats)
    print("missing sample:", missing[:30])


if __name__ == "__main__":
    main()
