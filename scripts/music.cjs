// Renders Crumbstack's background music (the same synth as the game) to marketing/music/loop.wav,
// so voiceover videos can use the game's own music. Run: node scripts/music.cjs  (needs Playwright)
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const out = path.join(__dirname, '..', 'marketing/music');

const PAGE = `<script>
async function render(loops){
  const BPM = 112, STEP = 60/BPM/2, SR = 44100, dur = loops*64*STEP + 1.5;
  const ac = new OfflineAudioContext(2, Math.ceil(SR*dur), SR);
  const comp = ac.createDynamicsCompressor(); comp.connect(ac.destination);
  const bus = ac.createGain(); bus.gain.value = .55; bus.connect(comp);
  const mf = m => 440*Math.pow(2,(m-69)/12);
  function tone(freq, d, o, t){ const osc = ac.createOscillator(), g = ac.createGain(); osc.type = o.type||'triangle'; osc.frequency.setValueAtTime(freq, t);
    g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(o.vol||.2, t+.006); g.gain.exponentialRampToValueAtTime(.0001, t+d);
    osc.connect(g); g.connect(bus); osc.start(t); osc.stop(t+d+.05); }
  const nb = ac.createBuffer(1, SR*.5, SR); const nd = nb.getChannelData(0); for (let i=0;i<nd.length;i++) nd[i] = Math.random()*2-1;
  function noise(d, o, t){ const src = ac.createBufferSource(); src.buffer = nb; const f = ac.createBiquadFilter(); f.type = o.ft||'highpass'; f.frequency.value = o.freq||6000;
    const g = ac.createGain(); g.gain.setValueAtTime(o.vol||.1, t); g.gain.exponentialRampToValueAtTime(.0001, t+d); src.connect(f); f.connect(g); g.connect(bus); src.start(t); src.stop(t+d+.02); }
  const CH = [[48,55,60,64],[45,52,57,60],[41,48,53,57],[43,50,55,59]], _ = null;
  const MEL = [76,_,79,_,81,79,76,_, 72,_,74,76,_,_,72,_, 69,_,72,_,74,72,69,_, 67,_,69,71,74,_,_,_,
               76,_,79,_,84,_,81,79, 76,_,74,_,72,_,_,_,  77,_,76,74,72,_,69,_, 71,_,72,74,72,_,_,_];
  for (let s = 0; s < loops*64; s++) {
    const t = .05 + s*STEP, bar = Math.floor(s/8)%4, ch = CH[bar];
    if (s%8===0) tone(mf(ch[0]-12), STEP*3.5, {type:'sine', vol:.28}, t);
    if (s%8===4) tone(mf(ch[1]-12), STEP*3, {type:'sine', vol:.2}, t);
    if (s%2===1) [ch[2],ch[3]].forEach(m => tone(mf(m), STEP*.9, {type:'triangle', vol:.035}, t));
    if (s%2===1) noise(.04, {vol:.025, freq:9000}, t);
    if (s%8===4) noise(.08, {vol:.05, freq:2500, ft:'bandpass'}, t);
    const m = MEL[s%64]; if (m) tone(mf(m), STEP*1.6, {type:'square', vol:.045}, t);
  }
  const buf = await ac.startRendering();
  // encode 16-bit PCM WAV
  const ch0 = buf.getChannelData(0), ch1 = buf.getChannelData(1), n = ch0.length, dv = new DataView(new ArrayBuffer(44 + n*4));
  const w = (o, s) => [...s].forEach((c, i) => dv.setUint8(o+i, c.charCodeAt(0)));
  w(0,'RIFF'); dv.setUint32(4, 36+n*4, true); w(8,'WAVE'); w(12,'fmt '); dv.setUint32(16,16,true); dv.setUint16(20,1,true); dv.setUint16(22,2,true);
  dv.setUint32(24,SR,true); dv.setUint32(28,SR*4,true); dv.setUint16(32,4,true); dv.setUint16(34,16,true); w(36,'data'); dv.setUint32(40,n*4,true);
  for (let i=0;i<n;i++){ dv.setInt16(44+i*4, Math.max(-1,Math.min(1,ch0[i]))*32767, true); dv.setInt16(46+i*4, Math.max(-1,Math.min(1,ch1[i]))*32767, true); }
  const bytes = new Uint8Array(dv.buffer); let bin = ''; for (let i=0;i<bytes.length;i+=8192) bin += String.fromCharCode.apply(null, bytes.subarray(i, i+8192));
  return btoa(bin);
}
</script>`;

(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.setContent(PAGE);
  const b64 = await p.evaluate(() => render(2));
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(path.join(out, 'loop.wav'), Buffer.from(b64, 'base64'));
  console.log('wrote marketing/music/loop.wav'); await b.close();
})();
