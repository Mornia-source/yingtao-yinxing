import re

_CIRCLED = "ⓆⓌⓇⓉⓎⓊⒾⓄⓅⓈⒹⒻⒼⒽⓂⒿⒸⓀⓁⓏⓍⓋⒷⓃ"
_PLAIN = "qwrtyuiopsdfghmjcklzxvbn"
_XLIT = dict(zip(_CIRCLED, _PLAIN))

# kind: 'sub' = plain re.sub with backreferences; 'final' = (\w+?)FINAL(;.*) -> group1+mark+group2
#
# 零声母的 an/en/ai/ei/ao/ou 本身拼写正好就是2个字母，不再重复"重复声母再
# 压缩韵母"这一套（例如"按(an)"直接就是 an，不再算成 aj）；只有 a/e/o 单独
# 或带 ng 的零声母（a/e/o/ang/eng）才需要重复首字母来腾出韵母键位。
_RULES = [
    ('sub', r'^([jqxy])u(;.*)$', r'\1v\2'),
    ('sub', r'^([aoe])(ng)?(;.*)$', r'\1\1\2\3'),
    ('final', r'^(\w+?)iu(;.*)$', 'Ⓠ'),
    ('final', r'^(\w+?)[uv]an(;.*)$', 'Ⓡ'),
    ('final', r'^(\w+?)[uv]e(;.*)$', 'Ⓣ'),
    ('final', r'^(\w+?)ing(;.*)$', 'Ⓨ'),
    ('final', r'^(\w+?)uai(;.*)$', 'Ⓨ'),
    ('final', r'^(\w+?)uo(;.*)$', 'Ⓞ'),
    ('final', r'^(\w+?)[uv]n(;.*)$', 'Ⓟ'),
    ('final', r'^(\w+?)i?ong(;.*)$', 'Ⓢ'),
    ('final', r'^(\w+?)[iu]ang(;.*)$', 'Ⓓ'),
    ('final', r'^(\w+?)en(;.*)$', 'Ⓕ'),
    ('final', r'^(\w+?)eng(;.*)$', 'Ⓖ'),
    ('final', r'^(\w+?)ang(;.*)$', 'Ⓗ'),
    ('final', r'^(\w+?)ian(;.*)$', 'Ⓜ'),
    ('final', r'^(\w+?)an(;.*)$', 'Ⓙ'),
    ('final', r'^(\w+?)iao(;.*)$', 'Ⓒ'),
    ('final', r'^(\w+?)ao(;.*)$', 'Ⓚ'),
    ('final', r'^(\w+?)ai(;.*)$', 'Ⓛ'),
    ('final', r'^(\w+?)ei(;.*)$', 'Ⓩ'),
    ('final', r'^(\w+?)ie(;.*)$', 'Ⓧ'),
    ('final', r'^(\w+?)ui(;.*)$', 'Ⓥ'),
    ('final', r'^(\w+?)ou(;.*)$', 'Ⓑ'),
    ('final', r'^(\w+?)in(;.*)$', 'Ⓝ'),
    ('final', r'^(\w+?)[iu]a(;.*)$', 'Ⓦ'),
    ('sub', r'^sh', 'Ⓤ'),
    ('sub', r'^ch', 'Ⓘ'),
    ('sub', r'^zh', 'Ⓥ'),
]


def _apply_final_rule(s, pattern, mark):
    m = re.match(pattern, s)
    if not m:
        return s
    groups = m.groups()
    return groups[0] + mark + groups[1]


def encode_zrm(pinyin):
    """pinyin: plain lowercase pinyin syllable without tone, e.g. 'ting', 'quan', 'a', 'yu'"""
    s = pinyin + ";"
    for kind, pattern, repl in _RULES:
        if kind == 'final':
            s = _apply_final_rule(s, pattern, repl)
        else:
            s = re.sub(pattern, repl, s)
    if s.endswith(';'):
        s = s[:-1]
    out = ''.join(_XLIT.get(ch, ch) for ch in s)
    return out


_BARE_V_FINAL = re.compile(r'^[jqxy]u$')


def encode_zrm_variants(pinyin):
    """像 ju/qu/xu/yu 这样的纯ü韵母字，ü键位既可以打v也可以直接打u
    (x/j/q/y从不真正跟"u"这个韵母搭配，所以复用u键不会有歧义)。
    返回该拼音全部等价双拼编码，通常只有一个。"""
    code = encode_zrm(pinyin)
    variants = [code]
    if _BARE_V_FINAL.match(pinyin) and code.endswith('v'):
        variants.append(code[:-1] + 'u')
    return variants


if __name__ == "__main__":
    tests = ["ting", "quan", "wo", "a", "ye", "yu", "yuan", "yue", "yun",
             "wai", "kuai", "ying", "bing", "zhong", "chi", "shi", "zhi",
             "an", "ang", "ai", "ei", "ao", "ou", "en", "eng", "er",
             "wa", "wo", "wu", "yi", "yin", "yan", "yang", "wan", "wang",
             "juan", "jue", "jun", "lve", "nve", "e", "o"]
    for t in tests:
        print(t, "->", encode_zrm(t))
