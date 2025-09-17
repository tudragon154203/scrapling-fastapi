"""
Demo script that mimics the browsing behavior of /browse for tiktok.com
This script demonstrates how to programmatically browse TikTok and perform search operations.
"""

import sys
import os
from typing import Optional, Dict, Any
import time

# Fix import path by adding the parent directory (project root) to Python path
# This assumes the script is in the demo directory and app is in the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from app.schemas.tiktok import TikTokSessionConfig
    from app.services.common.engine import CrawlerEngine
    from app.schemas.crawl import CrawlRequest
    from app.services.browser.actions.wait_for_close import WaitForUserCloseAction
    from app.services.browser.actions.humanize import human_pause
    from app.services.common.browser.user_data import user_data_context
    from app.services.browser.actions.humanize import type_like_human
    from app.services.browser.actions.base import BasePageAction
    import app.core.config as app_config
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root directory")
    print(f"Project root: {project_root}")
    print(f"App directory exists: {os.path.exists(os.path.join(project_root, 'app'))}")
    sys.exit(1)


class TikTokBrowseCrawler:
    """TikTok-specific browse crawler that mimics the /browse endpoint behavior"""

    def __init__(self, config: Optional[TikTokSessionConfig] = None):
        self.config = config or TikTokSessionConfig()
        self.engine = None

    def run_with_typing(self, url: str, search_query: str) -> Dict[str, Any]:
        """Run a browse request with automated typing functionality.

        This extends the browse endpoint to include automated typing.
        """
        try:
            print("LAUNCHING: Starting TikTok browsing session with automated typing...")
            print(f"URL: {url}")
            print(f"Search query: {search_query}")
            print("Browser will open and automatically type the search query!")

            page_action = TikTokAutoSearchAction(search_query)
            crawl_response = self._browse_with_action(url, page_action)

            return {
                "status": "success",
                "message": "TikTok browsing session with automated typing completed",
                "details": {
                    "url": url,
                    "search_query": search_query,
                    "response": crawl_response.model_dump() if hasattr(crawl_response, 'model_dump') else crawl_response.__dict__
                }
            }

        except Exception as e:
            print(f"ERROR: TikTok browse session with typing failed: {e}")
            return {
                "status": "failure",
                "message": f"Error: {str(e)}",
                "url": url,
                "search_query": search_query
            }

    def run(self, url: str = "https://www.tiktok.com/") -> Dict[str, Any]:
        """Run a browse request for TikTok user data population.

        This mimics the BrowseCrawler.run() method but specifically for TikTok.
        """
        try:
            print("LAUNCHING: Starting TikTok browsing session...")
            print(f"URL: {url}")
            print("Browser will open in headful mode - close it when done browsing")

            page_action = WaitForUserCloseAction()
            crawl_response = self._browse_with_action(url, page_action)

            return {
                "status": "success",
                "message": "TikTok browsing session completed successfully",
                "details": {
                    "url": url,
                    "response": crawl_response.model_dump() if hasattr(crawl_response, 'model_dump') else crawl_response.__dict__
                }
            }

        except Exception as e:
            print(f"Error: TikTok browse session failed: {e}")
            return {
                "status": "failure",
                "message": f"Error: {str(e)}",
                "url": url
            }

    def _browse_with_action(self, url: str, page_action: BasePageAction):
        """Shared browse flow: configure engine, user-data and run action."""
        # Convert browse request to crawl request with forced flags
        crawl_request = self._convert_browse_to_crawl_request(url)

        # Use user data context (always temporary clone)
        settings = app_config.get_settings()
        user_data_dir = getattr(settings, 'camoufox_user_data_dir', 'data/camoufox_profiles')

        with user_data_context(user_data_dir, 'write') as (effective_dir, cleanup):
            try:
                # Signal write-mode to CamoufoxArgsBuilder via settings (runtime-only flags)
                try:
                    setattr(settings, '_camoufox_user_data_mode', 'write')
                    setattr(settings, '_camoufox_effective_user_data_dir', effective_dir)
                except Exception:
                    pass

                # Update crawl request with user-data enablement
                crawl_request.force_user_data = True

                # Use the BrowseExecutor like the actual browse endpoint
                from app.services.browser.executors.browse_executor import BrowseExecutor

                browse_executor = BrowseExecutor()

                # Create CrawlerEngine with BrowseExecutor
                self.engine = CrawlerEngine(
                    executor=browse_executor,
                    fetch_client=browse_executor.fetch_client,
                    options_resolver=browse_executor.options_resolver,
                    camoufox_builder=browse_executor.camoufox_builder
                )

                # Execute browse session
                print("BROWSER: Starting browser...")
                return self.engine.run(crawl_request, page_action)

            finally:
                # Ensure cleanup is called
                try:
                    # Remove runtime flags to avoid leaking into subsequent requests
                    if hasattr(settings, '_camoufox_user_data_mode'):
                        delattr(settings, '_camoufox_user_data_mode')
                    if hasattr(settings, '_camoufox_effective_user_data_dir'):
                        delattr(settings, '_camoufox_effective_user_data_dir')
                except Exception:
                    pass
                cleanup()

    def _convert_browse_to_crawl_request(self, url: str):
        """Convert browse request to generic crawl request with forced flags."""
        # Use provided URL or default to TikTok
        if not url:
            url = "https://www.tiktok.com/"

        return CrawlRequest(
            url=url,
            force_headful=True,  # Always use headful mode for interactive browsing
            force_user_data=True,  # Always enable user data
            timeout_seconds=None,  # No timeout for manual sessions
        )


class TikTokAutoSearchAction(BasePageAction):
    """Page action that automatically performs TikTok search using human-like typing."""

    def __init__(self, search_query: str):
        self.search_query = search_query
        self.page = None

    def __call__(self, page):
        return self._execute(page)

    def _execute(self, page):
        try:
            self.page = page
            print("AUTOMATION: Starting automated TikTok search...")

            # Wait for page to load and search bar to be available
            print("AUTOMATION: Waiting for page to load...")

            # Find and click the search button using the specific TikTok selector
            search_selectors = [
                'button[data-e2e="nav-search"]',
                '.css-1o3yfob-5e6d46e3--DivSearchWrapper e9sj7gd4 button[data-e2e="nav-search"]',
                '.TUXButton[data-e2e="nav-search"]',
                '[data-e2e="nav-search"]',
                'button[aria-label*="Search"]',
                '.css-udify9-5e6d46e3--StyledTUXSearchButton'
            ]

            search_clicked = False
            for selector in search_selectors:
                try:
                    search_bar = page.wait_for_selector(selector, timeout=5000)
                    if search_bar:
                        print(f"AUTOMATION: Found search bar with selector: {selector}")
                        # Use human-like hover and click
                        from app.services.browser.actions.humanize import move_mouse_to_locator, click_like_human

                        # Move mouse to search bar
                        move_mouse_to_locator(page, search_bar, steps_range=(15, 25))

                        # Click like human
                        click_like_human(search_bar)

                        search_clicked = True
                        break
                except Exception as e:
                    print(f"AUTOMATION: Selector {selector} failed: {e}")
                    continue

            if not search_clicked:
                print("AUTOMATION: Could not find search button, proceeding with typing attempt...")
                try:
                    # Fallback: try to focus on the page and type
                    page.focus('body')
                except Exception:
                    pass

            # Find the search input field after clicking the search button
            search_input_selectors = [
                'input[data-e2e="search-user-input"]',
                'input[placeholder*="Search"]',
                'input[type="search"]',
                '.search-bar',
                'input[placeholder*="search"]',
                'input[data-e2e="search-input"]'
            ]

            search_input_found = False
            for selector in search_input_selectors:
                try:
                    search_input = page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        print(f"AUTOMATION: Found search input with selector: {selector}")
                        search_input_found = True
                        break
                except Exception as e:
                    print(f"AUTOMATION: Search input selector {selector} failed: {e}")
                    continue

            # Type the search query using human-like typing
            print(f"AUTOMATION: Typing search query: '{self.search_query}'")

            # Handle encoding issues by trying different approaches
            search_query_encoded = self.search_query
            try:
                # Try to encode the query to handle special characters
                search_query_encoded = self.search_query.encode('utf-8', errors='ignore').decode('utf-8')
            except Exception:
                pass

            if search_input_found:
                try:
                    type_like_human(search_input, search_query_encoded, delay_ms_range=(50, 100))
                except Exception as e:
                    print(f"AUTOMATION: type_like_human failed: {e}")
                    # Fallback to keyboard typing
                    try:
                        page.keyboard.type(search_query_encoded)
                    except Exception as e2:
                        print(f"AUTOMATION: Keyboard typing fallback failed: {e2}")
            else:
                # Fallback: try to type on the focused element
                try:
                    human_pause(1, 2)
                    page.keyboard.type(search_query_encoded)
                except Exception as e:
                    print(f"AUTOMATION: Fallback typing failed: {e}")

            # Submit the search (press Enter)
            print("AUTOMATION: Submitting search...")
            try:
                page.keyboard.press('Enter')
            except Exception as e:
                print(f"AUTOMATION: Enter key failed: {e}")

            # Wait for search results to load - deterministic wait for URL containing '/search'
            print("AUTOMATION: Waiting for search results page to load...")
            human_pause(2, 3)  # Human-like pause

            # Wait for URL to contain '/search' - deterministic wait
            print("AUTOMATION: Waiting for URL to contain '/search'...")
            try:
                page.wait_for_function(
                    "window.location.href.includes('/search')",
                    timeout=15000
                )
                print("AUTOMATION: Search URL detected!")
            except Exception as e:
                print(f"AUTOMATION: Search URL wait timeout or error: {e}")
                # Continue anyway, as search might have loaded

            # Wait for presence of real result selectors - deterministic wait with enhanced robustness
            print("AUTOMATION: Waiting for search result elements...")
            result_selectors = [
                # Content-based selectors
                '[class*="video"]',  # Any element with video in class
                '[class*="card"]',  # Any element with card in class
                'img[src*="tiktokcdn"]',  # TikTok images
                'video',  # Video elements

                # Primary selectors based on HTML analysis
                'a[href*="/@"]',  # User profile links
                'a[href*="/video/"]',  # Video links
                '[data-e2e="search-result-item"]',  # TikTok search result items
                '[data-e2e="search-result-video"]',  # Video results

                # Secondary selectors based on common TikTok patterns
                '.css-1dc0ofe-5e6d46e3--DivOneColSkeletonContainer',  # Content container
                '.css-1moj8bd-5e6d46e3--DivOneColSkeletonCard',  # Video card skeleton

                # Fallback selectors
                '.video-card',  # Video cards
                '.tiktok-card',  # TikTok cards
                '.search-result-item',  # Generic search results
                'a[href*="/discover"]',  # Discover links
                'a[href*="/trending"]'  # Trending links
            ]

            result_found = False
            for selector in result_selectors:
                try:
                    print(f"AUTOMATION: Trying result selector: {selector}")
                    result_element = page.wait_for_selector(selector, timeout=5000)
                    if result_element:
                        print(f"AUTOMATION: Found search result with selector: {selector}")
                        result_found = True
                        break
                except Exception as e:
                    print(f"AUTOMATION: Result selector {selector} failed: {e}")
                    continue

            if not result_found:
                print("AUTOMATION: No specific result selectors found, trying content-based detection...")

                # Fallback 1: Check for any content that indicates search results loaded
                try:
                    page_content = page.content()
                    if len(page_content) > 10000:  # Substantial content indicates page loaded
                        print("AUTOMATION: Page content detected (length > 10KB), assuming search results loaded")
                        result_found = True
                    else:
                        print(f"AUTOMATION: Page content seems light ({len(page_content)} chars)")
                except Exception as e:
                    print(f"AUTOMATION: Could not check page content: {e}")

                # Fallback 2: Wait for any interactive elements that suggest content is ready
                if not result_found:
                    try:
                        interactive_selectors = [
                            'button',  # Any buttons
                            'a',  # Any links
                            '[role="button"]',  # Button elements
                            'div[tabindex]',  # Focusable divs
                        ]

                        for selector in interactive_selectors:
                            try:
                                elements = page.query_selector_all(selector)
                                if len(elements) > 10:  # Many interactive elements suggest content
                                    print(f"AUTOMATION: Found {len(elements)} {selector} elements, assuming content loaded")
                                    result_found = True
                                    break
                            except Exception:
                                continue
                    except Exception as e:
                        print(f"AUTOMATION: Could not check interactive elements: {e}")

                # Final fallback: wait a bit more for content to settle
                if not result_found:
                    print("AUTOMATION: Using final fallback wait...")
                    human_pause(3, 5)
                else:
                    print("AUTOMATION: Content-based detection confirmed search results loaded")

            # Scroll down for 10 seconds
            print("AUTOMATION: Scrolling down for 10 seconds...")
            start_time = time.time()
            while time.time() - start_time < 10:
                try:
                    page.mouse.wheel(0, 500)  # Scroll down
                    time.sleep(1)  # Small delay between scroll actions
                except Exception as e:
                    print(f"AUTOMATION: Scroll error: {e}")
                    break

            # Wait additional short time after scrolling for content to settle
            print("AUTOMATION: Waiting briefly after scrolling...")
            human_pause(1, 2)

            # Save HTML content after scrolling completes
            print("AUTOMATION: Saving HTML content...")
            self._save_html(page)

            print("AUTOMATION: Search automation completed!")
            print("BROWSER: You can now browse the search results manually. Close browser when done.")

        except Exception as e:
            print(f"AUTOMATION: Error during automated search: {e}")
            print("AUTOMATION: Manual interaction may be required")

        return page

    def _save_html(self, page):
        """Save the final HTML content to a file"""
        try:
            # Get HTML content from the page
            html_content = page.content()

            # Create demo directory if it doesn't exist
            demo_dir = os.path.dirname(os.path.abspath(__file__))
            html_file_path = os.path.join(demo_dir, 'browsing_tiktok_search.html')

            # Ensure demo directory exists
            os.makedirs(demo_dir, exist_ok=True)

            # Save HTML with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            try:
                with open(html_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"<!-- TikTok Search Demo Results - {timestamp} -->\n")
                    f.write(f"<!-- Search query: {self.search_query} -->\n\n")
                    f.write(html_content)
            except UnicodeEncodeError:
                # Fallback to latin-1 with error handling
                with open(html_file_path, 'w', encoding='latin-1', errors='replace') as f:
                    f.write(f"<!-- TikTok Search Demo Results - {timestamp} -->\n")
                    f.write(f"<!-- Search query: {self.search_query} -->\n\n")
                    f.write(html_content)

            print(f"HTML saved to: {html_file_path}")

        except Exception as e:
            print(f"ERROR: Could not save HTML: {e}")
            # Try alternative method
            try:
                # Fallback: get page title and URL
                title = page.title()
                url = page.url
                try:
                    with open(html_file_path, 'w', encoding='utf-8') as f:
                        f.write(f"<!-- TikTok Search Demo Results - {timestamp} -->\n")
                        f.write(f"<!-- Search query: {self.search_query} -->\n")
                        f.write(f"<!-- Page Title: {title} -->\n")
                        f.write(f"<!-- Page URL: {url} -->\n")
                        f.write("<!-- Could not retrieve full HTML content -->\n")
                except UnicodeEncodeError:
                    # Fallback to latin-1 with error handling
                    with open(html_file_path, 'w', encoding='latin-1', errors='replace') as f:
                        f.write(f"<!-- TikTok Search Demo Results - {timestamp} -->\n")
                        f.write(f"<!-- Search query: {self.search_query} -->\n")
                        f.write(f"<!-- Page Title: {title} -->\n")
                        f.write(f"<!-- Page URL: {url} -->\n")
                        f.write("<!-- Could not retrieve full HTML content -->\n")
                print(f"Fallback HTML info saved to: {html_file_path}")
            except Exception as e2:
                print(f"ERROR: Could not save fallback HTML: {e2}")


class TikTokSearchDemo:
    """TikTok browsing demo using the Browse-like behavior"""

    def __init__(self, config: Optional[TikTokSessionConfig] = None):
        self.config = config or TikTokSessionConfig()
        self.browse_crawler = TikTokBrowseCrawler(self.config)

    def browse_tiktok_with_search(self, url: str, search_query: str) -> Dict[str, Any]:
        """Browse TikTok and perform search bar interaction with automated typing"""
        try:
            print("STARTING: Starting TikTok search session with automated typing...")
            print(f"Homepage URL: {url}")
            print(f"Search query: {search_query}")

            # Use the enhanced browse crawler with automated typing
            result = self.browse_crawler.run_with_typing(url, search_query)

            return result

        except Exception as e:
            print(f"ERROR: TikTok search session failed: {e}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}",
                "url": url,
                "search_query": search_query
            }

    def browse_tiktok(self, url: str = "https://www.tiktok.com/", search_query: str = None) -> Dict[str, Any]:
        """
        Browse TikTok and optionally perform a search.
        This mimics the /browse endpoint behavior for TikTok.
        """
        try:
            print("Starting: Starting TikTok browsing session...")
            print(f"URL: {url}")

            if search_query:
                print(f"Search query: {search_query}")

            # Use the browse crawler to run the session
            result = self.browse_crawler.run(url)

            # Add search query to result if provided
            if search_query:
                result["search_query"] = search_query

            return result

        except Exception as e:
            print(f"Error: TikTok browsing session failed: {e}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}",
                "url": url,
                "search_query": search_query
            }

    def demo_search(self, search_query: str = "gai xinh"):
        """Demonstrate TikTok search functionality using the search bar"""
        print(f"\nDEMO: Demonstrating TikTok search: '{search_query}'")
        print("=" * 50)
        print("This will:")
        print("1. Go to TikTok homepage")
        print("2. Find and click the search bar")
        print("3. Type the search query")
        print("4. Submit the search")
        print("5. Wait for search results to load")
        print("Watch the browser automation process...")

        # We'll start at the homepage and perform search interaction
        base_url = "https://www.tiktok.com/"

        # For this demo, we'll show the search functionality instructions
        result = self.show_search_demo(base_url, search_query)

        return result

    def show_search_demo(self, url: str, search_query: str) -> Dict[str, Any]:
        """Show search demo with real browsing"""
        print(f"\nSEARCH DEMO: '{search_query}'")
        print("=" * 50)
        print("This demo will perform a real search on TikTok:")
        print("1. Browser opens to TikTok homepage")
        print("2. Automatically clicks the search icon")
        print("3. Types the search query")
        print("4. Submits the search")
        print("5. Waits for search results to load")
        print("6. You can manually browse the results")
        print("7. Close browser when done")
        print()

        print("Starting at:", url)
        print("Will search for:", search_query)
        print()

        # Directly browse to the URL
        result = self.browse_crawler.run_with_typing(url, search_query)

        return result

    def _interactive_search_session(self, url: str, search_query: str) -> Dict[str, Any]:
        """Create an interactive search session with manual search instructions"""
        print("\nINTERACTIVE SEARCH SESSION:")
        print("-" * 30)
        print("MANUAL SEARCH INSTRUCTIONS:")
        print("1. Browser will open to TikTok homepage")
        print("2. Look for the search icon/bar at the top")
        print("3. Click on the search area")
        print("4. Type: gai xinh")
        print("5. Press Enter or click search button")
        print("6. Browse the search results")
        print("7. Close browser when done")
        print()

        # Start browsing the homepage (user will perform search manually)
        return self.browse_crawler.run(url)


def main():
    """Main demo function"""
    print("TikTok Browser Demo - Actual Browser Launch")
    print("=" * 50)
    print("This demo will launch a real browser for TikTok browsing!")
    print("Close the browser window to continue to the next demo.")
    print()

    # Create demo instance with custom configuration
    config = TikTokSessionConfig(
        tiktok_url="https://www.tiktok.com/",
        headless=False,  # Show browser (interactive)
        max_session_duration=300,
        user_data_master_dir="./user_data",
        user_data_clones_dir="./user_data/clones"
    )

    demo = TikTokSearchDemo(config)

    try:
        print("1. TikTok Search Demo")
        print("-" * 25)
        print("This will perform a real TikTok search for 'gai xinh'")
        print("Starting demo now...")

        search_result = demo.demo_search("gai xinh")

        print("\n" + "=" * 50)
        print("DEMO SUMMARY:")
        print("-" * 15)
        print(f"Search result: {search_result['status']}")
        print("\nDemo completed successfully!")

    except KeyboardInterrupt:
        print("\nSTOP: Demo interrupted by user")
    except Exception as e:
        print(f"\nERROR: Demo error: {e}")
    finally:
        print("\nDONE: Demo completed!")


if __name__ == "__main__":
    # Run the demo
    main()
