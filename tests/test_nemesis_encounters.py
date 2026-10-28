"""R208 deferred actor eligibility, independent of loaded actor/local flags."""
import json, runpy, struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
t = runpy.run_path(str(ROOT / 'tests/test_native.py'))
u, call, setup, set_bit, visit, S = (t[k] for k in ('u','call','setup','set_bit','visit','S'))
# Both original script sets reconstruct local4:0 from the same four persistent pickups.
for ds in ('DATA_J','DATA_AJ'):
    text = (ROOT / 'local/scd' / ds / 'R208.bio').read_text()
    init = text.split('proc main_34\n',1)[1].split('proc main_35',1)[0]
    assert all(f'ck(7, {n}, 1)' in init for n in (47,34,35,36))
    assert 'cmp(0, 4, CMP_EQ, 4)' in init and 'set(4, 0, 1)' in init
    assert 'if (ck(5, 140, 0))' in text
    assert 'ENEMY_NEMESIS, 1, 192, 0, 0, 0, 52, 0, 140, 0, 0, 0' in text
marker = next(m for m in json.loads((ROOT/'data/overlay.json').read_text())['markers']
              if m.get('monster')=='nemesis' and m.get('anchor')=='room' and m['rdt']=='208')
assert marker['sets']==3 and marker['kill']==140
blob = b''.join(struct.pack('<BBBBhhBBHH', *m) for m in t['markers'])
offset = bytes(t['di']).find(blob); assert offset>=0
for i,m in enumerate(t['markers']):
    if m[0]==8 and (m[1:3]!=(marker['page'],marker['idx']) or m[6]!=7):
        u.mem_write(0x10000000+offset+i*14+3,b'\0')
u.mem_write(0xA6228C,struct.pack('<I',0xA621EC))
checks=0
for aj in (0,1):
    u.mem_write(0xA67A44,struct.pack('<I',aj))
    for n in (47,34,35,36):set_bit(7,n)
    set_bit(5,140,False)
    for room in (7,8,7):  # before entering, inside, after leaving
        u.mem_write(0xA673C6,struct.pack('<HH',1,room))
        for local in (False,True):
            set_bit(4,0,local);set_bit(4,3,local)
            setup(1);call('AnnotatedMapTestSet',1,3,0);call('AnnotatedMapTestDraw',S)
            assert call('AnnotatedMapTestCount',8)==1,(aj,room,local)
            checks+=1
    for n in (47,34,35,36):
        set_bit(7,n,False);call('AnnotatedMapTestDraw',S)
        assert call('AnnotatedMapTestCount',8)==0
        set_bit(7,n);checks+=1
    set_bit(5,140);call('AnnotatedMapTestDraw',S)
    assert call('AnnotatedMapTestCount',8)==0
    set_bit(5,140,False)
    visit(1,8,False);call('AnnotatedMapTestSet',1,1,0);call('AnnotatedMapTestDraw',S)
    assert call('AnnotatedMapTestCount',8)==0
    visit(1,8);call('AnnotatedMapTestDraw',S)
    assert call('AnnotatedMapTestCount',8)==1
    u.mem_write(0xA673C6,struct.pack('<HH',2,0));call('AnnotatedMapTestDraw',S)
    assert call('AnnotatedMapTestCount',8)==0
print('Three Points Street:',checks,'before/inside/after/local-state/pickup checks; both datasets, kill/scope/later-stage OK')
# Real primitive placement: fixed first spawn, then badge beside the shifted/scaled room label.
def sprite_quads(sprite):
    pg,su,sv,sw,sh=t['sprites'][sprite]
    base,n=t['prims']();out=[]
    for i in range(n):
        q=bytes(u.mem_read(base+i*40,40))
        if (q[12],q[13],struct.unpack_from('<H',q,22)[0])==(su,sv,pg+1):out.append(q)
    return out
room_label=next(r for r in t['rooms'] if r[:2]==(1,8))
u.mem_write(0xA673C6,struct.pack('<HH',1,7))
for n in (47,34,35,36):set_bit(7,n)
set_bit(5,140,False)
for lang in (0,1):
    for size in (50,100,150):
        while call('AnnotatedMapTestSize')!=size:
            call('AnnotatedMapTestKeys',1 << (10 if call('AnnotatedMapTestSize')<size else 11));call('AnnotatedMapTestKeys',0)
        for zoom in (50,100):
            set_bit(3,125)
            setup(1,zoom=zoom,ox=-250,oy=-180)
            call('AnnotatedMapTestSet',1,3,lang);call('AnnotatedMapTestDraw',S)
            heads=sprite_quads(t['head_ids'][7]);labels=sprite_quads(room_label[6+lang])
            assert len(heads)==len(labels)==1,(lang,size,zoom,len(heads),len(labels))
            hx,hy=struct.unpack_from('<hh',heads[0],8)
            lx,ly=struct.unpack_from('<hh',labels[0],8);right=struct.unpack_from('<h',labels[0],16)[0]
            assert hx==right+2,(hx,right)
            set_bit(3,125,False);call('AnnotatedMapTestDraw',S)
            first=sprite_quads(t['head_ids'][7]);assert len(first)==1
            assert first[0][8:12]!=heads[0][8:12]
print('Nemesis room badge: both languages, 50/100/150 name sizes, both zooms; first spawn differs OK')
