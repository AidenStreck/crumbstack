// Records vertical gameplay clips (1080x1920, 30fps MP4) for TikTok / Reels / Shorts into marketing/clips/.
// A small bot plays the real game. Time is simulated frame by frame, so the video is perfectly smooth
// no matter how slow the recording machine is.
// Run: node scripts/build.mjs && node scripts/clips.cjs [clip-id ...]   (needs Playwright + Chromium + ffmpeg)
const fs = require('fs'), path = require('path'), http = require('http'), { execFileSync } = require('child_process');
const { chromium } = require('playwright');

const root = path.join(__dirname, '..'), www = path.join(root, 'www'), out = path.join(root, 'marketing/clips');
const FPS = 30, STEP = 1000 / FPS;
const TYPES = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.png':'image/png', '.woff':'font/woff', '.json':'application/json', '.webmanifest':'application/manifest+json' };

// Each clip: level, seconds, a hook shown at the start, and optional setup tweaks.
const CLIPS = [
  { id: 'lunch-rush', level: 4, seconds: 15, hook: 'POV: the lunch rush<br>just hit' },
  { id: 'vip-patience', level: 13, seconds: 15, hook: 'He tips double.<br>He has zero patience.', vip: true },
  { id: 'dont-topple', level: 18, seconds: 15, hook: 'Don\'t. Let. It.<br>Topple.', long: true },
];

const SAVE = { unlocked: 24, stars: {}, best: {}, coins: 500, inv: { magnet: 0, plate: 0, heart: 0 },
  gifted: { magnet: true, plate: true, heart: true }, giftDay: '', sound: { music: false, sfx: false } };

// Virtual clock: the game only moves when we call __step().
const CLOCK = `(() => {
  let now = 0, q = [], timers = [], id = 0;
  performance.now = () => now;
  window.requestAnimationFrame = cb => { q.push(cb); return ++id; };
  window.setTimeout = (fn, ms) => { timers.push({ at: now + (ms || 0), fn }); return ++id; };
  window.clearTimeout = () => {};
  window.__step = ms => {
    now += ms;
    const due = timers.filter(t => t.at <= now); timers = timers.filter(t => t.at > now); due.forEach(t => { try { t.fn(); } catch (e) {} });
    const cbs = q; q = []; cbs.forEach(cb => cb(now));
  };
})();`;

// The bot: chase the ingredient the ticket needs, grab power-ups when nothing is needed, and only dodge
// wrong food or flies that are about to land on the plate.
const BOT = `(() => {
  const c = window.__cs, S = c.S; if (!S || !S.order || S.over) return;
  const pw = Math.min(118, c.W * .3) * (S.boost && S.boost.plate ? 1.22 : 1);
  const H = { bunTop:.38, patty:.21, cheese:.1, lettuce:.13, tomato:.12, onion:.1, bunBottom:.2 };
  let top = c.plateY; S.stack.forEach(t => top -= H[t] * pw * .9);
  const need = S.order[S.idx];
  const falling = S.items.filter(i => i.state === 'fall' && i.y < top);
  const needed = falling.filter(i => i.kind === 'ing' && i.type === need).sort((a, b) => b.y - a.y);
  const tokens = falling.filter(i => i.kind === 'token').sort((a, b) => b.y - a.y);
  let target = needed.length ? needed[0].x : tokens.length ? tokens[0].x : S.targetX;
  const soon = falling.filter(i => ((i.kind === 'ing' && i.type !== need) || i.kind === 'fly') && top - i.y < 70);
  for (const b of soon) {
    if (Math.abs(b.x - target) < pw * .6) target = b.x + (target >= b.x ? 1 : -1) * pw * .7;
  }
  target = Math.max(pw / 2, Math.min(c.W - pw / 2, target));
  const maxStep = 12, d = target - S.targetX;
  S.targetX += Math.max(-maxStep, Math.min(maxStep, d));
})();`;

const server = http.createServer((req, res) => {
  let f = path.join(www, decodeURIComponent(req.url.split('?')[0])); if (f.endsWith('/')) f += 'index.html';
  fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); res.end(); } else { res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); res.end(d); } });
});

const OVERLAY_CSS = `
#mk-hook,#mk-end{position:fixed;left:0;right:0;z-index:99;text-align:center;font-family:"Lilita One",sans-serif;pointer-events:none}
#mk-hook{top:34%;font-size:34px;line-height:1.1;color:#fff;padding:0 18px;text-shadow:0 3px 0 #A21E53,0 0 22px rgba(0,0,0,.55);transition:opacity .3s}
#mk-end{inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;background:rgba(26,16,60,.9)}
#mk-end img{width:110px;height:110px;border-radius:26px;box-shadow:0 8px 24px rgba(0,0,0,.4)}
#mk-end b{font-weight:400;font-size:44px;color:#FFD25E;text-shadow:0 4px 0 #B8531F}
#mk-end span{font-family:"Nunito",sans-serif;font-weight:900;font-size:20px;color:#fff;background:#D63A78;border-radius:999px;padding:6px 18px}
#mk-end small{font-family:"Nunito",sans-serif;font-weight:800;font-size:16px;color:#E9E3FF}`;

(async () => {
  const only = process.argv.slice(2);
  await new Promise(r => server.listen(8798, r));
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const RAW = 40; // seconds recorded; the best stretch is kept
  for (const clip of CLIPS.filter(c => !only.length || only.includes(c.id))) {
  for (let attempt = 1; attempt <= 4; attempt++) {
    const page = await browser.newPage({ viewport: { width: 360, height: 640 }, deviceScaleFactor: 3 });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(CLOCK);
    await page.addInitScript(s => { try { localStorage.setItem('crumbstack-save-v2', s); } catch (e) {} }, JSON.stringify(SAVE));
    await page.goto('http://localhost:8798/#shots');
    for (let i = 0; i < 10; i++) await page.evaluate(ms => __step(ms), STEP);
    await page.evaluate(({ level, long }) => {
      __cs.start(level, {});
      const S = __cs.S;
      if (long) { S.order = ['bunBottom','patty','cheese','lettuce','tomato','onion','patty','bunTop']; S.patMax *= 1.6; __cs.renderTicket(); }
      window.__lastOrder = -1;
    }, { level: clip.level, long: !!clip.long });
    const cdp = await page.context().newCDPSession(page); await cdp.send('Animation.enable');
    const dir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'clip-'));
    const rawFrames = RAW * FPS, served = [];
    const t0 = Date.now();
    for (let f = 0; f < rawFrames; f++) {
      const st = await page.evaluate(({ bot, ms, vip }) => {
        const S = __cs.S;
        if (vip && S.orderNo !== window.__lastOrder && !S.over) { window.__lastOrder = S.orderNo; S.cust = __cs.newCustomer(true); __cs.renderTicket(); }
        if (!S.over) eval(bot); __step(ms);
        return { served: S.served, over: S.over };
      }, { bot: BOT, ms: STEP, vip: !!clip.vip });
      served.push(st.served);
      await page.screenshot({ path: path.join(dir, `f${String(f).padStart(4, '0')}.jpg`), type: 'jpeg', quality: 92 });
      if (f === 5) await cdp.send('Animation.setPlaybackRate', { playbackRate: Math.min(1, STEP / ((Date.now() - t0) / 6)) });
      if (st.over) break;
    }
    // Pick the stretch with the most burgers served, preferring one that ends just after a serve.
    const len = Math.round(clip.seconds * FPS), n = served.length;
    let best = 0, bestScore = -1;
    for (let a = 0; a + len <= n; a += 5) {
      const b = a + len - 1;
      let score = served[b] - served[a];
      const lastServe = served.lastIndexOf(served[b], b) ; // first frame where final count was reached
      if (served[b] > served[a] && b - served.indexOf(served[b]) < 45) score += .5;
      if (score > bestScore) { bestScore = score; best = a; }
    }
    if ((n < len || bestScore < 1) && attempt < 4) {
      console.log(`${clip.id}: take ${attempt} had no served burger, recording again`);
      fs.rmSync(dir, { recursive: true, force: true }); await page.close(); continue;
    }
    // Overlays: hook text (first 2.6s) and an end card, rendered as transparent PNGs with the game's font.
    const ov = await browser.newPage({ viewport: { width: 360, height: 640 }, deviceScaleFactor: 3 });
    const font = n => fs.readFileSync(path.join(root, 'fonts', n)).toString('base64');
    const base = `<style>@font-face{font-family:"Lilita One";src:url(data:font/woff;base64,${font('lilita-one-400.woff')})}
      @font-face{font-family:"Nunito";font-weight:900;src:url(data:font/woff;base64,${font('nunito-900.woff')})}
      html,body{margin:0;background:transparent}${OVERLAY_CSS}</style>`;
    await ov.setContent(base + `<div id="mk-hook">${clip.hook}</div>`);
    await ov.screenshot({ path: path.join(dir, 'hook.png'), omitBackground: true });
    const icon = fs.readFileSync(path.join(root, 'resources/icon-512.png')).toString('base64');
    await ov.setContent(base + `<div id="mk-end"><img src="data:image/png;base64,${icon}" alt=""><b>Crumbstack</b><span>Free. No ads.</span><small>Play free · link in bio</small></div>`);
    await ov.screenshot({ path: path.join(dir, 'end.png'), omitBackground: true });
    await ov.close();
    const dur = clip.seconds, endDur = 2.2;
    // Two versions: with the hook text (for posting as-is) and "-clean" without it (for voiceover videos with captions).
    for (const clean of [false, true]) {
    const mp4 = path.join(out, clip.id + (clean ? '-clean' : '') + '.mp4');
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error',
      '-framerate', String(FPS), '-start_number', String(best), '-i', path.join(dir, 'f%04d.jpg'),
      '-loop', '1', '-i', path.join(dir, 'hook.png'), '-loop', '1', '-i', path.join(dir, 'end.png'),
      '-filter_complex',
      `[0:v]trim=end_frame=${len},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=${endDur}[g];` +
      `[1:v]format=rgba,fade=t=out:st=2.3:d=0.3:alpha=1[h];` +
      `[2:v]format=rgba,fade=t=in:st=${dur}:d=0.25:alpha=1[e];` +
      `[g][h]overlay=0:0:enable='${clean ? 0 : 'lte(t,2.6)'}':shortest=1[gh];[gh][e]overlay=0:0:shortest=1,format=yuv420p[v]`,
      '-map', '[v]', '-t', String(dur + endDur), '-r', String(FPS),
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-movflags', '+faststart', mp4]);
    }
    const poster = Math.min(n - 1, best + Math.round(len * .6));
    fs.copyFileSync(path.join(dir, `f${String(poster).padStart(4, '0')}.jpg`), path.join(out, clip.id + '.jpg'));
    console.log(clip.id, `saved ${(fs.statSync(path.join(out, clip.id + '.mp4')).size / 1e6).toFixed(1)} MB (+ clean version), burgers served in clip: ${served[best + len - 1] - served[best]}, whole run: ${served[n - 1]}`, errors.length ? errors : '');
    fs.rmSync(dir, { recursive: true, force: true });
    await page.close();
    break;
  }
  }
  await browser.close(); server.close();
})();
