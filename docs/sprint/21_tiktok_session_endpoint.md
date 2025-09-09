# New Endpoint: `/tiktok/session` (POST)

This endpoint provides interactive browsing capabilities for TikTok, similar to the existing `/browse` endpoint, but with specific considerations for TikTok login status and read-only access to user data.

## Functionality

* **Behavior:** Operates like the `/browse` endpoint, specifically targeting `tiktok.com`.
* **Login Check:** Upon launching the browser, the system will check if the user is already logged in to TikTok using the provided user data directory.
  * **If Logged In:** The user is allowed to interact freely with the browser. Upon browser closure (either by user or timeout), a `200 OK` response is returned.
  * **If Not Logged In:** The browser is immediately closed, and an error response indicating "not logged in to TikTok" is returned.

## API Specification

### Request Schema (`TikTokSessionRequest`)

The `/tiktok/session` endpoint expects an empty request body. All necessary parameters are derived from the context (e.g., `user_data_dir_path` from the environment or default configurations).

### Response Schema (`TikTokSessionResponse`)

* **`status` (string):** "success" or "error".
* **`message` (string):** A descriptive message about the outcome.
* **`error_details` (optional, object):** Contains additional error information (only on error).

## Technical Details

### Login-State Detection

1. Navigate to TikTok home.
2. Wait for either:
   * Selector unique to logged-in header (e.g., profile avatar).
   * Selector unique to logged-out state (e.g., “Log in” button).
3. Fallback: intercept TikTok API requests for `<span>/user/info</span>`. HTTP 2xx = logged in, 401/403 = not logged in.
4. Retry once after soft refresh if inconclusive (max 8s).

If not logged in, close window and return 409.

---

### User-Data Handling

* Default = **read mode**: clone `<span>.../master</span>` to `<span>.../clones/<uuid></span>` and use as `<span>user_data_dir</span>`. Cleanup on session end.
* Write mode not exposed here. If enabled in config, requires exclusive lock. Return 423 if locked.
* Always redact proxy values in logs.

### Interactive

When the user is "working freely," the browser supports and expects full interactive capabilities, including but not limited to:

* Direct navigation to any URL.
* Form submission.
* Clicking links and buttons.
* Keyboard input.
* Scrolling.
* Waiting for user input or specific page events.
  The session remains active until manually closed by the user or the `timeout_seconds` is reached. Due to the read-only nature of the user data directory, any actions that would typically persist data (like logging in or changing settings) will not be saved.

## Architectural Considerations

**Separate Service:** A dedicated service, `app/services/tiktok`, should be created to encapsulate TikTok-specific logic.

**`TiktokExecutor`:** This executor can be modeled after the existing `BrowseExecutor` in `app/services/browser/executors/browse_executor.py`.

**`AbstractBrowsingExecutor`:** To promote code reuse and maintain consistency, an abstract base class, `AbstractBrowsingExecutor`, should be considered in `app/services/common` to encapsulate common functionalities shared between `BrowseExecutor` and `TiktokExecutor`. This would include:

* Browser lifecycle management (`_launch_browser`, `_close_browser`).
* Interactive session handling (`_wait_for_user_close`, `_handle_interactive_error`).
* User data management (`_resolve_user_data_dir`, `_acquire_user_data_lock`, `_release_user_data_lock`).
* The core execution flow (`execute` method).

## Test Plan

* Unit tests for login detection and user-data handling.
* Integration test (headless):
  * Start session → 200 with `<span>session_id</span>`.
  * Not logged in → 409.
  * Expired session → 504.
* API schema validation: empty body accepted; unknown fields rejected.
