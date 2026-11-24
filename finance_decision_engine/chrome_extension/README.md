# FDE Chrome Extension (prototype v1) - Amazon.in

Open an Amazon.in product page, click the extension, confirm the detected price, and get an
affordability verdict from your **existing FDE backend**.

**Principle:** the FastAPI engine computes every number and the SAFE/MODERATE/RISKY verdict.
The extension only collects inputs and displays the response. AI (server-side OpenAI) only
explains the engine's numbers. No financial maths exists in this JavaScript.

## Architecture

```
popup.html/css/js ──(user clicks icon)──► chrome.scripting injects content.js into the active
                                          Amazon.in tab (activeTab), asks for {title, price}
        │
        ├─ profile  ── chrome.storage.local  (income, expenses, savings, optional EMI defaults)
        │
        └─ POST {API_BASE_URL}/api/v1/purchase-decision/analyze
             call 1: include_ai_explanation=false → engine result rendered immediately
             call 2: include_ai_explanation=true  → AI card (never changes call-1 numbers;
                                                    discarded if decision/score differ)
```

Design choices:
- **No static content script.** `content.js` is injected only when you open the popup (via
  `activeTab` + `scripting`), so the extension has no standing access to any site and shows no
  "read your data on amazon.in" install warning.
- **Two calls** so the deterministic verdict never waits on, or depends on, AI.
- The product **title is display-only**; it is not sent to the backend.

## Files

```
chrome_extension/
├── manifest.json     MV3; permissions: activeTab, storage, scripting; host: localhost:8000
├── config.js         the ONLY place the API URL is configured
├── popup.html/.css   UI (FDE palette)
├── popup.js          profile, detection, validation, API call, rendering
├── content.js        Amazon.in title/price reader (reads only those two things)
├── README.md
└── tests/            optional automated tests (jsdom) + synthetic fixtures
```

Backend changes (in `backend/`): see "Backend changes" below.

## Run the backend locally

```bash
cd finance_decision_engine
pip install -r requirements.txt
cp .env.example .env            # optional: add OPENAI_API_KEY for real AI; without it you get the fallback explanation
uvicorn backend.main:app --reload --port 8000
curl http://127.0.0.1:8000/health      # {"status":"healthy"}
```

## Install the extension

1. Open `chrome://extensions`.
2. Turn on **Developer mode** (top right).
3. Click **Load unpacked** and choose the `chrome_extension/` folder.
4. (Optional) Pin the FDE icon from the puzzle-piece menu.
5. Open an Amazon.in product page, click the FDE icon.
6. Open **Your financial profile**, enter income, expenses, savings → **Save profile**.
7. Confirm the detected price → choose Cash or EMI → **Check affordability**.

After editing any extension file, press the reload icon on the extension card.

## Configuration

**Development** (default): `config.js` → `ENVIRONMENT: "development"` → `http://127.0.0.1:8000`.
`manifest.json` already lists `http://127.0.0.1:8000/*` and `http://localhost:8000/*`.

**Production:**
1. Deploy the backend. **Verify** `GET <url>/health` and `POST <url>/api/v1/purchase-decision/analyze`
   work. The `bank-statement-analyzer-fb0s.onrender.com` URL in the website's `config.js` is not
   verified to serve this route - I could not confirm it, so it is deliberately not used here.
2. `config.js` → `API_BASE_URLS.production = "https://api.yourdomain.com"` and `ENVIRONMENT: "production"`
   (HTTPS is enforced in code).
3. `manifest.json` → add `"https://api.yourdomain.com/*"` to `host_permissions`.
4. Backend CORS (env vars):
   - `FDE_EXTENSION_IDS=<your extension id>` - copy the ID from `chrome://extensions`.
     (An unpacked extension's ID is stable for a given folder path; a Chrome Web Store build gets its own ID.)
   - `CORS_ALLOW_ORIGINS=https://your-website.com` (default `*`).
   - Credentials are disabled; the API uses no cookies.
5. Keep `OPENAI_API_KEY` only on the server.

## Backend changes (minimal, reasons)

| File | Change | Why |
|---|---|---|
| `backend/main.py` | CORS: credentials off; methods/headers narrowed; `chrome-extension://<32 chars>` origin allowed; optional `FDE_EXTENSION_IDS` and `CORS_ALLOW_ORIGINS` env vars | Previously `*` **with** credentials. Extension origin is handled explicitly. CORS is not authentication. |
| `.../purchase_decision/schemas.py` | Field bounds (income>0, amounts ≥0, months 1-120, rate 0-60) | Bad input returns a clear 422 instead of a crash or nonsense. |
| `routers/purchase_decision.py` | 422 when cash + expenses=0, or down payment > price | Cash runway divides by expenses (was a 500). |

No endpoint, schema field or calculation was added or changed. Existing website behaviour is unchanged
except that previously-crashing or nonsensical inputs now give a 422.

## Tests I actually ran

| Suite | Result |
|---|---|
| Backend `pytest backend/tests` (AI layer + CORS/validation) | 15 passed |
| `tests/content.test.js` (content script vs **synthetic** Amazon-style fixtures) | 10 passed |
| `tests/popup.test.js` (popup in jsdom, stubbed `chrome` APIs, mocked backend) | 21 passed |
| Same popup suite with `FDE_LIVE=1` against the real running FastAPI backend | 22 passed (cash/EMI values on screen equal the API response) |
| CORS preflight with a `chrome-extension://` Origin (curl); pinned-ID mode (TestClient) | verified |

Run them yourself:
```bash
python -m pytest backend/tests -q
cd chrome_extension/tests && npm install && npm test                 # mocked
uvicorn backend.main:app --port 8000 &  FDE_LIVE=1 npm test           # live (backend must be running)
```

**NOT tested:** loading in real Chrome, and detection on real Amazon.in pages. I have no browser or
Amazon access here. The Amazon selectors in `content.js` come from commonly seen Amazon page
structure (`#productTitle`, `.priceToPay .a-offscreen`, `.a-text-price` for struck prices) and are
exercised only against fixtures I wrote to imitate it. **Amazon changes its markup often - expect to
tune `PRICE_TIERS` after trying real pages.** The popup shows which tier matched, to help with that.

## Manual test checklist (do these in Chrome)

**Extension**
- [ ] Load unpacked; popup opens; no errors on `chrome://extensions` → "Errors".
- [ ] Save profile; close and reopen popup → values come back, badge says "Saved locally".
- [ ] Invalid profile values (blank, `abc`, expenses `0`) → red inline errors, nothing saved.
- [ ] Clear saved profile → fields empty, "Not set up", Check shows "Save your financial profile first".
- [ ] On a non-Amazon site → "This website isn't supported yet"; typing a price manually still works.
- [ ] On an Amazon.in search/results page → "isn't a product page".

**Product detection (real Amazon.in pages)**
- [ ] A normal product page → title and price filled; note shows "Detected ₹… (tier)".
- [ ] Compare with the page: the **selling price**, not MRP/crossed-out, not "EMI from ₹…", not a carousel item.
- [ ] A product whose price is `₹1,29,999` → input shows `129999`; `₹60,000` → `60000`.
- [ ] A product with no price (unavailable) → "Couldn't detect the price", field blank, manual entry works.
- [ ] Change the variant on the page, press **Detect from page** → price updates.
- [ ] Edit the detected price by hand → previous result clears and asks you to re-run.

**Backend / analysis** (backend running)
- [ ] Cash purchase → result card + AI card appear.
- [ ] EMI purchase (down payment, months, rate) → EMI, EMI share, surplus after EMI shown.
- [ ] Compare on-screen numbers with `curl` / Swagger (`/docs`) for the same inputs (amounts display rounded to ₹).
- [ ] Down payment above price, price `0` → inline errors, no request (DevTools → Network).
- [ ] Stop the backend → "Can't reach the FDE service…".
- [ ] No `OPENAI_API_KEY` (or wrong key) → verdict shown, AI card says standard explanation / unavailable.
- [ ] Untick "Include AI explanation" → only one request, no AI card.

## Known prototype limitations

- Amazon.in only; selectors unverified on live pages (see above); Amazon A/B tests may break them.
- Profile is stored unencrypted in `chrome.storage.local` on this device; anyone with access to the
  browser profile could read it. It is sent to your backend only when you press Check.
- No authentication or rate limiting on the API; CORS is not access control. Add both before launch.
- Profile is one set of numbers (no multiple profiles, no currency other than INR).
- Backend has no "positive factors" field; the AI card shows `key_points`, `risks`, `suggestions`.
- Amounts are shown rounded to whole rupees; EMI share shows the backend's value as returned.
- Dependent EMIs/loans you already pay are not modelled (the engine doesn't take them).
- No extension icons yet (Chrome shows a default one).
- Popup closes when you click away; an in-flight check is lost.

## Done vs future

**Done:** MV3 popup, on-demand Amazon.in detection with manual override, local profile
(save/edit/clear), cash/EMI, existing endpoint integration, deterministic-first rendering,
AI card with fallback handling, error states, backend CORS/validation hardening, automated tests.

**Future:** more retailers, real-page selector hardening, icons, API auth + rate limiting,
Chrome Web Store packaging (pinned ID/`key`), in-page badge near the price, price-history,
multiple profiles, loading existing EMIs.
