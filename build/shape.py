import sqlite3, json, io, sys

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(_HERE, "..", "sources")

WUBI98_PATH = os.path.join(_SOURCES, "wubi98.dict.yaml")
PYCHAI_DB = os.path.join(_SOURCES, "pychai_main.sqlite")
ATOMS_TXT = os.path.join(_HERE, "atoms.txt")
# User-supplied authoritative reference: 通用规范汉字8105字, 98五笔码已手动去除
# 末笔识别码，只保留真实字根序列。首选数据源，覆盖率约8104/8139。
NOIDENT_REF_PATH = os.path.join(_SOURCES, "wubi98_noident_8105.txt")

SUFFIXES = ["变","左","右","上","下","角","内","外","框","底","中","头","旁"]
MANUAL_FIRST = {"半竹":"t","双折":"n","横斜钩":"g","横日":"g","横钩":"g","竖折":"h"}
RESOLVED_SUFFIXED_PATH = os.path.join(_HERE, "resolved_suffixed_atoms.json")

# Manually confirmed corrections for specific characters (from user feedback),
# overriding whatever the general decomposition pipeline would produce.
# ("是" used to need this before the authoritative wubi98_noident_8105.txt
# reference was supplied; the reference now gives "jh" directly.)
CHAR_SHAPE_OVERRIDE = {}


def load_longest_code():
    longest_code = {}
    with io.open(WUBI98_PATH, encoding="utf-8") as f:
        started = False
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "...":
                started = True
                continue
            if not started:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            text, code = parts[0], parts[1]
            if len(text) != 1 or not code or not code.isalpha():
                continue
            prev = longest_code.get(text)
            if prev is None or len(code) > len(prev):
                longest_code[text] = code
    return longest_code


def _is_suffixed(name):
    return any(name.endswith(s) and len(name) > 1 for s in SUFFIXES)


def load_atom_first(longest_code):
    with io.open(ATOMS_TXT, encoding="utf-8") as f:
        atoms = [l.strip() for l in f if l.strip()]
    try:
        with io.open(RESOLVED_SUFFIXED_PATH, encoding="utf-8") as f:
            resolved_suffixed = json.load(f)
    except IOError:
        resolved_suffixed = {}

    atom_first = {}
    for a in atoms:
        if a in MANUAL_FIRST:
            atom_first[a] = MANUAL_FIRST[a]
            continue
        if _is_suffixed(a):
            # Position-suffixed synthetic shapes (e.g. '竹头','定下') are NOT
            # reliably the same wubi key as their namesake base character.
            # Only trust cross-reference-verified values; otherwise leave
            # unresolved so shape() falls back to the whole character's own
            # official code instead of a wrong guess.
            atom_first[a] = resolved_suffixed.get(a)
            continue
        code = longest_code.get(a)
        atom_first[a] = code[0] if code else None
    return atom_first


def load_tree():
    conn = sqlite3.connect(PYCHAI_DB)
    cur = conn.cursor()
    cur.execute("select name, operator, first, second from main")
    return {name: (op, f, s) for name, op, f, s in cur.fetchall()}


def load_noident_ref():
    ref = {}
    try:
        with io.open(NOIDENT_REF_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\r\n")
                parts = line.split("\t")
                if len(parts) != 2:
                    continue
                ch, code = parts
                if len(ch) == 1 and code.isalpha() and code.islower():
                    ref[ch] = code
    except IOError:
        pass
    return ref


class ShapeEncoder:
    def __init__(self):
        self.longest_code = load_longest_code()
        self.atom_first = load_atom_first(self.longest_code)
        self.tree = load_tree()
        self.noident_ref = load_noident_ref()
        sys.setrecursionlimit(10000)

    def leaves(self, name, depth=0, seen=None):
        if seen is None:
            seen = set()
        if name in seen or depth > 20:
            return [name]
        seen = seen | {name}
        entry = self.tree.get(name)
        if not entry or entry[0] is None:
            return [name]
        op, f, s = entry
        if not f or not s:
            return [name]
        return self.leaves(f, depth + 1, seen) + self.leaves(s, depth + 1, seen)

    def shape(self, char):
        """Returns (code, mode) where mode in
        {ref, decomp, own-full, own1, fail, override}"""
        if char in CHAR_SHAPE_OVERRIDE:
            return CHAR_SHAPE_OVERRIDE[char], "override"
        root_code = self.noident_ref.get(char)
        if root_code:
            if len(root_code) == 1:
                return root_code[0] + root_code[0], "ref"
            return root_code[0] + root_code[-1], "ref"
        ls = self.leaves(char)
        if len(ls) >= 2:
            fk = self.atom_first.get(ls[0])
            lk = self.atom_first.get(ls[-1])
            if fk and lk:
                return fk + lk, "decomp"
        code = self.longest_code.get(char)
        if code:
            if len(code) == 1:
                return code[0] + code[0], "own1"
            return code[0] + code[-1], "own-full"
        return None, "fail"


if __name__ == "__main__":
    enc = ShapeEncoder()
    with io.open(os.path.join(_SOURCES, "8105.dict.yaml"), encoding="utf-8") as f:
        started = False
        chars = []
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "...":
                started = True
                continue
            if not started:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            chars.append(parts[0])
    modes = {}
    fails = []
    for c in chars:
        code, mode = enc.shape(c)
        modes[mode] = modes.get(mode, 0) + 1
        if mode == "fail":
            fails.append(c)
    print(len(chars), "chars total")
    print(modes)
    print("fails sample:", fails[:50])
