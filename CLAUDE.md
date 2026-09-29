# Crumbstack: rules for agents working in this repo

The owner is not a programmer. He sends requests from the Studio dashboard, reviews the result, and approves it. Everything you hand back must be something he can judge by playing it, explained in plain words.

## Where things are

- `src/game.html` is the entire game (HTML, CSS and JS in one file). Almost every request is a change here.
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
