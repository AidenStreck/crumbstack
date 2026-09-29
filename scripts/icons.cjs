// Renders the app icons into resources/ using the game's own ingredient art.
// Run with Node + Playwright (Claude runs this; you don't need to).
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const root = path.join(__dirname, '..');
const src = fs.readFileSync(path.join(root, 'src/game.html'), 'utf8');
const art = src.slice(src.indexOf('const H = {'), src.indexOf('// Power-up tokens'));
const page = `<canvas id="c" width="1024" height="1024"></canvas><script>${art}
const c = document.getElementById('c').getContext('2d');
// background
const g = c.createLinearGradient(0,0,0,1024); g.addColorStop(0,'#7FDCD0'); g.addColorStop(1,'#2C8E9A'); c.fillStyle=g; c.fillRect(0,0,1024,1024);
const sp = c.createRadialGradient(512,470,40,512,470,560); sp.addColorStop(0,'rgba(255,248,210,.75)'); sp.addColorStop(1,'rgba(255,248,210,0)'); c.fillStyle=sp; c.fillRect(0,0,1024,1024);
// sprinkles
[[160,190,'#FF6FA8'],[860,230,'#FFD25E'],[210,820,'#FFD25E'],[840,800,'#FF6FA8'],[120,520,'#FFFFFF'],[900,520,'#FFFFFF']].forEach(([x,y,col],i)=>{ c.save(); c.translate(x,y); c.rotate(i); c.fillStyle=col; c.beginPath(); c.roundRect(-34,-11,68,22,11); c.fill(); c.restore(); });
// plate
const w = 560, cx = 512; let y = 860;
c.fillStyle='rgba(20,10,40,.28)'; c.beginPath(); c.ellipse(cx,y+34,w*.64,40,0,0,7); c.fill();
const pg=c.createLinearGradient(0,y-30,0,y+40); pg.addColorStop(0,'#fff'); pg.addColorStop(1,'#D9D2F2');
c.fillStyle=pg; c.beginPath(); c.ellipse(cx,y+10,w*.66,44,0,0,7); c.fill(); c.strokeStyle='#2A1B4F'; c.lineWidth=10; c.stroke();
c.strokeStyle='#FF6FA8'; c.lineWidth=9; c.beginPath(); c.ellipse(cx,y+10,w*.53,28,0,0,7); c.stroke();
['bunBottom','patty','cheese','lettuce','tomato','bunTop'].forEach(t=>{ drawIng(c,t,cx,y,w); y-=H[t]*w; });
</script>`;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport:{width:1024,height:1024} });
  await p.setContent('<style>body{margin:0}</style>' + page);
  const el = await p.$('#c');
  const out = path.join(root, 'resources'); fs.mkdirSync(out, { recursive: true });
  await el.screenshot({ path: path.join(out, 'icon-1024.png'), omitBackground: false });
  for (const [name, size] of [['icon-512.png',512],['icon-192.png',192],['apple-touch-icon.png',180]]) {
    await p.setViewportSize({ width: size, height: size });
    await p.evaluate(s => { const cv=document.getElementById('c'); cv.style.width=s+'px'; cv.style.height=s+'px'; }, size);
    await el.screenshot({ path: path.join(out, name) });
  }
  await b.close(); console.log('icons written');
})();
