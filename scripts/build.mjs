// Builds the playable web app in www/ from the single game source in src/game.html.
// The same www/ folder is used for the free website (GitHub Pages) and inside the iPhone app.
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const src = fs.readFileSync(path.join(root, 'src/game.html'), 'utf8');
const www = path.join(root, 'www');
fs.rmSync(www, { recursive: true, force: true });
fs.mkdirSync(path.join(www, 'icons'), { recursive: true });

// 1) Split the <title> out of the game source; everything else goes in <body>.
const title = (src.match(/<title>(.*?)<\/title>/) || [, 'Crumbstack'])[1];
let body = src.replace(/<title>.*?<\/title>\s*/, '');

// 2) Fonts: bundle them for offline play when the font packages are installed,
//    otherwise keep loading them from Google Fonts.
const fontLinks = /<link rel="preconnect" href="https:\/\/fonts\.googleapis\.com">\s*<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]*>\s*/;
const fontFiles = [
  ['@fontsource/lilita-one/files/lilita-one-latin-400-normal.woff2', 'Lilita One', 400],
  ['@fontsource/nunito/files/nunito-latin-700-normal.woff2', 'Nunito', 700],
  ['@fontsource/nunito/files/nunito-latin-800-normal.woff2', 'Nunito', 800],
  ['@fontsource/nunito/files/nunito-latin-900-normal.woff2', 'Nunito', 900],
];
let fontCss = '';
if (fontFiles.every(([f]) => fs.existsSync(path.join(root, 'node_modules', f)))) {
  fs.mkdirSync(path.join(www, 'fonts'));
  for (const [f, fam, w] of fontFiles) {
    const name = path.basename(f);
    fs.copyFileSync(path.join(root, 'node_modules', f), path.join(www, 'fonts', name));
    fontCss += `@font-face{font-family:"${fam}";font-weight:${w};font-style:normal;font-display:swap;src:url(fonts/${name}) format("woff2")}\n`;
  }
  body = body.replace(fontLinks, '');
  console.log('Fonts bundled for offline play.');
} else {
  console.log('Font packages not installed; using Google Fonts.');
}

// 3) Icons and web-app manifest
for (const f of fs.readdirSync(path.join(root, 'resources'))) {
  if (['icon-192.png', 'icon-512.png', 'apple-touch-icon.png'].includes(f)) fs.copyFileSync(path.join(root, 'resources', f), path.join(www, 'icons', f));
}
fs.writeFileSync(path.join(www, 'manifest.webmanifest'), JSON.stringify({
  name: 'Crumbstack', short_name: 'Crumbstack', start_url: './', scope: './',
  display: 'standalone', orientation: 'portrait', background_color: '#22174A', theme_color: '#22174A',
  icons: [
    { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
    { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
    { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
  ],
}, null, 2));

// 4) Offline support for the home-screen web app (not used inside the iPhone app)
const version = new Date().toISOString();
fs.writeFileSync(path.join(www, 'sw.js'), `// Generated ${version}
const CACHE = 'crumbstack-${Date.now()}';
self.addEventListener('install', e => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./', './index.html', './manifest.webmanifest']))); });
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; }).catch(() => caches.match(e.request).then(r => r || caches.match('./index.html'))));
});
`);

// 5) Page shell
const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<title>${title}</title>
<meta name="theme-color" content="#22174A">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Crumbstack">
<meta name="description" content="Stack burgers exactly as ordered. A bright, quick puzzle game.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" href="icons/icon-192.png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<style>
${fontCss}:root{color-scheme:dark;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);box-sizing:border-box;height:100%;background:#22174A}
body{margin:0;font-size:14px;overscroll-behavior:none;-webkit-touch-callout:none}
img{max-width:100%}
[hidden]{display:none!important}
</style>
</head>
<body>
${body}
<script>
if ('serviceWorker' in navigator && location.protocol === 'https:' && !window.Capacitor) {
  addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
}
</script>
</body>
</html>
`;
fs.writeFileSync(path.join(www, 'index.html'), html);
fs.writeFileSync(path.join(www, '.nojekyll'), '');
console.log('Built www/ (' + Math.round(html.length / 1024) + ' KB)');
