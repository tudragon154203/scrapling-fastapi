# Project Summary: Playwright FastAPI Crawler

This document summarizes the key information about the "Playwright FastAPI Crawler" project, focusing on details necessary for re-implementation using an alternative browser automation library.

## 1. Project Overview

The project is a web scraping service built with FastAPI that exposes HTTP API endpoints for crawling web pages. Its primary features include:
- Generic web crawling.
- Specialized DPD package tracking.
- Enhanced stealth capabilities to resist bot detection.
- Flexible headless/headful browser control.
- SOCKS5 proxy rotation and management.
- Configurable retry logic.
- Health monitoring and diagnostics.

## 2. Key Functionality to Replicate

The core functionalities that need to be replicated with a different browser automation library are:

### a. Web Page Interaction
- Navigating to URLs.
- Waiting for specific CSS selectors or fixed times.
- Capturing HTML content of pages.
- Filling forms (specifically for DPD tracking).

### b. Stealth and Anti-Detection
- Mimicking human browser behavior to avoid detection.
- Handling browser fingerprints.
- Potentially integrating with external stealth libraries or implementing custom techniques.

### c. Headless/Headful Control
- Ability to run the browser in headless or headful mode based on configuration or request parameters.
- Platform-aware handling of headful requests (e.g., forcing headful on Windows for debugging, ignoring on Linux/Docker).

### d. Proxy Integration
- Routing browser traffic through SOCKS5 proxies.
- Managing a pool of proxies and handling rotation/fallback.

### e. Error Handling and Retries
- Implementing retry mechanisms for failed crawling attempts.
- Detecting and handling proxy-related errors.

## 3. API Endpoints

The project exposes the following HTTP API endpoints:

### a. `POST /crawl` - Generic Web Crawling

- **Description**: Performs a generic web crawl of a specified URL.
- **Request Body (JSON)**:
    ```json
    {
        "url": "string",
        "x_wait_for_selector": "string | null",
        "x_wait_time": "integer | null",
        "x_force_user_data": "boolean",
        "x_force_headful": "boolean"
    }
    ```
    - `url`: Target URL to crawl.
    - `x_wait_for_selector`: Optional CSS selector to wait for before capturing HTML.
    - `x_wait_time`: Optional fixed wait time in seconds before capturing HTML.
    - `x_force_user_data`: Whether to use persistent user data directory (not recommended for parallel runs).
    - `x_force_headful`: Force browser to run in headful mode (Windows only).
- **Response Body (JSON)**:
    ```json
    {
        "status": "string", // "success" or "failure"
        "url": "string",
        "html": "string | null", // HTML content if successful
        "message": "string | null" // Error message if failed
    }
    ```

### b. `POST /crawl/dpd` - DPD Package Tracking

- **Description**: Specialized crawling for DPD package tracking, including automated form filling.
- **Request Body (JSON)**:
    ```json
    {
        "tracking_code": "string",
        "x_force_user_data": "boolean",
        "x_force_headful": "boolean"
    }
    ```
    - `tracking_code`: DPD tracking code to search for.
    - `x_force_user_data`: Whether to use persistent user data directory (not recommended for parallel runs).
    - `x_force_headful`: Force browser to run in headful mode (Windows only).
- **Response Body (JSON)**:
    ```json
    {
        "status": "string", // "success" or "failure"
        "tracking_code": "string",
        "html": "string | null", // HTML content of tracking results page if successful
        "message": "string | null" // Error message if failed
    }
    ```

### c. `GET /health` - Basic Service Health Check

- **Description**: Returns the basic health status of the service.

### d. `GET /health/stealth` - Detailed Stealth Health

- **Description**: Provides detailed health information about the stealth functionality.

### e. `GET /metrics/stealth` - Stealth Metrics

- **Description**: Returns comprehensive metrics and statistics related to stealth operations.

### f. `POST /diagnostics/stealth` - Stealth Diagnostics

- **Description**: Triggers stealth diagnostics and logging.

## 4. Core Technologies

- **Web Framework**: FastAPI (Python) - Likely to be retained.
- **Browser Automation (to be replaced)**: Playwright (Python library)
    - The current implementation heavily relies on `tf-playwright-stealth` for advanced anti-detection. Any new library must offer comparable stealth capabilities or allow for custom anti-detection techniques.
- **Data Validation**: Pydantic (Python) - Used for defining request/response schemas.

## 5. Environment Variables

The following environment variables control the application's behavior and need to be considered for any re-implementation:

- `CHROME_EXECUTABLE`: Path to Chrome Portable executable.
- `CHROME_DATA_DIR`: Path to Chrome user data directory.
- `TIMEOUT`: Default timeout for browser operations (seconds).
- `PORT`: FastAPI server port (default: 5681).
- `HEADLESS`: Whether to run browser in headless mode (boolean).
- `MAX_RETRIES`: Maximum number of retry attempts for crawling.
- `PROXY_LIST_FILE_PATH`: Path to the SOCKS5 proxy list file (e.g., `private_socks5_proxies.txt`).
- `LOG_LEVEL`: Logging level (e.g., INFO, DEBUG).

## 6. Proxy Management

The project includes robust proxy management:
- Supports SOCKS5 proxies.
- Reads proxy list from a file specified by `PROXY_LIST_FILE_PATH`.
- Implements automatic proxy rotation.
- Includes fallback to direct connection if proxies fail.
- Error detection for proxy-related issues.

## 7. Core Implementation Details

This section outlines the internal logic and flow of the application, particularly concerning browser automation, stealth, and retry mechanisms.

### a. Retry and Proxy Strategy (`app/services/crawler/base.py`)

- **`execute_crawl_with_retries`**: This central function orchestrates the crawling process with retries and proxy handling.
    - It attempts the crawl up to `MAX_RETRIES` times.
    - **Proxy Selection**: For each attempt, it dynamically selects a proxy using a `ProxyManager`. The strategy involves:
        - Prioritizing public proxies for initial attempts.
        - Using a private proxy for later attempts (e.g., second-to-last).
        - Falling back to a direct connection for the final attempt if all proxies fail.
    - **Browser Launch**: It calls `launch_browser` (from `app/services/browser/context.py`) to initialize the browser with the selected proxy and apply stealth.
    - **Error Handling**: It catches `PlaywrightTimeoutError` and `PlaywrightError`. If an error is identified as proxy-related, the failing proxy is removed from the pool to prevent future use.

### b. Browser Launch and Context Setup (`app/services/browser/context.py`)

- **`launch_browser`**: This function is responsible for launching the Chromium browser instance.
    - It takes parameters for headless mode, executable path, proxy strategy, and an optional user data directory for persistent contexts.
    - **Proxy Configuration**: The selected proxy (from `ProxyManager`) is directly passed to Playwright's `launch` or `launch_persistent_context` methods.
    - **Basic Anti-Detection**: It includes default browser arguments like `--disable-blink-features=AutomationControlled` and a custom user agent string.
    - **Stealth Application**: After launching the browser context, it calls `setup_context_stealth` to apply advanced stealth techniques at the context level.

### c. Enhanced Stealth Mechanism (`app/services/browser/stealth_enhanced.py`)

- The project employs a "combined" stealth approach for maximum bot detection resistance.
- **`COMPREHENSIVE_STEALTH_SCRIPT`**: A large JavaScript snippet containing numerous custom anti-detection techniques. This script is injected into every new page. Key techniques include:
    - Spoofing `navigator` properties (e.g., `webdriver`, `plugins`, `languages`, `platform`, `hardwareConcurrency`, `deviceMemory`).
    - Overriding `window.chrome`.
    - Masking WebGL vendor and renderer information.
    - Spoofing `Permissions.query()`.
    - Spoofing screen and window dimensions.
    - Spoofing `navigator.mimeTypes`.
    - Removing Playwright-specific traces (e.g., `navigator.__proto__.webdriver`, CDC properties).
- **`apply_combined_stealth`**: This method is called for each new page within a browser context.
    - It first attempts to apply `tf-playwright-stealth` (if available).
    - **Crucially**, it then *always* injects the `COMPREHENSIVE_STEALTH_SCRIPT` into the page, regardless of whether `tf-playwright-stealth` succeeded. This ensures a layered defense.

### d. Generic Crawling Logic (`app/services/crawler/generic.py`)

- **`GenericCrawler`**: Implements the `crawl` method for general web scraping.
    - It navigates to the target URL.
    - It supports waiting for a specific CSS selector to appear or for a fixed duration before extracting content.
    - It retrieves the full HTML content of the page.

### e. DPD Specific Crawling Logic (`app/services/crawler/dpd.py`)

- **`DPDCrawler`**: Implements the `crawl` method for DPD package tracking. This involves a sequence of specific Playwright interactions:
    - Navigating to the DPD tracking page.
    - Filling the tracking code into an input field (`page.fill()`).
    - Clicking the search button (`page.click()`).
    - Waiting for page loads and specific elements to appear.
    - Handling a "Continue without ZIP code" button if present.
    - Extracting the HTML content of the tracking results page.
    - Includes logic to check for common DPD error messages on the page.

This summary should provide a more in-depth understanding of the project's internal workings, which is essential for a successful re-implementation.