**Sprint 09: /crawl Integration Tests (Real Tracking URLs)**

- **Goal:** Validate the `/crawl` endpoint end-to-end against real-world carrier tracking pages, ensuring it waits for pages to fully load and returns substantial HTML content.
- **Scope:** Add pytest integration tests that hit the live network with representative tracking URLs from multiple carriers and tracking aggregators.

**Test Strategy**

- **Endpoint:** `POST /crawl`
- **Payload:** Use robust loading options to increase stability:
  - `wait_selector: "body"`
  - `wait_selector_state: "visible"`
  - `network_idle: true`
  - `timeout_ms: 45000`
  - `x_wait_time: 5` (extra buffer for dynamic content)
- **Assertions:**
  - HTTP 200 from API
  - JSON `status == "success"`
  - `html` present, contains `<html`, and length >= configured minimum (`MIN_HTML_CONTENT_LENGTH`)
- **Enabled by default:** Tests are marked `@pytest.mark.integration` and run by default along with the rest of the suite. Use `-m integration` to focus only these tests when needed.

**Test Cases (one per link)**

- 17TRACK: `https://t.17track.net/en#nums=1ZXH95910326694965`
- UPS: `https://www.ups.com/track?tracknum=1ZXH95910305309465&loc=vi_VN&requester=QUIC/trackdetails`
- FedEx: `https://www.fedex.com/fedextrack/?trknbr=883561067070&trkqual=2460902000~883561067070~FX`
- USPS: `https://tools.usps.com/go/TrackConfirmAction?tRef=fullpage&tLc=2&text28777=&tLabels=9200190381836321489085%2C&tABt=false`
- DPEX: `https://dpexonline.com/trace-and-track/index?id=226006280426`
- ParcelsApp: `https://parcelsapp.com/en/tracking/9200190381599918197427`
- La Poste: `https://www.laposte.fr/outils/suivre-vos-envois?code=LA866151484GB`

**Implementation Notes**

- Tests live under `tests/integration/test_crawl_real_urls.py`.
- Each URL is a dedicated test function for clearer reporting and triage.
- Uses the FastAPI `TestClient` (`tests/conftest.py`) to call the live app.
- Relies on `scrapling` being installed and available. If the `StealthyFetcher` cannot run (e.g., Playwright issues), the service may fall back to a lightweight HTTP fetch; pages protected by heavy client-side rendering or bot protections may still require the full stealth path to succeed.

**How To Run**

- Run all tests (default): `pytest -v`
- Only integration tests: `pytest -m integration -v`

**Risks & Mitigations**

- **Flakiness:** Third-party sites may change or intermittently rate-limit. Mitigated via higher timeouts, network idle wait, extra wait, and Cloudflare solving when supported by `StealthyFetcher`.
- **Environment:** Requires network access and `scrapling` runtime (and browser dependencies if stealth path is taken). Tests are opt-in to protect CI pipelines by default.
