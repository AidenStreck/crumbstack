// Pacing bot: plays a brand-new Tidy Tides coast with the real game rules, fast-forwarded (no drawing), and prints
// when each milestone is reached in minutes of play. It plays near-perfectly, so a real player takes 2-3x as long.
// Usage: node scripts/build.mjs && HOURS=6 node scripts/tidytides-bot.cjs   (takes about a minute)
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = []; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + require('path').resolve(__dirname, '../www/prototypes/tidy-tides/index.html') + '#test#spooky'); await pg.waitForTimeout(1500);
  await pg.evaluate(() => { const pb = document.getElementById('play'); if (pb) pb.click(); });
  await pg.waitForTimeout(800);
  const MAXH = +process.env.HOURS || 10;
  const res = await pg.evaluate(([src, MAXH]) => window.__ev('(' + src + ')(' + MAXH + ')'), [((MAXH) => {
    const T = window.__tt; T.endTutorial && T.endTutorial(); window.__nodraw = true; running = false;
    save.coached = new Proxy({}, { get: () => 1, set: () => true });
    const log = [], viol = [], mins = () => +(S.t / 60).toFixed(1), say = m => log.push(mins() + ' min: ' + m);
    const t0 = S.t; let lastGoal = save.goal, areasOpen = 1, candySeen = 0, candyGot0 = 0, nextBuy = 0, sailSeenAt = null, richAt = null, maxShoes = 0;
    const mark = {}; const dt = .05; const p = S.player;
    const goto = (x, y) => { keys.a = p.x > x + 3; keys.d = p.x < x - 3; keys.w = p.y > y + 3; keys.s = p.y < y - 3; };
    const clearUI = () => { document.querySelectorAll('.modalWrap,.tip,.toast').forEach(e => e.remove()); S.modal = false; coachQ.length = 0; };
    const buy = () => {
      const ps = pads().filter(q => q.kind !== 'sail' && !q.locked), padNeed = ps.length ? Math.min(...ps.map(q => q.cost - (save.pads[q.key] || 0))) : Infinity;
      for (const a of AREAS) { if (!A(a.id).unlocked) continue; S.boardOpen = a.id; renderBoard();
        for (let k = 0; k < 6; k++) { const rows = [...document.querySelectorAll('.sheet .up:not(.rush)')].map(r => ({ r, b: r.querySelector('.buy'), hl: r.classList.contains('hl') })).filter(o => o.b.dataset.cost && !o.b.disabled);
          const pickR = rows.find(o => o.hl) || rows.filter(o => +o.b.dataset.cost < padNeed * .6 || padNeed === Infinity).sort((x, y) => +x.b.dataset.cost - +y.b.dataset.cost)[0];
          if (!pickR) break; pickR.b.click(); } }
      closeBoard(); };
    const steps = MAXH * 3600 / dt;
    for (let i = 0; i < steps; i++) {
      if (i % 4 === 0) { if (document.querySelector('.modalWrap,.tip')) clearUI();
        // decide where to go
        const ps = pads().filter(q => q.kind !== 'sail' && !q.locked && save.coins >= q.cost - (save.pads[q.key] || 0));
        const goods = p.stack.filter(it => PRICE[it]), trashIn = p.stack.filter(it => !PRICE[it]);
        const mOut = MACHINES.filter(m => built(m) && mst(m).out > 0), full = p.stack.length >= cap();
        const topGood = [...p.stack].reverse().find(it => PRICE[it]);
        if (ps.length) goto(ps[0].x, ps[0].y);
        else if (goods.length && (full || goods.length >= Math.min(6, cap()) || !mOut.length)) { const m = MACHINES.find(q => q.output === topGood), a = dispCount(m.area) < dispCap(m.area) ? m.area : AREAS.find(q => A(q.id).unlocked && dispCount(q) < dispCap(q)) || m.area; goto(a.x + 200, L.sellY); }
        else if (mOut.length && !full) { const m = mOut.sort((x, y) => Math.abs(x.x - p.x) - Math.abs(y.x - p.x))[0]; goto(m.x, L.outY); }
        else if (trashIn.length && (full || trashIn.length >= cap() - 1)) { const m = MACHINES.find(q => built(q) && trashIn.includes(q.input) && mst(q).in < mst(q).in + 1 ); goto(m.x, L.inY); }
        else { const want = new Set(MACHINES.filter(built).map(m => m.input)); let best = null, bd = 1e9;
          const sps = S.specials.filter(s => !s.gone); for (const s of sps) { const d = Math.hypot(s.x - p.x, s.y - p.y); if (d < 400 && d < bd) { best = s; bd = d * .5; } }
          for (const a of AREAS) for (const tr of S.trash[a.id]) { if (tr.dead || !want.has(tr.type) || tr.y < waterline() + 4) continue; const d = Math.hypot(tr.x - p.x, tr.y - p.y); if (d < bd) { bd = d; best = tr; } }
          if (best) goto(best.x, best.y); else if (trashIn.length) { const m = MACHINES.find(q => built(q) && trashIn.includes(q.input)); goto(m.x, L.inY); } else goto(p.x, p.y); } }
      update(dt); featuresTick(dt);
      if (i % 40 === 0) {
        // goals
        for (let k = 0; k < 3; k++) { const g = goalAt(save.goal); if (g.t === 'sail') break; const [c, n] = goalProgress(g); if (c >= n) claimGoal(); else break; }
        if (S.t >= nextBuy) { nextBuy = S.t + 2; buy(); }
        const open = unlockedCount(); if (open > areasOpen) { areasOpen = open; say('opened area ' + open + ' (' + AREAS[open - 1].name + '), goal #' + (save.goal + 1) + ', shoes ' + save.shoes + ', bag ' + save.bag); }
        if (save.shoes > [1, 2, 4][open - 1] || save.bag > [2, 4, 6][open - 1]) viol.push(mins() + ': gate broken shoes ' + save.shoes + ' bag ' + save.bag + ' areas ' + open);
        for (const h of [.5, .9, 1]) for (const a of AREAS) { const k = a.i + ':' + h; if (!mark[k] && health(a) >= h) { mark[k] = 1; if (h !== .5) say(a.name + ' ' + h * 100 + '% healed'); } }
        const nl = pads().find(q => q.kind === 'area'); if (nl && !mark['pad' + nl.key]) { mark['pad' + nl.key] = 1; say('Restore spot for ' + nl.area.name + ' appeared (previous area ' + Math.round(health(AREAS[nl.area.i - 1]) * 100) + '% healed)'); }
        const sail = pads().some(q => q.kind === 'sail'); if (sail && save.goal < GOALS.length) viol.push(mins() + ': dock visible before goals done');
        if (sail && sailSeenAt == null) { sailSeenAt = mins(); say('all ' + GOALS.length + ' goals done, dock appeared, coins ' + Math.round(save.coins)); }
        if (sailSeenAt != null && richAt == null && save.coins >= SAIL_COST) { richAt = mins(); say('sail coins saved: can set sail'); break; }
        if (save.coins > 250000 && sailSeenAt == null) { say('STUCK? keys ' + JSON.stringify(keys) + ' modal ' + S.modal + ' payKey ' + S.payKey + ' dwell ' + S.dwell + ' wl ' + Math.round(waterline()) + ' machY ' + Math.round(L.machY) + ' cleanup ' + !!S.cleanup + ' placing ' + !!S.placing); break; }
        if (save.goal !== lastGoal && save.goal % 5 === 0) { lastGoal = save.goal; say('goal ' + save.goal + ' of ' + GOALS.length + ' done, coins ' + Math.round(save.coins)); }
      }
    }
    return { log, viol, simMin: mins(), goal: save.goal + '/' + GOALS.length, coins: Math.round(save.coins), stars: save.stars, wrappers: save.event.pts || 0, wrappersWashedUpToday: save.event.dayN, washed: S.washed || 0, recycled: AREAS.map(a => A(a.id).recycled).join('/'), shoes: save.shoes, bag: save.bag, speed: speed(), dbg: { pads: pads().map(q => [q.key, q.kind, Math.round(q.x), Math.round(q.y), q.cost, save.pads[q.key] || 0, !!q.locked]), px: Math.round(p.x), py: Math.round(p.y), maxY: L.playerMaxY, stack: p.stack.join(','), goal: goalText(goalAt(save.goal)), built: MACHINES.map(m => built(m) ? 1 : 0).join('') },
      areas: AREAS.map(a => ({ n: a.name, health: Math.round(health(a) * 100), crabs: A(a.id).crabs, pelicans: A(a.id).pelicans, mlv: a.machines.map(m => built(m) ? mlv(m) : '-').join('') })) };
  }).toString(), MAXH]);
  console.log(res.log.join('\n')); delete res.log; console.log(JSON.stringify(res, null, 1)); console.log('errors:', errs); await b.close();
})();
