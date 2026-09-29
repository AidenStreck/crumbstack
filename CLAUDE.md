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
5. Push the branch. Open a pull request titled `Request #<n>: <short summary>` whose body says `Closes #<n>`, what changed in plain words, and how to try it.
6. **Never push to `main` and never merge.** The owner approves by merging the pull request, and that is what makes it go live.

## Guardrails

- Player saves live in `localStorage` under `crumbstack-save-v2`. Never rename the key or drop fields. Add new fields with defaults.
- Real-money purchases are test-only until the App Store version exists. Never make a purchase button charge anything.
- Keep levels beatable. If you change difficulty, play the changed levels in the headless browser.
- Anything posted publicly (store text, social posts) is a draft in the pull request for the owner to approve, never published directly.
