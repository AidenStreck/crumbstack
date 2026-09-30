// Usage: node scripts/build.mjs && (cd www && python3 -m http.server 8765 &) && PROFILE=regular DAYS=90 node scripts/hatchwild-bot.cjs
// Hatchwild play bot: fake clock, plays sessions like a real player, logs pacing and any errors.
// PROFILE=casual|regular|hardcore DAYS=90 node hwbot.cjs
const { chromium } = require('playwright');
const PROFILE = process.env.PROFILE || 'regular', DAYS = +process.env.DAYS || 60;
const P = { casual: { per: 2, len: 6 }, regular: { per: 4, len: 8 }, hardcore: { per: 8, len: 12 } }[PROFILE];
(async () => {
  const br = await chromium.launch(); const pg = await br.newPage({ viewport: { width: 390, height: 844 } }); const errs = [];
  pg.on('pageerror', e => errs.push(e.message + ' @ ' + (e.stack || '').split('\n')[1]));
  await pg.addInitScript(() => { const start = Date.parse('2026-10-05T08:00:00'); window.__now = start; Date.now = () => window.__now; const RD = Date; window.Date = class extends RD { constructor(...a){ if (a.length) super(...a); else super(window.__now); } static now(){ return window.__now; } };
    window.requestAnimationFrame = () => 0; window.__nodraw = true; localStorage.clear(); });
  await pg.goto('http://localhost:8765/prototypes/hatchwild/#test'); await pg.waitForTimeout(600);
  const out = await pg.evaluate(async ({ P, DAYS }) => {
    const log = [], mile = {}, H = 3600e3, battles = { win: 0, loss: 0, replay: 0 }, stalls = [], waste = { coins: 0, food: 0 }, blocked = { denFull: 0, nestBusy: 0, noFood: 0 }, spent = { warm: 0, snack: 0 };
    const day = () => ((window.__now - Date.parse('2026-10-05T08:00:00')) / 864e5).toFixed(2);
    const mark = (k) => { if (!mile[k]) mile[k] = day(); };
    const closeModals = () => { let n = 0; while (document.querySelector('.modalWrap') && n++ < 20) { const b = document.querySelector('.modalWrap [data-close]') || document.querySelector('.modalWrap .btn'); if (b) b.click(); else document.querySelector('.modalWrap').remove(); } document.querySelectorAll('.tip').forEach(e => e.remove()); closeSheet(); };
    const tick = () => { tickBuildings(); updateHud(); };
    function doBuilds(){
      let guard = 0;
      while (busy() < BUILDERS && guard++ < 10) {
        const hq = hqLv(), cands = [];
        for (const b of save.bld) if (!b.build && b.lv && b.lv < maxLevel(b.k, hq)) cands.push({ b, k: b.k, c: cost(b.k, b.lv + 1), up: true });
        for (const k of BLD_ORDER) if (k !== 'hq' && k !== 'nest' && k !== 'dock' && B(k).length < maxCount(k, hq)) cands.push({ k, c: cost(k, 1), up: false });
        const pri = { hq: 0, dock: 1, farm: 2, mill: 2, den: roomLeft() <= 1 ? 1 : 4, pond: 3, tower: 5, cannon: 5, nest: 4 };
        cands.sort((a, b) => (pri[a.k] - pri[b.k]) || (a.c - b.c));
        // save up for the Keeper's Lodge when everything else is maxed for this level
        const pick = cands.find(x => x.c <= save.coins); if (!pick) break;
        if (pick.k !== 'hq' && cands[0].k === 'hq' && cands[0].c <= save.coins * 1.4 && cands[0].c > save.coins) break;
        if (pick.up) startUpgrade(pick.b);
        else { const p = freeSpot(pick.k); if (!p) { log.push(day() + ' no space for ' + pick.k); break; } save.coins -= pick.c; save.bld.push({ id: save.nextId++, k: pick.k, x: p.x, y: p.y, lv: 0, last: Date.now(), build: { to: 1, start: Date.now(), end: Date.now() + secs(btime(pick.k, 1)) } }); }
      }
      // land expansion when rich
      const n = save.plot.n; if (save.plot.w < PLOT_MAX && hqLv() >= expandHq(n) && save.coins > expandCost(n) * 2.5) { save.coins -= expandCost(n); if (save.plot.w <= save.plot.h) save.plot.w += 2; else save.plot.h += 2; save.plot.n++; mark('expand' + save.plot.n); }
    }
    function doNest(){
      if (save.nest && Date.now() >= save.nest.end) nestCollect(); closeModals();
      while (save.eggs.length && roomLeft() >= 0) { hatchEgg(); closeModals(); if (save.eggs.length && roomLeft() < 0) break; }
      if (save.nest && save.food > 60000) { const wc = warmCost(save.nest.s, save.nest.end - Date.now()); if (save.food - wc > 30000) { save.food -= wc; save.nest.end = Date.now(); nestCollect(); closeModals(); spent.warm += wc; } }
      if (save.nest) { blocked.nestBusy++; return; }
      if (roomLeft() <= 0) { blocked.denFull++; return; }
      const NL = lvOf('nest'), open = BASIC.filter(sp => regionOpen(SPECIES[sp].region) && nestRegion(NL) >= SPECIES[sp].region);
      // try pairs for undiscovered hybrids sometimes
      const pairs = Object.keys(HYBRIDS).filter(k => !save.tips['found-' + HYBRIDS[k]]).map(k => k.split('+')).filter(([a, b]) => save.crit.some(c => c.s === a) && save.crit.some(c => c.s === b));
      if (pairs.length && Math.random() < .5) { const [a, b] = pairs[0], R = Math.max(SPECIES[a].region, SPECIES[b].region), cf = EGG_FOOD[R] * 2; if (save.food >= cf) { save.food -= cf; const h = hybridOf(a, b), lucky = h && Math.random() < .35; save.nest = { s: lucky ? h : (Math.random() < .5 ? a : b), pair: true, start: Date.now(), end: Date.now() + secs(EGG_TIME[R] * 2) }; save.stats.pair++; return; } }
      // hatch the kind we have most of (to feed merges), preferring the newest region
      const best = open.slice().sort((x, y) => SPECIES[y].region - SPECIES[x].region || save.crit.filter(c => c.s === y).length - save.crit.filter(c => c.s === x).length)[0];
      if (best) { const R = SPECIES[best].region; if (save.food >= EGG_FOOD[R]) { save.food -= EGG_FOOD[R]; save.nest = { s: best, start: Date.now(), end: Date.now() + secs(EGG_TIME[R] * (1 - .07 * (NL - 1))) }; } else blocked.noFood++; }
    }
    function doMerge(){
      const pond = B('pond')[0]; if (!pond || !pond.lv) return; const cap = pondTier(pond.lv);
      for (let k = 0; k < 6; k++) { const groups = {}; for (const c of save.crit) (groups[c.s + ':' + c.t] = groups[c.s + ':' + c.t] || []).push(c);
        const g = Object.entries(groups).find(([key, l]) => l.length >= 3 && +key.split(':')[1] < cap); if (!g) break;
        const [sp, tier] = g[0].split(':'), T = +tier, cf = Math.round(250 * Math.pow(T, 1.6) * Math.pow(SPECIES[sp].region + 1, 2.2) / 10) * 10; if (save.food < cf) break;
        save.food -= cf; const three = g[1].slice(0, 3); save.crit = save.crit.filter(c => !three.includes(c)); save.crit.push({ id: save.nextId++, s: sp, t: T + 1, rest: 0 }); save.stats.merge++; addXp(10 * T); mark('tier' + (T + 1)); }
    }
    function fight(r, i){
      startPrep(r, i); if (!BT.squad.length) { endBattleUi(); BT = null; screen = 'base'; return null; } startFight(); let n = 0;
      while (BT.state === 'fight' && n < 20 * 155 && !BT.blds[0].dead) { stepBattle(1 / 20); n++;
        if (n % 30 === 0 && BT.state === 'fight') { const alive = BT.units.filter(u => !u.dead && u.wait <= 0);
          const def = BT.blds.filter(b => !b.dead && DEF[b.k]).sort((a, b) => Math.min(...alive.map(u => Math.hypot(u.x - a.x, u.y - a.y))) - Math.min(...alive.map(u => Math.hypot(u.x - b.x, u.y - b.y))))[0];
          const hurt = alive.filter(u => u.hp < u.max * .5);
          if (hurt.length >= 2 && BT.energy >= 3) { BT.sel = 'heal'; const p = toPx(hurt[0].x, hurt[0].y); battleTap(p[0], p[1]); }
          else if (def && BT.energy >= 5) { BT.sel = 'barrage'; const p = toPx(def.x + .5, def.y + .5); battleTap(p[0], p[1]); }
          else if (def && BT.energy >= 1 && !BT.flare && Math.random() < .3) { BT.sel = 'flare'; const p = toPx(def.x + .5, def.y + .5); battleTap(p[0], p[1]); } } }
      const won = BT.blds[0].dead; if (won && BT.state === 'fight') endBattle(true); else if (BT.state === 'fight') endBattle(false); closeModals(); BT = null; screen = 'base'; $('hud').hidden = false; closeMap(); return won;
    }
    function doBattles(){
      for (let tries = 0; tries < 3; tries++) {
        let r = REGIONS.findLastIndex((R, j) => regionOpen(j) && save.cleared[j] < ISLANDS_PER_REGION); if (r < 0) { mark('allClear'); return; }
        if (r > 0 && save.cleared[r - 1] < ISLANDS_PER_REGION) r = r - 1;   // finish a region before moving on
        if (save.food > 60000) for (const c of save.crit) if (c.rest) { const sc = snackCost(c, c.rest - Date.now()); if (save.food - sc > 40000) { save.food -= sc; c.rest = 0; spent.snack += sc; } }
        const rested = save.crit.filter(c => !c.rest).length; if (rested < Math.min(3, save.crit.length)) return;
        const i = save.cleared[r], won = fight(r, i); if (won == null) return;
        if (won) { battles.win++; mark(`r${r}i${i + 1}`); if (i === ISLANDS_PER_REGION - 1) mark('fortress' + r); }
        else { battles.loss++; // farm an easier island for loot instead
          if (i > 0) { const w2 = fight(r, i - 1); battles.replay++; } return; }
      }
    }
    function claimQuests(){ for (let k = 0; k < 5; k++) { renderQuest(); const b = $('qClaim'); if (!b) break; b.click(); } }
    const snap = () => `d${day()} lv${save.lvl} hq${hqLv()} dock${lvOf('dock')} nest${lvOf('nest')} pond${lvOf('pond')} crit${save.crit.length}/${B('den').reduce((s, b) => s + denCap(b.lv), 0)} best${Math.max(0, ...save.crit.map(c => c.t))}★ cleared${save.cleared.join('/')} coins${Math.floor(save.coins)} food${Math.floor(save.food)} gems${save.gems} plot${save.plot.w}x${save.plot.h} quest#${save.quest} wins${battles.win}/${battles.win + battles.loss} hybrids${Object.keys(save.tips).filter(k => k.startsWith('found-')).length}`;
    let lastQuest = -1, lastQuestDay = 0;
    for (let d = 0; d < DAYS; d++) {
      for (let s = 0; s < P.per; s++) {
        // session start
        raidCheck(); closeModals(); tick();
        for (let minute = 0; minute < P.len; minute++) {
          for (const b of save.bld) { const n = stored(b); if (n >= storeCap(b.k, b.lv) * .99) waste[b.k === 'farm' ? 'food' : 'coins']++; collect(b, true); }
          claimQuests(); doNest(); doMerge(); doBuilds(); if (minute % 3 === 0) doBattles(); closeModals();
          window.__now += 60e3; tick();
          for (let k = 0; k < 3; k++) await new Promise(r => setTimeout(r, 0));   // let queued timeouts (level-ups) run
          closeModals();
        }
        persist();
        if (hqLv() >= 2) mark('hq2'); if (hqLv() >= 4) mark('hq4'); if (hqLv() >= 7) mark('hq7'); if (hqLv() >= 10) mark('hq10');
        [1, 2, 3].forEach(r => { if (regionOpen(r)) mark('region' + r); });
        // gap until next session (spread over ~14 waking hours, then overnight)
        window.__now += s < P.per - 1 ? 14 * H / P.per : (24 - 14 + 14 / P.per) * H - P.per * P.len * 60e3; tick();
      }
      if (save.quest !== lastQuest) { lastQuest = save.quest; lastQuestDay = d; } else if (d - lastQuestDay === 5) stalls.push(`quest #${save.quest} "${questAt(save.quest).text}" stuck 5 days`);
      if (d % 5 === 4 || d === DAYS - 1) log.push(snap());
    }
    persist(); return { log, mile, battles, stalls, waste, blocked, spent, saveJson: localStorage.getItem('hatchwild-save-v1') };
  }, { P, DAYS });
  console.log(`=== ${PROFILE}: ${P.per} sessions/day x ${P.len} min, ${DAYS} days ===`);
  out.log.forEach(l => console.log(l));
  console.log('milestones (day):', JSON.stringify(out.mile));
  console.log('battles', JSON.stringify(out.battles), 'full-storage minutes', JSON.stringify(out.waste), 'blocked', JSON.stringify(out.blocked), 'berries spent on warming/snacks', JSON.stringify(out.spent));
  console.log('stalls', out.stalls.slice(0, 8));
  console.log('errors', errs.length, [...new Set(errs)].slice(0, 8));
  if (process.env.OUT) require('fs').writeFileSync(process.env.OUT, out.saveJson);
  await br.close();
})();
