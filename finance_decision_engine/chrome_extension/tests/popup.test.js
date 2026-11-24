const test = require("node:test");
const assert = require("node:assert");
const path = require("path");
const { JSDOM } = require("jsdom");

const POPUP = path.join(__dirname, "..", "popup.html");
const PRODUCT_URL = "https://www.amazon.in/Acme/dp/B0ABCDEFGH";
const LIVE = process.env.FDE_LIVE === "1";

const CORE = {
  decision: "MODERATE", decision_score: 65, headline: "Your EMI uses 9% of your monthly income.",
  monthly_emi: 8884.88, emergency_runway_months: 5, savings_remaining: 280000,
  recommendation: "Keep an emergency fund.", monthly_surplus_after_emi: 51115.12,
  emi_ratio: 8.9, ai_explanation: null
};
const AI = { summary: "Looks manageable.", key_points: ["EMI is ₹8,885."], risks: ["Runway is short."],
  suggestions: ["Build savings first."], source: "ai", model: "gpt-test" };

const resp = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const tick = (ms = 40) => new Promise((r) => setTimeout(r, ms));

async function boot({ tabUrl = PRODUCT_URL, product, stored, sendFails = 0, fetchImpl } = {}) {
  const calls = { fetch: [], inject: 0, sent: 0 };
  const store = stored ? { fde_profile: stored } : {};
  const defaultProduct = { ok: true, product: { title: "Acme Laptop", price: 60000, priceText: "₹60,000",
    priceSource: "main price block (priceToPay)", ambiguous: false, candidates: [60000] } };

  const dom = await JSDOM.fromFile(POPUP, {
    runScripts: "dangerously", resources: "usable", pretendToBeVisual: true,
    beforeParse(window) {
      let fails = sendFails;
      window.chrome = {
        storage: { local: {
          get: async (k) => (k in store ? { [k]: store[k] } : {}),
          set: async (o) => Object.assign(store, JSON.parse(JSON.stringify(o))),
          remove: async (k) => { delete store[k]; }
        } },
        tabs: {
          query: async () => [{ id: 7, url: tabUrl }],
          sendMessage: async () => {
            calls.sent++;
            if (fails > 0) { fails--; throw new Error("Receiving end does not exist"); }
            return product === undefined ? defaultProduct : product;
          }
        },
        scripting: { executeScript: async () => { calls.inject++; } }
      };
      window.fetch = fetchImpl
        ? (url, opts) => { calls.fetch.push({ url, body: JSON.parse(opts.body) }); return fetchImpl(url, opts, calls.fetch.length); }
        : async () => { throw new TypeError("fetch failed"); };
    }
  });
  await new Promise((r) => dom.window.addEventListener("load", r));
  await tick();
  const w = dom.window, d = w.document;
  const $ = (id) => d.getElementById(id);
  const type = (id, v) => { $(id).value = v; $(id).dispatchEvent(new w.Event("input", { bubbles: true })); };
  const submit = (id) => $(id).dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
  return { w, d, $, type, submit, calls, store, status: () => $("status").textContent, text: (id) => $(id).textContent };
}

const PROFILE = { monthly_income: 100000, monthly_expenses: 40000, current_savings: 300000 };

test("no saved profile: analysis is blocked with a clear message and no request is made", async () => {
  const t = await boot({ fetchImpl: async () => resp(200, CORE) });
  assert.equal(t.$("profile-details").open, true);
  t.submit("purchase-form"); await tick();
  assert.match(t.status(), /Save your financial profile first/);
  assert.equal(t.calls.fetch.length, 0);
});

test("profile validation, save to chrome.storage.local, badge, and clear", async () => {
  const t = await boot();
  t.type("p-income", "100000"); t.type("p-expenses", "0"); t.type("p-savings", "3,00,000");
  t.submit("profile-form"); await tick();
  assert.equal(t.$("p-expenses").getAttribute("aria-invalid"), "true");
  assert.deepEqual(t.store, {});

  t.type("p-expenses", "40,000");
  t.type("p-emi-months", "12"); t.type("p-emi-rate", "10.5");
  t.submit("profile-form"); await tick();
  assert.deepEqual(t.store.fde_profile, { ...PROFILE, emi_months: 12, annual_interest_rate: 10.5 });
  assert.equal(t.text("profile-badge"), "Saved locally");

  t.$("clear-profile-btn").click(); await tick();
  assert.deepEqual(t.store, {});
  assert.equal(t.$("p-income").value, "");
  assert.match(t.status(), /cleared/);
});

test("saved profile is loaded on open", async () => {
  const t = await boot({ stored: PROFILE });
  assert.equal(t.$("p-income").value, "100000");
  assert.equal(t.text("profile-badge"), "Saved locally");
  assert.equal(t.$("profile-details").open, false);
});

test("corrupted stored profile is ignored, not treated as zeros", async () => {
  const t = await boot({ stored: { monthly_income: "abc" } });
  assert.equal(t.$("p-income").value, "");
  assert.equal(t.text("profile-badge"), "Not set up");
});

test("auto-detects title and price on a product page; user can edit the price", async () => {
  const t = await boot({ stored: PROFILE });
  assert.equal(t.$("product-title").value, "Acme Laptop");
  assert.equal(t.$("product-price").value, "60000");
  assert.match(t.text("detect-note"), /₹60,000/);
});

test("injects the content script when it isn't present yet", async () => {
  const t = await boot({ stored: PROFILE, sendFails: 1 });
  assert.equal(t.calls.inject, 1);
  assert.equal(t.$("product-price").value, "60000");
});

test("unsupported website and non-product Amazon page", async () => {
  let t = await boot({ tabUrl: "https://www.example.com/item" });
  assert.match(t.status(), /isn't supported yet/);
  assert.equal(t.calls.sent, 0);               // never talks to non-Amazon tabs
  t = await boot({ tabUrl: "https://www.amazon.in/s?k=laptop" });
  assert.match(t.status(), /isn't a product page/);
  t.type("product-price", "1999");            // manual entry still possible
  assert.equal(t.$("product-price").value, "1999");
});

test("price or title not detected", async () => {
  const none = { ok: true, product: { title: null, price: null, priceText: null, priceSource: null, ambiguous: false, candidates: [] } };
  let t = await boot({ product: none });
  assert.match(t.status(), /Couldn't detect the product title or price/);
  assert.equal(t.$("product-price").value, "");
  t = await boot({ product: { ok: true, product: { ...none.product, title: "X" } } });
  assert.match(t.status(), /Couldn't detect the price/);
});

test("ambiguous prices are surfaced to the user", async () => {
  const amb = { ok: true, product: { title: "X", price: 10000, priceText: "", priceSource: "s", ambiguous: true, candidates: [10000, 12500.5] } };
  const t = await boot({ product: amb });
  assert.match(t.status(), /Several prices/);
  assert.match(t.status(), /₹10,000/);
});

test("CASH flow: deterministic result first (no AI), then AI; request matches backend schema", async () => {
  const cash = { ...CORE, decision: "SAFE", decision_score: 90, monthly_emi: 0, emi_ratio: 0,
    savings_remaining: 240000, emergency_runway_months: 6, monthly_surplus_after_emi: 60000, headline: "You will retain 6 months." };
  const t = await boot({ stored: PROFILE, fetchImpl: async (u, o, n) => resp(200, n === 1 ? cash : { ...cash, ai_explanation: AI }) });
  t.submit("purchase-form"); await tick(80);

  assert.equal(t.calls.fetch.length, 2);
  assert.match(t.calls.fetch[0].url, /127\.0\.0\.1:8000\/api\/v1\/purchase-decision\/analyze$/);
  assert.deepEqual(t.calls.fetch[0].body, { ...PROFILE, purchase_amount: 60000, payment_mode: "cash", include_ai_explanation: false });
  assert.equal(t.calls.fetch[1].body.include_ai_explanation, true);

  const r = t.text("results");
  assert.match(r, /SAFE/); assert.match(r, /Score 90\/100/);
  assert.match(r, /Savings remaining₹2,40,000/); assert.match(r, /Emergency runway6 months/);
  assert.match(r, /Monthly surplus₹60,000/); assert.doesNotMatch(r, /Monthly EMI/);
  assert.match(t.text("ai-section"), /Looks manageable/);
  assert.match(t.text("ai-section"), /Runway is short/);
  assert.equal(t.$("check-btn").disabled, false);
});

test("EMI flow: validation, payload, and rendered values equal the backend response", async () => {
  const t = await boot({ stored: { ...PROFILE, emi_months: 12, annual_interest_rate: 12 },
    fetchImpl: async (u, o, n) => resp(200, n === 1 ? CORE : { ...CORE, ai_explanation: AI }) });
  t.type("payment-mode", "emi"); t.$("payment-mode").dispatchEvent(new t.w.Event("change"));
  assert.equal(t.$("emi-fields").hidden, false);
  assert.equal(t.$("emi-months").value, "12");        // prefilled from profile defaults

  t.submit("purchase-form"); await tick();            // down payment empty
  assert.equal(t.$("down-payment").getAttribute("aria-invalid"), "true");
  assert.equal(t.calls.fetch.length, 0);

  t.type("down-payment", "70000"); t.submit("purchase-form"); await tick();
  assert.match(t.text("err-down-payment"), /more than the price/);

  t.type("down-payment", "10,000"); t.submit("purchase-form"); await tick(80);
  assert.deepEqual(t.calls.fetch[0].body, { ...PROFILE, purchase_amount: 60000, payment_mode: "emi",
    down_payment: 10000, emi_months: 12, annual_interest_rate: 12, include_ai_explanation: false });
  const r = t.text("results");
  assert.match(r, /MODERATE/); assert.match(r, /Monthly EMI₹8,885/); assert.match(r, /EMI share of income8\.9%/);
  assert.match(r, /Monthly surplus after EMI₹51,115/); assert.match(r, /Savings remaining₹2,80,000/);
  assert.match(r, /Emergency runway5 months/); assert.match(r, /Your EMI uses 9%/);
});

test("invalid price values are rejected before any request", async () => {
  const t = await boot({ stored: PROFILE, fetchImpl: async () => resp(200, CORE) });
  for (const bad of ["", "abc", "0", "-5", "12.345", "5000000000"]) {
    t.type("product-price", bad); t.submit("purchase-form"); await tick(10);
    assert.equal(t.$("product-price").getAttribute("aria-invalid"), "true", `value "${bad}"`);
  }
  assert.equal(t.calls.fetch.length, 0);
  t.type("product-price", "₹1,29,999.50"); t.submit("purchase-form"); await tick(60);
  assert.equal(t.calls.fetch[0].body.purchase_amount, 129999.5);
});

test("unsaved profile edits block analysis", async () => {
  const t = await boot({ stored: PROFILE, fetchImpl: async () => resp(200, CORE) });
  t.type("p-income", "200000");
  assert.equal(t.text("profile-badge"), "Unsaved changes");
  t.submit("purchase-form"); await tick();
  assert.match(t.status(), /unsaved profile changes/);
  assert.equal(t.calls.fetch.length, 0);
});

test("AI failure keeps the deterministic result visible", async () => {
  const t = await boot({ stored: PROFILE, fetchImpl: async (u, o, n) => {
    if (n === 1) return resp(200, CORE);
    throw new TypeError("fetch failed");
  } });
  t.submit("purchase-form"); await tick(80);
  assert.match(t.text("results"), /MODERATE/);
  assert.match(t.text("ai-section"), /isn't available right now/);
  assert.equal(t.$("results").hidden, false);
});

test("AI fallback explanation is labelled; AI that disagrees with the engine is discarded", async () => {
  let t = await boot({ stored: PROFILE, fetchImpl: async (u, o, n) => resp(200, n === 1 ? CORE : { ...CORE, ai_explanation: { ...AI, source: "fallback", model: null } }) });
  t.submit("purchase-form"); await tick(80);
  assert.match(t.text("ai-section"), /AI is unavailable, so this is a standard explanation/);

  t = await boot({ stored: PROFILE, fetchImpl: async (u, o, n) => resp(200, n === 1 ? CORE : { ...CORE, decision: "SAFE", ai_explanation: AI }) });
  t.submit("purchase-form"); await tick(80);
  assert.match(t.text("ai-section"), /isn't available right now/);
  assert.match(t.text("results"), /MODERATE/);
});

test("AI checkbox off makes only one request and hides the AI card", async () => {
  const t = await boot({ stored: PROFILE, fetchImpl: async () => resp(200, CORE) });
  t.$("include-ai").checked = false;
  t.submit("purchase-form"); await tick(60);
  assert.equal(t.calls.fetch.length, 1);
  assert.equal(t.$("ai-section").hidden, true);
});

test("error states: unreachable, timeout, 422, 404, 500, bad schema", async () => {
  const cases = [
    [async () => { throw new TypeError("x"); }, /Can't reach the FDE service/],
    [async () => { const e = new Error("a"); e.name = "AbortError"; throw e; }, /took too long/],
    [async () => resp(422, { detail: [{ loc: ["body", "purchase_amount"], msg: "Input should be greater than 0", input: -1 }] }), /purchase_amount: Input should be greater than 0/],
    [async () => resp(404, { detail: "Not Found" }), /endpoint wasn't found/],
    [async () => resp(500, { detail: "Internal" }), /HTTP 500/],
    [async () => resp(200, { decision: "SAFE" }), /doesn't understand/]
  ];
  for (const [impl, re] of cases) {
    const t = await boot({ stored: PROFILE, fetchImpl: impl });
    t.submit("purchase-form"); await tick(60);
    assert.match(t.status(), re);
    assert.equal(t.$("results").hidden, true);
    assert.equal(t.$("check-btn").disabled, false);
  }
});

test("422 message never echoes the submitted value", async () => {
  const t = await boot({ stored: PROFILE, fetchImpl: async () => resp(422, { detail: [{ loc: ["body", "x"], msg: "bad", input: 987654321 }] }) });
  t.submit("purchase-form"); await tick(60);
  assert.doesNotMatch(t.status(), /987654321/);
});

test("changing the price after a result clears it and asks to re-run", async () => {
  const t = await boot({ stored: PROFILE, fetchImpl: async (u, o, n) => resp(200, n === 1 ? CORE : { ...CORE, ai_explanation: AI }) });
  t.submit("purchase-form"); await tick(80);
  assert.equal(t.$("results").hidden, false);
  t.type("product-price", "65000");
  assert.equal(t.$("results").hidden, true);
  assert.equal(t.$("ai-section").hidden, true);
  assert.match(t.status(), /Inputs changed/);
});

test("untrusted text is rendered as text, not HTML", async () => {
  const evil = { ...CORE, headline: "<img src=x onerror=alert(1)>", recommendation: "<b>hi</b>" };
  const t = await boot({ stored: PROFILE, product: { ok: true, product: { title: "<script>1</script>", price: 100, priceText: "", priceSource: "s", ambiguous: false, candidates: [100] } },
    fetchImpl: async () => resp(200, evil) });
  t.submit("purchase-form"); await tick(60);
  assert.equal(t.d.querySelectorAll("#results img, #results b, #results script").length, 0);
  assert.match(t.text("results"), /<img src=x/);
});

test("production config without a URL shows a configuration error", async () => {
  const t = await boot({ stored: PROFILE, fetchImpl: async () => resp(200, CORE) });
  t.w.FDE_CONFIG; // config is a top-level const; emulate by mutating its object
  t.w.eval('FDE_CONFIG.ENVIRONMENT = "production"');
  t.submit("purchase-form"); await tick(60);
  assert.match(t.status(), /No API URL configured for "production"/);
  assert.equal(t.calls.fetch.length, 0);
});

test("LIVE: popup against the real backend, displayed values equal the API response", { skip: !LIVE }, async () => {
  const real = fetch;
  const t = await boot({ stored: PROFILE, fetchImpl: (u, o) => real(u, o) });
  t.type("payment-mode", "emi"); t.$("payment-mode").dispatchEvent(new t.w.Event("change"));
  t.type("down-payment", "10000"); t.type("emi-months", "12"); t.type("emi-rate", "12");
  t.submit("purchase-form"); await tick(1500);
  const direct = await (await real("http://127.0.0.1:8000/api/v1/purchase-decision/analyze", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...PROFILE, purchase_amount: 60000, payment_mode: "emi", down_payment: 10000, emi_months: 12, annual_interest_rate: 12, include_ai_explanation: false }) })).json();
  const fmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
  const r = t.text("results");
  assert.match(r, new RegExp(direct.decision));
  assert.ok(r.includes(fmt.format(direct.monthly_emi)));
  assert.ok(r.includes(fmt.format(direct.savings_remaining)));
  assert.ok(r.includes(fmt.format(direct.monthly_surplus_after_emi)));
  assert.ok(r.includes(`${direct.emergency_runway_months} month`));
  assert.ok(r.includes(direct.headline));
  assert.match(t.text("ai-section"), /\S/);   // fallback or AI text present
  console.log("LIVE result:", direct.decision, direct.monthly_emi);
});
