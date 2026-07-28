import re

_CIRCLED = "ⓆⓌⓇⓉⓎⓊⒾⓄⓅⓈⒹⒻⒼⒽⓂⒿⒸⓀⓁⓏⓍⓋⒷⓃ"
_PLAIN = "qwrtyuiopsdfghmjcklzxvbn"
_XLIT = dict(zip(_CIRCLED, _PLAIN))

# kind: 'sub' = plain re.sub with backreferences; 'final' = (\w+?)FINAL(;.*) -> group1+mark+group2
_RULES = [
    ('sub', r'^([jqxy])u(;.*)$', r'\1v\2'),
    ('sub', r'^([aoe])([ioun])(;.*)$', r'\1\1\2\3'),
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


if __name__ == "__main__":
    tests = ["ting", "quan", "wo", "a", "ye", "yu", "yuan", "yue", "yun",
             "wai", "kuai", "ying", "bing", "zhong", "chi", "shi", "zhi",
             "an", "ang", "ai", "ei", "ao", "ou", "en", "eng", "er",
             "wa", "wo", "wu", "yi", "yin", "yan", "yang", "wan", "wang",
             "juan", "jue", "jun", "lve", "nve", "e", "o"]
    for t in tests:
        print(t, "->", encode_zrm(t))
