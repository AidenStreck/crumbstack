// Runs right after `npx cap add ios` (on the Mac build server) to customize the iPhone project:
// app icon, launch screen, portrait only, hidden status bar, and the export-compliance flag.
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const app = path.join(root, 'ios/App/App');
if (!fs.existsSync(app)) { console.error('ios/App/App not found. Run `npx cap add ios` first.'); process.exit(1); }

// 1) App icon: replace every 1024px image in the AppIcon set with ours.
const iconSet = path.join(app, 'Assets.xcassets/AppIcon.appiconset');
const iconJson = JSON.parse(fs.readFileSync(path.join(iconSet, 'Contents.json'), 'utf8'));
let n = 0;
for (const img of iconJson.images) {
  if (img.filename) { fs.copyFileSync(path.join(root, 'resources/icon-1024.png'), path.join(iconSet, img.filename)); n++; }
}
console.log(`App icon: replaced ${n} image(s).`);

// 2) Launch screen: replace the default splash images.
const splashSet = path.join(app, 'Assets.xcassets/Splash.imageset');
if (fs.existsSync(splashSet)) {
  for (const f of fs.readdirSync(splashSet)) if (f.endsWith('.png')) fs.copyFileSync(path.join(root, 'resources/splash-2732.png'), path.join(splashSet, f));
  console.log('Launch screen replaced.');
}

// 3) Info.plist settings
const plistPath = path.join(app, 'Info.plist');
let plist = fs.readFileSync(plistPath, 'utf8');
const set = {
  UIStatusBarHidden: '<true/>',
  UIViewControllerBasedStatusBarAppearance: '<false/>',
  UIRequiresFullScreen: '<true/>',
  ITSAppUsesNonExemptEncryption: '<false/>',
  UISupportedInterfaceOrientations: '<array>\n\t\t<string>UIInterfaceOrientationPortrait</string>\n\t</array>',
  'UISupportedInterfaceOrientations~ipad': '<array>\n\t\t<string>UIInterfaceOrientationPortrait</string>\n\t</array>',
};
for (const [key, val] of Object.entries(set)) {
  const esc = key.replace(/[~]/g, '\\$&');
  plist = plist.replace(new RegExp(`\\s*<key>${esc}</key>\\s*(<array>[\\s\\S]*?</array>|<true/>|<false/>|<string>[^<]*</string>)`), '');
  plist = plist.replace(/<\/dict>\s*<\/plist>\s*$/, `\t<key>${key}</key>\n\t${val}\n</dict>\n</plist>\n`);
}
fs.writeFileSync(plistPath, plist);
console.log('Info.plist updated.');
