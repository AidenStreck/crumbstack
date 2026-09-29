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

## Studio: your control dashboard

Studio is at **https://aidenstreck.github.io/crumbstack/studio/**. It shows each game's website and iPhone build status, recent changes, the App Store launch checklist, and every change request with its progress.

To install it on your computer as an app, open it in **Chrome or Edge** and click the **Install** icon at the right end of the address bar. It then gets its own window and taskbar icon.

**How requests work:** type a request in Studio and click **Send request**. GitHub opens with it filled in, and you click **Create**. An agent builds the change on its own branch, and Studio shows **Ready for your approval**. Click **Review and approve**, try it, and press **Merge** on GitHub to make it go live. The rules agents follow are in `CLAUDE.md`.

## Play it on your iPhone (free)

1. Open the website link (Settings → Pages in this repo shows it) in **Safari** on your iPhone.
2. Tap the **Share** button, then **Add to Home Screen**.
3. Open Crumbstack from your home screen. It runs full screen and works offline after the first visit.

## How the iPhone app gets built

This project uses **Capacitor**, which wraps the game in a real native iPhone app. Building an iPhone app needs Apple's Xcode, which only runs on a Mac, so GitHub builds it on a Mac in the cloud. Open the **Actions** tab to see each build. A green check means the app compiled.

## Getting it onto the App Store

Apple Developer account: done (accepted Sept 29, 2026).

1. **Register the app ID.** developer.apple.com → Certificates, IDs & Profiles → Identifiers → + → App IDs → App. Description `Crumbstack`, Bundle ID (Explicit) `com.crumbstack.game`. Tick **In-App Purchase** (it's usually on already).
2. **Create the app.** appstoreconnect.apple.com → Apps → + → New App: iOS, name `Crumbstack`, language English (U.S.), bundle ID `com.crumbstack.game`, SKU `crumbstack`, Full Access.
3. **Make an API key** (lets GitHub's Mac sign and upload for you). App Store Connect → Users and Access → Integrations → App Store Connect API → Team Keys → +. Name `GitHub`, access **Admin**. Download the `.p8` file (Apple only lets you download it once). Note the **Key ID** and the **Issuer ID** shown above the list.
4. **Find your Team ID.** developer.apple.com/account → Membership details → Team ID (10 letters/numbers).
5. **Add four secrets to GitHub.** github.com/AidenStreck/crumbstack → Settings → Secrets and variables → Actions → New repository secret:
   - `ASC_KEY_ID`: the Key ID
   - `ASC_ISSUER_ID`: the Issuer ID
   - `ASC_KEY_P8`: open the .p8 file in Notepad and paste all of it, including the BEGIN/END lines
   - `APPLE_TEAM_ID`: the Team ID
6. **Send a build.** GitHub → Actions → iPhone app → Run workflow (or push anything to main). About 15–30 minutes later it appears in App Store Connect → TestFlight. Install the **TestFlight** app on your iPhone and add yourself as an internal tester to play it.
7. **Paid Apps agreement** (needed for coin purchases): App Store Connect → Business → sign the Paid Apps agreement and fill in tax and bank info. Then the coin packs get set up as in-app purchases and connected, with a Restore purchases button.
8. Fill in the store page from `store/listing.md` and the screenshots, then submit for review.

## Working on it yourself (optional)

Requires Node.js 22.

```
npm install
npm run build        # builds www/
```

Then open `www/index.html` in a browser.
