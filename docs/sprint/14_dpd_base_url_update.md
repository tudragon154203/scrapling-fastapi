# Sprint 14 - DPD Base URL Update (/crawl/dpd)

Goal: correct the DPD tracking target to the official DPD status page and remove the DHL URL currently used in the implementation. No API shape changes; only the target URL and its builder logic change.

## Context

- Current implementation for DPD builds a DHL URL:
  - app/services/crawler/dpd.py:38
    - `https://dhlparcel.nl/en/track-and-trace/{tracking_code}`
- Earlier docs referenced `https://tracking.dpd.de/parcelstatus` with a `?query=` pattern. DPD’s current canonical route for direct lookups uses a path pattern with locale.

This sprint standardizes on DPD’s status page with an explicit locale, using a path segment for the tracking number.

## Target URL Pattern

- Base: `https://tracking.dpd.de/status/en_US/parcel/`
- Full: `https://tracking.dpd.de/status/en_US/parcel/<number>`
  - Replace `<number>` with the normalized tracking code.
  - Normalize the code by removing whitespace (spaces) and hyphens before building the URL.
  - If any remaining characters are non-URL-safe, URL-encode them when constructing the path.

Rationale: DPD’s status route accepts the tracking number as a path segment and renders the status view without additional form steps.

## API (unchanged)

- Endpoint: `POST /crawl/dpd`
- Request (JSON):
  - `tracking_code` (string, required; trimmed, non-empty)
  - `force_user_data` (bool, optional, default `false`)
  - `force_headful` (bool, optional, default `false`)
- Response (JSON):
  - `status`: `success | failure`
  - `tracking_code`: echo of input
  - `html`: on success
  - `message`: on failure

## Implementation Notes

- Update URL construction in the DPD service:
  - app/services/crawler/dpd.py:38
    - From: `https://dhlparcel.nl/en/track-and-trace/{tracking_code}`
    - To: `https://tracking.dpd.de/status/en_US/parcel/{normalized_code}`
- Add a small normalizer for the tracking code used in the path:
  - Strip leading/trailing whitespace, remove internal spaces and hyphens.
  - Optionally, URL-encode the result if characters beyond `[A-Za-z0-9]` remain.
- Keep existing wait/timeout/network_idle options as-is; page actions remain unnecessary.
- Consider extracting a module-level constant for clarity:
  - `DPD_BASE = "https://tracking.dpd.de/status/en_US/parcel"`
  - `url = f"{DPD_BASE}/{normalized_code}"`

## Behavior

- Builds the DPD status URL using the normalized tracking code.
- Reuses the same fetch pipeline and success criteria as before:
  - HTTP 200 and HTML length above the configured threshold ⇒ `success`.
  - Otherwise ⇒ `failure` with diagnostic `message`.

## Testing

- Unit tests (service):
  - Verify the builder targets `tracking.dpd.de/status/en_US/parcel` and not any DHL domain.
  - Confirm normalization removes spaces/hyphens (`"01126819 7878 09"` ⇒ `"01126819787809"`).
  - Success path: mocked 200 + sufficient HTML length ⇒ `status=success` with `html`.
  - Failure path: non-200/exception/short HTML ⇒ `status=failure` with `message`.
- API tests (existing) remain valid; no request/response shape changes.
- Integration test can keep the provided real code; normalization accommodates embedded spaces.

## Acceptance Criteria

- Implementation no longer references the DHL URL in DPD crawling logic.
- DPD URL builder uses: `https://tracking.dpd.de/status/en_US/parcel/<normalized_code>`.
- Tracking code normalization is applied before URL assembly.
- All existing DPD tests pass; added unit checks confirm the domain and path pattern.
- Documentation updated to reflect the new base.

## Out of Scope

- Adding interactive steps or alternate locales.
- Changing request/response models or force flag semantics.

## References

- DPD service implementation: app/services/crawler/dpd.py:38
- Prior DPD sprint spec: docs/sprint/07_dpd_tracking_endpoint.md

