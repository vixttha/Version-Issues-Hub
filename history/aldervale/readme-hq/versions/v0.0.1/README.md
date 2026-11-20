# AlderVale: Pact of Ten

A 3D fantasy RPG set at a spellcasting academy on floating islands. Create a wizard, explore the campus, and build a deck for turn-based duels.

**In development.** The first playable is a local guest journey through Breeze, from wizard creation to earning and saving your first quest rewards.

[Run locally](#run-locally) · [First playthrough](#first-playthrough) · [Troubleshooting](#troubleshooting) · [Validation](#validation) · [Report a bug](#report-a-bug)

## Run locally

You’ll need Git, Node.js **24.12.0 or later**, Bun **1.4.4**, and a browser with **WebGL 2** for the 3D campus. Run these commands in a terminal.

```bash
git clone https://github.com/vixttha/AlderVale-Pact-of-Ten.git
cd AlderVale-Pact-of-Ten
bun install --frozen-lockfile
bun run dev
```

Keep the server terminal open and visit [http://localhost:3000](http://localhost:3000). You can play as a guest without a Google account or an API key.

## First playthrough

1. On the title screen, choose **Breeze**, enter a wizard name, and use the **Human** race with **Rowan** as the appearance. Select **Begin Academy Journey**.
2. On campus, open **Duel**. Under **Solo Academy Skirmishes**, select **Frost**. Pick a spell you have enough pips to cast and select **Cast Turn**, or use **Pass (+Gain Pip)** to build up pips.
3. After winning, select **Claim Rewards & Return**. Open **Active Saga Quest** and check that **First Spark in the Ring** shows **Completed**.
4. Reload the page, select the same wizard in **Breeze**, and choose **Enter Aldervale**. Check that the quest is still complete and your Florin and Spell Shard totals match what you saw before reloading.

## Troubleshooting

- **3D world unavailable.** Try **Retry 3D**. You can still access your wizard and menus.
- **Guest progress could not be saved.** Check that the browser allows site storage, then select **Retry save** before reloading or closing the tab.
- **Your wizard is missing after reload.** Use the same browser profile, URL, and realm. Guest saves are stored in the browser. Clearing the site’s data removes them.

## Validation

Run `bun run validate:core` for the type check, rules lint, tests, production build, and HTTP/WebSocket checks. GitHub Actions also checks the guest flow in Chromium, Firefox, and WebKit and runs Firestore tests in a local emulator.

| What you want to check | Where to look |
| --- | --- |
| Build and test commands | [Validation guide](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/main/docs/VALIDATION.md) |
| Player journeys and regression coverage | [Test Vault](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/main/docs/test-vault/README.md) |
| Results for a specific commit | [GitHub Actions](https://github.com/vixttha/AlderVale-Pact-of-Ten/actions) |

## Report a bug

Search [GitHub Issues](https://github.com/vixttha/AlderVale-Pact-of-Ten/issues) first. Include the commit or build, browser and operating system, realm, and steps to reproduce. Describe what you expected and what happened.
