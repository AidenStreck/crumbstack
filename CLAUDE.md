# Crumbstack: rules for agents working in this repo

The owner is not a programmer. He sends requests from the Studio dashboard, reviews the result, and approves it. Everything you hand back must be something he can judge by playing it, explained in plain words.

## Where things are

- `src/game.html` is the entire game (HTML, CSS and JS in one file). Almost every request is a change here.
- `prototypes/tidy-tides/src.html` is the second game, **Tidy Tides** (a single file, no doctype/head). Requests whose title names "Tidy Tides" are changes there, not to Crumbstack. Start commit messages for it with `Tidy Tides:` so Studio files them under that game. Its save key is `tidytides-save-v2`: same rules as Crumbstack's save.
  - **Tidy Tides events** live in `EVENT` (Spooky Shore runs every Oct 1 – Nov 2; preview any time by adding `#spooky` to the link). A new seasonal event copies that shape: dates, a reward track, and a page in `CREATURES` for its stickers. New coasts also need an album page in `CREATURES` (5 creatures + 1 rare).
  - **iPhone app & rewarded videos**: `scripts/ios-app.mjs` holds each game's bundle ID, version and ad settings; the iOS workflow sends Tidy Tides to TestFlight on every push to `main`. Tidy Tides has optional rewarded videos (Google AdMob) in the iPhone app only: double the welcome-back coins, double the daily gift, and Crew Rush (helpers 2× for 5 min), max 8 a day, see `ADS` in the game. The website never shows ads (`#fakeads` in the link fakes a 2-second video for testing). Keep `ads.test: true` until the version is actually submitted to the App Store, and when it ships the App Store privacy answers and age rating (Advertising) must say ads are in.
  - **Tidy Tides pacing** (the owner wants a coast to take a normal player a few days): areas heal by `HEAL_NEED` pieces recycled; trash left on the sand 25+ seconds is taken by the rising tide and costs a little health (never below the last wildlife milestone); upgrades are gated by areas open / machines built (`GLOBAL_GATE`, `areaLocked`, `machLocked`); the next area's Restore spot appears at 90% healed; the dock appears only after every goal in `GOAL_PLAN`, and sailing needs `SAIL_COST` coins saved. Sea Stars are scarce on purpose (10 per sail; small perks). After changing costs, healing or rewards, run `node scripts/build.mjs && HOURS=6 node scripts/tidytides-bot.cjs`: the bot plays near-perfectly and should finish the first coast in about 2.5 hours of play (a real player takes 2-3x as long).
  - **Adding a new Tidy Tides coast** (new areas, trash, goods, helper animals): add an entry to `COASTS` in the data section (same shape as Coral Bay), put it before the tours start, and draw each new item in `drawItem` (plus any new helper kind in `drawCrab`/`CARRIER_LOOK`, hats in `drawHat`, landmarks in `drawLandmark`). Keep prices by position (`AREA_COST`, `MACH_COST`, `SLOT_PRICE`): the owner doesn't want costs growing forever. Item ids must be unique across all coasts and must not clash with upgrade keys (bag, shoes, crabs, pelicans, display, umbrella).
- `prototypes/sunsprout/src.html` is the third game, **Sunsprout** (light-bending puzzle). Requests naming "Sunsprout" go there; start commit messages with `Sunsprout:`. Levels are generated from seeds in `levelSpec`/`getLevel` and checked by solvers. Rule: every beam must end in a pot (no wasted light). Levels 6+ load from the precomputed `LEVEL_SEEDS` table (which also stores each Place level's honest move goal and blocking rocks): 5 modes (Turn, Place, Split, Color, Warp) × 250 levels. Every 10th level (`isChallenge`) is an optional extra-hard challenge: skipping it doesn't block the next level, beating it grows a golden bloom. Levels 1–50 of the first four modes are the originals: don't change their specs or seeds (players have progress on them). New levels or modes: add specs in `laterSpec`, then run `node scripts/sunsprout-levels.cjs` (only fills in missing seeds). After changing the generator itself, run it with `--all` (slow). Save key `sunsprout-save-v1`.
- `prototypes/hatchwild/src.html` is the fourth game, **Hatchwild** (island base-builder with critters). Requests naming "Hatchwild" go there; start commit messages with `Hatchwild:`. Data (regions, `SPECIES`, `HYBRIDS`, `BLD` costs/times, `islandSpec` rival islands) is near the top; battles are in the BATTLE section. Build times grow ~2.3x per level (cap 4 days) on purpose: the owner wants regions to take weeks to months to unlock. `#fast` in the link runs timers 60x, `#test` exposes `window.__hw`. If you change battle numbers, re-check that early islands stay winnable with starter critters. After changing costs, times or rewards, run the play bot (`scripts/hatchwild-bot.cjs`, PROFILE casual/regular/hardcore) and check the pacing: for a regular player the Tropic fortress falls around day 5, the Sky Islands open then, and the Undersea Domes around day 70–75. Save key `hatchwild-save-v1`. **Real artwork**: PNGs in `prototypes/hatchwild/art/` replace the code-drawn art once listed in `ART_FILES` (critters/<species>.png feet at the bottom edge facing right; buildings/<key>-<1|2|3>.png for levels 1–3/4–6/7+, placed by `BLD_META` (the width of the picture's base diamond and its front corner, in picture pixels; keep the original in `art-src/hatchwild/`); icons/<coin|food|gem|hammer|bolt>.png). Trim transparent edges before adding. **Animated critters**: keep the original picture in `art-src/hatchwild/<id>.png`, mark its head/legs/eyes in `RIGS` in `scripts/hatchwild-rig.py`, run `python3 scripts/hatchwild-rig.py <id>` and paste the printed line into `RIGS` in the game. Rigged critters walk, breathe, bob and blink. **Preferred: pose sheets.** Save the ChatGPT sprite sheet (see-through background) as `art-src/hatchwild/<id>-sheet.png`, list which poses are idle/walk/nap in `SHEETS` in `scripts/hatchwild-sheet.py`, run it and paste the printed line into `ANIMS` in the game. Napping critters sleep by the den. Buildings are still pictures (the owner found ChatGPT's animated buildings moved too much); the game adds a barely-there breath and a few drifting glints. **Decor shop** (`DECOR_SHOP`, coins only, never real money): placed decorations live in `save.decor` and can be moved or sold; critters can be tapped for a bio, a treat (+10% attack next battle) and petting.
- `studio/` is the owner's control dashboard. `studio/apps.json` lists every game and its App Store launch checklist.
- `scripts/build.mjs` builds `www/` (website + Studio). `scripts/patch-ios.mjs` customizes the generated iPhone project.
- `.github/workflows/website.yml` publishes `www/` to GitHub Pages on every push to `main`.
- `.github/workflows/ios.yml` builds the iPhone app on a GitHub Mac runner on every push to `main`.
- `www/` and `ios/` are generated. Never commit them.

## How to handle a request (a GitHub issue)

1. Read the issue. If it is unclear, or it would spend money, delete player progress, or change prices, comment with one plain question and stop.
2. Create a branch named `request-<issue number>` from `main`.
3. Make the change in `src/game.html` (or the relevant file). Keep the game's look: Lilita One + Nunito, plum/butter/pink palette, hand-drawn canvas art.
4. Check it: run `node scripts/build.mjs`, then load `www/index.html` in a headless browser and play through the affected part. There must be no console errors.
5. Commit with a message that ends in `Closes #<n>` (so the request closes itself when approved), then push the branch. Open a pull request titled `Request #<n>: <short summary>` whose body says `Closes #<n>`, what changed in plain words, and how to try it. If you can't open pull requests, the pushed branch is enough: Studio shows it for approval.
6. **Never push to `main` and never merge.** The owner approves by merging the pull request, and that is what makes it go live.

## Game ideas (issues titled `[Game idea] ...`)

These are new game concepts, not changes to Crumbstack. Don't build a game.

1. On branch `request-<n>`, add the idea to `studio/ideas.json` at stage `"Idea"` with `"by": "You"`. Tighten the pitch to 1–2 sentences and add a one-line `notes` on what would make it stand out (and anything that makes it too close to an existing game, since Apple rejects lookalikes).
2. Open the pull request as usual (`Closes #<n>`). Merging adds it to the board.
3. When the owner asks to move an idea to **Prototype**, build a small playable version as a single file at `prototypes/<id>/src.html` (no doctype/head: the build wraps it) (same approach as `src/game.html`) and set its stage to `"Prototype"`. It will be playable at `https://aidenstreck.github.io/crumbstack/prototypes/<id>/`. Put that link in the idea's `notes`.

## Marketing (requests typed `[Marketing]`)

**Marketing is paused until Crumbstack is on the App Store.** The owner wants people able to download before any posting. When the App Store submission is live, remind him to turn the Monday marketing agent back on (it's a scheduled task named "Crumbstack marketing agent") and set up Buffer.


- Social posts live in `studio/marketing.json` and show in Studio's Marketing tab. Add new posts there with a hook, caption and hashtags. Always keep "free, no ads".
- Gameplay clips come from `scripts/clips.cjs` (a bot plays the real game and records 1080×1920 MP4s into `marketing/clips/`). Add a clip entry and run it, e.g. `node scripts/build.mjs && node scripts/clips.cjs <clip-id>`. Clips must show real gameplay. Never fake or stage things the game can't do.
- **Voiceover videos** (the main pre-launch content): add an entry to `marketing/voiced.json` with a gameplay clip id and 4–6 short spoken lines (keep the voice under about 12 seconds, end with "Free game, no ads. Link in bio."). Add a matching post to `studio/marketing.json` with `"media": {"dir": "voiced", "id": "<id>"}` and `"phase": "now"`. After merge, the **Make videos** GitHub Action renders it with an AI voice (Kokoro), captions and the game's music. Don't render voiceovers yourself.
- Screenshots come from `scripts/screenshots.cjs`.
- Weekly batches go on a branch named `marketing-<YYYY-MM-DD>`. Studio shows unmerged `marketing-*` branches as waiting for approval.
- You draft; the owner posts. Never post anywhere yourself.

## Guardrails

- Player saves live in `localStorage` under `crumbstack-save-v2`. Never rename the key or drop fields. Add new fields with defaults.
- Real-money purchases are test-only until the App Store version exists. Never make a purchase button charge anything.
- Keep levels beatable. If you change difficulty, play the changed levels in the headless browser.
- Anything posted publicly (store text, social posts) is a draft in the pull request for the owner to approve, never published directly.
