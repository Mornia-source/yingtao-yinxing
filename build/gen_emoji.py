# -*- coding: utf-8 -*-
"""生成 emoji 支持用的两份数据：
  1. yingtao_emoji.dict.yaml —— 把每个 emoji 名字当成普通词条注册进
     词典（编码规则跟普通词一样），这样正常打字流程里才会出现这个
     名字的候选，供 lua 过滤器识别、插入对应 emoji。
  2. lua/yingtao_emoji.txt —— 名字 -> emoji 列表 的查找表，格式跟
     moran 的 zrmdb.txt 一样(名字\tab emoji1 emoji2...)，lua_filter
     启动时一次性加载。

名字和 emoji 的对应关系来自 iDvel/rime-ice 的 opencc/emoji.txt
(OpenCC 词典格式：key\tkey emoji1 [emoji2 ...])，一个名字可能对应
多个 emoji，同一个 emoji 也可能有多个名字，两种多对多关系原始文件
里都已经有了，不需要额外处理。
"""
import io, os

from flypy import encode_flypy_variants
from shape import ShapeEncoder
from tier_boost import boosted_weight

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(_HERE, "..", "sources")

SRC = os.path.join(_SOURCES, "emoji_raw.txt")
OUT_DICT = os.path.join(_HERE, "yingtao_emoji.dict.yaml")
OUT_LUT = os.path.join(_HERE, "yingtao_emoji.txt")

# 名字长度上限：原始表里混了一些国家全称("越南社会主义共和国")之类的
# 超长条目，日常用不上，跳过以免词典/候选噪音过多。
MAX_NAME_LEN = 6

_pypinyin = None


def fallback_pinyin(text):
    global _pypinyin
    if _pypinyin is None:
        from pypinyin import lazy_pinyin, Style
        _pypinyin = (lazy_pinyin, Style)
    lazy_pinyin, Style = _pypinyin
    syls = lazy_pinyin(text, style=Style.NORMAL, v_to_u=False, errors="ignore")
    return syls if len(syls) == len(text) else None


def load_name_emoji():
    """返回 {名字: [emoji, ...]}，跳过超长/非纯中文的名字。"""
    result = {}
    with io.open(SRC, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or "\t" not in line:
                continue
            name, rest = line.split("\t", 1)
            if not name or len(name) > MAX_NAME_LEN:
                continue
            if not all("一" <= c <= "鿿" for c in name):
                continue
            parts = rest.split(" ")
            emojis = [p for p in parts[1:] if p]  # parts[0] 是名字本身，跳过
            if not emojis:
                continue
            result.setdefault(name, [])
            for e in emojis:
                if e not in result[name]:
                    result[name].append(e)
    return result


def codes_for_name(text, enc, shape_cache):
    """单字/多字名字统一按樱桃音形的词组全码规则编码：
    首字双拼(2位) + 末字形码(2位)。单字则直接用单字的双拼+形码全码。"""

    def shape_of(ch):
        if ch not in shape_cache:
            shape_cache[ch] = enc.shape(ch)[0] or None
        return shape_cache[ch]

    syls = fallback_pinyin(text)
    if not syls:
        return []
    zrm_variants = []
    for syl in syls:
        variants = encode_flypy_variants(syl)
        if any(len(v) != 2 for v in variants):
            return []
        zrm_variants.append(variants)

    tail_shape = shape_of(text[-1])
    if not tail_shape:
        return []
    return [z0 + tail_shape for z0 in zrm_variants[0]]


def main():
    enc = ShapeEncoder()
    shape_cache = {}
    name_emoji = load_name_emoji()

    dict_lines = []
    lut_lines = []
    skipped = 0
    for name in sorted(name_emoji):
        codes = codes_for_name(name, enc, shape_cache)
        if not codes:
            skipped += 1
            continue
        for code in codes:
            # 权重给得很低，只是为了让这个名字能作为候选出现、供 lua
            # 过滤器识别，不应该在正常候选排序里抢占前面的位置。
            dict_lines.append("%s\t%s\t%d" % (name, code, boosted_weight(code, 1, name)))
        lut_lines.append("%s\t%s" % (name, " ".join(name_emoji[name])))

    with io.open(OUT_DICT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Rime dictionary\n# encoding: utf-8\n#\n")
        f.write("# 樱桃音形 - emoji 名字词条表\n")
        f.write("# 只是为了让这些名字能正常打出来、被 lua/yingtao_emoji.lua 识别，\n")
        f.write("# 权重很低，不参与正常候选排序的竞争\n")
        f.write("#\n---\nname: yingtao_emoji\nversion: \"1.0\"\nsort: by_weight\n...\n")
        for l in dict_lines:
            f.write(l + "\n")

    with io.open(OUT_LUT, "w", encoding="utf-8", newline="\n") as f:
        for l in lut_lines:
            f.write(l + "\n")

    print("names:", len(name_emoji), "skipped(no pinyin/code):", skipped)
    print("dict entries:", len(dict_lines))
    print("lookup entries:", len(lut_lines))


if __name__ == "__main__":
    main()
