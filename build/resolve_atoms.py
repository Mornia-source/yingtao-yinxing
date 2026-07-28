# -*- coding: utf-8 -*-
"""Resolve the wubi-key for pychai's position-suffixed synthetic atoms
(e.g. '竹头','定下') by cross-referencing characters where that same shape
is used as a component, using the official wubi98 code's first-letter
invariant (first letter of any code is always a real root)."""
import sqlite3, io, json, os
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(_HERE, "..", "sources")

SUFFIXES = ["变", "左", "右", "上", "下", "角", "内", "外", "框", "底", "中", "头", "旁"]


def is_suffixed(name):
    return any(name.endswith(s) and len(name) > 1 for s in SUFFIXES)


def load_longest_code():
    longest_code = {}
    with io.open(os.path.join(_SOURCES, "wubi98.dict.yaml"), encoding="utf-8") as f:
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


def load_tree():
    conn = sqlite3.connect(os.path.join(_SOURCES, "pychai_main.sqlite"))
    cur = conn.cursor()
    cur.execute("select name, operator, first, second from main")
    return list(cur.fetchall())


def build_simple_first(longest_code, tree_rows, atoms):
    """First pass: atoms resolvable directly (no suffix, or suffix-stripped base works
    and the base itself is a simple radical). Used only as a bootstrap for the
    'first-position' cross reference below (needs SOME trusted keys to start)."""
    simple_first = {}
    for a in atoms:
        if is_suffixed(a):
            continue
        code = longest_code.get(a)
        simple_first[a] = code[0] if code else None
    return simple_first


def resolve(atoms):
    longest_code = load_longest_code()
    tree_rows = load_tree()
    tree = {name: (op, f, s) for name, op, f, s in tree_rows}

    trusted = build_simple_first(longest_code, tree_rows, atoms)

    # index: atom -> list of outer chars where atom is the FIRST component
    first_users = {}
    for name, op, f, s in tree_rows:
        if op is not None and f:
            first_users.setdefault(f, []).append(name)

    resolved = {}
    votes_log = {}

    problem_atoms = [a for a in atoms if is_suffixed(a)]

    # Method A: atom appears as first-component of some outer char with a known code
    for atom in problem_atoms:
        votes = Counter()
        for outer in first_users.get(atom, []):
            code = longest_code.get(outer)
            if code:
                votes[code[0]] += 1
        if votes:
            best, n = votes.most_common(1)[0]
            if n >= max(1, 0.6 * sum(votes.values())):
                resolved[atom] = best
                votes_log[atom] = ("firstpos", dict(votes))

    # Method B: atom appears as SECOND component of a 2-leaf split whose outer char's
    # own code position matches (first component contributes exactly 1 letter when
    # it's a simple/trusted atom).
    for atom in problem_atoms:
        if atom in resolved:
            continue
        votes = Counter()
        for name, op, f, s in tree_rows:
            if op is None or s != atom or not f:
                continue
            fk = trusted.get(f) or resolved.get(f)
            if not fk:
                continue
            code = longest_code.get(name)
            if not code or len(code) < 2:
                continue
            if code[0] != fk:
                continue  # first component's own key must match position0 to trust position1
            votes[code[1]] += 1
        if votes:
            best, n = votes.most_common(1)[0]
            if n >= max(1, 0.6 * sum(votes.values())):
                resolved[atom] = best
                votes_log[atom] = ("secondpos", dict(votes))

    return resolved, votes_log, problem_atoms


if __name__ == "__main__":
    with io.open(os.path.join(_HERE, "atoms.txt"), encoding="utf-8") as f:
        atoms = [l.strip() for l in f if l.strip()]
    resolved, votes_log, problem_atoms = resolve(atoms)
    print("problem atoms:", len(problem_atoms), " resolved:", len(resolved))
    unresolved = [a for a in problem_atoms if a not in resolved]
    print("still unresolved:", len(unresolved))
    print(unresolved)
    with io.open(os.path.join(_HERE, "resolved_suffixed_atoms.json"), "w", encoding="utf-8") as f:
        json.dump(resolved, f, ensure_ascii=False, indent=1)
