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
  'sparkfinch': {'cut': 120, 'ref': 'idle', 'seqs': [
      S('idle', range(0, 10), 5), S('walk', range(10, 20), 9), S('fly', range(20, 28), 12, reg='torso'), S('cheer', range(28, 37), 11, False, 'sheet'),
      S('zap', range(37, 45), 12, False, 'plant'), S('hurt', range(45, 53), 10, False, 'plant'), S('sleep', range(53, 62), 4)],
    'game': {'idle': 'idle', 'walk': 'walk', 'fly': 'fly', 'attack': 'zap', 'hurt': 'hurt', 'nap': 'sleep'}},
  'squidlet': {'ref': 'idle', 'seqs': [
      S('idle', range(0, 8), 5), S('walk', range(8, 17), 9), S('squirt', range(17, 23), 12, False, 'plant'),
      S('laugh', range(24, 32), 8), S('look', range(32, 40), 5)],
    'skip': {23: 'the ink blob flying on its own (the game draws its own ink shot)'},
    'game': {'idle': 'idle', 'walk': 'walk', 'attack': 'squirt'}},
  'eelectra': {'cut': 120, 'ref': 'idle', 'seqs': [
      S('idle', range(0, 7), 5), S('swim', range(7, 14), 9), S('laugh', range(14, 21), 8), S('blink', range(21, 28), 8, hold=1.2)],
    'game': {'idle': 'idle', 'walk': 'swim'}},
  'cogbot': {'cut': 120, 'ref': 'idle', 'seqs': [
      S('idle', range(0, 8), 5), S('walk', range(8, 16), 9), S('punch', range(16, 20), 12, False, 'plant'),
      S('knockdown', range(23, 31), 10, False, 'plant'), S('sleep', [35], 4)],
    'skip': {20: 'a single shield-block pose', 21: 'a single crouch pose', 22: 'a single cheer pose', 31: 'a single expression pose', 32: 'a single wink',
             33: 'a single laugh', 34: 'a single pointing pose', 36: 'a single happy pose with stars', 37: 'a single sitting pose, eyes closed', 38: 'a single standing pose'},
    'game': {'idle': 'idle', 'walk': 'walk', 'attack': 'punch', 'hurt': ('knockdown', [1, 1, 1, 1, 0]), 'nap': 'sleep'}},   # the full knockdown is too long for every hit
}
GAME_H = 190   # a standing critter is this many pixels tall in the game atlas
SRC, EXP, ATLAS = 'art-src/hatchwild', 'art-src/hatchwild/export', 'prototypes/hatchwild/art'

# ---------- finding poses ----------
class Pose:
  def __init__(s, px, X, Y, row, warn=None): s.px, s.X, s.Y, s.row, s.warn = px, X, Y, row, warn or []

def keep_pieces(a, main, box, margin=.12):
  # small separate pieces (Zzz, dizzy stars, sparks) belong to a pose if they sit over it
  x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0; H, W = a.shape
  X0, Y0, X1, Y1 = max(0, int(x0 - w * margin)), max(0, int(y0 - h * margin)), min(W, int(x1 + w * margin)), min(H, int(y1 + h * .05))
  aw, mw = a[Y0:Y1, X0:X1], main[Y0:Y1, X0:X1]
  n, lab, st, _ = cv2.connectedComponentsWithStats(aw.astype(np.uint8))
  inmain = set(np.unique(lab[mw]).tolist())
  cand = [i for i in range(1, n) if i not in inmain and st[i][4] >= 150 and st[i][0] > 0 and st[i][1] > 0 and st[i][0] + st[i][2] < aw.shape[1] and st[i][1] + st[i][3] < aw.shape[0]]
  keep = main.copy(); keep[Y0:Y1, X0:X1] |= np.isin(lab, cand)
  return keep, 0

def find_plain(img, cut=40):
  a = img[..., 3] > cut; m = cv2.morphologyEx(a.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
  n, lab, st, _ = cv2.connectedComponentsWithStats(m)
  bl = [(i, *st[i][:4]) for i in range(1, n) if st[i][4] > 2000]
  rows = []
  for b in sorted(bl, key=lambda b: b[2]):
    for r in rows:
      if b[2] < r['y1'] - 20: r['b'].append(b); r['y1'] = max(r['y1'], b[2] + b[4]); break
    else: rows.append({'b': [b], 'y1': b[2] + b[4]})
  out = []; loose = img[..., 3] > 40; taken = np.isin(lab, [b[0] for b in bl])
  for r_i, r in enumerate(rows):
    for i, x, y, w, h in sorted(r['b'], key=lambda b: b[1]):
      m, _ = keep_pieces(loose & (~taken | (lab == i)), lab == i, (x, y, x + w, y + h))
      ys, xs = np.where(m); x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
      out.append(Pose(img[y0:y1, x0:x1] * m[y0:y1, x0:x1][..., None], x0, y0, r_i))
  return out, []

def split_touching(comp, seeds):
  # grow each seed outward through the shape only (never across empty space), so a pose keeps its own
  # tail or ear even when it touches the pose next to it
  lab = np.zeros(comp.shape, np.uint16)
  for j, sd in enumerate(seeds): lab[sd] = j + 1
  k = np.ones((3, 3), np.uint8)
  for _ in range(400):
    grown = cv2.dilate(lab, k); new = (lab == 0) & comp & (grown > 0)
    if not new.any(): break
    lab[new] = grown[new]
  return [(lab == j + 1) for j in range(len(seeds))]

def find_labeled(img):
  # rows are marked by text pills at the left edge. Each pose is its own shape on the sheet; where two
  # poses touch, the shared shape is split between their bodies.
  a = img[..., 3] > 40; n, lab, st, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8))
  labels = [i for i in range(1, n) if st[i][0] < 20 and st[i][2] > 60 and st[i][3] < 45]
  tops = sorted(int(st[i][1]) for i in labels); a = a & ~np.isin(lab, labels)
  n, lab, st, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8))
  core = cv2.erode(a.astype(np.uint8), np.ones((15, 15), np.uint8))
  k, sl, s2, cen = cv2.connectedComponentsWithStats(core)
  seeds = [i for i in range(1, k) if s2[i][4] > 1500]
  by_comp = {}
  for i in seeds:
    ys, xs = np.where(sl == i); by_comp.setdefault(int(lab[ys[0], xs[0]]), []).append(i)
  poses = []
  for c, sids in by_comp.items():
    x, y, w, h, _ = st[c]; comp = lab[y:y + h, x:x + w] == c
    parts = [comp] if len(sids) == 1 else split_touching(comp, [sl[y:y + h, x:x + w] == i for i in sids])
    for sid, m in zip(sids, parts):
      if m.sum() < 5000: continue
      cy = cen[sid][1]; row = max([r for r, t in enumerate(tops) if t - 30 <= cy] or [0])
      warn = ['touched the pose next to it on the sheet; split along the narrowest join'] if len(sids) > 1 else []
      poses.append((row, cen[sid][0], m, x, y, warn))
  out = []
  for row, cx, m, x, y, warn in sorted(poses, key=lambda p: (p[0], p[1])):
    full = np.zeros(a.shape, bool); ys, xs = np.where(m); full[ys + y, xs + x] = True
    bx, by_, bx1, by1 = xs.min() + x, ys.min() + y, xs.max() + x + 1, ys.max() + y + 1
    full, _ = keep_pieces(a & ~(np.isin(lab, list(by_comp)) & ~full), full, (bx, by_, bx1, by1))
    ys, xs = np.where(full); bx, by_, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    out.append(Pose(img[by_:by1, bx:bx1] * full[by_:by1, bx:bx1][..., None], bx, by_, row, warn))
  from collections import Counter
  print('rows:', [c for _, c in sorted(Counter(p.row for p in out).items())], file=sys.stderr)
  return out, []

def clean(px):
  # the artwork stays as drawn, glows included. Only the outer 2px rim, where AI tools leave a coloured
  # halo of the old background, takes its colour from just inside the edge; faint haze is faded out.
  a = px[..., 3].astype(np.float32); empty = (a < 25).astype(np.uint8)
  rim = (cv2.dilate(empty, np.ones((5, 5), np.uint8)) > 0) & (a < 200) & (empty == 0)
  rgb = cv2.cvtColor(np.ascontiguousarray(px[..., :3]), cv2.COLOR_RGB2BGR)
  fixed = cv2.cvtColor(cv2.inpaint(rgb, ((rim | (empty > 0)) * 255).astype(np.uint8), 4, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
  rgb = np.where(rim[..., None], fixed, px[..., :3])
  lo, hi = 25, 235; u = np.clip((a - lo) / (hi - lo), 0, 1); a = u * u * (3 - 2 * u) * 255
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
  P, notes = find_labeled(img) if C.get('labeled') else find_plain(img, C.get('cut', 40)); notes = C.get('notes', []) + notes
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
