# Turns a ChatGPT sprite sheet (see-through background) into animation strips for Hatchwild.
#   python3 scripts/hatchwild-sheet.py pebblet
# Reads art-src/hatchwild/<id>-sheet.png, finds every pose, cleans the coloured fringe AI tools
# leave on the edges, lines the frames up (feet on the ground, body centred) and writes
# prototypes/hatchwild/art/anims/<id>.png (one row per animation). Prints the line for ANIMS in the game.
import sys, json, os
import numpy as np, cv2
from PIL import Image

# Poses are numbered left to right, top to bottom (0 = top-left). ref = poses of the normal standing
# size; scale lets a row drawn smaller on the sheet be brought up to size.
SHEETS = {
  'pebblet': {'ref': range(8, 16), 'anims': {
      'idle': {'poses': list(range(8, 16)), 'fps': 5},
      'walk': {'poses': list(range(0, 8)), 'fps': 11},
      'nap':  {'poses': [34, 35, 36, 37, 36, 35], 'fps': 2, 'scaleFrom': range(27, 31), 'size': .85},
  }},
  'zippy': {'ref': [14, 18, 19, 20], 'anims': {
      'idle': {'poses': [14, 18, 19, 18, 14, 15, 16, 17], 'fps': 4},
      'walk': {'poses': list(range(0, 8)), 'fps': 12},
      'fly':  {'poses': [8, 9, 10, 11, 12, 11, 10, 9], 'fps': 12},   # used for moving in battle
      'nap':  {'poses': [24], 'fps': 1, 'size': .95},
  }},
}
CELL_H = 240   # pixels per frame in the output

def poses(img):
  a = img[..., 3]; m = cv2.morphologyEx((a > 40).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
  n, lab, st, _ = cv2.connectedComponentsWithStats(m)
  bl = [(i, *st[i][:4]) for i in range(1, n) if st[i][4] > 2000]
  rows = []   # group into rows by vertical overlap, then left to right
  for b in sorted(bl, key=lambda b: b[2]):
    for r in rows:
      if b[2] < r['y1'] - 20: r['b'].append(b); r['y1'] = max(r['y1'], b[2] + b[4]); break
    else: rows.append({'b': [b], 'y1': b[2] + b[4]})
  out = []
  for r in rows:
    for i, x, y, w, h in sorted(r['b'], key=lambda b: b[1]): out.append((lab[y:y + h, x:x + w] == i, img[y:y + h, x:x + w]))
  return out

def clean(mask, px):
  a = px[..., 3].astype(np.float32) * mask; solid = (a >= 245).astype(np.uint8)
  solid = cv2.erode(solid, np.ones((3, 3), np.uint8))
  rgb = cv2.cvtColor(px[..., :3], cv2.COLOR_RGB2BGR)
  rgb = cv2.cvtColor(cv2.inpaint(rgb, (1 - solid) * 255, 5, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)   # edge colours come from inside, not the halo
  a = cv2.erode(a, np.ones((3, 3), np.uint8)); a = np.where(a > 200, 255, a)
  return np.dstack([rgb, a.astype(np.uint8)])

def anchor(p):   # feet = lowest solid row; centre = middle of the upper body
  a = p[..., 3] > 128; ys = np.where(a.any(1))[0]; top, bot = ys[0], ys[-1]
  upper = a[top:top + int((bot - top) * .6)]; xs = np.where(upper)[1]
  return xs.mean(), bot, bot - top

def main(cid):
  S = SHEETS[cid]; img = np.array(Image.open(f'art-src/hatchwild/{cid}-sheet.png').convert('RGBA'))
  P = [clean(m, px) for m, px in poses(img)]; print(f'{len(P)} poses found', file=sys.stderr)
  refH = np.median([anchor(P[i])[2] for i in S['ref']]); k = CELL_H * .8 / refH   # a standing pose fills 80% of the cell height
  rows, spec = [], {'cell': [0, CELL_H], 'ref': .8}
  prepared = {}
  for name, A in S['anims'].items():
    f = k * (refH / np.median([anchor(P[i])[2] for i in A['scaleFrom']]) if 'scaleFrom' in A else 1) * A.get('size', 1)
    fr = []
    for i in A['poses']:
      p = P[i]; cx, by, _ = anchor(p); im = Image.fromarray(p).resize((round(p.shape[1] * f), round(p.shape[0] * f)), Image.LANCZOS)
      fr.append((im, cx * f, by * f))
    prepared[name] = fr
  W = int(max(max(max(cx, im.width - cx) for im, cx, _ in fr) for fr in prepared.values()) * 2 + 8)
  spec['cell'][0] = W
  names = list(prepared)
  sheet = Image.new('RGBA', (W * max(len(fr) for fr in prepared.values()), CELL_H * len(names)), (0, 0, 0, 0))
  for r, name in enumerate(names):
    for j, (im, cx, by) in enumerate(prepared[name]):
      sheet.alpha_composite(im, (round(j * W + W / 2 - cx), round(r * CELL_H + CELL_H - 4 - by)))
    spec[name] = {'row': r, 'n': len(prepared[name]), 'fps': S['anims'][name]['fps']}
  os.makedirs('prototypes/hatchwild/art/anims', exist_ok=True); sheet.save(f'prototypes/hatchwild/art/anims/{cid}.png', optimize=True)
  still = prepared['idle'][0][0]; still.crop(still.getchannel('A').getbbox()).save(f'prototypes/hatchwild/art/critters/{cid}.png', optimize=True)
  print(f"  {cid}: {json.dumps(spec, separators=(',', ':'))},")

if __name__ == '__main__': main(sys.argv[1])
