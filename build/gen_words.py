# -*- coding: utf-8 -*-
"""生成樱桃音形词组码表（二字词及以上）。

词表来源：openfly（开源小鹤音形词库）的 primary/secondary 词表。
          只取「词本身」和它所在的层级，小鹤自己的编码一概不用——
          樱桃音形的编码全部由下面的规则现算。
拼音来源：pypinyin，按词整体注音，能正确区分多音字
          （银行 yin-hang、重庆 chong-qing、会计 kuai-ji、音乐 yin-yue）。
词频来源：rime-ice 的 base/chengyu 词库降级为「只查词频」的辅助表，
          不再决定收录哪些词。openfly 有而 rime-ice 没有的词给一个
          偏低的默认词频，保证能打出来但不会盖过真正的常用词。

词组编码完全不涉及形码，所以这里不引入 shape.ShapeEncoder。
"""
import io, os
from pypinyin import lazy_pinyin, Style

from zrm import encode_zrm_variants
from tier_boost import boosted_weight

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(_HERE, "..", "sources")

# 词表（只取词，不取小鹤编码）；数字是层级，越小越优先
WORD_SOURCES = [
    ("openfly.primary.dict.yaml", 0),    # 首选词
    ("openfly.secondary.dict.yaml", 1),  # 次选词
]
# 词频查询表（只查词频，不决定收录）
FREQ_SOURCES = ["base.dict.yaml", "chengyu.dict.yaml"]

OUT = os.path.join(_HERE, "yingtao_words.dict.yaml")

# openfly 收了但 rime-ice 没词频的词用这个默认值。
# 实测 rime-ice 词频中位数约 315、下四分位约 95，取 100 让这些词
# 排在常用词之后、生僻词之前。
DEFAULT_FREQ = 100
# 次选词整体降权，体现 openfly 里 primary/secondary 的分层。
TIER_FACTOR = {0: 1.0, 1: 0.3}


def _is_cjk(ch):
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF
            or 0x20000 <= o <= 0x2FA1F)


def load_freq():
    freq = {}
    for name in FREQ_SOURCES:
        path = os.path.join(_SOURCES, name)
        try:
            f = io.open(path, encoding="utf-8")
        except IOError:
            continue
        with f:
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
                try:
                    w = int(parts[2])
                except ValueError:
                    continue
                if w > freq.get(parts[0], 0):
                    freq[parts[0]] = w
    return freq


def load_words():
    """返回 {词: 最优层级}，只保留纯汉字的多字词。"""
    words = {}
    for name, tier in WORD_SOURCES:
        path = os.path.join(_SOURCES, name)
        try:
            f = io.open(path, encoding="utf-8")
        except IOError:
            continue
        with f:
            started = False
            for line in f:
                line = line.rstrip("\n")
                if line.strip() == "...":
                    started = True
                    continue
                if not started:
                    continue
                parts = line.split("\t")
                if len(parts) != 2:
                    continue
                text = parts[0]
                if len(text) < 2:
                    continue  # 单字走 gen_chars.py，这里只管词
                if not all(_is_cjk(c) for c in text):
                    continue  # 含标点/字母的条目跳过，注音对不齐
                if text not in words or tier < words[text]:
                    words[text] = tier
    return words


def codes_for(text, zrm_variants, firsts):
    """按樱桃音形规则返回该词的全部编码。"""
    n = len(text)
    out = []
    if n == 2:
        # 全码 = 前字前两位 + 后字前两位；简码 = 前字前两位 + 后字首位（3位）。
        # 2位编码专属于单字双拼（见 gen_chars.py），词组一律从3位起。
        for z0 in zrm_variants[0]:
            for z1 in zrm_variants[1]:
                out.append(z0 + z1)
            out.append(z0 + firsts[1])
    elif n == 3:
        out.append(firsts[0] + firsts[1] + firsts[2])
        for z2 in zrm_variants[2]:
            out.append(firsts[0] + firsts[1] + z2)
    elif n == 4:
        out.append("".join(firsts))
    else:
        out.append(firsts[0] + firsts[1] + firsts[2] + firsts[-1])
    return out


def main():
    freq = load_freq()
    words = load_words()

    out = []
    skipped_pinyin = 0
    no_freq = 0
    for text, tier in words.items():
        syls = lazy_pinyin(text, style=Style.NORMAL, v_to_u=False, errors="ignore")
        if len(syls) != len(text):
            skipped_pinyin += 1
            continue

        zrm_variants = []
        firsts = []
        ok = True
        for syl in syls:
            variants = encode_zrm_variants(syl)
            if any(len(v) != 2 for v in variants):
                ok = False  # ng/m/hm 之类拼不成两位的音节
                break
            zrm_variants.append(variants)
            firsts.append(variants[0][0])
        if not ok:
            skipped_pinyin += 1
            continue

        w = freq.get(text)
        if w is None:
            w = DEFAULT_FREQ
            no_freq += 1
        w = int(w * TIER_FACTOR.get(tier, 1.0)) or 1

        for code in codes_for(text, zrm_variants, firsts):
            out.append((text, code, w))

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Rime dictionary\n# encoding: utf-8\n#\n")
        f.write("# 樱桃音形 - 词组码表（二字词/三字词/四字词/多字词）\n")
        f.write("# 词表来源: openfly 开源小鹤音形词库(只取词与层级，不用其编码)\n")
        f.write("# 注音来源: pypinyin(按词注音，正确处理多音字)\n")
        f.write("# 词频来源: rime-ice base/chengyu 词库(仅作词频查询)\n")
        f.write("#\n---\nname: yingtao_words\nversion: \"2.0\"\nsort: by_weight\n...\n")
        for text, code, weight in out:
            f.write("%s\t%s\t%d\n" % (text, code, boosted_weight(code, weight, text)))

    print("openfly words:", len(words))
    print("skipped (pinyin mismatch):", skipped_pinyin)
    print("no freq in rime-ice (used default):", no_freq)
    print("written entries:", len(out))


if __name__ == "__main__":
    main()
