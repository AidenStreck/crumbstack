// Makes the App Store screenshots in store/screenshots/ (1290 x 2796, iPhone 6.9").
// Run: node scripts/build.mjs && node scripts/screenshots.cjs   (needs Playwright + Chromium)
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require('playwright');

const root = path.join(__dirname, '..'), www = path.join(root, 'www'), out = path.join(root, 'store/screenshots');
const TYPES = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.png':'image/png', '.woff':'font/woff', '.json':'application/json', '.webmanifest':'application/manifest+json' };
const server = http.createServer((req, res) => {
  let f = path.join(www, decodeURIComponent(req.url.split('?')[0]));
  if (f.endsWith('/')) f += 'index.html';
  fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); res.end(); } else { res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); res.end(d); } });
});

const SAVE = { unlocked: 12, stars: {1:3,2:3,3:3,4:2,5:3,6:3,7:2,8:3,9:3,10:2,11:3}, best: {}, coins: 850,
  inv: { magnet: 2, plate: 1, heart: 3 }, gifted: { magnet: true, plate: true, heart: true }, giftDay: '', sound: { music: false, sfx: false } };

// Each shot: a caption and a function that sets up the game state.
const SHOTS = [
  { file: '1-stack.png', title: 'Stack every burger', accent: 'just right', setup: async p => {
    await p.evaluate(() => { const c = __cs; c.start(7, {}, 'classic'); });
    await p.waitForTimeout(1900);
    await p.evaluate(() => { const c = __cs, S = c.S, W = c.W, H = c.H; c.stop();
      S.order = ['bunBottom','patty','cheese','lettuce','tomato','bunTop']; S.idx = 3; S.stack = ['bunBottom','patty','cheese'];
      S.px = S.targetX = W*.52; S.score = 236; S.served = 2; S.patience = .72; S.combo = 2; S.lean = 0;
      S.cust = c.newCustomer(false); S.cust.name = 'Mabel'; S.cust.skin = '#E9B48A'; S.cust.hair = '#C0442E'; S.cust.shirt = '#4FB6E8'; S.cust.style = 1;
      const pw = Math.min(118, W*.3)*.9;
      S.items = [
        { kind:'ing', type:'lettuce', x:W*.5, y:H*.55, rot:.12, vr:0, vy:0, state:'fall' },
        { kind:'ing', type:'onion', x:W*.2, y:H*.32, rot:-.3, vr:0, vy:0, state:'fall' },
        { kind:'ing', type:'bunTop', x:W*.8, y:H*.18, rot:.25, vr:0, vy:0, state:'fall' },
        { kind:'token', type:'magnet', x:W*.25, y:H*.62, vy:0, state:'fall' },
      ];
      S.pops = []; c.pop('+5', S.px, c.plateY - 90, '#FFD25E', 22); S.pops[0].t = .12;
      c.burst(S.px, c.plateY - 50, ['#FFC62E', '#FFFFFF'], 10, 140);
      c.renderTicket(); c.updateHud(); }); } },
  { file: '2-vip.png', title: 'VIPs, flies and', accent: 'wobbly towers', setup: async p => {
    await p.evaluate(() => { __cs.closeModal(); __cs.start(14, {}, 'classic'); });
    await p.waitForTimeout(1900);
    await p.evaluate(() => { const c = __cs, S = c.S, W = c.W, H = c.H; c.stop();
      S.order = ['bunBottom','patty','cheese','tomato','lettuce','patty','bunTop']; S.idx = 5; S.stack = ['bunBottom','patty','cheese','tomato','lettuce'];
      S.px = S.targetX = W*.45; S.lean = .55; S.score = 612; S.served = 4; S.patience = .38; S.combo = 3;
      S.cust = c.newCustomer(true); S.cust.name = 'Big Lou'; S.cust.skin = '#C98E62'; S.cust.hair = '#2B1B12'; S.cust.shirt = '#8A6BE0'; S.cust.style = 0;
      S.items = [
        { kind:'ing', type:'patty', x:W*.62, y:H*.4, rot:.1, vr:0, vy:0, state:'fall' },
        { kind:'fly', x:W*.22, bx:W*.22, y:H*.3, vy:0, ph:0, amp:0, state:'fall' },
        { kind:'token', type:'freeze', x:W*.78, y:H*.22, vy:0, state:'fall' },
        { kind:'ing', type:'cheese', x:W*.3, y:H*.12, rot:-.2, vr:0, vy:0, state:'fall' },
      ];
      S.pops = []; c.pop('Steady!', S.px, c.plateY - 230, '#FFD25E', 26); S.pops[0].t = .15;
      c.renderTicket(); c.updateHud(); }); } },
  { file: '3-map.png', title: '24 levels across', accent: '3 tasty worlds', setup: async p => {
    await p.evaluate(() => { __cs.closeModal(); __cs.showMap(); });
    await p.waitForTimeout(600); } },
  { file: '4-stars.png', title: 'Serve fast.', accent: 'Earn every star.', setup: async p => {
    await p.evaluate(() => { __cs.start(6, {}, 'classic'); });
    await p.waitForTimeout(1900);
    await p.evaluate(() => { const c = __cs, S = c.S; S.served = S.L.goal; S.score = S.L.stars[2] + 40; S.items = []; S.stack = []; c.updateHud(); c.finish(true); });
    await p.waitForTimeout(3600); } },
  { file: '5-boosters.png', title: 'Power up with', accent: 'boosters', setup: async p => {
    await p.evaluate(() => { __cs.closeModal(); __cs.showMap(); __cs.openLevel(12); });
    await p.waitForTimeout(900);
    await p.evaluate(() => { document.querySelector('[data-boost="magnet"]').click(); document.querySelector('[data-boost="heart"]').click(); });
    await p.waitForTimeout(300); } },
];

(async () => {
  await new Promise(r => server.listen(8799, r));
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const game = await browser.newPage({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 3 });
  const errors = []; game.on('pageerror', e => errors.push(e.message));
  await game.addInitScript(s => { try { localStorage.setItem('crumbstack-save-v2', s); } catch (e) {} }, JSON.stringify(SAVE));
  await game.goto('http://localhost:8799/#shots'); await game.waitForTimeout(800);
  const frame = await browser.newPage({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 3 });
  const fonts = fs.readdirSync(path.join(root, 'fonts')).filter(f => f.endsWith('.woff'));
  const fontCss = `@font-face{font-family:"Lilita One";src:url(data:font/woff;base64,${fs.readFileSync(path.join(root,'fonts/lilita-one-400.woff')).toString('base64')})}`;
  for (const [i, s] of SHOTS.entries()) {
    await s.setup(game); await game.waitForTimeout(250);
    const raw = (await game.screenshot()).toString('base64');
    await frame.setContent(`<style>${fontCss}
      body{margin:0;width:430px;height:932px;overflow:hidden;font-family:"Lilita One",sans-serif;
        background:${['linear-gradient(#6FD6C8,#2C8E9A)','linear-gradient(#8B6BE0,#FF7FA0 60%,#FFC46B)','linear-gradient(#FF8FBA,#D63A78)','linear-gradient(#3A2A86,#150F33)','linear-gradient(#FFE48E,#F7A934)'][i]};position:relative}
      .cap{position:absolute;top:58px;left:0;right:0;text-align:center;color:#fff;font-size:40px;line-height:1.05;text-shadow:0 4px 0 rgba(42,27,79,.35);padding:0 22px}
      .cap b{display:block;font-weight:400;color:#FFE48E;font-size:48px}
      ${i===4?'.cap{color:#2A1B4F;text-shadow:none}.cap b{color:#D63A78}':''}
      .phone{position:absolute;left:50%;top:196px;width:344px;height:746px;transform:translateX(-50%);border-radius:44px;background:#150F33;padding:9px;box-shadow:0 24px 60px rgba(20,10,50,.45)}
      .phone img{width:100%;height:100%;border-radius:36px;display:block;object-fit:cover;object-position:top}
      </style><div class="cap">${s.title}<b>${s.accent}</b></div><div class="phone"><img src="data:image/png;base64,${raw}"></div>`);
    await frame.waitForTimeout(300);
    await frame.screenshot({ path: path.join(out, s.file) });
    console.log('saved', s.file);
  }
  console.log('errors:', errors.length ? errors : 'none');
  await browser.close(); server.close();
})();
