# Sprint 17 - Humanize AusPost Crawler (/crawl/auspost)

## Overview

Improve the AusPost endpoint's reliability against bot protection by simulating realistic user behavior: randomized actions, human-like mouse motion, slower interactions, and light random scrolling up/down. The AusPost site uses DataDome, so this sprint focuses on subtle humanization plus configuration that supports consistent fingerprints.

## Problem

- Current page action fills and clicks too deterministically (instant fill, direct click), which can correlate with bot patterns.
- DataDome is sensitive to timing, input method, scroll/mouse heuristics, and fingerprint/geo coherence.
- We need opt-in "humanization" that is bounded (does not tank throughput) yet increases success rates.

## Solution

Add a reusable humanization helper and weave it into `AuspostTrackAction` so the flow feels like a person:

- Mouse moves along stepped paths, with hover and slight jitter before click.
- Type the tracking code with per-character delay instead of instantaneous fill.
- Random micro-pauses between actions; realistic order (hover -> click, brief dwell before typing).
- Light scroll noise up/down during idle moments that will not disturb the form.
- Keep variability bounded via settings so tests and throughput remain acceptable.

## Design

- New helper: `app/services/crawler/actions/humanize.py`

  - `human_pause(min_s, max_s)` - sleep for a small random interval.
  - `move_mouse_to_locator(page, locator, *, steps_range=(12,28), pre_hover=True)` - compute target box center, move mouse using `page.mouse.move(..., steps=n)` with random steps; optional `locator.hover()` pre-hover.
  - `jitter_mouse(page, radius_px=3, steps=2)` - tiny random wiggle before click.
  - `click_like_human(locator, *, hover_first=True)` - hover -> jitter -> `locator.click()`.
  - `type_like_human(locator, text, delay_ms_range=(60,140))` - use `locator.type(text, delay=ms)`.
  - `scroll_noise(page, cycles_range=(1,3), dy_range=(120,480))` - `page.mouse.wheel(0, +/-dy)` with occasional up/down.
- Integrate into `AuspostTrackAction` (`app/services/crawler/actions/auspost.py`)

  - Before focusing the input, add a tiny pause and move mouse to the input like a user, then click.
  - Replace `fill(self.tracking_code)` with `type_like_human(...)`.
  - Move to the Track/Search button, hover, slight jitter, then click.
  - Between attempts and while waiting for verification/device checks, add brief `human_pause` and occasional `scroll_noise` that does not blur the form (for example, once after page load, not constantly).
- Configuration (opt-in; safe defaults): `app/core/config.py`

  - `auspost_humanize_enabled: bool = True`
  - `auspost_humanize_scroll: bool = True`
  - `auspost_typing_delay_ms_min: int = 60`
  - `auspost_typing_delay_ms_max: int = 140`
  - `auspost_mouse_steps_min: int = 12`
  - `auspost_mouse_steps_max: int = 28`
  - `auspost_jitter_radius_px: int = 3`
  - `auspost_jitter_steps: int = 2`
  - `auspost_micro_pause_min_s: float = 0.15`
  - `auspost_micro_pause_max_s: float = 0.40`
  - Intensity/probability gates:
    - `auspost_mouse_move_prob: float = 0.5`
    - `auspost_mouse_jitter_prob: float = 0.5`
    - `auspost_scroll_prob: float = 0.25`
  - Scroll bounds (light by default):
    - `auspost_scroll_cycles_min: int = 1`
    - `auspost_scroll_cycles_max: int = 1`
    - `auspost_scroll_dy_min: int = 80`
    - `auspost_scroll_dy_max: int = 180`
  - AusPost endpoint behavior:
    - `auspost_use_proxy: bool = False` (toggle to run AusPost with or without proxies)
  - `.env` example:

```env
# Humanize AusPost interactions
AUSPOST_HUMANIZE_ENABLED=true
AUSPOST_HUMANIZE_SCROLL=true
AUSPOST_TYPING_DELAY_MS_MIN=60
AUSPOST_TYPING_DELAY_MS_MAX=140
AUSPOST_MOUSE_STEPS_MIN=12
AUSPOST_MOUSE_STEPS_MAX=28
#! Optional fine-tuning (reduced motion)
AUSPOST_JITTER_RADIUS_PX=2
AUSPOST_JITTER_STEPS=2
AUSPOST_MICRO_PAUSE_MIN_S=0.15
AUSPOST_MICRO_PAUSE_MAX_S=0.40
AUSPOST_MOUSE_MOVE_PROB=0.35
AUSPOST_MOUSE_JITTER_PROB=0.30
AUSPOST_SCROLL_PROB=0.15
AUSPOST_SCROLL_CYCLES_MIN=1
AUSPOST_SCROLL_CYCLES_MAX=1
AUSPOST_SCROLL_DY_MIN=60
AUSPOST_SCROLL_DY_MAX=120

# Endpoint behavior
AUSPOST_USE_PROXY=false
```

- Logging
  - Add debug logs to humanize helpers when enabled (for example, chosen delays/steps). Guard behind `LOG_LEVEL=DEBUG` to avoid noise.

## Pseudocode/Example

`app/services/crawler/actions/auspost.py`

```python
from .humanize import (
    human_pause,
    move_mouse_to_locator,
    jitter_mouse,
    click_like_human,
    type_like_human,
    scroll_noise,
)

class AuspostTrackAction(BasePageAction):
    def _execute(self, page):
        settings = app_config.get_settings()
        humanize = getattr(settings, 'auspost_humanize_enabled', True)

        if humanize:
            human_pause(0.25, 0.8)
            scroll_noise(page, cycles_range=(1,2))  # small, once

        for attempt in range(3):
            if humanize:
                # short pre-interaction dwell
                human_pause(0.15, 0.4)

            self._close_global_search(page)

            input_locator = self._first_visible(page, [...])
            if humanize:
                move_mouse_to_locator(page, input_locator)
                jitter_mouse(page)
                input_locator.click()
                type_like_human(input_locator, self.tracking_code)
            else:
                input_locator.click(); input_locator.fill(self.tracking_code)

            try:
                track_btn = self._first_visible(page, [...])
                if humanize:
                    click_like_human(track_btn)
                else:
                    track_btn.click()
            except Exception:
                page.keyboard.press("Enter")

            self._handle_verification(page)

            try:
                page.wait_for_url("**/mypost/track/details/**", timeout=15_000)
                break
            except Exception:
                if humanize:
                    human_pause(0.25, 0.7)
                    scroll_noise(page, cycles_range=(1,1))
                # loop and retry

        # extra wait for header
        page.locator("h3#trackingPanelHeading").first.wait_for(state="visible", timeout=15_000)
        if humanize:
            human_pause(0.2, 0.5)
            scroll_noise(page, cycles_range=(1,2))
        return page
```

`app/services/crawler/actions/humanize.py`

```python
import random, time

def human_pause(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))

def move_mouse_to_locator(page, locator, steps_range=(12, 28), pre_hover=True):
    box = locator.bounding_box()
    if not box:
        return
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    steps = random.randint(*steps_range)
    if pre_hover:
        locator.hover()
    page.mouse.move(cx, cy, steps=steps)

def jitter_mouse(page, locator, radius_px=3, steps=2):
    # jitter around locator center (guarded; skips if no bounding box)
    box = locator.bounding_box()
    if not box:
        return
    cx = box["x"] + box["width"]/2
    cy = box["y"] + box["height"]/2
    page.mouse.move(cx + random.randint(-radius_px, radius_px),
                    cy + random.randint(-radius_px, radius_px), steps=steps)

def click_like_human(locator, hover_first=True):
    if hover_first:
        locator.hover()
    locator.click()

def type_like_human(locator, text, delay_ms_range=(60, 140)):
    locator.fill("")
    locator.type(text, delay=random.randint(*delay_ms_range))

def scroll_noise(page, cycles_range=(1,3), dy_range=(120,480)):
    cycles = random.randint(*cycles_range)
    for _ in range(cycles):
        dy = random.randint(*dy_range)
        if random.random() < 0.35:
            dy = -dy  # occasional upward scroll
        page.mouse.wheel(0, dy)
        time.sleep(random.uniform(0.08, 0.25))
```

Notes

- Keep scroll noise light and avoid while the form has focus to prevent unwanted page movement.
- Replace `.fill()` with `.type()` only for the tracking input to keep humanization targeted.
- All randomness stays within small, user-plausible ranges; probability gates reduce frequency of motion.

## DataDome Considerations

Humanization helps, but fingerprint/geo coherence matters:

- Enable `force_user_data` on this endpoint so the DataDome cookie persists across attempts.
- Prefer headful (`force_headful=true`) during troubleshooting; headless can work once the profile stabilizes.
- Ensure locale and headers match proxy geography:
  - Set `.env` `CAMOUFOX_LOCALE` (for example, `en-AU,en;q=0.9`) and window size `CAMOUFOX_WINDOW` (for example, `1366x768`).
  - Use residential or high-quality datacenter proxies; keep IP stable per profile.
- Leverage existing Camoufox features (WebGL, media, timezone/webRTC/UA harmonization) via our adapter.
- Avoid rapid re-queries; add dwell time after success to mimic reading.

Windows note

- On Windows, the crawler sets `asyncio.WindowsProactorEventLoopPolicy()` to ensure Playwright runs without `NotImplementedError` from the default selector loop.

Example request with persistence knobs:

```bash
curl -sS -X POST http://localhost:8000/crawl/auspost \
  -H 'Content-Type: application/json' \
  -d '{
    "tracking_code": "36LB4503170001000930309",
    "force_user_data": true,
    "force_headful": true
  }'
```

Caution: respect target site Terms; use legitimate purposes and rate limits.

## Testing

- Unit (API): existing schema tests continue to pass.
- Unit (actions): monkeypatch Playwright `locator.type` to assert `delay` is within configured range; assert `mouse.move(..., steps=...)` uses range; guard random with seeded RNG in test mode.
- Integration: run `/crawl/auspost` with humanization on; confirm navigation reaches details and HTML length >= `min_html_content_length`.
- Toggle: with `AUSPOST_HUMANIZE_ENABLED=false`, verify the flow still works using the previous deterministic behavior.
- Proxy behavior: set `AUSPOST_USE_PROXY=true` to run AusPost via the default engine (proxies, retries per global settings); set to `false` to use the no-proxy single-attempt executor.

## Acceptance Criteria

- New humanization helper is added and used by the AusPost page action.
- AusPost action uses typing delays, stepped mouse movement, hover+jitter before click, and light scroll noise.
- Behavior is gated by settings, on by default, and fully off when disabled.
- Logs (DEBUG) show chosen delays/steps when enabled.
- No regression in tests; success rate improves on real runs.
- HTTP fallback completely removed; all fetches use Scrapling/Playwright only.

## Related Files

- Modified: `app/services/crawler/actions/auspost.py` (integrated humanization; safe fallbacks; optional direct-details fallback on NotImplementedError)
- New: `app/services/crawler/actions/humanize.py`
- Modified: `app/services/crawler/executors/single_executor.py` (Windows event loop policy; no HTTP fallback)
- New: `app/services/crawler/executors/auspost_no_proxy.py` (single-attempt, no-proxy executor)
- Modified: `app/services/crawler/auspost.py` (AUSPOST_USE_PROXY toggles engine)
- Modified: `app/core/config.py` (new settings and AUSPOST_USE_PROXY)
- Unchanged API: `app/api/routes.py` — request/response remain the same

## Future Enhancements

* Click random page and go back to main page before typing the url

- Add curved/Bezier mouse paths and edge-following to further mimic human motion.
- Track per-profile success/failure with DataDome to adapt pacing.
- Consider a "profile warm-up" task that visits harmless pages first to seed cookies.
- Optional global "humanize level" (off | light | strong) to scale delays.
