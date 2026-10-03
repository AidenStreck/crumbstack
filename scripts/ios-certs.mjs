// Every iPhone build runs on a brand-new Mac, and Xcode makes a new throwaway *development* certificate each time.
// Apple only allows a few, so after several builds signing fails with "maximum number of certificates".
// This clears out the old development certificates before each build. Distribution certificates (the ones that
// matter for TestFlight and the App Store) are never touched. Usage: node scripts/ios-certs.mjs <AuthKey.p8>
import fs from 'node:fs';
import crypto from 'node:crypto';
const [keyPath] = process.argv.slice(2), kid = process.env.ASC_KEY_ID, iss = process.env.ASC_ISSUER_ID;
if (!keyPath || !kid || !iss) { console.log('ios-certs: no key, skipping.'); process.exit(0); }
const b64 = o => Buffer.from(typeof o === 'string' ? o : JSON.stringify(o)).toString('base64url');
const now = Math.floor(Date.now() / 1000);
const head = b64({ alg: 'ES256', kid, typ: 'JWT' }) + '.' + b64({ iss, iat: now, exp: now + 600, aud: 'appstoreconnect-v1' });
const token = head + '.' + crypto.sign('sha256', Buffer.from(head), { key: fs.readFileSync(keyPath, 'utf8'), dsaEncoding: 'ieee-p1363' }).toString('base64url');
const api = (path, init = {}) => fetch('https://api.appstoreconnect.apple.com/v1/' + path, { ...init, headers: { Authorization: 'Bearer ' + token } });
try {
  const res = await api('certificates?limit=200'); if (!res.ok) throw new Error('list failed: ' + res.status + ' ' + (await res.text()).slice(0, 300));
  const certs = (await res.json()).data || [];
  console.log('ios-certs: ' + certs.map(c => c.attributes.certificateType).sort().join(', '));
  let n = 0;
  for (const c of certs) { if (!/DEVELOPMENT/.test(c.attributes.certificateType)) continue;
    const r = await api('certificates/' + c.id, { method: 'DELETE' }); if (r.ok) n++; else console.log('ios-certs: could not remove ' + c.id + ': ' + r.status + ' ' + (await r.text()).slice(0, 200)); }
  console.log(`ios-certs: removed ${n} old development certificate(s).`);
} catch (e) { console.log('::warning title=Certificates::' + e.message); }
