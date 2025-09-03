# Scrapling Techniques Documentation

This document outlines the web scraping techniques demonstrated in the `demo/` directory files, using the Scrapling library with StealthyFetcher and Camoufox.

## Overview

The demo files showcase two different scraping approaches:
- [`scrapling_aupost_test.py`](scrapling_aupost_test.py:1) - Automated form filling and navigation on Australia Post tracking page
- [`scrapling_parcelsapp_test.py`](scrapling_parcelsapp_test.py:1) - Direct URL scraping from ParcelsApp tracking page

Both use Scrapling's StealthyFetcher for anti-detection capabilities.

## Common Techniques

### 1. StealthyFetcher Setup
```python
from scrapling.fetchers import StealthyFetcher

# Enable adaptive selector system globally
StealthyFetcher.adaptive = True
```

### 2. Basic Fetch Configuration
```python
page = StealthyFetcher.fetch(
    URL,
    headless=False,  # Visible browser for debugging
    network_idle=True,  # Wait for network to be idle
    wait_selector=SELECTOR,
    wait_selector_state="visible",
    timeout=TIMEOUT
)
```

### 3. HTML Content Extraction
```python
if page.status == 200:
    html = page.html_content
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
```

## Specific Techniques

### Australia Post Tracking (scrapling_aupost_test.py)

#### Form Automation with Page Actions
Uses Playwright page actions to automate the tracking search form:

```python
def _go_to_details(page):
    # Locate and fill tracking input
    input_locator = page.locator('input[data-testid="SearchBarInput"]').first
    input_locator.wait_for(state="visible")
    input_locator.fill(TRACKING_NUMBER)

    # Submit form
    track_btn = page.locator('button[data-testid="SearchButton"]').first
    track_btn.click()

    # Wait for navigation to details page
    page.wait_for_url("**/mypost/track/details/**", timeout=15_000)

    # Wait for content selector
    page.locator(SELECTOR).first.wait_for(state="visible", timeout=15_000)
```

#### Anti-Bot Handling
Handles AusPost's device verification interstitial:

```python
# Wait for verification popup
verifying = page.locator("text=Verifying the device")
verifying.first.wait_for(state="visible", timeout=4_000)
verifying.first.wait_for(state="hidden", timeout=20_000)
```

#### Fallback Mechanisms
Multiple retry strategies if initial attempts fail:
- Alternative button selectors
- Manual Enter key submission
- Re-filling form if still on search page
- GeoIP fallback if MaxMind DB is missing

### ParcelsApp Tracking (scrapling_parcelsapp_test.py)

#### Direct URL Scraping
Simpler approach for pages that don't require form interaction:

```python
page = StealthyFetcher.fetch(
    "https://parcelsapp.com/en/tracking/TRACKING_NUMBER",
    headless=False,
    wait_selector="ul.list-unstyled.events",
    timeout=20_000,
    wait_selector_state='visible'
)
```

## Advanced Configuration Options

### GeoIP Integration
```python
# Try with geoip for better fingerprint coherence
try:
    page = _fetch(geoip=True)
except Exception as e:
    if "InvalidDatabaseError" in str(e):
        page = _fetch(geoip=False)  # Fallback without geoip
```

### Additional Browser Arguments
```python
additional_args={
    "disable_coop": True,  # Help with anti-bot checks
}
```

### WebGL and Image Handling
```python
allow_webgl=True,
block_images=False,
```

## Results and Output

Both demos successfully extract tracking information:

- **Australia Post**: Saves complete tracking details page HTML to [`scrapling_aupost_test.html`](scrapling_aupost_test.html)
- **ParcelsApp**: Saves tracking events and package details to [`scrapling_parcelsapp_test.html`](scrapling_parcelsapp_test.html)

The HTML outputs contain structured tracking data including:
- Package status and events timeline
- Delivery location information
- Carrier details
- Estimated delivery times

## Best Practices Demonstrated

1. **Error Handling**: Comprehensive try-catch blocks with specific fallbacks
2. **Selector Stability**: Use of data-testid attributes and stable CSS selectors
3. **Timeout Management**: Appropriate timeouts for different operations
4. **State Verification**: Waiting for elements to be visible before interaction
5. **Network Awareness**: Using network_idle and URL change detection
6. **Anti-Detection**: StealthyFetcher with Camoufox browser fingerprinting

## Usage Notes

- Set `headless=False` during development for debugging
- Enable `adaptive=True` for dynamic selector handling
- Use `network_idle=True` for pages with dynamic content loading
- Implement multiple fallback strategies for reliability
- Handle anti-bot measures like device verification gracefully