# Prepares a building picture for Hatchwild.   python3 scripts/hatchwild-building.py farm-1 [scale] [left right tipx tipy]
# (give the base corners by hand, in source pixels, when plants or props stick out past the base)
# Reads art-src/hatchwild/<key>.png (see-through background), finds its base diamond (left and right
# corners in the lower part, front tip at the bottom), cleans the edge haze, sizes it and writes
# prototypes/hatchwild/art/buildings/<key>.png. Prints the entry for BLD_META in the game.
import sys, json
import numpy as np, cv2
from PIL import Image
# Animated sheets:  python3 scripts/hatchwild-building.py mill --anim [fps]
# cuts art-src/hatchwild/mill-anim.png (labelled rows LV 1-3 / LV 4-6 / LV 7+, frames left to right) into
# prototypes/hatchwild/art/buildings/mill-anim.png (one row per level) with every frame's base tip on the
# same spot, and prints the line for BLD_ANIM in the game.
if len(sys.argv) > 2 and sys.argv[2] == '--anim':
  key = sys.argv[1]; fps = float(sys.argv[3]) if len(sys.argv) > 3 else 8
  src = open(__file__.replace('hatchwild-building.py', 'hatchwild-sheet.py')).read().split("if __name__")[0]; g = {}; exec(src, g)
  img = np.array(Image.open(f'art-src/hatchwild/{key}-anim.png').convert('RGBA')); P, _ = g['find_labeled'](img)
  rows = {}
  for p in P: rows.setdefault(p.row, []).append(g['clean'](p.px))
  rows = [rows[r] for r in sorted(rows)]
  def meas(px):
    sol = px[..., 3] > 128; ys = np.where(sol.any(1))[0]; top, bot = ys[0], ys[-1]
    lowr = sol[top + int((bot - top) * .55):]; cols = np.where(lowr.any(0))[0]
    tip = np.where(sol[max(top, bot - int((bot - top) * .06)):bot + 1].any(0))[0].mean()
    return tip, bot, cols[-1] - cols[0]
  H = 300   # every level drawn so its frames are this tall at most
  prepared, spec_rows = [], []
  for fr in rows:
    k = H / max(f.shape[0] for f in fr); base = np.median([meas(f)[2] for f in fr]) * k
    items = []
    for f in fr:
      tx, by, _ = meas(f); im = Image.fromarray(f).resize((round(f.shape[1] * k), round(f.shape[0] * k)), Image.LANCZOS)
      items.append((im, tx * k, by * k))
    prepared.append(items); spec_rows.append({'base': round(float(base), 1), 'n': len(items), 'fps': fps})
  Lm = max(tx for fr in prepared for _, tx, _ in fr); Rm = max(im.width - tx for fr in prepared for im, tx, _ in fr)
  Um = max(by for fr in prepared for _, _, by in fr); Dm = max(im.height - by for fr in prepared for im, _, by in fr)
  W, CH, AX, AY = int(Lm + Rm) + 8, int(Um + Dm) + 8, int(Lm) + 4, int(Um) + 4
  out = Image.new('RGBA', (W * max(len(f) for f in prepared), CH * len(prepared)))
  for r, fr in enumerate(prepared):
    for j, (im, tx, by) in enumerate(fr): out.alpha_composite(im, (round(j * W + AX - tx), round(r * CH + AY - by)))
  out.save(f'prototypes/hatchwild/art/buildings/{key}-anim.png', optimize=True)
  print(f"  {key}: {json.dumps({'cell': [W, CH], 'tip': [AX, AY], 'rows': spec_rows}, separators=(',', ':'))},")
  sys.exit()
# All-levels sheets:  python3 scripts/hatchwild-building.py mill --sheet [scale]
# splits art-src/hatchwild/mill-sheet.png (three buildings left to right, labels under them) into
# mill-1.png, mill-2.png, mill-3.png, then prepares each one.
if len(sys.argv) > 2 and sys.argv[2] == '--sheet':
  key = sys.argv[1]; img = np.array(Image.open(f'art-src/hatchwild/{key}-sheet.png').convert('RGBA'))
  col = (img[..., 3] > 40).any(0); spans, x = [], 0   # buildings are separated by empty columns
  while x < len(col):
    if col[x]:
      x1 = x
      while x1 < len(col) and (col[x1] or (x1 + 12 < len(col) and col[x1:x1 + 12].any())): x1 += 1
      if x1 - x > 120: spans.append((x, x1))
      x = x1
    else: x += 1
  def run(r):
    best = cur = 0
    for v in r: cur = cur + 1 if v else 0; best = max(best, cur)
    return best
  for j, (x0, x1) in enumerate(spans[:3]):
    cell = img[:, x0:x1].copy(); h = cell.shape[0]; ys = np.where((cell[..., 3] > 40).any(1))[0]; bot = ys[-1]
    for y in range(max(0, bot - 140), bot + 1):   # the dark label pill under the building: cut it off
      row = cell[y]
      if run((row[:, :3].max(1) < 70) & (row[:, 3] > 200)) > 60: cell[y - 1:] = 0; break
    a2 = Image.fromarray(cell); a2.crop(a2.getchannel('A').getbbox()).save(f'art-src/hatchwild/{key}-{j + 1}.png')
  import subprocess
  for j in range(3): subprocess.run([sys.executable, __file__, f'{key}-{j + 1}'] + sys.argv[3:4])
  sys.exit()
key = sys.argv[1]; scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1
im = Image.open(f'art-src/hatchwild/{key}.png').convert('RGBA')
a = np.array(im)[..., 3].astype(float); u = np.clip((a - 25) / 210, 0, 1); a = u * u * (3 - 2 * u) * 255
im.putalpha(Image.fromarray(a.astype(np.uint8)))
solid = a > 128; ys = np.where(solid.any(1))[0]; top, bot = ys[0], ys[-1]
low = solid[top + int((bot - top) * .45):]
cols = np.where(low.any(0))[0]; L, R = cols[0], cols[-1]
tip_x = np.where(solid[bot - 3:bot + 1].any(0))[0].mean()
if len(sys.argv) > 6: L, R, tip_x, bot = map(float, sys.argv[3:7])
bb = im.getchannel('A').getbbox(); im = im.crop(bb); H = 560; k = H / im.height
im.resize((round(im.width * k), H), Image.LANCZOS).save(f'prototypes/hatchwild/art/buildings/{key}.png', optimize=True)
print(f"'{key}': {json.dumps({'base': round((R - L) * k, 1), 'tip': [round((tip_x - bb[0]) * k, 1), round((bot - bb[1]) * k, 1)], 'scale': scale}, separators=(', ', ': '))}")
