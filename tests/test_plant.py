"""Disused Plant native floor gates, secret locker lifecycle and missing HD header."""
import itertools, json, runpy, struct, sys, zlib
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_room_data import const_items
from decode_map import SIZES, tim, image
m=json.loads((ROOT/'data/overlay.json').read_text())
steam=[x for x in m['markers'] if x['rdt']=='502']
assert {(r['idx'],r['name']) for r in m['rooms'] if r['page']==4 and r['idx'] in (2,17)}=={(2,'Steam Room'),(17,'Weapons Storage')}
assert not any(x['kind']=='lock' and x.get('item')==const_items()['ITEM_DUMMY_KEY'] for x in m['markers'])
assert all(x['idx']==2 for x in steam if x.get('aot') in range(10,16))
assert all(x['idx']==17 for x in steam if x.get('item') in (10,24,127))
assert all(not any(b==4 and n==31 for cl in x['guard'] for b,n,v in cl) for x in steam)
rocket=next(x for x in steam if x.get('item')==10)
assert rocket['guard']==[[[9,34,1]]],rocket
blob=(ROOT/'local/extracted/DATA_J/ETC2/MAP_J.MAP').read_bytes()
seg=blob[sum(SIZES[:4]):sum(SIZES[:5])]; h=struct.unpack_from('<9I',seg)
a=np.asarray(image(tim(seg[h[7]:]))).copy(); v=np.rint(a[:,:,:3].astype(float)*31/255).astype('uint8');a[:,:,:3]=(v<<3)|(v>>2)
key=f'{zlib.crc32(a[:,:,[2,1,0,3]].tobytes()):08X}'
assert key=='4D420B84'
hd=Image.open(ROOT/f'build/hires/misc/{key}.webp').convert('RGBA')
ref=Image.open(ROOT/'assets/map/clock-header-reference.webp').convert('RGBA')
assert hd.size==(1024,160)
assert np.array_equal(np.asarray(hd.crop((128,64,704,160))).astype('uint16') * np.asarray(hd.crop((128,64,704,160)))[:,:,3:4], np.asarray(ref.crop((128,64,704,160))).astype('uint16') * np.asarray(ref.crop((128,64,704,160)))[:,:,3:4])
assert np.array_equal(np.asarray(hd.crop((0,0,128,160)))[:,:,:3] * (np.asarray(hd.crop((0,0,128,160)))[:,:,3:4]>0), np.asarray(ref.crop((0,0,128,160)))[:,:,:3] * (np.asarray(ref.crop((0,0,128,160)))[:,:,3:4]>0))

native=runpy.run_path(str(ROOT/'tests/test_native.py'))
u,run,setup,bit,visit=[native[k] for k in ('u','run','setup','set_bit','visit')]
for i in range(64):visit(4,i,False)
for i in (2,17):visit(4,i)
# Only Steam Room and its split floor are visited; explicitly activate native floor selection.
for aj,fallen,opened,floor in itertools.product((False,True),repeat=4):
    for bank,flag,value in ((3,239,fallen),(9,34,opened),(4,31,True),(8,89,False),(8,90,False),(8,104,False),(9,33,False),(3,213,False)):
        bit(bank,flag,value)
    u.mem_write(0xA673C6,struct.pack('<HH',4,2))
    setup(4,100,-330,-185)
    u.mem_write(native['S']+0xAD,bytes((1,int(floor))))
    counts=run(4,scope=1,aj=aj)
    assert counts[3]==int(not floor and opened),(aj,fallen,opened,floor,counts)
    assert counts[6]==(7 if floor else int(not opened)),(aj,fallen,opened,floor,counts)
    assert counts[7]==2,(aj,fallen,opened,floor,counts)
    assert counts['room']==1,counts
# The elevator's room-local floor flag must not move remote pickups between levels.
bit(3,239,True);u.mem_write(0xA673C6,struct.pack('<HH',4,6))
for opened in (False,True):
    bit(9,34,opened)
    setup(4,100,-330,-185);u.mem_write(native['S']+0xAD,bytes((1,0)))
    counts=run(4,scope=1)
    assert counts[3]==int(opened) and counts[6]==int(not opened) and counts[7]==2,counts
print('Plant: two floor labels; native floor/item/puzzle/locker lifecycle in both datasets; dummy locks absent; HD title/scale key verified')

# The locked rocket acquisition puzzle uses the reward weapon icon under key5.
bit(9,34,False)
setup(4,100,-325,-199);u.mem_write(native['S']+0xAD,bytes((1,0)))
counts=run(4,scope=1,toggles=(1,0,0,0,0,1,0,0))
assert counts[6]==1 and counts[3]==0,counts
base,count=native['prims']()
assert count==15,count
q=bytes(u.mem_read(base,40))
pg,x,y,w,h=native['sprites'][native['item_ids'][10]]
assert (struct.unpack_from('<H',q,22)[0]-1,q[12],q[13])==(pg,x,y)
bit(9,34,True)
assert run(4,scope=1,toggles=(1,0,0,0,0,1,0,0))[6]==0
assert run(4,scope=1,toggles=(1,0,0,1,0,0,0,0))[3]==1
print('Rocket reward icon: actual UV on key5 before locker unlock, key3 pickup afterwards OK')
