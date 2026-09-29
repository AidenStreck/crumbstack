# Crumbstack

A burger-stacking puzzle game for iPhone. Catch falling ingredients in the order each customer asks for, across 24 levels in three worlds.

## What's in here

| Folder / file | What it is |
|---|---|
| `src/game.html` | **The whole game.** This is the only file you normally change. |
| `scripts/build.mjs` | Turns the game into the `www/` web app (adds the app icon, offline support and bundled fonts). |
| `scripts/patch-ios.mjs` | Customizes the iPhone project: icon, launch screen, portrait only, full screen. |
| `resources/` | App icon (1024×1024 for the App Store), smaller icons and the launch screen image. |
| `capacitor.config.json` | Settings for the iPhone app shell (app name and bundle ID). |
| `.github/workflows/website.yml` | Publishes the game as a free website each time `main` changes. |
| `.github/workflows/ios.yml` | Builds the iPhone app on GitHub's free Mac servers each time `main` changes. |

The `www/` and `ios/` folders are generated automatically and are not stored in the repo.

## Play it on your iPhone (free)

1. Open the website link (Settings → Pages in this repo shows it) in **Safari** on your iPhone.
2. Tap the **Share** button, then **Add to Home Screen**.
3. Open Crumbstack from your home screen. It runs full screen and works offline after the first visit.

## How the iPhone app gets built

This project uses **Capacitor**, which wraps the game in a real native iPhone app. Building an iPhone app needs Apple's Xcode, which only runs on a Mac, so GitHub builds it on a Mac in the cloud. Open the **Actions** tab to see each build. A green check means the app compiled.

## Before the App Store (needs the $99/year Apple Developer account)

1. Join the Apple Developer Program at developer.apple.com.
2. Create the app in App Store Connect with the bundle ID `com.crumbstack.game` (or change it in `capacitor.config.json` first).
3. Create an App Store Connect API key and add it to this repo's secrets.
4. Add the signing + TestFlight upload step to `ios.yml`.
5. Set up the coin packs as in-app purchases and connect them to the shop. Add a **Restore purchases** button.
6. Add a privacy policy page, App Store screenshots and the description.

## Working on it yourself (optional)

Requires Node.js 22.

```
npm install
npm run build        # builds www/
```

Then open `www/index.html` in a browser.
