"""Normalise data/scd-rooms.json into data/rooms-<set>.json (items, doors, enemies, interactions).

Field layouts follow biorand biohazard-utils opcode readers (RE3 / OpcodeV3):
  item_aot_set   id sce sat floor super x z w d item amount flag md1 action
  item_aot_set_4p id sce sat floor super x0 z0 x1 z1 x2 z2 x3 z3 item amount flag md1 action
  door_aot_se    id sce sat floor super x z w d nx ny nz nd stage room cut nfloor tex anim snd lock_id key free
  door_aot_set_4p id sce sat floor super x0..z3(8) nx ny nz nd stage room cut nfloor tex anim snd lock_id key free
  aot_set        id sce sat floor super x z w d b0..b5
  aot_set_4p     id sce sat floor super x0..z3(8) b0..b5
  em_set         unk id type state ai unk09 unk0a floor snd tex kill x y z d anim unk15
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK_ITEMS = ROOT / 'local/reference/re3-mod-sdk/xml_eng/items_simple.xml'
CONST = ROOT / 'local/reference/biohazard-utils/src/IntelOrca.Biohazard/Script/Bio3ConstantTable.cs'


def item_names():
    names = re.findall(r'<Text>(.*?)</Text>', SDK_ITEMS.read_text(encoding='utf-8-sig'), re.S)
    return names


def const_items():
    """biorand symbol -> numeric item id (same Namify rule: upper, non-alnum -> _)."""
    src = CONST.read_text(encoding='utf-8-sig')
    block = src[src.index('string[] g_itemNames'):]
    block = block[block.index('{') + 1:block.index('};')]
    names = re.findall(r'"(.*?)"', block)
    table = {}
    for i, n in enumerate(names):
        sym = re.sub(r'_+', '_', 'ITEM_' + re.sub(r'[^A-Z0-9_]', '_', n.upper())) if n else None
        if sym:
            table.setdefault(sym, i)
    return table


def item_id(sym, table):
    if isinstance(sym, int):
        return sym
    if sym in ('UNLOCKED', 'LOCKED', 'UNLOCK'):
        return {'UNLOCKED': 0, 'LOCKED': 255, 'UNLOCK': 254}[sym]
    m = re.fullmatch(r'ITEM_([0-9A-F]{2})', sym)
    if m:
        return int(m.group(1), 16)
    return table[sym]


def rect(a, four):
    if four:
        xs, zs = a[5:13:2], a[6:13:2]
        return dict(x=min(xs), z=min(zs), w=max(xs) - min(xs), d=max(zs) - min(zs), quad=list(zip(xs, zs)))
    return dict(x=a[5], z=a[6], w=a[7], d=a[8])


def build(rooms, names, table):
    out = {}
    for room, recs in rooms.items():
        r = dict(items=[], doors=[], enemies=[], aots=[], map_open=[], sets=[])
        for rec in recs:
            a, op = rec['args'], rec['op']
            ctx = dict(cond=rec['cond'], proc=rec['proc'], path=rec['path'], callconds=rec.get('callconds', []))
            if op in ('item_aot_set', 'item_aot_set_4p'):
                k = 13 if op.endswith('4p') else 9
                iid = item_id(a[k], table)
                r['items'].append(dict(aot=a[0], floor=a[3], **rect(a, op.endswith('4p')), item=iid,
                                       name=names[iid] if iid < len(names) else f'#{iid}',
                                       amount=a[k + 1], flag=a[k + 2], md1=a[k + 3], action=a[k + 4], **ctx))
            elif op in ('door_aot_se', 'door_aot_set_4p'):
                k = 17 if op.endswith('4p') else 13
                stage, rid = a[k], a[k + 1]
                r['doors'].append(dict(aot=a[0], sat=a[2], floor=a[3], **rect(a, op.endswith('4p')),
                                       target=f'{stage + 1:X}{rid:02X}', cut=a[k + 2], nfloor=a[k + 3],
                                       lock_id=a[k + 7], key=item_id(a[k + 8], table), **ctx))
            elif op == 'em_set':
                r['enemies'].append(dict(id=a[1], type=a[2], state=a[3], ai=a[4], floor=a[7], kill=a[10],
                                         x=a[11], y=a[12], z=a[13], d=a[14], **ctx))
            elif op in ('aot_set', 'aot_set_4p'):
                k = 13 if op.endswith('4p') else 9
                r['aots'].append(dict(aot=a[0], sce=a[1], sat=a[2], floor=a[3], **rect(a, op.endswith('4p')),
                                      data=a[k:k + 6], **ctx))
            elif op == 'map_open':
                r['map_open'].append(dict(args=a, **ctx))
            elif op == 'set':
                r['sets'].append(dict(bank=a[0], bit=a[1], value=a[2], **ctx))
        out[room] = r
    return out


def main():
    scd = json.loads((ROOT / 'data/scd-rooms.json').read_text())
    names, table = item_names(), const_items()
    (ROOT / 'data/item-names-en.json').write_text(json.dumps(names, ensure_ascii=False, indent=0) + '\n')
    for dataset, rooms in scd.items():
        data = build(rooms, names, table)
        (ROOT / f'data/rooms-{dataset}.json').write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
        print(dataset, len(data), {k: sum(len(v[k]) for v in data.values()) for k in ('items', 'doors', 'enemies', 'aots')})


if __name__ == '__main__':
    main()
