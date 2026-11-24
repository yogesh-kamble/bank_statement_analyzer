"use strict";

(() => {
  // ------------------------------------------------------------------ setup
  const PROFILE_KEY = "fde_profile";
  const ANALYZE_PATH = "/api/v1/purchase-decision/analyze";
  const TIMEOUT_MS = { core: 10000, ai: 30000 };
  const SUPPORTED_HOSTS = new Set(["www.amazon.in", "amazon.in"]);
  const PRODUCT_PATH_RE = /\/(?:dp|gp\/product)\/[A-Z0-9]{10}(?:[/?]|$)/i;
  const MAX_AMOUNT = 1e9;

  const $ = (id) => document.getElementById(id);
  const inrFormat = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  });
  const formatInr = (n) => inrFormat.format(n);

  const state = { profile: null, profileDirty: false, busy: false, runId: 0 };

  const DECISIONS = {
    SAFE: { cls: "safe", icon: "✓" },
    MODERATE: { cls: "moderate", icon: "!" },
    RISKY: { cls: "risky", icon: "✕" }
  };

  const STATUS_ICONS = { info: "ℹ", success: "✓", warn: "!", error: "✕" };

  class ApiError extends Error {
    constructor(kind, message, hint) {
      super(message);
      this.kind = kind;
      this.hint = hint;
    }
  }

  // ---------------------------------------------------------------- DOM utils
  function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else node.setAttribute(key, value);
    }
    for (const child of children) if (child) node.append(child);
    return node;
  }

  function showStatus(kind, message, hint) {
    const box = $("status");
    box.className = `status ${kind}`;
    box.setAttribute("role", kind === "error" ? "alert" : "status");
    box.hidden = false;
    box.replaceChildren(
      el("span", { class: "status-icon", "aria-hidden": "true", text: STATUS_ICONS[kind] }),
      el(
        "div",
        {},
        el("p", { class: "status-msg", text: message }),
        hint ? el("p", { class: "status-hint", text: hint }) : null
      )
    );
  }

  function clearStatus() {
    const box = $("status");
    box.hidden = true;
    box.replaceChildren();
  }

  function setFieldError(id, message) {
    const input = $(id);
    const err = $(`err-${id}`);
    input.setAttribute("aria-invalid", "true");
    if (err) {
      err.textContent = message;
      err.hidden = false;
    }
  }

  function clearFieldErrors() {
    document.querySelectorAll(".field-error").forEach((n) => {
      n.hidden = true;
      n.textContent = "";
    });
    document.querySelectorAll('[aria-invalid="true"]').forEach((n) => n.removeAttribute("aria-invalid"));
  }

  function focusFirstInvalid() {
    const first = document.querySelector('[aria-invalid="true"]');
    if (first) first.focus();
  }

  // --------------------------------------------------------- input parsing
  // Returns null for empty, NaN for malformed, otherwise a number.
  function parseAmount(raw) {
    const s = String(raw ?? "")
      .replace(/^\s*(?:rs\.?|inr)/i, "")
      .replace(/[₹,\s]/g, "");
    if (s === "") return null;
    if (!/^\d+(?:\.\d{1,2})?$/.test(s)) return NaN;
    return Number(s);
  }

  // Returns number, undefined (optional & empty) or null (error shown).
  function readAmount(id, label, opts = {}) {
    const raw = $(id).value.trim();
    if (raw === "") {
      if (opts.optional) return undefined;
      setFieldError(id, `Enter ${label.toLowerCase()}.`);
      return null;
    }
    const n = parseAmount(raw);
    if (Number.isNaN(n)) {
      setFieldError(id, `${label} must be a valid number${opts.example ? ` (for example ${opts.example})` : ""}.`);
      return null;
    }
    if (opts.positive && n <= 0) {
      setFieldError(id, `${label} must be greater than 0.`);
      return null;
    }
    if (n > (opts.max ?? MAX_AMOUNT)) {
      setFieldError(id, `${label} looks too large. Please check it.`);
      return null;
    }
    return n;
  }

  function readInteger(id, label, min, max, opts = {}) {
    const raw = $(id).value.trim();
    if (raw === "") {
      if (opts.optional) return undefined;
      setFieldError(id, `Enter ${label.toLowerCase()}.`);
      return null;
    }
    const n = /^\d+$/.test(raw) ? Number(raw) : NaN;
    if (!Number.isInteger(n) || n < min || n > max) {
      setFieldError(id, `${label} must be a whole number from ${min} to ${max}.`);
      return null;
    }
    return n;
  }

  const MONEY_EXAMPLE = "60000 or 1,29,999";

  // ---------------------------------------------------------------- profile
  function isValidProfile(p) {
    const num = (v) => typeof v === "number" && Number.isFinite(v);
    return (
      p &&
      typeof p === "object" &&
      num(p.monthly_income) && p.monthly_income > 0 &&
      num(p.monthly_expenses) && p.monthly_expenses > 0 &&
      num(p.current_savings) && p.current_savings >= 0 &&
      (p.emi_months === undefined || (Number.isInteger(p.emi_months) && p.emi_months >= 1 && p.emi_months <= 120)) &&
      (p.annual_interest_rate === undefined || (num(p.annual_interest_rate) && p.annual_interest_rate >= 0 && p.annual_interest_rate <= 60))
    );
  }

  function updateProfileBadge() {
    const badge = $("profile-badge");
    badge.className = "badge-pill";
    if (state.profileDirty) {
      badge.textContent = "Unsaved changes";
      badge.classList.add("dirty");
    } else if (state.profile) {
      badge.textContent = "Saved locally";
      badge.classList.add("saved");
    } else {
      badge.textContent = "Not set up";
    }
  }

  function fillProfileForm(profile) {
    $("p-income").value = profile ? String(profile.monthly_income) : "";
    $("p-expenses").value = profile ? String(profile.monthly_expenses) : "";
    $("p-savings").value = profile ? String(profile.current_savings) : "";
    $("p-emi-months").value = profile?.emi_months !== undefined ? String(profile.emi_months) : "";
    $("p-emi-rate").value = profile?.annual_interest_rate !== undefined ? String(profile.annual_interest_rate) : "";
  }

  function prefillEmiFromProfile() {
    if (!state.profile) return;
    if (!$("emi-months").value && state.profile.emi_months !== undefined) {
      $("emi-months").value = String(state.profile.emi_months);
    }
    if (!$("emi-rate").value && state.profile.annual_interest_rate !== undefined) {
      $("emi-rate").value = String(state.profile.annual_interest_rate);
    }
  }

  async function loadProfile() {
    try {
      const stored = await chrome.storage.local.get(PROFILE_KEY);
      const profile = stored[PROFILE_KEY];
      if (profile === undefined) return;
      if (isValidProfile(profile)) {
        state.profile = profile;
      } else {
        showStatus("warn", "Your saved profile looks corrupted, so it was ignored.", "Re-enter and save it below.");
      }
    } catch (_) {
      showStatus("error", "Couldn't read your saved profile from the browser.", "Reload the extension and try again.");
    }
  }

  async function onSaveProfile(event) {
    event.preventDefault();
    clearFieldErrors();
    clearStatus();

    const income = readAmount("p-income", "Monthly income", { positive: true, example: MONEY_EXAMPLE });
    const expenses = readAmount("p-expenses", "Monthly expenses", { positive: true, example: MONEY_EXAMPLE });
    const savings = readAmount("p-savings", "Current savings", { example: MONEY_EXAMPLE });
    const months = readInteger("p-emi-months", "EMI months", 1, 120, { optional: true });
    const rate = readAmount("p-emi-rate", "Interest rate", { optional: true, max: 60, example: "12 or 10.5" });

    if ([income, expenses, savings, months, rate].includes(null)) {
      showStatus("error", "Please fix the highlighted fields.", "Monthly expenses must be above 0 - the engine uses it to work out your emergency runway.");
      focusFirstInvalid();
      return;
    }

    const profile = {
      monthly_income: income,
      monthly_expenses: expenses,
      current_savings: savings
    };
    if (months !== undefined) profile.emi_months = months;
    if (rate !== undefined) profile.annual_interest_rate = rate;

    try {
      await chrome.storage.local.set({ [PROFILE_KEY]: profile });
    } catch (_) {
      showStatus("error", "Couldn't save your profile.", "Check that the extension has storage access, then try again.");
      return;
    }

    state.profile = profile;
    state.profileDirty = false;
    updateProfileBadge();
    prefillEmiFromProfile();
    showStatus("success", "Profile saved in this browser.", "You can now check a purchase.");
  }

  async function onClearProfile() {
    clearFieldErrors();
    try {
      await chrome.storage.local.remove(PROFILE_KEY);
    } catch (_) {
      showStatus("error", "Couldn't clear your profile.", "Try again or remove the extension's data from chrome://extensions.");
      return;
    }
    state.profile = null;
    state.profileDirty = false;
    fillProfileForm(null);
    updateProfileBadge();
    invalidateResults();
    $("profile-details").open = true;
    showStatus("info", "Saved profile cleared.", "Enter your details again to check another purchase.");
  }

  // -------------------------------------------------------- product detection
  function describeDetectError(code) {
    if (code === "NOT_PRODUCT_PAGE") {
      return ["This Amazon.in page isn't a product page.", "Open a product page (URL contains /dp/…), or enter the details manually."];
    }
    return ["This website isn't supported yet.", "FDE currently detects products on Amazon.in only. You can still type the product price below."];
  }

  async function requestProduct(tabId) {
    const ask = () => chrome.tabs.sendMessage(tabId, { type: "FDE_GET_PRODUCT" });
    try {
      return await ask();
    } catch (_) {
      // Content script not present yet: inject it into this tab (activeTab) and retry once.
      await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
      return await ask();
    }
  }

  function setDetectNote(text) {
    const note = $("detect-note");
    note.textContent = text || "";
    note.hidden = !text;
  }

  async function detectProduct() {
    const btn = $("detect-btn");
    btn.disabled = true;
    clearStatus();
    setDetectNote("");

    try {
      let tab;
      try {
        [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      } catch (_) {
        tab = undefined;
      }

      let url = null;
      try {
        url = tab && tab.url ? new URL(tab.url) : null;
      } catch (_) {
        url = null;
      }

      if (!url || url.protocol !== "https:" || !SUPPORTED_HOSTS.has(url.hostname)) {
        const [msg, hint] = describeDetectError("UNSUPPORTED_SITE");
        showStatus("warn", msg, hint);
        return;
      }
      if (!PRODUCT_PATH_RE.test(url.pathname)) {
        const [msg, hint] = describeDetectError("NOT_PRODUCT_PAGE");
        showStatus("warn", msg, hint);
        return;
      }

      let reply;
      try {
        reply = await requestProduct(tab.id);
      } catch (_) {
        showStatus("error", "Couldn't read this page.", "Refresh the product page and click Detect again, or enter the details manually.");
        return;
      }

      if (!reply || reply.ok !== true) {
        const [msg, hint] = describeDetectError(reply && reply.error);
        showStatus("warn", msg, hint);
        return;
      }

      applyDetectedProduct(reply.product);
    } finally {
      btn.disabled = false;
    }
  }

  function applyDetectedProduct(product) {
    invalidateResults();
    const problems = [];

    if (product.title) {
      $("product-title").value = product.title;
    } else {
      problems.push("title");
    }

    if (typeof product.price === "number" && product.price > 0) {
      $("product-price").value = String(product.price);
      setDetectNote(`Detected ${formatInr(product.price)} (${product.priceSource}). Please confirm it matches the option you selected.`);
    } else {
      problems.push("price");
    }

    if (product.ambiguous) {
      const list = product.candidates.map(formatInr).join(", ");
      showStatus("warn", `Several prices were found on this page (${list}).`, "Check that the price in the box is the one you'd actually pay, and correct it if not.");
    } else if (problems.length === 2) {
      showStatus("warn", "Couldn't detect the product title or price.", "Amazon may have changed its page layout. Please type them in manually.");
    } else if (problems.includes("price")) {
      showStatus("warn", "Couldn't detect the price.", "Type the price you'd pay into the Price box.");
    } else if (problems.includes("title")) {
      showStatus("info", "Price detected, but not the title.", "The title is optional - it's only shown in your result.");
    } else {
      showStatus("info", "Product details detected.", "Confirm the price, pick a payment method, then check affordability.");
    }
  }

  // ------------------------------------------------------------- API calling
  function isNum(v) {
    return typeof v === "number" && Number.isFinite(v);
  }

  function isValidResult(d) {
    return (
      d && typeof d === "object" &&
      typeof d.decision === "string" &&
      isNum(d.decision_score) &&
      typeof d.headline === "string" &&
      typeof d.recommendation === "string" &&
      isNum(d.monthly_emi) &&
      isNum(d.savings_remaining) &&
      isNum(d.emergency_runway_months) &&
      isNum(d.monthly_surplus_after_emi) &&
      (d.emi_ratio === undefined || isNum(d.emi_ratio))
    );
  }

  function isValidAi(ai) {
    return (
      ai && typeof ai === "object" &&
      typeof ai.summary === "string" &&
      ["key_points", "risks", "suggestions"].every(
        (k) => ai[k] === undefined || (Array.isArray(ai[k]) && ai[k].every((x) => typeof x === "string"))
      )
    );
  }

  function validationMessage(body) {
    // FastAPI 422: {detail: [{loc, msg, ...}]} or {detail: "text"}. Echo only loc+msg, never input values.
    const detail = body && body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .slice(0, 3)
        .map((d) => `${Array.isArray(d.loc) ? d.loc.filter((x) => x !== "body").join(".") : "input"}: ${d.msg}`)
        .join("; ");
    }
    return "The service rejected one of the values.";
  }

  async function postAnalyze(payload, timeoutMs) {
    let base;
    try {
      base = FDE_CONFIG.getApiBaseUrl();
    } catch (err) {
      throw new ApiError("config", err.message, "Fix config.js as described in the README, then reload the extension.");
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      let res;
      try {
        res = await fetch(base + ANALYZE_PATH, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal
        });
      } catch (err) {
        if (err && err.name === "AbortError") {
          throw new ApiError("timeout", "The FDE service took too long to respond.", "Try again in a moment.");
        }
        throw new ApiError("network", `Can't reach the FDE service at ${base}.`, "Make sure the backend is running (see README), then try again.");
      }

      let body = null;
      try {
        body = await res.json();
      } catch (err) {
        if (err && err.name === "AbortError") {
          throw new ApiError("timeout", "The FDE service took too long to respond.", "Try again in a moment.");
        }
        body = null;
      }

      if (res.status === 422) {
        throw new ApiError("validation", `The service couldn't accept these values - ${validationMessage(body)}`, "Correct the values and try again.");
      }
      if (res.status === 404) {
        throw new ApiError("notfound", "The purchase-analysis endpoint wasn't found at the configured URL.", "That server may not be the FDE backend. Check config.js.");
      }
      if (res.status === 429) {
        throw new ApiError("ratelimit", "Too many requests.", "Wait a minute and try again.");
      }
      if (!res.ok) {
        throw new ApiError("server", `The FDE service returned an error (HTTP ${res.status}).`, "Try again later. If it keeps happening, check the backend logs.");
      }
      if (!isValidResult(body)) {
        throw new ApiError("schema", "The service sent a response this extension doesn't understand.", "The backend and extension may be out of sync. Update both to the same version.");
      }
      return body;
    } finally {
      clearTimeout(timer);
    }
  }

  // ---------------------------------------------------------------- rendering
  function metricRow(label, value) {
    return [el("dt", { text: label }), el("dd", { text: value })];
  }

  function renderResults(data, input) {
    const section = $("results");
    const info = DECISIONS[String(data.decision).toUpperCase()] || { cls: "unknown", icon: "?" };
    const score = Math.max(0, Math.min(100, data.decision_score));
    const isEmi = input.payload.payment_mode === "emi";

    const metrics = el("dl", { class: "metrics" });
    const rows = [
      ["Price you entered", formatInr(input.price)],
      ...(isEmi
        ? [
            ["Monthly EMI", formatInr(data.monthly_emi)],
            ...(isNum(data.emi_ratio) ? [["EMI share of income", `${data.emi_ratio}%`]] : []),
            ["Monthly surplus after EMI", formatInr(data.monthly_surplus_after_emi)]
          ]
        : [["Monthly surplus", formatInr(data.monthly_surplus_after_emi)]]),
      ["Savings remaining", formatInr(data.savings_remaining)],
      ["Emergency runway", `${data.emergency_runway_months} month${data.emergency_runway_months === 1 ? "" : "s"}`]
    ];
    rows.forEach(([label, value]) => metrics.append(...metricRow(label, value)));

    const decision = el(
      "div",
      { class: `decision ${info.cls}` },
      el("span", { class: "label" }, el("span", { class: "icon", "aria-hidden": "true", text: info.icon }), document.createTextNode(String(data.decision).toUpperCase())),
      el("span", { class: "score", text: `Score ${data.decision_score}/100` })
    );

    const bar = el("div", { class: "score-bar", "aria-hidden": "true" }, el("span", { style: `width:${score}%` }));

    section.replaceChildren(
      el("p", { class: "section-label", id: "results-h", text: "Calculated by the FDE engine" }),
      input.title ? el("p", { class: "product-line", text: input.title }) : null,
      decision,
      bar,
      metrics,
      el("p", { class: "headline", text: data.headline }),
      el("p", { class: "recommendation", text: data.recommendation })
    );
    section.hidden = false;
  }

  function renderAiState(kind, ai) {
    const section = $("ai-section");
    const head = el("p", { class: "section-label", id: "ai-h", text: "AI explanation" });
    const note = el("p", { class: "note", text: "AI explains the engine's numbers above. It does not change them or the decision." });

    if (kind === "off") {
      section.hidden = true;
      return;
    }
    section.hidden = false;

    if (kind === "loading") {
      section.replaceChildren(head, el("p", { class: "muted", text: "Generating explanation…" }));
      return;
    }
    if (kind === "unavailable") {
      section.replaceChildren(
        head,
        el("p", { class: "muted", text: "The AI explanation isn't available right now. The calculated result above is unaffected." })
      );
      return;
    }

    const parts = [head];
    if (ai.source === "fallback") {
      parts.push(el("p", { class: "note", text: "AI is unavailable, so this is a standard explanation based on the same numbers." }));
    }
    parts.push(el("p", { class: "summary", text: ai.summary }));

    const addList = (title, items) => {
      if (!items || !items.length) return;
      parts.push(el("h3", { text: title }), el("ul", {}, ...items.map((t) => el("li", { text: t }))));
    };
    addList("Key points", ai.key_points);
    addList("Risks", ai.risks);
    addList("What you can do", ai.suggestions);
    parts.push(note);
    section.replaceChildren(...parts);
  }

  function showApiError(err) {
    if (err instanceof ApiError) {
      showStatus("error", err.message, err.hint);
    } else {
      showStatus("error", "Something went wrong.", "Please try again.");
    }
  }

  // ------------------------------------------------------------- run analysis
  function setBusy(busy) {
    state.busy = busy;
    const btn = $("check-btn");
    btn.disabled = busy;
    btn.textContent = busy ? "Checking…" : "Check affordability";
  }

  function invalidateResults() {
    const hadResults = !$("results").hidden || !$("ai-section").hidden;
    state.runId += 1;
    setBusy(false);
    $("results").hidden = true;
    $("results").replaceChildren();
    $("ai-section").hidden = true;
    $("ai-section").replaceChildren();
    return hadResults;
  }

  function onInputsChanged() {
    if (invalidateResults()) {
      showStatus("info", "Inputs changed - previous result cleared.", "Press “Check affordability” to re-run.");
    }
  }

  function collectPurchaseInput() {
    clearFieldErrors();

    if (!state.profile) {
      showStatus("error", "Save your financial profile first.", "Open “Your financial profile” below, fill it in and press Save.");
      $("profile-details").open = true;
      return null;
    }
    if (state.profileDirty) {
      showStatus("error", "You have unsaved profile changes.", "Press “Save profile” to use them.");
      $("profile-details").open = true;
      return null;
    }

    const price = readAmount("product-price", "Price", { positive: true, example: MONEY_EXAMPLE });
    const mode = $("payment-mode").value;
    let down, months, rate;

    if (mode === "emi") {
      down = readAmount("down-payment", "Down payment", { example: MONEY_EXAMPLE });
      months = readInteger("emi-months", "EMI months", 1, 120);
      rate = readAmount("emi-rate", "Interest rate", { max: 60, example: "12 or 10.5" });
      if (down != null && price != null && down > price) {
        setFieldError("down-payment", "Down payment can't be more than the price.");
        down = null;
      }
    }

    if ([price, down, months, rate].includes(null)) {
      showStatus("error", "Please fix the highlighted fields.");
      focusFirstInvalid();
      return null;
    }

    // Field names/types match PurchaseDecisionRequest in the backend.
    const payload = {
      monthly_income: state.profile.monthly_income,
      monthly_expenses: state.profile.monthly_expenses,
      current_savings: state.profile.current_savings,
      purchase_amount: price,
      payment_mode: mode
    };
    if (mode === "emi") {
      payload.down_payment = down;
      payload.emi_months = months;
      payload.annual_interest_rate = rate;
    }

    return { payload, price, title: $("product-title").value.trim() };
  }

  async function onCheck(event) {
    event.preventDefault();
    if (state.busy) return;

    clearStatus();
    invalidateResults();

    const input = collectPurchaseInput();
    if (!input) return;

    const runId = state.runId;
    const wantAi = $("include-ai").checked;
    setBusy(true);

    try {
      // 1) Deterministic result first, so it never waits on (or depends on) AI.
      const core = await postAnalyze({ ...input.payload, include_ai_explanation: false }, TIMEOUT_MS.core);
      if (runId !== state.runId) return;
      renderResults(core, input);

      if (!wantAi) {
        renderAiState("off");
        return;
      }

      // 2) AI explanation, requested separately.
      renderAiState("loading");
      try {
        const withAi = await postAnalyze({ ...input.payload, include_ai_explanation: true }, TIMEOUT_MS.ai);
        if (runId !== state.runId) return;

        const consistent = withAi.decision === core.decision && withAi.decision_score === core.decision_score;
        if (consistent && isValidAi(withAi.ai_explanation)) {
          renderAiState("ready", withAi.ai_explanation);
        } else {
          renderAiState("unavailable");
        }
      } catch (_) {
        if (runId === state.runId) renderAiState("unavailable");
      }
    } catch (err) {
      if (runId === state.runId) showApiError(err);
    } finally {
      if (runId === state.runId) setBusy(false);
    }
  }

  // --------------------------------------------------------------------- init
  function togglePaymentMode() {
    $("emi-fields").hidden = $("payment-mode").value !== "emi";
    if (!$("emi-fields").hidden) prefillEmiFromProfile();
  }

  async function init() {
    try {
      $("api-info").textContent = `API: ${FDE_CONFIG.getApiBaseUrl()} (${FDE_CONFIG.ENVIRONMENT})`;
    } catch (err) {
      $("api-info").textContent = err.message;
    }

    $("purchase-form").addEventListener("submit", onCheck);
    $("profile-form").addEventListener("submit", onSaveProfile);
    $("clear-profile-btn").addEventListener("click", onClearProfile);
    $("detect-btn").addEventListener("click", detectProduct);

    $("payment-mode").addEventListener("change", () => {
      togglePaymentMode();
      onInputsChanged();
    });
    ["product-price", "down-payment", "emi-months", "emi-rate"].forEach((id) =>
      $(id).addEventListener("input", onInputsChanged)
    );
    ["p-income", "p-expenses", "p-savings", "p-emi-months", "p-emi-rate"].forEach((id) =>
      $(id).addEventListener("input", () => {
        state.profileDirty = true;
        updateProfileBadge();
      })
    );

    await loadProfile();
    fillProfileForm(state.profile);
    updateProfileBadge();
    $("profile-details").open = !state.profile;
    togglePaymentMode();

    // Attempt detection on open (read-only; analysis only runs on user action).
    await detectProduct();
  }

  init();
})();
