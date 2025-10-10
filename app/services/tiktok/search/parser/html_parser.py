"""
BeautifulSoup DOM parsing for TikTok
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List

from bs4 import BeautifulSoup

from .json_parser import _from_sigi_state
from .utils import parse_like_count

logger = logging.getLogger(__name__)


def _extract_id_from_url(href: str) -> str:
    if not href:
        return ""

    url = href
    if url.startswith('/'):
        url = f"https://www.tiktok.com{url}"

    match = re.search(r"/video/(\d+)", url)
    if match:
        return match.group(1)

    try:
        clean = url.split('?', 1)[0].split('#', 1)[0]
        parts = [part for part in clean.split('/') if part and not part.startswith('http')]
        return parts[-1] if parts else ""
    except Exception:
        return ""


def _best_caption_from(item) -> str:
    caption = item.find(attrs={"data-e2e": "search-card-video-caption"})
    if caption and caption.get_text(strip=True):
        return caption.get_text(strip=True)

    caption = item.find(attrs={"data-e2e": "search-card-desc"})
    if caption and caption.get_text(strip=True):
        return caption.get_text(strip=True)

    selectors = [
        '[data-e2e="search-card-video-caption"]',
        '.search-card-video-caption',
        '[class*="caption"]',
        '[class*="title"]',
        '[class*="description"]',
        '[class*="text"]',
        '[class*="content"]',
        '[class*="message"]',
        '[class*="body"]',
        'h3', 'h4', 'p', 'div[class*="caption"]', 'div[class*="title"]',
    ]

    for selector in selectors:
        element = item.select_one(selector)
        if not element:
            continue

        text = element.get_text(strip=True) if element else ""
        if not text:
            continue

        if (
            len(text) > 10
            and not text.startswith('@')
            and not re.match(r'^[a-zA-Z0-9_\.]+$', text)
            and not re.match(r'^#[a-zA-Z0-9_\.]+$', text)
        ):
            return text

    for text in item.stripped_strings:
        if not text:
            continue
        if len(text) < 3:
            continue
        if text.startswith('@'):
            continue
        if re.match(r'^\d+(?:\.\d+)?[KkMm]?$', text):
            continue
        return text

    return ""


def _best_author_from(item, url: str) -> str:
    link = item.find(attrs={"data-e2e": "search-card-user-link"})
    if link and link.get('href') and str(link.get('href')).startswith('/@'):
        return str(link.get('href'))[2:].split('/', 1)[0]

    uid = item.find(attrs={"data-e2e": "search-card-user-unique-id"})
    if uid and uid.get_text(strip=True):
        text = uid.get_text(strip=True)
        return text[1:] if text.startswith('@') else text

    if url:
        match = re.search(r'/@([^/]+)/', url)
        if match:
            return match.group(1)

    return ""


def _best_like_from(item) -> int:
    like_selectors = [
        '[class*="like"]', '[class*="heart"]', '[class*="favorite"]', '[class*="count"]',
        '.css-1i43xsj', '.e1g2efjf9', '.e1g2efjf10', 'span'
    ]

    candidates: List[str] = []
    for selector in like_selectors:
        for element in item.select(selector) or []:
            text = element.get_text(strip=True) if element else ""
            if not text:
                continue
            if re.match(r'^\d+(?:\.\d+)?[KkMm]?$', text):
                candidates.append(text)

    if not candidates:
        for text in item.stripped_strings:
            if re.match(r'^\d+(?:\.\d+)?[KkMm]?$', text):
                candidates.append(text)

    for text in candidates:
        value = parse_like_count(text)
        if value > 0:
            return value

    logger.debug(f"No valid like count found, returning 0. Candidates: {candidates}")
    return 0


def _best_time_from(item) -> str:
    logger.debug(f"Attempting to extract time from item: {item.prettify()}")

    time_element = item.select_one('[data-e2e="search-card-time"]')
    if time_element:
        time_text = time_element.get_text(strip=True)
        if time_text:
            logger.debug("Found time using data-e2e='search-card-time': %s", time_text)
            return time_text

    time_element = item.select_one('[class*="--DivTimeTag"]')
    if time_element:
        time_text = time_element.get_text(strip=True)
        if time_text:
            logger.debug("Found time using class pattern --DivTimeTag: %s", time_text)
            return time_text

    for element in item.select('time, small, span, div') or []:
        text = element.get_text(strip=True) if element else ""
        if not text:
            continue

        match = re.search(r'(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}-\d{1,2}-\d{4})', text)
        if match:
            logger.debug("Found time using full date regex: %s", match.group(1))
            return match.group(1)

        match = re.search(r'(\d{1,2}-\d{1,2})', text)
        if match:
            logger.debug("Found time using partial date regex: %s", match.group(1))
            return match.group(1)

        match = re.search(r'(\d+\s*(?:days?|hours?|minutes?|weeks?|months?|years?)\s*ago)', text, re.IGNORECASE)
        if match:
            logger.debug("Found time using relative time regex: %s", match.group(1))
            return match.group(1)

    logger.debug("No time found using any strategy within the item.")
    return ""


def _extract_from_extracted_search_items(html_content: str) -> List[Dict[str, Any]]:
    try:
        match = re.search(
            r'<script[^>]+id=["\']EXTRACTED_SEARCH_ITEMS["\'][^>]*>(.*?)</script>',
            html_content or "",
            re.DOTALL | re.IGNORECASE,
        )
        if not match:
            return []

        payload = (match.group(1) or "").strip()
        if not payload:
            return []

        data = json.loads(payload)
        if not isinstance(data, list) or not data:
            return []

        normalized: List[Dict[str, Any]] = []
        for item in data:
            try:
                normalized.append({
                    "id": str(item.get("id") or ""),
                    "caption": str(item.get("caption") or ""),
                    "authorHandle": str(item.get("authorHandle") or item.get("author") or "").lstrip('@'),
                    "likeCount": int(item.get("likeCount") or 0),
                    "uploadTime": str(item.get("uploadTime") or ""),
                    "webViewUrl": str(item.get("webViewUrl") or item.get("url") or ""),
                })
            except Exception:
                continue

        return [item for item in normalized if item.get("id") and item.get("webViewUrl")]
    except Exception as exc:
        logger.warning("Error extracting from EXTRACTED_SEARCH_ITEMS script: %s", exc)
        return []


def _extract_from_meta_tags(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    try:
        canonical = soup.find('link', rel=lambda value: value and 'canonical' in str(value).lower())
        href = canonical.get('href') if canonical else None
        if not href or '/video/' not in href:
            return []

        video_match = re.search(r"/video/(\d+)", href)
        video_id = video_match.group(1) if video_match else ""

        user_match = re.search(r"/@([^/]+)/", href)
        author = user_match.group(1) if user_match else ""

        caption_meta = soup.find('meta', attrs={'property': 'og:description'}) or soup.find(
            'meta', attrs={'name': 'description'}
        )
        caption = caption_meta.get('content').strip() if caption_meta and caption_meta.get('content') else ""

        if video_id and href:
            return [{
                "id": video_id,
                "caption": caption,
                "authorHandle": author,
                "likeCount": 0,
                "uploadTime": "",
                "webViewUrl": href,
            }]
        return []
    except Exception as exc:
        logger.warning("Error extracting from video detail meta: %s", exc)
        return []


def _extract_from_video_containers(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    video_containers = soup.find_all('div', id=re.compile(r'column-item-video-container-\d+'))

    for container in video_containers:
        data: Dict[str, Any] = {
            "id": "",
            "caption": "",
            "authorHandle": "",
            "likeCount": 0,
            "uploadTime": "",
            "webViewUrl": "",
        }

        anchor = container.find('a', href=re.compile(r'/video/'))
        href = anchor.get('href') if anchor and anchor.get('href') else ""
        if href:
            if href.startswith('/'):
                href = f"https://www.tiktok.com{href}"
            data["webViewUrl"] = href
            data["id"] = _extract_id_from_url(href)

        data["caption"] = _best_caption_from(container)
        data["authorHandle"] = _best_author_from(container, data["webViewUrl"])
        data["likeCount"] = _best_like_from(container)
        data["uploadTime"] = _best_time_from(container)

        if data["id"] and data["webViewUrl"]:
            logger.debug(
                "Extracted video data: ID=%s, Caption='%s', Author='%s', Likes=%s, UploadTime='%s', URL='%s'",
                data["id"],
                data["caption"],
                data["authorHandle"],
                data["likeCount"],
                data["uploadTime"],
                data["webViewUrl"],
            )
            results.append(data)

    return results


class TikTokHtmlParser:
    """Parser exposing discrete extraction strategies for TikTok HTML."""

    def extract_from_sigi(self, html_content: str) -> List[Dict[str, Any]]:
        try:
            json_items = _from_sigi_state(html_content)
            if json_items:
                return json_items
        except Exception as exc:
            logger.warning("Error extracting from SIGI_STATE: %s", exc)
        return []

    def extract_from_dom(self, html_content: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html_content or "", 'html.parser')
        return _extract_from_video_containers(soup)

    def extract_from_meta(self, html_content: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html_content or "", 'html.parser')
        return _extract_from_meta_tags(soup)

    def parse(self, html_content: str) -> List[Dict[str, Any]]:
        if not html_content:
            logger.warning("Empty HTML content provided for parsing.")
            return []

        strategies: List[tuple[str, Callable[[str], List[Dict[str, Any]]]]] = [
            ("extract_from_sigi", self.extract_from_sigi),
            ("extract_from_extracted_search_items", _extract_from_extracted_search_items),
            ("extract_from_dom", self.extract_from_dom),
            ("extract_from_meta", self.extract_from_meta),
        ]

        for name, strategy in strategies:
            items = strategy(html_content)
            if items:
                logger.debug(
                    "Strategy %s extracted %d video items.",
                    name,
                    len(items),
                )
                return items

        logger.debug("Finished parsing HTML. Found 0 videos.")
        return []


def extract_video_data_from_html(html_content: str) -> List[Dict[str, Any]]:
    parser = TikTokHtmlParser()
    return parser.parse(html_content)
