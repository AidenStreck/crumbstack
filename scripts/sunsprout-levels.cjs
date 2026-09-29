// Sunsprout level seeds: finds a good seed for every level (and the honest move goal for Place levels),
// writes them into prototypes/sunsprout/src.html, then re-checks every level (5 modes x 250).
// Adding levels or a mode:          node scripts/sunsprout-levels.cjs          (only finds seeds for levels that don't have one)
// After changing the generator:     node scripts/sunsprout-levels.cjs --all    (redoes every level; takes a couple of hours)
const fs = require('fs'), file = __dirname + '/../prototypes/sunsprout/src.html';
let html = fs.readFileSync(file, 'utf8');
const engine = () => html.slice(html.indexOf('// ================= PUZZLE ENGINE ================='), html.indexOf('// ================= ART ================='));
const run = (code, extra) => new Function(code + '\n' + extra)();
const all = process.argv.includes('--all'), old = all ? {} : JSON.parse(html.match(/\/\*SEEDS\*\/(.*?)\/\*END\*\//s)[1]);
const seeds = run('var HARDEN_BUDGET = 150000;\n' + engine().replace(/\/\*SEEDS\*\/.*?\/\*END\*\//s, '/*SEEDS*/{}/*END*/'), `
  const out = ${JSON.stringify(old)};
  for (let wi = 0; wi < WORLDS.length; wi++) for (let i = 0; i < PER_WORLD; i++) {
    const k = wi + ':' + i; if (out[k]) continue; const lv = findLevel(levelSpec(wi, i), levelSeed(wi, i));
    if (!lv) throw new Error('no level for ' + k);
    if (lv.mode === 'place' && i >= INTRO) { let km = lv.kmin || lv.solution.length; for (let kk = 1; kk < km; kk++) { const r = solvePlace(lv, kk, 1, 250000); if (r.count) { km = r.used; break; } }
      const need = [0, 0], have = [0, 0]; lv.solution.forEach(s => need[s.o]++); lv.tray.forEach(p => have[p.o]++);
      lv.kmin = km; lv.par = km + Math.min(Math.max(0, need[0] - have[0]) + Math.max(0, need[1] - have[1]), km); }
    out[k] = lv.mode === 'place' ? [...lv.found, lv.par, lv.kmin || lv.solution.length, lv.addedRocks || []] : lv.found;
    if (i % 10 === 9) console.log('found', k);
  }
  return out;`);
html = html.replace(/\/\*SEEDS\*\/.*?\/\*END\*\//s, '/*SEEDS*/' + JSON.stringify(seeds) + '/*END*/');
fs.writeFileSync(file, html);
const fails = run(engine(), `
  const f = [];
  for (let wi = 0; wi < WORLDS.length; wi++) for (let i = 0; i < PER_WORLD; i++) { const lv = getLevel(wi, i); if (!lv) { f.push('missing ' + wi + ':' + i); continue; }
    const b = cloneBoard(lv); if (lv.mode === 'place') lv.solution.forEach(s => b.g[s.i] = { t:'mirror', o:s.o }); else b.g.forEach(p => { if (p && p.t === 'mirror') p.o = p.sol; });
    if (!judge(b, simulate(b)).solved) f.push('unsolvable ' + wi + ':' + i); if (judge(lv, simulate(lv)).solved) f.push('starts solved ' + wi + ':' + i); }
  return f;`);
console.log(fails.length ? 'PROBLEMS: ' + fails.join(', ') : 'All ' + Object.keys(seeds).length + ' levels solvable. Seeds written.');
