// ---------------------------------------------------------------------------
// FDE extension configuration - the ONLY place the API URL is set.
//
// Development: run the backend locally (see README) and keep ENVIRONMENT as
//              "development".
// Production:  1. Deploy the backend and confirm GET <url>/health works and
//                 POST <url>/api/v1/purchase-decision/analyze exists
//                 (the existing onrender.com URL may serve a different app).
//              2. Put the HTTPS URL in API_BASE_URLS.production below.
//              3. Add the same origin to "host_permissions" in manifest.json,
//                 e.g. "https://api.yourdomain.com/*".
//              4. Set ENVIRONMENT to "production".
//
// Never put API keys or secrets in this file - the extension only talks to
// the FDE backend, which keeps the OpenAI key server-side.
// ---------------------------------------------------------------------------
const FDE_CONFIG = {
  ENVIRONMENT: "development", // "development" | "production"

  API_BASE_URLS: {
    development: "http://127.0.0.1:8000",
    production: "" // intentionally empty until a verified HTTPS URL is set
  },

  getApiBaseUrl() {
    const url = (this.API_BASE_URLS[this.ENVIRONMENT] || "").trim().replace(/\/+$/, "");

    if (!url) {
      throw new Error(
        `No API URL configured for "${this.ENVIRONMENT}". Edit config.js.`
      );
    }
    if (this.ENVIRONMENT === "production" && !url.startsWith("https://")) {
      throw new Error("Production API URL must use HTTPS. Edit config.js.");
    }
    return url;
  }
};
