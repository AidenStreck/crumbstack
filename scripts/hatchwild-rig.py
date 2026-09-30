# Cuts a Hatchwild critter picture into animatable parts (body, head, legs) so the game can
# move its legs, bob its head, breathe and blink.
#   python3 scripts/hatchwild-rig.py pebblet
# Reads art-src/hatchwild/<id>.png and the part outlines in RIGS below (in the source picture's
# pixels), writes prototypes/hatchwild/art/rigs/<id>/*.png and prints the line to paste into RIGS
# in the game (p3d: `const RIGS`).
import sys, json, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter

RIGS = {
  'pebblet': {
    'head': {'poly': [(725,450),(800,330),(900,282),(1060,282),(1200,378),(1242,500),(1218,622),(1150,702),(1000,738),(850,722),(760,650),(718,560)],
             'pivot': (840,660), 'behind': [(700,420),(820,300),(1010,262),(1000,500),(900,720),(740,730)],
             'eyes': [((945,528),(60,42)), ((1188,580),(28,34))]},
    'legs': [  # drawn back to front; phase: which pair steps together
      {'poly': [(150,800),(215,748),(400,752),(432,800),(432,1032),(138,1032)], 'pivot': (290,770), 'phase': 0},
      {'poly': [(898,765),(1000,738),(1105,752),(1172,850),(1182,1038),(893,1038)], 'pivot': (1030,770), 'phase': 0},
      {'poly': [(560,742),(700,700),(812,760),(836,900),(832,1088),(498,1088),(505,900)], 'pivot': (680,745), 'phase': 1},
    ],
    'height': 400,
  },
}

def poly_mask(size, poly, blur=2.5):
  m = Image.new('L', size, 0); ImageDraw.Draw(m).polygon(poly, fill=255)
  return np.array(m.filter(ImageFilter.GaussianBlur(blur)), dtype=np.float32) / 255

def main(cid):
  R = RIGS[cid]; src = Image.open(f'art-src/hatchwild/{cid}.png').convert('RGBA')
  a0 = np.array(src.getchannel('A')); a0 = np.where(a0 >= 248, 255, np.where(a0 < 24, 0, a0)).astype(np.uint8)
  src.putalpha(Image.fromarray(a0)); bb = src.getchannel('A').getbbox(); src = src.crop(bb)
  sh = lambda pts: [(x - bb[0], y - bb[1]) for x, y in pts]; W, H = src.size
  rgba = np.array(src).astype(np.float32); alpha = rgba[..., 3] / 255
  parts = [('head', R['head'])] + [(f'leg{i}', L) for i, L in enumerate(R['legs'])]
  # body: fill in what the moving parts were covering
  hole = np.zeros((H, W), np.uint8)
  for _, P in parts: hole = np.maximum(hole, (poly_mask((W, H), sh(P['poly']), 0) > .5).astype(np.uint8))
  hole = cv2.dilate(hole, np.ones((9, 9), np.uint8))
  bgr = cv2.cvtColor(rgba[..., :3].astype(np.uint8), cv2.COLOR_RGB2BGR)
  src_mask = np.maximum(hole, (alpha < .5).astype(np.uint8))   # never borrow colour from the empty background
  filled = cv2.cvtColor(cv2.inpaint(bgr, src_mask * 255, 18, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
  keep = np.zeros((H, W), np.float32)   # where the body stays solid behind a part
  keep = np.maximum(keep, poly_mask((W, H), sh(R['head']['behind']), 6))
  for L in R['legs']:
    top = min(p[1] for p in L['poly']) - bb[1]; ramp = np.clip((top + 90 - np.arange(H)) / 50, 0, 1)[:, None]
    keep = np.maximum(keep, poly_mask((W, H), sh(L['poly']), 6) * ramp)
  inside = np.zeros((H, W), np.float32)   # only replace what's inside the parts' outlines
  for _, P in parts: inside = np.maximum(inside, poly_mask((W, H), sh(P['poly']), 1.5))
  body = rgba.copy(); body[..., :3] = filled * inside[..., None] + rgba[..., :3] * (1 - inside[..., None])
  body_a = keep * inside + alpha * (1 - inside)
  k = R['height'] / H; out = f'prototypes/hatchwild/art/rigs/{cid}'; os.makedirs(out, exist_ok=True)
  def save(name, arr, a, box=None):
    arr = arr.copy(); arr[..., 3] = np.clip(a, 0, 1) * 255
    im = Image.fromarray(arr.astype(np.uint8), 'RGBA'); box = box or im.getchannel('A').getbbox(); im = im.crop(box)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS); im.save(f'{out}/{name}.png', optimize=True)
    return [round(box[0] * k, 1), round(box[1] * k, 1)]
  spec = {'w': round(W * k, 1), 'h': round(H * k, 1), 'body': save('body', body, body_a), 'parts': []}
  for name, P in parts:
    m = cv2.GaussianBlur(cv2.dilate((poly_mask((W, H), sh(P['poly']), 0) > .5).astype(np.float32), np.ones((7, 7), np.uint8)), (0, 0), 1.5) * alpha; box = Image.fromarray((m * 255).astype(np.uint8)).getbbox()
    px, py = sh([P['pivot']])[0]; e = {'n': name, 'at': save(name, rgba, m, box), 'pv': [round(px * k, 1), round(py * k, 1)]}
    if name == 'head':   # a blink frame: eyes painted over with eyelid skin and a lash line
      eye = np.zeros((H, W), np.uint8)
      for (cx, cy), (rx, ry) in P['eyes']: cv2.ellipse(eye, (cx - bb[0], cy - bb[1]), (rx, ry), 0, 0, 360, 255, -1)
      closed = cv2.cvtColor(cv2.inpaint(bgr, eye, 25, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB).astype(np.float32)
      em = cv2.GaussianBlur(eye.astype(np.float32) / 255, (0, 0), 3)[..., None]
      blink = rgba.copy(); blink[..., :3] = rgba[..., :3] * (1 - em) + closed * em
      img = Image.fromarray(blink.astype(np.uint8), 'RGBA'); d = ImageDraw.Draw(img)
      for (cx, cy), (rx, ry) in P['eyes']:
        cx -= bb[0]; cy -= bb[1]; d.arc((cx - rx, cy - ry * .6, cx + rx, cy + ry * .9), 20, 160, fill=(70, 58, 44, 255), width=max(4, rx // 7))
      save('blink', np.array(img).astype(np.float32), m, box)
    else: e['ph'] = P['phase']
    spec['parts'].append(e)
  print(f"  {cid}: {json.dumps(spec, separators=(',', ':'))},")

if __name__ == '__main__': main(sys.argv[1])
