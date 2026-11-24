// Reads the product title and displayed price from an Amazon.in product page.
//
// - Injected on demand by the popup (activeTab + scripting) - it does NOT run
//   on pages automatically, and only runs when the user opens the popup.
// - Reads only the title and price elements. No page text, forms, addresses,
//   cart or payment data are read. Nothing is sent anywhere by this script;
//   it only replies to a message from this extension's own popup.
// - The financial profile never reaches this script.
(() => {
  "use strict";

  if (window.__fdeProductReaderLoaded) return; // guard against double injection
  window.__fdeProductReaderLoaded = true;

  const SUPPORTED_HOSTS = ["www.amazon.in", "amazon.in"];
  const PRODUCT_PATH_RE = /\/(?:dp|gp\/product)\/[A-Z0-9]{10}(?:[/?]|$)/i;

  const TITLE_SELECTORS = ["#productTitle", "#title #productTitle", "h1#title span"];

  // Ordered from most to least trustworthy. Every selector is anchored inside
  // the main price block, so prices in carousels, "customers also bought",
  // sponsored items, EMI widgets, etc. are never candidates.
  //   .priceToPay   = the current selling price Amazon shows for the selection
  //   .a-text-price = Amazon's class for crossed-out list price / MRP
  const PRICE_TIERS = [
    {
      name: "main price block (priceToPay)",
      selectors: [
        "#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen",
        "#corePrice_feature_div .priceToPay .a-offscreen",
        "#apex_desktop .priceToPay .a-offscreen",
        "#corePriceDisplay_mobile_feature_div .priceToPay .a-offscreen"
      ]
    },
    {
      name: "main price block (non-struck price)",
      selectors: [
        "#corePriceDisplay_desktop_feature_div .a-price:not(.a-text-price) .a-offscreen",
        "#corePrice_feature_div .a-price:not(.a-text-price) .a-offscreen",
        "#apex_desktop .a-price:not(.a-text-price) .a-offscreen"
      ]
    },
    {
      name: "legacy price element",
      selectors: [
        "#priceblock_dealprice",
        "#priceblock_ourprice",
        "#priceblock_saleprice",
        "#price_inside_buybox",
        "#newBuyBoxPrice"
      ]
    }
  ];

  // Never accept a price that sits inside any of these.
  const EXCLUDED_ANCESTORS = [
    '[data-a-strike="true"]',
    ".basisPrice",
    ".a-text-price",
    '[id^="emi" i]',
    '[id*="emi_" i]',
    '[id*="carousel" i]',
    "#similarities_feature_div",
    '[id^="sims-consolidated"]',
    '[id^="sponsoredProducts"]'
  ].join(",");

  function cleanText(text) {
    return String(text || "").replace(/\s+/g, " ").trim();
  }

  // Parses one displayed INR price: "₹60,000", "₹1,29,999", "₹1,29,999.00".
  // Returns {value} or {value:null, reason}. Ranges / several numbers in one
  // element are rejected rather than guessed.
  function parseInrPrice(text) {
    const raw = String(text || "").replace(/\u00a0/g, " ");
    const tokens = raw.match(/\d[\d,]*(?:\.\d+)?/g);

    if (!tokens) return { value: null, reason: "no-number" };
    if (tokens.length !== 1) return { value: null, reason: "multiple-numbers" };

    const token = tokens[0].replace(/,$/, "");
    if (!/^(?:\d+|\d{1,3}(?:,\d{2,3})+)(?:\.\d{1,2})?$/.test(token)) {
      return { value: null, reason: "bad-format" };
    }

    const value = Number(token.replace(/,/g, ""));
    if (!Number.isFinite(value) || value <= 0 || value >= 1e9) {
      return { value: null, reason: "out-of-range" };
    }
    return { value: Math.round(value * 100) / 100 };
  }

  function isExcluded(node) {
    try {
      return Boolean(node.closest(EXCLUDED_ANCESTORS));
    } catch (_) {
      return false;
    }
  }

  function readTitle() {
    for (const selector of TITLE_SELECTORS) {
      const node = document.querySelector(selector);
      const text = node ? cleanText(node.textContent) : "";
      if (text) return text.slice(0, 200);
    }
    return null;
  }

  function readPrice() {
    for (const tier of PRICE_TIERS) {
      const found = [];

      for (const selector of tier.selectors) {
        for (const node of document.querySelectorAll(selector)) {
          if (isExcluded(node)) continue;
          const parsed = parseInrPrice(node.textContent);
          if (parsed.value !== null) {
            found.push({ value: parsed.value, text: cleanText(node.textContent) });
          }
        }
      }

      if (found.length) {
        const distinct = [...new Set(found.map((f) => f.value))];
        return {
          price: found[0].value,
          priceText: found[0].text,
          priceSource: tier.name,
          ambiguous: distinct.length > 1,
          candidates: distinct
        };
      }
    }

    return { price: null, priceText: null, priceSource: null, ambiguous: false, candidates: [] };
  }

  function readProduct() {
    if (!SUPPORTED_HOSTS.includes(location.hostname)) {
      return { ok: false, error: "UNSUPPORTED_SITE" };
    }
    if (!PRODUCT_PATH_RE.test(location.pathname)) {
      return { ok: false, error: "NOT_PRODUCT_PAGE" };
    }
    return { ok: true, product: { title: readTitle(), ...readPrice() } };
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || message.type !== "FDE_GET_PRODUCT") return;
    if (sender.id !== chrome.runtime.id) return; // only our own extension
    sendResponse(readProduct());
  });
})();
