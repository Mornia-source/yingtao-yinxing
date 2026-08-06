import re

# 小鹤双拼(flypy)算法，规则原样翻译自
# https://github.com/kchen0x/rime-crane/blob/main/double_pinyin_flypy.schema.yaml
# (speller/algebra)，跟 zrm.py(自然码) 是同一套接口，互相替换用。
#
# kind: 'xform' = 强制替换(不保留原串)；'derive' = 派生出一个新变体(原串也保留)。
_RULES = [
    ('derive', r'^([jqxy])u$', r'\1v'),
    ('derive', r'^([aoe])([ioun])$', r'\1\1\2'),
    ('xform', r'^([aoe])(ng)?$', r'\1\1\2'),
    ('xform', r'iu$', 'Ⓠ'),
    ('xform', r'(.)ei$', r'\1Ⓦ'),
    ('xform', r'uan$', 'Ⓡ'),
    ('xform', r'[uv]e$', 'Ⓣ'),
    ('xform', r'un$', 'Ⓨ'),
    ('xform', r'^sh', 'Ⓤ'),
    ('xform', r'^ch', 'Ⓘ'),
    ('xform', r'^zh', 'Ⓥ'),
    ('xform', r'uo$', 'Ⓞ'),
    ('xform', r'ie$', 'Ⓟ'),
    ('xform', r'(.)i?ong$', r'\1Ⓢ'),
    ('xform', r'ing$|uai$', 'Ⓚ'),
    ('xform', r'(.)ai$', r'\1Ⓓ'),
    ('xform', r'(.)en$', r'\1Ⓕ'),
    ('xform', r'(.)eng$', r'\1Ⓖ'),
    ('xform', r'[iu]ang$', 'Ⓛ'),
    ('xform', r'(.)ang$', r'\1Ⓗ'),
    ('xform', r'ian$', 'Ⓜ'),
    ('xform', r'(.)an$', r'\1Ⓙ'),
    ('xform', r'(.)ou$', r'\1Ⓩ'),
    ('xform', r'[iu]a$', 'Ⓧ'),
    ('xform', r'iao$', 'Ⓝ'),
    ('xform', r'(.)ao$', r'\1Ⓒ'),
    ('xform', r'ui$', 'Ⓥ'),
    ('xform', r'in$', 'Ⓑ'),
]

# 每个圆圈字母对应的真实按键，跟规则表逐条对应。
_XLIT = {
    "Ⓠ": "q", "Ⓦ": "w", "Ⓡ": "r", "Ⓣ": "t", "Ⓨ": "y",
    "Ⓤ": "u", "Ⓘ": "i", "Ⓞ": "o", "Ⓟ": "p", "Ⓢ": "s",
    "Ⓓ": "d", "Ⓕ": "f", "Ⓖ": "g", "Ⓗ": "h", "Ⓙ": "j",
    "Ⓚ": "k", "Ⓛ": "l", "Ⓩ": "z", "Ⓧ": "x", "Ⓒ": "c",
    "Ⓥ": "v", "Ⓑ": "b", "Ⓝ": "n", "Ⓜ": "m",
}


def encode_flypy(pinyin):
    """pinyin: 不带声调的小写拼音音节，如 'zhong'、'jiu'、'an'。返回2位双拼码
    （如果算法跑完不是2位，说明这个音节压根不合法，调用方应自行校验长度）。"""
    variants = _encode_flypy_all(pinyin)
    return variants[0] if variants else pinyin


def _encode_flypy_all(pinyin):
    candidates = {pinyin}
    for kind, pattern, repl in _RULES:
        if kind == 'xform':
            new_candidates = set()
            for s in candidates:
                new_candidates.add(re.sub(pattern, repl, s))
            candidates = new_candidates
        else:  # derive
            new_candidates = set(candidates)
            for s in candidates:
                if re.match(pattern, s):
                    new_candidates.add(re.sub(pattern, repl, s))
            candidates = new_candidates

    out = []
    for s in candidates:
        code = ''.join(_XLIT.get(ch, ch) for ch in s)
        if len(code) == 2 and code.isalpha():
            out.append(code)
    return out


def encode_flypy_variants(pinyin):
    """返回该拼音全部等价双拼编码（比如 ju 可能对应 jv 和 ju 两种打法）。"""
    variants = _encode_flypy_all(pinyin)
    if not variants:
        return [pinyin]
    # 稳定顺序：不带 v 变体的排前面
    variants.sort(key=lambda v: v.endswith('v'))
    return variants


if __name__ == "__main__":
    tests = ["ting", "quan", "wo", "a", "ye", "yu", "yuan", "yue", "yun",
             "wai", "kuai", "ying", "bing", "zhong", "chi", "shi", "zhi",
             "an", "ang", "ai", "ei", "ao", "ou", "en", "eng", "er",
             "wa", "wo", "wu", "yi", "yin", "yan", "yang", "wan", "wang",
             "juan", "jue", "jun", "lve", "nve", "e", "o", "jiu", "jiu",
             "shui", "chuan", "xian", "qiang", "liang", "duan"]
    for t in tests:
        print(t, "->", encode_flypy_variants(t))
