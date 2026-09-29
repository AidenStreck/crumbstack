// Picks which game goes into the iPhone app before `npx cap add ios` (run on the Mac build server):
//   node scripts/ios-app.mjs tidy-tides
// Writes capacitor.config.json (bundle ID, name, colours) and, for games in prototypes/, a
// ready-to-ship web folder app-www/ with the game's fonts bundled so the app never needs the internet.
// patch-ios.mjs then uses the icon and splash from the game's resources folder.
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
export const APPS = {
  crumbstack: { appId: 'com.crumbstack.game', appName: 'Crumbstack', bg: '#22174A', res: 'resources' },
  'tidy-tides': { appId: 'Com.aidenstreck.tidytides', appName: 'Tidy Tides', bg: '#1C7F9A', res: 'resources/tidy-tides', proto: 'tidy-tides', version: '1.1',
    // Rewarded videos (Google AdMob). test: true shows Google's sample videos; set it to false only when this
    // version is sent to Apple for the App Store, so nobody earns (or gets flagged for) test views of real ads.
    ads: { appId: 'ca-app-pub-3761245517174322~2575152825', unit: 'ca-app-pub-3761245517174322/9039740397', test: true },
    fonts: [{ family: 'Fredoka', weight: '300 700', file: 'Fredoka.ttf', url: 'https://github.com/google/fonts/raw/main/ofl/fredoka/Fredoka%5Bwdth%2Cwght%5D.ttf' }] },
};
const id = process.argv[2] || 'crumbstack', app = APPS[id];
if (!app) { console.error('Unknown app ' + id + '. Known: ' + Object.keys(APPS).join(', ')); process.exit(1); }

let webDir = 'www';
if (app.proto) {
  webDir = 'app-www'; const out = path.join(root, webDir), built = path.join(root, 'www/prototypes', app.proto);
  if (!fs.existsSync(built)) { console.error('Run `npm run build` first.'); process.exit(1); }
  fs.rmSync(out, { recursive: true, force: true }); fs.cpSync(built, out, { recursive: true });
  let html = fs.readFileSync(path.join(out, 'index.html'), 'utf8'), css = '';
  fs.mkdirSync(path.join(out, 'fonts'), { recursive: true });
  for (const f of app.fonts || []) {
    const dest = path.join(out, 'fonts', f.file), cached = path.join(root, 'fonts', f.file);
    if (fs.existsSync(cached)) fs.copyFileSync(cached, dest);
    else { const r = await fetch(f.url); if (!r.ok) throw new Error('Font download failed: ' + f.url); fs.writeFileSync(dest, Buffer.from(await r.arrayBuffer())); }
    css += `@font-face{font-family:"${f.family}";font-weight:${f.weight};font-style:normal;font-display:swap;src:url(fonts/${f.file}) format("truetype")}`;
  }
  html = html.replace(/<link rel="preconnect" href="https:\/\/fonts\.googleapis\.com">\s*/g, '').replace(/<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]*>\s*/g, '');
  if (app.ads) html = html.replace('<style>', `<script>window.__ADS=${JSON.stringify({ unit: app.ads.unit, test: !!app.ads.test })}</script>\n<style>`);
  html = html.replace('<style>', `<style>${css}html,body{background:${app.bg};overscroll-behavior:none;-webkit-touch-callout:none}.proto{display:none!important}`);
  fs.writeFileSync(path.join(out, 'index.html'), html);
  if (/fonts\.googleapis/.test(html)) throw new Error('A Google Fonts link is still in the app page');
}
// games without ads leave Google's ad kit out of their app entirely (only on the build server, so local files stay as they are)
if (!app.ads && process.env.CI) {
  const pj = path.join(root, 'package.json'), pkg = JSON.parse(fs.readFileSync(pj, 'utf8'));
  delete pkg.dependencies['@capacitor-community/admob']; fs.writeFileSync(pj, JSON.stringify(pkg, null, 2) + '\n');
  fs.rmSync(path.join(root, 'node_modules/@capacitor-community/admob'), { recursive: true, force: true });
  console.log('No ads in this game: ad plugin removed from the build.');
}
fs.writeFileSync(path.join(root, 'capacitor.config.json'), JSON.stringify({
  appId: app.appId, appName: app.appName, webDir, backgroundColor: app.bg,
  ios: { contentInset: 'never', scrollEnabled: false, backgroundColor: app.bg },
}, null, 2) + '\n');
fs.writeFileSync(path.join(root, '.ios-app.json'), JSON.stringify({ id, ...app }));
console.log(`iPhone app set to ${app.appName} (${app.appId}), web files from ${webDir}/`);
