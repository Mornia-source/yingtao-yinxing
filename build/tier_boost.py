# -*- coding: utf-8 -*-
"""共享的"码长优先"权重加成表。

新规则：无论用户当前打了几个字符、无论候选是单字还是词/句，
候选自身编码位数越少，优先级越高——2位(单字双拼) > 3位(词组简码) > 4位(全码)。
每一档之间的加成差远大于该档内任何真实权重的最大值，保证跨档时
位数少的永远排在前面，档内再按原始词频排序。
"""

# 实测最大真实权重：单字表(8105.dict.yaml)约1.5e7，词库(base.dict.yaml)约6.6e5，
# 留足安全余量。
TIER_BOOST = {
    2: 100_000_000,
    3: 50_000_000,
    4: 0,
}

# 手动指定"某个编码优先显示哪个候选"的兜底名单，不依赖候选排序机制本身
# 是否可靠——不管排序有没有问题，这里点名的(编码, 文本)组合权重都会被
# 加到远超同编码其它候选的水平。发现类似的撞码问题可以往这里加一条。
PRIORITY_OVERRIDES = {
    ("womf", "我们"): 900_000_000,
}


def boosted_weight(code, weight, text=None):
    w = weight + TIER_BOOST.get(len(code), 0)
    if text is not None:
        w += PRIORITY_OVERRIDES.get((code, text), 0)
    return w
