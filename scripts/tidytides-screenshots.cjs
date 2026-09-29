// Makes the Tidy Tides App Store screenshots (needs Playwright + Chromium):
//   node scripts/build.mjs && node scripts/tidytides-screenshots.cjs        -> store/tidy-tides/screenshots/     1290 x 2796 (iPhone 6.9")
//   node scripts/tidytides-screenshots.cjs 6.5                               -> store/tidy-tides/screenshots-6.5/ 1284 x 2778 (iPhone 6.5")
// The game starts from store/tidy-tides/shots-save.json, a save made by a bot playing ~20 minutes of the real game.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require('playwright');
const SIZE = process.argv[2] === '6.5' ? { w: 428, h: 926, dir: 'screenshots-6.5' } : { w: 430, h: 932, dir: 'screenshots' };
const root = path.join(__dirname, '..'), www = path.join(root, 'www'), out = path.join(root, 'store/tidy-tides', SIZE.dir);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.ttf': 'font/ttf', '.woff': 'font/woff', '.json': 'application/json' };
const server = http.createServer((req, res) => { let f = path.join(www, decodeURIComponent(req.url.split('?')[0].split('#')[0])); if (f.endsWith('/')) f += 'index.html';
  fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); res.end(); } else { res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); res.end(d); } }); });
const SAVE = fs.readFileSync(path.join(root, 'store/tidy-tides/shots-save.json'), 'utf8');
const closeAll = p => p.evaluate(() => { document.querySelectorAll('.modalWrap, .tip').forEach(e => e.remove()); if (window.__tt) { const P = __tt.S.player; P.x = 150; P.y = __tt.waterline() + 120; __tt.closeBoard(); } });
const SHOTS = [
  { file: '1-clean.png', title: 'Clean up', accent: 'the beach', bg: 'linear-gradient(#3FC4D6,#157E97)', setup: async p => {
    await p.evaluate(() => { const T = __tt, P = T.S.player; T.camX = 0; P.x = 150; P.y = T.waterline() + 120; }); await p.waitForTimeout(2500); } },
  { file: '2-recycle.png', title: 'Turn trash into', accent: 'treasure', bg: 'linear-gradient(#F7A94A,#D9582B)', setup: async p => {
    await p.evaluate(() => { const T = __tt, P = T.S.player, a = T.AREAS[1]; P.x = a.x + 200; P.y = T.L.sellY + 30; }); await p.waitForTimeout(2500); } },
  { file: '3-crew.png', title: 'Hire a', accent: 'helpful crew', bg: 'linear-gradient(#4CC38A,#1C7A52)', setup: async p => {
    await p.evaluate(() => { const T = __tt, P = T.S.player; const a = T.AREAS[0]; P.x = a.x + 44; P.y = T.L.row0 + 10; T.openBoard(a); }); await p.waitForTimeout(1200); } },
  { file: '4-album.png', title: 'Collect', accent: 'sea creatures', bg: 'linear-gradient(#8E7CF0,#4B37B0)', setup: async p => {
    await p.evaluate(() => __tt.openJournal('album')); await p.waitForTimeout(900); } },
  { file: '5-sail.png', title: 'Sail to', accent: '13 coasts', bg: 'linear-gradient(#8FD0FF,#2E6FD0)', setup: async p => {
    await p.evaluate(() => __tt.openSail()); await p.waitForTimeout(900); } },
];
(async () => {
  await new Promise(r => server.listen(8798, r)); fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch(), fontData = `@font-face{font-family:"Fredoka";font-weight:300 700;src:url(data:font/ttf;base64,${fs.readFileSync(path.join(root, 'fonts/Fredoka.ttf')).toString('base64')}) format("truetype")}`, fontCss = `@font-face{font-family:"Fredoka";font-weight:300 700;src:url(http://localhost:8798/fonts/Fredoka.ttf) format("truetype")}`;
  const game = await browser.newPage({ viewport: { width: SIZE.w, height: SIZE.h }, deviceScaleFactor: 3 }); const errors = []; game.on('pageerror', e => errors.push(e.message));
  await game.route(/fonts\.googleapis\.com/, r => r.fulfill({ contentType: 'text/css', body: fontCss }));
  await game.addInitScript(s => { try { if (!sessionStorage.getItem('shots')) { const o = JSON.parse(s); o.lastSeen = Date.now(); o.giftDay = new Date().toDateString(); localStorage.setItem('tidytides-save-v2', JSON.stringify(o)); sessionStorage.setItem('shots', 1); } } catch (e) {} }, SAVE);
  await game.goto('http://localhost:8798/prototypes/tidy-tides/#test'); await game.addStyleTag({ content: '.proto{display:none!important}' }); await game.waitForTimeout(1200);
  await game.evaluate(() => { const b = document.getElementById('play'); if (b) b.click(); }); await game.waitForTimeout(1500); await closeAll(game);
  const frame = await browser.newPage({ viewport: { width: SIZE.w, height: SIZE.h }, deviceScaleFactor: 3 });
  for (const s of SHOTS) {
    await closeAll(game); await s.setup(game); await game.evaluate(() => document.querySelectorAll('.tip,.toast').forEach(e => e.remove()));
    const raw = (await game.screenshot()).toString('base64');
    await frame.setContent(`<style>${fontData}
      body{margin:0;width:${SIZE.w}px;height:${SIZE.h}px;overflow:hidden;font-family:Fredoka,sans-serif;background:${s.bg};position:relative}
      .cap{position:absolute;top:56px;left:0;right:0;text-align:center;color:#fff;font-weight:600;font-size:36px;color:#FFF3C4;line-height:1.05;text-shadow:0 3px 0 rgba(10,30,50,.35);padding:0 22px}
      .cap b{display:block;font-weight:700;color:#fff;font-size:52px}
      .phone{position:absolute;left:50%;top:196px;width:344px;height:746px;transform:translateX(-50%);border-radius:44px;background:#16324A;padding:9px;box-shadow:0 24px 60px rgba(10,30,50,.4)}
      .phone img{width:100%;height:100%;border-radius:36px;display:block;object-fit:cover;object-position:top}
      </style><div class="cap">${s.title}<b>${s.accent}</b></div><div class="phone"><img src="data:image/png;base64,${raw}"></div>`);
    await frame.evaluate(() => document.fonts.ready); await frame.waitForTimeout(400); await frame.screenshot({ path: path.join(out, s.file) }); console.log('saved', s.file);
  }
  console.log('errors:', errors.length ? errors : 'none'); await browser.close(); server.close();
})();
