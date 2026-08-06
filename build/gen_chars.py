# -*- coding: utf-8 -*-
import io, os
from shape import ShapeEncoder
from flypy import encode_flypy_variants
from tier_boost import boosted_weight, SINGLE_KEY_CHARS

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
    stats = {}
    missing = []
    char_weight = {}  # 字 -> 字频，供单键硬性首选复用
    for char, pinyin, weight in rows:
        # pinyin field may contain multiple syllables separated by space for a single 'char'? For single chars it's one syllable.
        py = pinyin.strip()
        if not py or not py.isalpha():
            continue
        zrms = encode_flypy_variants(py)
        if any(len(z) != 2 for z in zrms):
            # some rare finals (e.g. 'ng', 'm', 'hm') won't reduce to exactly 2 letters; skip gracefully
            missing.append((char, pinyin, "badzrm:" + repr(zrms)))
            continue
        shp, mode = enc.shape(char)
        stats[mode] = stats.get(mode, 0) + 1
        if not shp:
            missing.append((char, pinyin, "noshape"))
            continue
        for zrm in zrms:
            code = zrm + shp
            out_lines.append("%s\t%s\t%d" % (char, code, boosted_weight(code, weight, char)))
            # 双拼码打完(2位)即可作为同音字候选出现，权重按字频排序，
            # 不必非要把形码也打完才能看到这个字；形码留给需要精确选字的时候用。
            out_lines.append("%s\t%s\t%d" % (char, zrm, boosted_weight(zrm, weight, char)))
        char_weight[char] = weight

    # 单键硬性首选：给这26个字各发一条1位编码的词条，权重档位压过一切补全候选。
    single_key_missing = []
    for key, ch in sorted(SINGLE_KEY_CHARS.items()):
        w = char_weight.get(ch)
        if w is None:
            single_key_missing.append((key, ch))
            w = 0
        out_lines.append("%s\t%s\t%d" % (ch, key, boosted_weight(key, w, ch)))

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Rime dictionary\n# encoding: utf-8\n#\n")
        f.write("# 樱桃音形 - 单字全码表\n")
        f.write("# 小鹤双拼(2位) + 98五笔首二字根形码(2位)\n")
        f.write("# 数据来源: rime-ice(拼音/字频), 用户提供的98五笔去识别码参考表(sources/wubi98_noident_8105.txt，首选)，\n")
        f.write("# lotem/rime-wubi98 + hanzi-chai/pychai(仅供参考表覆盖不到的极少数生僻字兜底)\n")
        f.write("#\n---\nname: yingtao_chars\nversion: \"1.0\"\nsort: by_weight\n...\n")
        for l in out_lines:
            f.write(l + "\n")

    print("total rows:", len(rows))
    print("written:", len(out_lines))
    print("missing:", len(missing))
    print("shape stats:", stats)
    print("single-key entries:", len(SINGLE_KEY_CHARS),
          "not found in char table:", single_key_missing)
    print("missing sample:", missing[:30])


if __name__ == "__main__":
    main()
