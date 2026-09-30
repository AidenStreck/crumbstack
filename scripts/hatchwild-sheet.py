# Turns a ChatGPT pose sheet for a Hatchwild critter into clean animation assets.
#   python3 scripts/hatchwild-sheet.py coconeer        (or: all)
#
# Reads art-src/hatchwild/<id>-sheet.png and does, for every sequence listed in SHEETS:
#   - cuts each pose out (labelled rows or plain rows), erasing labels and the coloured fringe AI tools
#     leave on edges; the artwork itself is not redrawn or altered
#   - registers the frames to one anchor so nothing jitters: feet on the ground and the body locked for
#     walks/idles, feet planted for actions, torso centre for flying, and the sheet's own heights for jumps
#   - exports art-src/hatchwild/export/<id>/: each frame as a PNG, one strip per sequence (identical cells),
#     a preview GIF, <id>_manifest.json and a quality report, plus <id>_overview.gif (every sequence at once)
#   - builds the game atlas prototypes/hatchwild/art/anims/<id>.png (only the rows the game plays) and
#     prints the line to paste into ANIMS in the game.
import sys, json, os, glob
import numpy as np, cv2
from PIL import Image, ImageDraw

# Poses are numbered left to right, top to bottom (0 = top-left) as the finder sees them.
# reg: lock = feet on the ground, head/back locked in place (walk, run, idle, blink, sleep)
#      plant = feet planted, body free to lean and recoil (attack, hurt, turn)
#      sheet = heights kept from the sheet, so jumps really rise (jump, land)
#      torso = torso centre (flying)
# scale: for a sequence drawn smaller on the sheet, poses of that sequence's area that match the
#        standing pose, used to bring it back to the same size (game atlas only; exports stay 1:1).
def S(name, poses, fps, loop=True, reg='lock', **kw): return dict(name=name, poses=list(poses), fps=fps, loop=loop, reg=reg, **kw)
SHEETS = {
  'pebblet': {'ref': 'idle', 'seqs': [
      S('walk', range(0, 8), 9), S('idle', range(8, 16), 5), S('turn', range(16, 27), 8, False, 'plant'),
      S('blink', range(27, 31), 10, hold=1.2, scale=range(27, 31)), S('yawn', range(31, 34), 6, False, 'plant', scale=range(27, 31)),
      S('sleep', range(34, 38), 4, scale=range(27, 31)), S('wake', range(38, 40), 6, False, 'plant', scale=range(27, 31))],
    'game': {'idle': 'idle', 'walk': 'walk', 'nap': 'sleep'}},
  'zippy': {'ref': 'idle', 'seqs': [
      S('walk', range(0, 8), 9), S('fly', range(8, 14), 12, reg='torso'), S('idle', range(14, 21), 5),
      S('peck', range(22, 24), 8, False, 'plant'), S('sleep', [24], 4), S('surprise', range(25, 27), 8, False, 'plant')],
    'skip': {21: 'a single back-view pose at the end of the idle row', 27: 'a single fly-away pose seen from behind'},
    'game': {'idle': 'idle', 'walk': 'walk', 'fly': 'fly', 'nap': 'sleep'}},
  'coconeer': {'labeled': True, 'ref': 'idle', 'seqs': [
      S('idle', range(0, 6), 5), S('walk', range(6, 16), 9), S('run', range(16, 26), 12), S('jump', range(26, 33), 11, False, 'sheet'),
      S('throw', range(33, 41), 12, False, 'plant'), S('hit', range(41, 48), 10, False, 'plant'), S('hurt', range(48, 54), 10, False, 'plant'),
      S('sleep', range(54, 60), 4)],
    'notes': ['The two in-flight coconut frames on the THROW row are just the coconut, not Coco, so they are left out; the game draws its own flying coconut.'],
    'game': {'idle': 'idle', 'walk': 'walk', 'run': 'run', 'attack': 'throw', 'hurt': 'hurt', 'nap': 'sleep'}},
  'puffling': {'labeled': True, 'ref': 'idle', 'seqs': [
      S('idle', range(0, 7), 5), S('walk', range(7, 15), 9), S('run', range(15, 23), 12), S('jump', range(23, 31), 11, False, 'sheet'),
      S('blink', range(31, 39), 10, hold=1.2), S('sleep', range(39, 46), 4)],
    'game': {'idle': 'idle', 'walk': 'walk', 'run': 'run', 'nap': ('sleep', range(0, 5))}},   # the last two sleep poses are drawn smaller
}
GAME_H = 190   # a standing critter is this many pixels tall in the game atlas
SRC, EXP, ATLAS = 'art-src/hatchwild', 'art-src/hatchwild/export', 'prototypes/hatchwild/art'

# ---------- finding poses ----------
class Pose:
  def __init__(s, px, X, Y, row, warn=None): s.px, s.X, s.Y, s.row, s.warn = px, X, Y, row, warn or []

def keep_pieces(a, main, box, margin=.12):
  # small separate pieces (Zzz, dizzy stars, sparks) belong to a pose if they sit over it
  x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0; n, lab, st, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8))
  keep = main.copy(); dropped = 0
  for i in range(1, n):
    x, y, bw, bh, ar = st[i]
    if keep[lab == i].any() or ar < 150: continue
    cx, cy = x + bw / 2, y + bh / 2
    if x0 - w * margin < cx < x1 + w * margin and y0 - h * margin < cy < y1 + h * .05: keep |= lab == i
    else: dropped += 1
  return keep, dropped

def find_plain(img):
  a = img[..., 3] > 40; m = cv2.morphologyEx(a.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
  n, lab, st, _ = cv2.connectedComponentsWithStats(m)
  bl = [(i, *st[i][:4]) for i in range(1, n) if st[i][4] > 2000]
  rows = []
  for b in sorted(bl, key=lambda b: b[2]):
    for r in rows:
      if b[2] < r['y1'] - 20: r['b'].append(b); r['y1'] = max(r['y1'], b[2] + b[4]); break
    else: rows.append({'b': [b], 'y1': b[2] + b[4]})
  out = []
  for r_i, r in enumerate(rows):
    for i, x, y, w, h in sorted(r['b'], key=lambda b: b[1]):
      out.append(Pose(img[y:y + h, x:x + w] * (lab[y:y + h, x:x + w] == i)[..., None], x, y, r_i))
  return out, []

def find_labeled(img):
  # rows are marked by text pills at the left edge; poses may touch their neighbours
  a = img[..., 3] > 40; n, lab, st, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8))
  labels = [i for i in range(1, n) if st[i][0] < 20 and st[i][2] > 60 and st[i][3] < 45]
  tops = sorted(int(st[i][1]) for i in labels); a = a & ~np.isin(lab, labels)
  H = img.shape[0]; out, dropped = [], 0
  for r, y0 in enumerate(tops):
    y0 = max(0, y0 - 12); y1 = min(H, tops[r + 1] - 12) if r + 1 < len(tops) else H
    band = a[y0:y1]; rgb = np.ascontiguousarray(img[y0:y1, :, :3])
    core = cv2.erode(band.astype(np.uint8), np.ones((15, 15), np.uint8))
    k, seeds, s2, _ = cv2.connectedComponentsWithStats(core)
    ids = [i for i in range(1, k) if s2[i][4] > 1500]; markers = np.zeros(band.shape, np.int32)
    for j, i in enumerate(ids): markers[seeds == i] = j + 2
    markers[~cv2.dilate(band.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)] = 1
    cv2.watershed(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), markers)
    regions = [(markers == j + 2) & band for j in range(len(ids))]
    row = []
    for j, m in enumerate(regions):
      if m.sum() < 5000: continue
      ys, xs = np.where(m); box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
      others = np.zeros_like(m)
      for jj, mm in enumerate(regions):
        if jj != j: others |= mm
      warn = []
      if (cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & others).sum() > 40: warn.append('touched the pose next to it on the sheet; its edge there may be slightly cut')
      if m[0].any() or m[-1].any(): warn.append('reaches into the row above or below; may be cut at the top or bottom')
      m, d = keep_pieces(band & ~others, m, box); dropped += d
      ys, xs = np.where(m); bx, by, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
      px = img[y0 + by:y0 + by1, bx:bx1] * m[by:by1, bx:bx1][..., None]
      row.append(Pose(px, bx, y0 + by, r, warn))
    out += sorted(row, key=lambda p: p.X)
  notes = []
  return out, notes

def clean(px):
  # the artwork stays as drawn; only the semi-transparent coloured halo around the edge is replaced by
  # the neighbouring edge colour, and the alpha edge is tightened by one pixel
  a = px[..., 3].astype(np.float32); solid = cv2.erode((a >= 245).astype(np.uint8), np.ones((3, 3), np.uint8))
  rgb = cv2.cvtColor(np.ascontiguousarray(px[..., :3]), cv2.COLOR_RGB2BGR)
  fixed = cv2.cvtColor(cv2.inpaint(rgb, (1 - solid) * 255, 5, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
  rgb = np.where(solid[..., None] > 0, px[..., :3], fixed)
  a = cv2.erode(a, np.ones((3, 3), np.uint8)); a = np.where(a > 200, 255, a)
  return np.dstack([rgb, a]).astype(np.uint8)

# ---------- measuring ----------
def feet_row(p):
  rows = np.where(((p[..., 3] > 128).sum(1)) >= 4)[0]; return rows[-1] if len(rows) else p.shape[0] - 1
def height(p): a = (p[..., 3] > 128).any(1); ys = np.where(a)[0]; return feet_row(p) - ys[0]
def upper_x(p):
  a = p[..., 3] > 128; ys = np.where(a.any(1))[0]; top, bot = ys[0], feet_row(p)
  return np.where(a[top:top + int((bot - top) * .6)])[1].mean()
def feet_x(p):
  a = p[..., 3] > 128; b = feet_row(p); top = np.where(a.any(1))[0][0]
  return np.where(a[max(top, b - int((b - top) * .1)):b + 1])[1].mean()
def torso(p):
  a = (p[..., 3] > 128).astype(np.uint8); d = cv2.distanceTransform(a, cv2.DIST_L2, 5)
  ys, xs = np.where(d > d.max() * .55); return xs.mean(), ys.mean()

def upper_img(p, ax, ay, S=512):
  c = np.zeros((S, S), np.float32); ox, oy = round(S / 2 - ax), round(S * .8 - ay)
  a = p[..., 3].astype(np.float32) / 255; g = p[..., :3].mean(2) * a
  top = np.where(a.any(1))[0][0]; g[int(top + (feet_row(p) - top) * .6):] = 0
  h, w = g.shape; x0, y0 = max(0, ox), max(0, oy); x1, y1 = min(S, ox + w), min(S, oy + h)
  if x1 > x0 and y1 > y0: c[y0:y1, x0:x1] = g[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
  return c

def register(frames, reg, poses):
  # returns the anchor point (ax, ay) inside each frame
  if reg == 'torso': return [torso(p) for p in frames]
  if reg == 'plant': return [(feet_x(p), feet_row(p)) for p in frames]
  anc = [(upper_x(p), feet_row(p)) for p in frames]
  if reg == 'sheet':   # keep the heights the sheet drew: the lowest pose stands on the ground
    base = max(ps.Y + feet_row(p) for ps, p in zip(poses, frames)); anc = [(ax, base - ps.Y) for (ax, _), ps in zip(anc, poses)]
  if len(frames) > 1:   # lock the head and back to the first frame so the body doesn't jitter sideways
    win = cv2.createHanningWindow((512, 512), cv2.CV_32F); ref = upper_img(frames[0], *anc[0]) * win
    for i in range(1, len(frames)):
      (dx, dy), resp = cv2.phaseCorrelate(ref, upper_img(frames[i], *anc[i]) * win)
      if resp > .05 and abs(dx) < frames[i].shape[1] * .15: anc[i] = (anc[i][0] + dx, anc[i][1])
  return anc

def qc(name, frames, anc, seq, poses):
  out = []
  for i, ps in enumerate(poses):
    for w in ps.warn: out.append(f'frame {i + 1} {w}')
  if seq['reg'] in ('lock', 'sheet') and len(frames) > 1:
    hs = [height(p) for p in frames]; v = (max(hs) - min(hs)) / np.median(hs)
    if v > .12 and seq['reg'] == 'lock': out.append(f'size changes by {v:.0%} between frames (the sheet drew some frames bigger)')
    win = cv2.createHanningWindow((512, 512), cv2.CV_32F); ups = [upper_img(p, *a) * win for p, a in zip(frames, anc)]
    worst = max(abs(cv2.phaseCorrelate(ups[i], ups[i + 1])[0][0]) for i in range(len(ups) - 1))
    if worst > frames[0].shape[1] * .04: out.append(f'the head/back still shifts up to {worst:.0f}px between frames')
  def diff(p, q, a, b):
    S = 512; c = []
    for f, (ax, ay) in ((p, a), (q, b)):
      im = Image.new('RGBA', (S, S)); im.alpha_composite(Image.fromarray(f), (round(S / 2 - ax), round(S * .8 - ay))); c.append(np.array(im).astype(np.float32))
    return np.abs(c[0] - c[1]).mean()
  if len(frames) > 2:
    ds = [diff(frames[i], frames[i + 1], anc[i], anc[i + 1]) for i in range(len(frames) - 1)]
    for i, d in enumerate(ds):
      if d < np.median(ds) * .15: out.append(f'frames {i + 1} and {i + 2} are nearly identical')
    if seq['loop']:
      dl = diff(frames[-1], frames[0], anc[-1], anc[0])
      if dl > max(ds) * 1.5: out.append('the loop jumps noticeably from the last frame back to the first')
  return out

# ---------- output ----------
def layout(frames, anc, f=1, pad=6):
  L = max(ax * f for ax, _ in anc); R = max((p.shape[1] - ax) * f for p, (ax, _) in zip(frames, anc))
  U = max(ay * f for _, ay in anc); D = max((p.shape[0] - ay) * f for p, (_, ay) in zip(frames, anc))
  return int(np.ceil(L + R)) + 2 * pad, int(np.ceil(U + D)) + 2 * pad, int(np.ceil(L)) + pad, int(np.ceil(U)) + pad

def place(p, ax, ay, W, H, AX, AY, f=1):
  im = Image.fromarray(p)
  if f != 1: im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
  c = Image.new('RGBA', (W, H), (0, 0, 0, 0)); c.alpha_composite(im, (round(AX - ax * f), round(AY - ay * f))); return c

def gif(cells, path, fps, hold=0, loop=True, bg=(236, 240, 232)):
  sc = min(1, 256 / max(cells[0].size)); out = []
  for c in cells:
    b = Image.new('RGBA', c.size, bg + (255,)); b.alpha_composite(c); b = b.convert('RGB')
    out.append(b.resize((round(b.width * sc), round(b.height * sc)), Image.LANCZOS) if sc < 1 else b)
  dur = [round(1000 / fps)] * len(out)
  if hold: dur[0] = round(hold * 1000)
  if not loop: dur[-1] = 900   # pause on the last frame so a one-shot is readable
  out[0].save(path, save_all=True, append_images=out[1:], duration=dur, loop=0)

def main(cid):
  C = SHEETS[cid]; img = np.array(Image.open(f'{SRC}/{cid}-sheet.png').convert('RGBA'))
  P, notes = (find_labeled if C.get('labeled') else find_plain)(img); notes = C.get('notes', []) + notes
  for p in P: p.px = clean(p.px)
  used = {i for s in C['seqs'] for i in s['poses']}
  for i in range(len(P)):
    if i not in used: notes.append(f'pose {i} not used: ' + C.get('skip', {}).get(i, 'not part of a clear sequence'))
  out = f'{EXP}/{cid}'; os.makedirs(out, exist_ok=True)
  for f in glob.glob(f'{out}/*'): os.remove(f)
  refH = np.median([height(P[i].px) for i in next(s for s in C['seqs'] if s['name'] == C['ref'])['poses']])
  man = {'character': cid, 'source': f'{cid}-sheet.png', 'poses_found': len(P), 'notes': notes, 'animations': []}
  done = {}
  for seq in C['seqs']:
    poses = [P[i] for i in seq['poses']]; frames = [p.px for p in poses]; anc = register(frames, seq['reg'], poses)
    W, H, AX, AY = layout(frames, anc); cells = [place(p, ax, ay, W, H, AX, AY) for p, (ax, ay) in zip(frames, anc)]
    n = seq['name']
    for j, c in enumerate(cells): c.save(f'{out}/{cid}_{n}_{j + 1:02d}.png', optimize=True)
    strip = Image.new('RGBA', (W * len(cells), H))
    for j, c in enumerate(cells): strip.alpha_composite(c, (j * W, 0))
    strip.save(f'{out}/{cid}_{n}_spritesheet.png', optimize=True)
    gif(cells, f'{out}/{cid}_{n}_preview.gif', seq['fps'], seq.get('hold', 0), seq['loop'])
    sf = refH / np.median([height(P[i].px) for i in seq['scale']]) if 'scale' in seq else 1
    issues = qc(n, frames, anc, seq, poses)
    man['animations'].append({'name': n, 'frames': len(cells), 'frame_width': W, 'frame_height': H, 'fps': seq['fps'], 'loop': seq['loop'],
      **({'hold_first_frame_s': seq['hold']} if seq.get('hold') else {}),
      'anchor': {'x': AX, 'y': AY, 'type': {'lock': 'feet on the ground, head/back locked', 'plant': 'feet planted', 'sheet': 'ground line of the lowest pose (heights from the sheet)', 'torso': 'torso centre'}[seq['reg']]},
      'frame_order': [f'{cid}_{n}_{j + 1:02d}.png' for j in range(len(cells))], 'source_poses': seq['poses'],
      **({'drawn_at_scale': round(1 / sf, 2)} if sf != 1 else {}), 'checks': issues or ['ok']})
    done[n] = (frames, anc, sf, seq)
  json.dump(man, open(f'{out}/{cid}_manifest.json', 'w'), indent=2)
  # overview: every sequence playing side by side
  seqs = list(done); tiles = []
  for n in seqs:
    frames, anc, sf, seq = done[n]; W, H, AX, AY = layout(frames, anc, sf * 170 / refH)
    tiles.append((n, [place(p, ax, ay, W, H, AX, AY, sf * 170 / refH) for p, (ax, ay) in zip(frames, anc)], seq))
  TW, TH, cols = max(t[1][0].width for t in tiles), max(t[1][0].height for t in tiles) + 26, 4
  rows = (len(tiles) + cols - 1) // cols; ov = []
  for k in range(60):
    t = k / 20; im = Image.new('RGB', (TW * cols, TH * rows), (236, 240, 232)); d = ImageDraw.Draw(im)
    for j, (n, cells, seq) in enumerate(tiles):
      x, y = (j % cols) * TW, (j // cols) * TH; fi = int(t * seq['fps']); fi = fi % len(cells) if seq['loop'] else min(fi % (len(cells) + 8), len(cells) - 1)
      im.paste(cells[fi], (x + (TW - cells[fi].width) // 2, y + 22), cells[fi]); d.text((x + 8, y + 6), n, fill=(60, 50, 40))
    ov.append(im)
  ov[0].save(f'{out}/{cid}_overview.gif', save_all=True, append_images=ov[1:], duration=50, loop=0)
  # game atlas: only the rows the game plays, one shared cell with one anchor
  G = C['game']; f0 = GAME_H / refH; parts = []
  for gname, sname in G.items():
    sub = None
    if isinstance(sname, tuple): sname, sub = sname
    frames, anc, sf, seq = done[sname]
    if sub is not None: frames, anc = [frames[i] for i in sub], [anc[i] for i in sub]
    parts.append((gname, frames, anc, f0 * sf, seq))
  L = max(max(ax * f for ax, _ in anc) for _, _, anc, f, _ in parts); R = max(max((p.shape[1] - ax) * f for p, (ax, _) in zip(fr, anc)) for _, fr, anc, f, _ in parts)
  U = max(max(ay * f for _, ay in anc) for _, _, anc, f, _ in parts); D = max(max((p.shape[0] - ay) * f for p, (_, ay) in zip(fr, anc)) for _, fr, anc, f, _ in parts)
  pad = 4; W, H, AX, AY = int(L + R) + 2 * pad, int(U + D) + 2 * pad, int(L) + pad, int(U) + pad
  atlas = Image.new('RGBA', (W * max(len(p[1]) for p in parts), H * len(parts))); spec = {'cell': [W, H], 'anchor': [AX, AY], 'h': GAME_H}
  for r, (gname, frames, anc, f, seq) in enumerate(parts):
    for j, (p, (ax, ay)) in enumerate(zip(frames, anc)): atlas.alpha_composite(place(p, ax, ay, W, H, AX, AY, f), (j * W, r * H))
    spec[gname] = {'row': r, 'n': len(frames), 'fps': seq['fps'], **({'torso': 1} if seq['reg'] == 'torso' else {})}
  os.makedirs(f'{ATLAS}/anims', exist_ok=True); atlas.save(f'{ATLAS}/anims/{cid}.png', optimize=True)
  frames, anc, sf, _ = done[G['idle'] if isinstance(G['idle'], str) else G['idle'][0]]; st = place(frames[0], *anc[0], W, H, AX, AY, f0 * sf); st.crop(st.getchannel('A').getbbox()).save(f'{ATLAS}/critters/{cid}.png', optimize=True)
  # report
  print(f'== {cid}: {len(P)} poses found', file=sys.stderr)
  for a in man['animations']: print(f"  {a['name']:<9} {a['frames']:>2} frames {a['frame_width']}x{a['frame_height']} {a['fps']}fps {'loop' if a['loop'] else 'once'}  " + '; '.join(a['checks']), file=sys.stderr)
  for n in notes: print('  note:', n, file=sys.stderr)
  print(f"  {cid}: {json.dumps(spec, separators=(',', ':'))},")

if __name__ == '__main__':
  for c in (SHEETS if sys.argv[1] == 'all' else [sys.argv[1]]): main(c)
