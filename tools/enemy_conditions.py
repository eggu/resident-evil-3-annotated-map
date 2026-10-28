"""Conservative SCD encounter predicates, in the overlay's CNF representation."""
import re

CMP_OPS = ('CMP_EQ', 'CMP_GT', 'CMP_GE', 'CMP_LT', 'CMP_LE', 'CMP_NE')
# Nemesis encounter state, set natively (never by SCD) and global: var 39 picks the room event, 42 its stage.
REMOTE_VARS = {39, 42}


def either(a, b):
    return [x + y for x in a for y in b]


def expression(s, invert=False):
    s = s.strip()
    while s.startswith('(') and s.endswith(')'):
        depth = 0
        for i, c in enumerate(s):
            depth += (c == '(') - (c == ')')
            if depth == 0:
                break
        if i != len(s) - 1:
            break
        s = s[1:-1].strip()
    for operator in ('||', '&&'):
        depth = 0
        for i, c in enumerate(s):
            depth += (c == '(') - (c == ')')
            if depth == 0 and s[i:i + 2] == operator:
                a, b = expression(s[:i], invert), expression(s[i + 2:], invert)
                return either(a, b) if (operator == '||') != invert else a + b
    m = re.fullmatch(r'ck\(\s*(\d+)\s*,\s*(\d+)\s*,\s*([01])\s*\)', s)
    if m:
        b, n, v = map(int, m.groups())
        return [[[b, n, v ^ invert]]]
    m = re.fullmatch(r'cmp\(\s*\d+\s*,\s*(?:var_([0-9A-Fa-f]+)|(\d+))\s*,\s*(CMP_[A-Z]+|\d+)\s*,\s*(-?\d+)\s*\)', s)
    if m:
        var = int(m[1], 16) if m[1] else int(m[2])
        op = CMP_OPS.index(m[3]) if m[3] in CMP_OPS else int(m[3])
        value = int(m[4])
        # Only global state means the same thing for a room that is not loaded; cut (26), previous
        # room (27/31), coordinates etc. describe the current room only.
        if var in REMOTE_VARS and op <= 5:
            if invert:
                op = [5, 4, 3, 2, 1, 0][op]
            return [[[50 + op, var, value]]]
    # Unknown predicates are not evidence for either branch.
    return [[]]


def guard(conditions):
    result = []
    for c in conditions:
        neg = c.startswith('else[') and c.endswith(']')
        text = c[5:-1] if neg else c
        if text.startswith('if '):
            result += expression(text[3:], neg)
        else:
            result += [[]]
    return result
