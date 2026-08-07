# -*- coding: utf-8 -*-
"""生成樱桃音形词组码表（二字词及以上）。

词表 / 注音 / 词频都来自 rime-ice（雾凇拼音）的基础词库：
  词 \t 逐字拼音(空格分隔) \t 词频
注音是雾凇自己手工校订过的，多音字比通用注音库更可靠（银行 yin hang、
重庆 chong qing、会计 kuai ji、音乐 yin yue 都是对的），所以优先用它；
个别注音缺失或对不齐的条目才退回 pypinyin。

原先用过 openfly（开源小鹤音形）的词表，后来查明：小鹤官方词库闭源，
openfly 是对 v9 时代的复刻且已停更（2024-09）；社区里还在维护的所谓
「小鹤词库」方案用的其实都是雾凇词库，只是套了小鹤的编码规则。所以
「小鹤重码少」是编码方案 + 词表精简的功劳，词库本身并无独到之处，
直接用长期维护、注音更准的雾凇即可。

词组编码规则见 README「编码规则」一节。
"""
import io, os

from shape import ShapeEncoder
from flypy import encode_flypy_variants as encode_zrm_variants
from tier_boost import boosted_weight

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(_HERE, "..", "sources")

WORD_SOURCES = ["rime-ice.base.dict.yaml", "rime-ice.others.dict.yaml"]
OUT = os.path.join(_HERE, "yingtao_words.dict.yaml")

# 词频下限。雾凇全量 base+others 有 54 万词，词库越大重码越严重；
# 参考小鹤音形官方码表(约5.8万词)的规模，这里定了一个门槛把量级
# 收敛到差不多同一个数量级，压掉大量低频人名/地名/品牌词条。
# 想要更全可以调低，想要更少重码可以调高，实测数据见 README。
MIN_FREQ = 15000

_pypinyin = None


def fallback_pinyin(text):
    """雾凇注音缺失时的兜底。"""
    global _pypinyin
    if _pypinyin is None:
        from pypinyin import lazy_pinyin, Style
        _pypinyin = (lazy_pinyin, Style)
    lazy_pinyin, Style = _pypinyin
    syls = lazy_pinyin(text, style=Style.NORMAL, v_to_u=False, errors="ignore")
    return syls if len(syls) == len(text) else None


def _is_cjk(ch):
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF
            or 0x20000 <= o <= 0x2FA1F)


def load_words():
    """返回 [(词, 逐字拼音, 词频)]，只保留纯汉字的多字词。"""
    rows = []
    seen = {}
    for name in WORD_SOURCES:
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
                if not started or not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                text = parts[0]
                if len(text) < 2:
                    continue  # 单字走 gen_chars.py
                if not all(_is_cjk(c) for c in text):
                    continue
                try:
                    w = int(parts[2])
                except ValueError:
                    continue
                if w < MIN_FREQ:
                    continue
                syls = parts[1].split()
                if len(syls) != len(text):
                    syls = fallback_pinyin(text)
                    if syls is None:
                        continue
                # 同一个词可能在多份词库里重复，取词频最高的那条
                if text in seen:
                    if w > seen[text][2]:
                        seen[text] = (text, syls, w)
                else:
                    seen[text] = (text, syls, w)
    return list(seen.values())


def codes_for(text, zrm_variants, firsts, tail_shape=None):
    """按樱桃音形规则返回该词的全部编码（简码 + 全码 + ；声明扩展码）。

    全码默认是纯拼音接龙，跟打字的直觉节奏一致，不会打到一半突然要
    切换成"打形码"的逻辑：
      二字词 = 前字双拼 + 后字双拼（4位）
      三字词 = 前两字首码 + 第三字前两位（4位）
      四字词 = 四字首码（4位）
      五字及以上 = 前三字首码 + 末字首码（4位）
    简码（图快用的额外短码）：
      二字词 = 前字前两位 + 后字首位（3位）
      三字词 = 三字首码（3位）

    ；声明扩展码：全码本身还重码时，用户可以主动在全码后面打 ；再接
    末字形码，进一步消歧（比如"梅花"/"美化"字面撞车，用；声明区分）。
    这是唯一会用到形码的地方，且必须用户主动打 ；才会用到，默认打字
    从头到尾都是纯拼音，不会被"形码"打断。
    """
    n = len(text)
    out = []
    fulls = []
    if n == 2:
        for z0 in zrm_variants[0]:
            for z1 in zrm_variants[1]:
                fulls.append(z0 + z1)
            out.append(z0 + firsts[1])
    elif n == 3:
        out.append(firsts[0] + firsts[1] + firsts[2])
        for z2 in zrm_variants[2]:
            fulls.append(firsts[0] + firsts[1] + z2)
    elif n == 4:
        fulls.append("".join(firsts))
    else:
        fulls.append(firsts[0] + firsts[1] + firsts[2] + firsts[-1])

    if tail_shape:
        for full in fulls:
            out.append(full + ";" + tail_shape)

    out.extend(fulls)
    return out


def main():
    enc = ShapeEncoder()
    shape_cache = {}

    def shape_of(ch):
        if ch not in shape_cache:
            shape_cache[ch] = enc.shape(ch)[0] or None
        return shape_cache[ch]

    rows = load_words()

    out = []
    skipped = 0
    for text, syls, weight in rows:
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
            skipped += 1
            continue

        # 末字查不到形码（极少数生僻字）时，跳过；声明扩展码，
        # 全码本身不受影响。
        tail_shape = shape_of(text[-1])

        for code in codes_for(text, zrm_variants, firsts, tail_shape):
            out.append((text, code, weight))

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Rime dictionary\n# encoding: utf-8\n#\n")
        f.write("# 樱桃音形 - 词组码表（二字词/三字词/四字词/多字词）\n")
        f.write("# 词表/注音/词频来源: rime-ice 雾凇拼音 基础词库\n")
        f.write("# 全码默认纯拼音接龙，简码/全码之外还有一条用户主动打；声明的\n")
        f.write("# 扩展码(全码+；+末字形码)，供全码本身还重码时进一步消歧，\n")
        f.write("# 默认不声明不受影响\n")
        f.write("#\n---\nname: yingtao_words\nversion: \"5.0\"\nsort: by_weight\n...\n")
        for text, code, weight in out:
            f.write("%s\t%s\t%d\n" % (text, code, boosted_weight(code, weight, text)))

    print("words:", len(rows), "skipped(bad syllable):", skipped)
    print("written entries:", len(out))


if __name__ == "__main__":
    main()
