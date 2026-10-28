"""Extract per-room placements from biorand `scd --decompile` output (local/scd/<set>/Rxxx.bio).

Writes data/scd-rooms.json: for each data set (DATA_J, DATA_AJ) and room, every
item_aot_set / door_aot_se / em_set / aot_set (+_4p) / map_open with its
procedure, the enclosing condition stack and how the procedure is reached.
Read-only; the game files are only read through the decompiler output.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCD = ROOT / 'local/scd'
OPS = ('item_aot_set', 'item_aot_set_4p', 'door_aot_se', 'door_aot_set_4p', 'em_set',
       'aot_set', 'aot_set_4p', 'aot_reset', 'map_open', 'set', 'item_get_ck', 'item_lost')
CALL = re.compile(r'^(\w+)\(\);$')
REF = re.compile(r'I_GOSUB, (\w+)|\b(main_[0-9A-F]{2})\b')
OP = re.compile(r'^(\w+)\((.*)\);$')


def args(s):
    return [a.strip() for a in s.split(',')] if s.strip() else []


def num(a):
    try:
        return int(a, 0)
    except ValueError:
        return a


def parse_room(path, strict=False):
    procs, records, cur, stack, pending_else, header, prev_if = {}, [], None, [], None, None, None
    cases, switch_values = {}, {}
    lines = path.read_text().splitlines()
    calls = {}  # proc -> [(callee, enclosing conditions at the call site)]
    for line_no, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        m = re.match(r'^proc (\w+)$', s)
        if m:
            cur, stack = m.group(1), []
            cases, switch_values = {}, {}
            procs[cur] = set()
            calls[cur] = []
            continue
        if s == '{':
            stack.append(pending_else or header)
            pending_else = header = None
            continue
        if s == '}':
            cases.pop(len(stack), None)
            switch_values.pop(len(stack), None)
            last = stack.pop() if stack else None
            header = None
            prev_if = last if last and last.startswith('if') else None
            continue
        if s in ('else',):
            header = f'else[{prev_if}]'
            continue
        if re.match(r'^(if|while|switch|do|for)\b', s):
            header = s
            if strict and s.startswith('switch'):
                values, depth = [], 0
                for following in lines[line_no + 1:]:
                    text = following.strip()
                    if text == '{': depth += 1
                    if text == '}':
                        depth -= 1
                        if depth == 0: break
                    label = re.match(r'case (\d+):', text)
                    if depth == 1 and label: values.append(int(label[1]))
                switch_values[len(stack) + 1] = values
            continue
        if re.match(r'^(case .*|default):$', s):
            if strict:
                switch = next((h for h in reversed(stack) if h and h.startswith('switch')), '')
                var = re.search(r'var_([0-9A-Fa-f]+)', switch)
                value = re.match(r'case (\d+):', s)
                if var and value:
                    cases[len(stack)] = f'if (cmp(0, var_{var[1]}, 0, {value[1]}))'
                elif var and switch_values.get(len(stack)):
                    terms = ' && '.join(f'cmp(0, var_{var[1]}, 5, {v})' for v in switch_values[len(stack)])
                    cases[len(stack)] = f'if ({terms})'
                else:
                    cases[len(stack)] = 'unknown_switch'
                continue
            # Labels do not open braces; track them separately so outer conditions still close.
            cases[len(stack)] = s[:-1]
            continue
        header = None
        if cur is None:
            continue
        here = [c for c in stack if c and not (strict and c.startswith('switch'))] + list(cases.values())
        for g in REF.finditer(s):
            procs[cur].add(g.group(1) or g.group(2))
            calls[cur].append((g.group(1) or g.group(2), here + (['event_trigger'] if strict and s.startswith(('aot_set(', 'aot_set_4p(', 'aot_reset(')) else [])))
        c = CALL.match(s)
        if c:
            procs[cur].add(c.group(1))
            calls[cur].append((c.group(1), here))
        o = OP.match(s)
        if o and o.group(1) in OPS:
            name, a = o.group(1), args(o.group(2))
            if name == 'set' and len(a) == 3:
                pass
            elif name == 'set':
                continue
            records.append(dict(op=name, args=[num(x) for x in a], proc=cur, cond=here))
    return procs, records, calls


def call_conditions(calls, limit=32):
    """Every acyclic call chain from main/aot to each proc, as the concatenated call-site conditions."""
    out = {}
    def walk(p, conds, seen):
        alts = out.setdefault(p, [])
        if len(alts) < limit and conds not in alts:
            alts.append(conds)
        for q, c in calls.get(p, ()):
            if q not in seen and len(out.get(q, ())) < limit:
                walk(q, conds + c, seen | {q})
    for root in ('main', 'aot'):
        if root in calls:
            walk(root, [], {root})
    return out


def reach(procs):
    """Shortest call path from main/aot to each proc, tagging event-handler (I_GOSUB from aot_set) hops."""
    paths = {}
    frontier = [(r, [r]) for r in ('main', 'aot') if r in procs]
    while frontier:
        nxt = []
        for p, path in frontier:
            if p in paths:
                continue
            paths[p] = path
            for q in sorted(procs.get(p, ())):
                if q not in paths:
                    nxt.append((q, path + [q]))
        frontier = nxt
    return paths


def main():
    out = {}
    for dataset in ('DATA_J', 'DATA_AJ'):
        rooms = {}
        for bio in sorted((SCD / dataset).glob('R*.bio')):
            procs, records, calls = parse_room(bio)
            paths = reach(procs)
            chains = call_conditions(calls)
            for r in records:
                r['path'] = paths.get(r['proc'])
                r['callconds'] = chains.get(r['proc'], [])
            rooms[bio.stem[1:]] = records
        out[dataset] = rooms
    dst = ROOT / 'data/scd-rooms.json'
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=None, separators=(',', ':')) + '\n')
    n = {k: sum(len(v) for v in d.values()) for k, d in out.items()}
    print(dst, n)


if __name__ == '__main__':
    main()
