# Sprint 04 - Proxy Wiring and Health

Goal: enable real proxy usage in the crawler, honor rotation mode, and add lightweight health handling so failing proxies don’t waste retries.

## Problem Statement

- `StealthyFetcher.fetch` is not yet receiving a proxy parameter from our retry loop.
- `PROXY_ROTATION_MODE` exists in config but selection is always sequential.
- Unhealthy proxies (timeouts, 4xx/5xx) can be retried repeatedly and degrade success rate.
- Minimal observability to understand proxy selection and health decisions.

## Objectives

- Wire selected proxy (direct/public/private) into `StealthyFetcher.fetch` when supported; degrade gracefully if not.
- Respect `PROXY_ROTATION_MODE=sequential|random` during attempt selection.
- Add in-memory proxy health with a failure threshold and cool-off TTL; skip unhealthy proxies during TTL.
- Keep final direct attempt fallback and current strategy order intact.
- Update docs and `.env.example` with new health-related settings.

## Deliverables

- Proxy pass-through in the retry loop with feature detection and safe fallback.
- Rotation mode implementation for sequential and random selection.
- In-memory proxy health tracker (threshold + TTL) applied to public and private proxies.
- Unit tests covering wiring, rotation behavior, and health skip/recovery.
- Documentation updates (this file + env examples).

## Configuration

Add the following settings to `app/core/config.py` with env bindings:

- proxy_health_failure_threshold (`PROXY_HEALTH_FAILURE_THRESHOLD`): int, default `2`.
- proxy_unhealthy_cooldown_ms (`PROXY_UNHEALTHY_COOLDOWN_MS`): int, default `1_800_000` (30 minutes).

Notes:
- Threshold counts consecutive failures per proxy (exceptions or non-2xx). Threshold reached -> mark unhealthy until now + cooldown duration.
- Health store is in-memory (process-local) and resets on restart.
- `PROXY_ROTATION_MODE` already exists; this sprint makes it effective. Random mode selection should be testable by seeding `random` inside tests.

## Design Overview

- Where: `app/services/crawler/generic.py`.
- How:
  - Detect proxy support on `StealthyFetcher.fetch` (e.g., try/except TypeError or inspect signature) and pass `proxy=...` when available.
  - Update attempt selection to honor rotation mode and health status:
    - Sequential: current plan order, skipping proxies that are unhealthy.
    - Random: pick next candidate uniformly at random from healthy proxies; if none, fall back to direct/private per strategy.
  - Track failures per proxy; on threshold, mark unhealthy until a timestamp (TTL). Success resets failure count and health.

## Implementation Details

- Proxy wiring:
  - Assemble `proxy_url` based on attempt (direct=None, public list entry, or `private_proxy_url`).
  - Call `StealthyFetcher.fetch(..., proxy=proxy_url)` when supported.
  - If not supported, continue without proxy and log a one-time warning.
- Rotation mode:
  - Sequential: retain `_build_attempt_plan` behavior but filter candidates dynamically per attempt for health.
  - Random: pick from healthy public proxies each time; avoid immediate repetition when multiple are available.
- Health tracking:
  - Keep a dict: `{proxy: {failures: int, unhealthy_until: float}}`.
  - On exception or non-2xx: increment failures; if `>= threshold`, set `unhealthy_until=now+cooldown_ms`.
  - On success: reset failures and clear `unhealthy_until`.
  - Skip proxies with `unhealthy_until > now`.
- Edge cases:
  - If all proxies are unhealthy, still attempt private (if configured) and final direct fallback.
  - Do not health-track direct mode.

## Testing

- Unit tests (new):
  - Wiring: verify `proxy` argument is passed to `StealthyFetcher.fetch` (monkeypatch and capture kwargs); verify graceful no-proxy when unsupported.
  - Rotation sequential: order is direct → public proxies (filtered for health) → private → final direct; confirms skip of unhealthy proxies.
  - Rotation random: with seeded RNG, assert chosen sequence matches expectation and excludes unhealthy proxies.
- Health: after N consecutive failures, proxy is skipped for the configured cooldown; after cooldown, it becomes eligible again.
- Integration (optional, marked):
  - If a stable test proxy is available via env, run a smoke test to confirm end-to-end behavior; otherwise skip.

## Acceptance Criteria

- Crawler passes `proxy` to fetch when available; otherwise operates without error.
- Rotation behavior matches `PROXY_ROTATION_MODE` and excludes proxies marked unhealthy.
- After reaching the failure threshold, a proxy is skipped for the configured TTL; success resets health.
- Existing API contracts unchanged; all existing tests pass; new tests cover wiring, rotation, and health.

## Observability

- Log attempt number, mode (direct/public/private), selected proxy (redacted host if necessary), and outcome at INFO.
- Log health state changes (mark unhealthy / recover) at INFO.
- Keep logs concise to avoid noise in normal operation.

## Risks and Mitigations

- Scrapling proxy API mismatch: feature-detect and fall back to no-proxy with a one-time warning.
- Flaky public proxies: health handling and final direct fallback reduce impact.
- Random mode nondeterminism: seed RNG in tests; avoid adding a persistent seed in production.

## Rollout

- Phase 1 (this sprint): proxy wiring enabled, rotation mode honored, basic health tracking and tests.
- Phase 2 (future): proxy health persistence, richer metrics/observability, optional proxy pre-checks (lightweight liveness ping).

## Out of Scope

- Persisting proxy health across restarts.
- Active liveness probing of proxies on a schedule.
- Advanced rotation algorithms (weighted by historical success/latency).
