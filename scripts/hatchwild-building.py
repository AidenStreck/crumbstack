# Prepares a building picture for Hatchwild.   python3 scripts/hatchwild-building.py farm-1 [scale] [left right tipx tipy]
# (give the base corners by hand, in source pixels, when plants or props stick out past the base)
# Reads art-src/hatchwild/<key>.png (see-through background), finds its base diamond (left and right
# corners in the lower part, front tip at the bottom), cleans the edge haze, sizes it and writes
# prototypes/hatchwild/art/buildings/<key>.png. Prints the entry for BLD_META in the game.
import sys, json
import numpy as np
from PIL import Image
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
