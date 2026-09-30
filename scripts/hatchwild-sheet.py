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
  'coconeer': {'labeled': True, 'ref': range(0, 6), 'anims': {
      'idle':   {'poses': [0, 1, 2, 3, 4, 5, 4, 3, 2, 1], 'fps': 5},
      'walk':   {'poses': list(range(6, 16)), 'fps': 13},
      'run':    {'poses': list(range(16, 26)), 'fps': 16},   # moving in battle
      'attack': {'poses': list(range(33, 41)), 'fps': 16},   # plays once per throw
      'hurt':   {'poses': list(range(48, 54)), 'fps': 12},   # plays once when hit
      'nap':    {'poses': [54, 55, 56, 57, 58, 59, 58, 57, 56, 55], 'fps': 2.5},
  }},
  'puffling': {'labeled': True, 'ref': range(0, 7), 'anims': {
      'idle': {'poses': [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1], 'fps': 5},
      'walk': {'poses': list(range(7, 15)), 'fps': 11},
      'run':  {'poses': list(range(15, 23)), 'fps': 14},
      'nap':  {'poses': [39, 40, 41, 42, 43, 42, 41, 40], 'fps': 2.5},
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

def poses_labeled(img, label_w=100):
  # rows marked by text labels at the left edge; poses may touch the rows above and below
  a = img[..., 3] > 40; n, lab, st, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8))
  labels = [i for i in range(1, n) if st[i][0] < 20 and st[i][2] > 60 and st[i][3] < 45]
  tops = sorted(int(st[i][1]) for i in labels)
  a = a & ~np.isin(lab, labels); label_w = 0   # erase the label pills, keep poses that reach the left edge
  H = img.shape[0]; out = []
  for r, y0 in enumerate(tops):
    y0 = max(0, y0 - 12); y1 = min(H, tops[r + 1] - 12) if r + 1 < len(tops) else H
    band = a[y0:y1, label_w:]; rgb = np.ascontiguousarray(img[y0:y1, label_w:, :3])
    # split touching poses: seeds from a heavily shrunk mask, then grow them back (watershed)
    core = cv2.erode(band.astype(np.uint8), np.ones((15, 15), np.uint8))
    k, seeds, s2, _ = cv2.connectedComponentsWithStats(core)
    markers = np.zeros(band.shape, np.int32); ids = [i for i in range(1, k) if s2[i][4] > 1500]
    for j, i in enumerate(ids): markers[seeds == i] = j + 2
    markers[~cv2.dilate(band.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)] = 1
    cv2.watershed(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), markers)
    row = []
    for j in range(len(ids)):
      m = (markers == j + 2) & band
      if m.sum() < 5000: continue   # a thrown coconut, a star, some Zzz
      ys, xs = np.where(m); bx, by, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
      row.append((bx, m[by:by1, bx:bx1], img[y0 + by:y0 + by1, label_w + bx:label_w + bx1]))
    row = [(m, px) for _, m, px in sorted(row, key=lambda f: f[0])]
    out.append(row)
  print('rows:', [len(r) for r in out], file=sys.stderr)
  return [f for r in out for f in r]

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
  P = [clean(m, px) for m, px in (poses_labeled(img) if S.get('labeled') else poses(img))]; print(f'{len(P)} poses found', file=sys.stderr)
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
