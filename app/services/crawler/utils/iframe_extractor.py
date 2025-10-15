"""Utility for extracting and processing iframe content from HTML."""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from app.services.common.adapters.fetch_params import FetchParams
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter

logger = logging.getLogger(__name__)


class IframeExtractor:
    """Extracts and processes iframe content from HTML pages."""

    _DEFAULT_TIMEOUT_MS = 20_000

    def __init__(self, fetch_client: Optional[ScraplingFetcherAdapter] = None):
        self.fetch_client = fetch_client or ScraplingFetcherAdapter()

    def extract_iframes(self, html: str, base_url: str, fetch_kwargs: Optional[dict] = None) -> Tuple[str, List[dict]]:
        """
        Extract iframe content from HTML and replace iframe tags with their content.

        Args:
            html: The HTML content to process
            base_url: Base URL for resolving relative iframe URLs
            fetch_kwargs: Arguments to pass to fetch client for iframe content

        Returns:
            Tuple of (processed_html, iframe_results)
        """
        if not html:
            return html, []

        # Pattern to match iframe tags with src attribute
        iframe_pattern = r'<iframe[^>]*src=["\']([^"\']+)["\'][^>]*>'
        iframes = re.finditer(iframe_pattern, html, re.IGNORECASE | re.DOTALL)

        processed_html = html
        iframe_results = []

        # Process iframes from end to start to maintain position indices
        iframe_matches = list(iframes)

        if len(iframe_matches) > 1:
            # Use parallel processing for multiple iframes
            iframe_results = self._extract_iframes_parallel(iframe_matches, base_url, fetch_kwargs)
        else:
            # Use sequential processing for single iframe
            iframe_results = self._extract_iframes_sequential(iframe_matches, base_url, fetch_kwargs)

        # Replace iframe tags with their content. Iterate from the end so the
        # string slicing indices remain valid after earlier replacements.
        for match, result in reversed(list(zip(iframe_matches, iframe_results))):
            if result and result.get("content"):
                content_wrapper = f'<iframe>{result["content"]}</iframe>'
                processed_html = (
                    processed_html[:match.start()] +
                    content_wrapper +
                    processed_html[match.end():]
                )

        return processed_html, iframe_results

    def _should_skip_iframe(self, src_url: str) -> bool:
        """Determine if an iframe should be skipped based on its src."""
        if not src_url or src_url.strip() == "":
            return True

        # Skip data URLs, javascript:, and other non-HTTP schemes
        parsed = urlparse(src_url.lower())
        if parsed.scheme in ['data', 'javascript', 'about', 'mailto', 'tel', 'file']:
            return True

        # Skip relative URLs that don't look like external resources
        if not parsed.scheme and not src_url.startswith(('http://', 'https://')):
            # Allow relative URLs that start with / or look like paths
            if not src_url.startswith('/') and '/' not in src_url:
                return True

        return False

    def _is_valid_url(self, url: str) -> bool:
        """Validate if URL is properly formatted and accessible."""
        try:
            parsed = urlparse(url)

            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False

            # Must be http or https
            if parsed.scheme not in ('http', 'https'):
                return False

            return True

        except Exception:
            return False

    def _fetch_iframe_content(self, url: str, fetch_kwargs: Optional[object]) -> Optional[str]:
        """Fetch content from iframe URL."""
        try:
            iframe_params = self._prepare_iframe_params(fetch_kwargs)
            page = self.fetch_client.fetch(url, iframe_params)
            html_content = getattr(page, "html_content", None)

            if html_content and len(html_content.strip()) > 0:
                return html_content.strip()

        except Exception as e:
            logger.debug(f"Failed to fetch iframe content from {url}: {e}")

        return None

    def get_iframe_summary(self, iframe_results: List[dict]) -> dict:
        """Get a summary of processed iframes."""
        return {
            "total_iframes": len(iframe_results),
            "processed_iframes": len([r for r in iframe_results if r.get("content")]),
            "failed_iframes": len([r for r in iframe_results if not r.get("content")]),
            "iframe_sources": [r["src"] for r in iframe_results]
        }

    def _prepare_iframe_params(self, fetch_kwargs: Optional[object]) -> FetchParams:
        """
        Create a FetchParams instance for iframe fetches, trimming unsupported args.
        """
        if isinstance(fetch_kwargs, FetchParams):
            params = fetch_kwargs.copy()
        else:
            params = FetchParams(fetch_kwargs or {})

        # Remove unsupported / conflicting arguments
        if "timeout_seconds" in params:
            del params["timeout_seconds"]
        for selector_key in ("wait_selector", "wait_selector_state"):
            if selector_key in params:
                del params[selector_key]

        # Normalize timing behaviour for iframe fetches with network idle
        params["network_idle"] = True
        params["wait"] = 0

        timeout = params.get("timeout")
        try:
            timeout_int = int(timeout) if timeout is not None else None
        except (TypeError, ValueError):
            timeout_int = None
        params["timeout"] = (
            min(timeout_int, self._DEFAULT_TIMEOUT_MS)
            if timeout_int and timeout_int > 0
            else self._DEFAULT_TIMEOUT_MS
        )
        return params

    def _extract_iframes_parallel(self, iframe_matches, base_url: str, fetch_kwargs: Optional[dict] = None) -> List[dict]:
        """Extract iframe content in parallel using ThreadPoolExecutor."""
        results: List[Optional[dict]] = [None] * len(iframe_matches)
        seen_indices: Dict[str, int] = {}
        duplicate_map: Dict[int, int] = {}

        with ThreadPoolExecutor(max_workers=min(len(iframe_matches), 5)) as executor:
            future_to_index: Dict[object, int] = {}
            for index, match in enumerate(iframe_matches):
                iframe_tag = match.group(0)
                src_url = match.group(1)

                # Skip iframes without src or with internal/srcless attributes
                if self._should_skip_iframe(src_url):
                    logger.debug(f"Skipping iframe with src: {src_url}")
                    continue

                # Resolve relative URL to absolute
                absolute_url = urljoin(base_url, src_url)

                # Validate URL
                if not self._is_valid_url(absolute_url):
                    logger.warning(f"Invalid iframe URL: {absolute_url}")
                    continue

                if absolute_url in seen_indices:
                    duplicate_map[index] = seen_indices[absolute_url]
                    continue

                seen_indices[absolute_url] = index
                future = executor.submit(
                    self._process_single_iframe,
                    src_url,
                    absolute_url,
                    iframe_tag,
                    fetch_kwargs,
                )
                future_to_index[future] = index

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                except Exception as e:
                    logger.error(f"Error processing iframe in parallel: {e}")
                    results[index] = None

        for duplicate_index, original_index in duplicate_map.items():
            results[duplicate_index] = results[original_index]

        return results

    def _extract_iframes_sequential(self, iframe_matches, base_url: str, fetch_kwargs: Optional[dict] = None) -> List[dict]:
        """Extract iframe content sequentially (original behavior)."""
        results: List[Optional[dict]] = []
        seen_results: Dict[str, Optional[dict]] = {}

        for match in iframe_matches:
            iframe_tag = match.group(0)
            src_url = match.group(1)

            # Skip iframes without src or with internal/srcless attributes
            if self._should_skip_iframe(src_url):
                logger.debug(f"Skipping iframe with src: {src_url}")
                results.append(None)
                continue

            # Resolve relative URL to absolute
            absolute_url = urljoin(base_url, src_url)

            # Validate URL
            if not self._is_valid_url(absolute_url):
                logger.warning(f"Invalid iframe URL: {absolute_url}")
                results.append(None)
                continue

            if absolute_url in seen_results:
                results.append(seen_results[absolute_url])
                continue

            # Process single iframe
            result = self._process_single_iframe(src_url, absolute_url, iframe_tag, fetch_kwargs)
            seen_results[absolute_url] = result
            results.append(result)

        return results

    def _process_single_iframe(self, src_url: str, absolute_url: str, iframe_tag: str,
                               fetch_kwargs: Optional[dict] = None) -> Optional[dict]:
        """Process a single iframe and return result."""
        try:
            # Fetch iframe content
            iframe_content = self._fetch_iframe_content(absolute_url, fetch_kwargs)

            if iframe_content:
                # Create result record
                iframe_result = {
                    "src": src_url,
                    "absolute_url": absolute_url,
                    "content": iframe_content,
                    "original_tag": iframe_tag
                }
                return iframe_result
            else:
                logger.warning(f"Failed to fetch content for iframe: {absolute_url}")
                return None

        except Exception as e:
            logger.error(f"Error processing iframe {absolute_url}: {e}")
            return None
