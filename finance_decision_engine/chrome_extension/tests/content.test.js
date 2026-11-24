const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const SCRIPT = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

// Load a fixture at a given URL, run content.js, and return a function to ask for the product.
function load(fixture, url = "https://www.amazon.in/Acme-Laptop/dp/B0ABCDEFGH?th=1") {
  const html = fs.readFileSync(path.join(__dirname, "fixtures", fixture), "utf8");
  const dom = new JSDOM(html, { url, runScripts: "outside-only" });
  let listener = null;
  dom.window.chrome = {
    runtime: { id: "ext-id", onMessage: { addListener: (fn) => (listener = fn) } }
  };
  dom.window.eval(SCRIPT);
  return {
    dom,
    ask(message = { type: "FDE_GET_PRODUCT" }, senderId = "ext-id") {
      let out;
      const ret = listener(message, { id: senderId }, (r) => (out = r));
      return { out, ret };
    }
  };
}

test("detects title and the selling price, ignoring MRP, EMI and carousel prices", () => {
  const { out } = load("product_normal.html").ask();
  assert.equal(out.ok, true);
  assert.equal(out.product.title, "Acme Laptop 15 (16GB / 512GB)");
  assert.equal(out.product.price, 129999);          // ₹1,29,999.00
  assert.equal(out.product.ambiguous, false);
  assert.deepEqual(out.product.candidates, [129999]);
});

test("parses ₹60,000 and ignores the struck-through price", () => {
  const { out } = load("product_60k.html").ask();
  assert.equal(out.product.price, 60000);
  assert.equal(out.product.title, "Phone X");
});

test("EMI-only and carousel-only prices are NOT used when no real price exists", () => {
  const { out } = load("product_no_price.html").ask();
  assert.equal(out.ok, true);
  assert.equal(out.product.price, null);
  assert.equal(out.product.title, "Out of stock thing");
});

test("a price range is rejected rather than guessed", () => {
  const { out } = load("product_range.html").ask();
  assert.equal(out.product.price, null);
});

test("multiple distinct selling prices are flagged ambiguous (first one chosen)", () => {
  const { out } = load("product_ambiguous.html").ask();
  assert.equal(out.product.price, 10000);
  assert.equal(out.product.ambiguous, true);
  assert.deepEqual(out.product.candidates, [10000, 12500.5]);
});

test("legacy price element with a space after the rupee sign", () => {
  const { out } = load("product_legacy.html").ask();
  assert.equal(out.product.price, 2499);
});

test("non product page and unsupported site are reported", () => {
  assert.equal(load("product_normal.html", "https://www.amazon.in/s?k=laptop").ask().out.error, "NOT_PRODUCT_PAGE");
  assert.equal(load("product_normal.html", "https://www.flipkart.com/p/dp/B0ABCDEFGH").ask().out.error, "UNSUPPORTED_SITE");
});

test("ignores unknown messages and messages from other senders", () => {
  const page = load("product_normal.html");
  assert.equal(page.ask({ type: "SOMETHING_ELSE" }).out, undefined);
  assert.equal(page.ask({ type: "FDE_GET_PRODUCT" }, "evil-ext").out, undefined);
});

test("double injection registers only one listener", () => {
  const page = load("product_normal.html");
  let added = 0;
  page.dom.window.chrome.runtime.onMessage.addListener = () => added++;
  page.dom.window.eval(SCRIPT);
  assert.equal(added, 0);
});

test("response contains only title/price fields (no extra page data)", () => {
  const { out } = load("product_normal.html").ask();
  assert.deepEqual(Object.keys(out.product).sort(),
    ["ambiguous", "candidates", "price", "priceSource", "priceText", "title"]);
});
