"""
BeautifulSoup DOM parsing for TikTok
"""
import re
import logging
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from app.services.tiktok.parser.json_parser import _from_sigi_state
from app.services.tiktok.parser.utils import parse_like_count

logger = logging.getLogger(__name__)


def extract_video_data_from_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Extract video data from TikTok search HTML.

    Order of strategies (most reliable first):
    1) Parse embedded SIGI_STATE JSON (structured, complete fields)
    2) Parse DOM via main video container blocks (e.g., column-item-video-container-X)
    """
    # Strategy 0: Try embedded JSON first (fast, most accurate when available)
    try:
        json_items = _from_sigi_state(html_content)
        if json_items:
            return json_items
    except Exception as e:
        logger.warning(f"Error extracting from SIGI_STATE: {e}")
        pass

    # Strategy 0.25: Client-extracted search items injected by page_action
    try:
        m = re.search(r'<script[^>]+id=["\']EXTRACTED_SEARCH_ITEMS["\'][^>]*>(.*?)</script>', html_content or "", re.DOTALL | re.IGNORECASE)
        if m:
            payload = (m.group(1) or "").strip()
            if payload:
                data = json.loads(payload)
                if isinstance(data, list) and data:
                    # Normalize keys to our shape
                    out: List[Dict[str, Any]] = []
                    for it in data:
                        try:
                            out.append({
                                "id": str(it.get("id") or ""),
                                "caption": str(it.get("caption") or ""),
                                "authorHandle": str(it.get("authorHandle") or it.get("author") or "").lstrip('@'),
                                "likeCount": int(it.get("likeCount") or 0),
                                "uploadTime": str(it.get("uploadTime") or ""),
                                "webViewUrl": str(it.get("webViewUrl") or it.get("url") or ""),
                            })
                        except Exception:
                            continue
                    if out:
                        return out
    except Exception as e:
        logger.warning(f"Error extracting from EXTRACTED_SEARCH_ITEMS script: {e}")
        pass

    soup = BeautifulSoup(html_content or "", 'html.parser')

    # Strategy 0.5: Video detail meta fallback (canonical + og:description)
    try:
        canonical = soup.find('link', rel=lambda v: v and 'canonical' in str(v).lower())
        href = canonical.get('href') if canonical else None
        if href and '/video/' in href:
            vid_m = re.search(r"/video/(\d+)", href)
            vid = vid_m.group(1) if vid_m else ""
            user_m = re.search(r"/@([^/]+)/", href)
            author = user_m.group(1) if user_m else ""
            cap_meta = soup.find('meta', attrs={'property': 'og:description'}) or soup.find('meta', attrs={'name': 'description'})
            caption = cap_meta.get('content').strip() if cap_meta and cap_meta.get('content') else ""
            if vid and href:
                return [{
                    "id": vid,
                    "caption": caption,
                    "authorHandle": author,
                    "likeCount": 0,
                    "uploadTime": "",
                    "webViewUrl": href,
                }]
    except Exception as e:
        logger.warning(f"Error extracting from video detail meta: {e}")
        pass

    def _extract_id_from_url(href: str) -> str:
        if not href:
            return ""
        # Absolute URL if needed
        url = href
        if url.startswith('/'):
            url = f"https://www.tiktok.com{url}"
        # Prefer regex /video/<digits>
        m = re.search(r"/video/(\d+)", url)
        if m:
            return m.group(1)
        # Fallback: last clean path segment without query/fragment
        try:
            clean = url.split('?', 1)[0].split('#', 1)[0]
            parts = [p for p in clean.split('/') if p and not p.startswith('http')]
            return parts[-1] if parts else ""
        except Exception:
            return ""

    def _best_caption_from(item) -> str:
        # Prefer explicit caption selectors
        cap = item.find(attrs={"data-e2e": "search-card-video-caption"})
        if cap and cap.get_text(strip=True):
            return cap.get_text(strip=True)
        cap = item.find(attrs={"data-e2e": "search-card-desc"})
        if cap and cap.get_text(strip=True):
            return cap.get_text(strip=True)
        # Broader selectors adapted from demo with sanity checks
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
        for sel in selectors:
            el = item.select_one(sel)
            if not el:
                continue
            txt = el.get_text(strip=True) if el else ""
            if not txt:
                continue
            if (
                len(txt) > 10 and
                not txt.startswith('@') and
                not re.match(r'^[a-zA-Z0-9_\.]+$', txt) and
                not re.match(r'^#[a-zA-Z0-9_\.]+$', txt)
            ):
                return txt
        # Last resort: any non-handle, non-count, non-hashtag text (allow shorter captions)
        for txt in item.stripped_strings:
            if not txt:
                continue
            if len(txt) < 3:
                continue
            if txt.startswith('@'):
                continue
            if re.match(r'^\d+(?:\.\d+)?[KkMm]?$', txt):
                continue
            return txt
        return ""

    def _best_author_from(item, url: str) -> str:
        link = item.find(attrs={"data-e2e": "search-card-user-link"})
        if link and link.get('href') and str(link.get('href')).startswith('/@'):
            return str(link.get('href'))[2:].split('/', 1)[0]
        uid = item.find(attrs={"data-e2e": "search-card-user-unique-id"})
        if uid and uid.get_text(strip=True):
            t = uid.get_text(strip=True)
            return t[1:] if t.startswith('@') else t
        if url:
            m = re.search(r'/@([^/]+)/', url)
            if m:
                return m.group(1)
        return ""

    def _best_like_from(item) -> int:
        # Scan focused selectors first
        like_selectors = [
            '[class*="like"]', '[class*="heart"]', '[class*="favorite"]', '[class*="count"]',
            '.css-1i43xsj', '.e1g2efjf9', '.e1g2efjf10', 'span'
        ]
        cand: List[str] = []
        for sel in like_selectors:
            for el in item.select(sel) or []:
                t = el.get_text(strip=True) if el else ""
                if not t:
                    continue
                if re.match(r'^\d+(?:\.\d+)?[KkMm]?$', t):
                    cand.append(t)
        # If nothing obvious, scan all short texts
        if not cand:
            for t in item.stripped_strings:
                if re.match(r'^\d+(?:\.\d+)?[KkMm]?$', t):
                    cand.append(t)
        for t in cand:
            v = parse_like_count(t)
            if v > 0:
                return v
        logger.debug(f"No valid like count found, returning 0. Candidates: {cand}")
        return 0

    def _best_time_from(item) -> str:
        logger.debug(f"Attempting to extract time from item: {item.prettify()}")

        # Strategy 1: Prefer explicit data-e2e attribute
        time_el = item.select_one('[data-e2e="search-card-time"]')
        if time_el:
            time_text = time_el.get_text(strip=True)
            if time_text:
                logger.debug(f"Found time using data-e2e='search-card-time': {time_text}")
                return time_text

        # Strategy 2: Prefer explicit class pattern (DivTimeTag)
        # Search within all descendants of the item
        time_el = item.select_one('[class*="--DivTimeTag"]')
        if time_el:
            time_text = time_el.get_text(strip=True)
            if time_text:
                logger.debug(f"Found time using class pattern --DivTimeTag: {time_text}")
                return time_text

        # Strategy 3: Iterate through common tags for date patterns
        for el in item.select('time, small, span, div') or []:
            txt = el.get_text(strip=True) if el else ""
            if not txt:
                continue

            # Full date (e.g., YYYY-MM-DD or MM-DD-YYYY)
            m = re.search(r'(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}-\d{1,2}-\d{4})', txt)
            if m:
                logger.debug(f"Found time using full date regex: {m.group(1)}")
                return m.group(1)
            # Partial date (e.g., MM-DD)
            m = re.search(r'(\d{1,2}-\d{1,2})', txt)
            if m:
                logger.debug(f"Found time using partial date regex: {m.group(1)}")
                return m.group(1)
            # Relative time (e.g., "3 days ago")
            m = re.search(r'(\d+\s*(?:days?|hours?|minutes?|weeks?|months?|years?)\s*ago)', txt, re.IGNORECASE)
            if m:
                logger.debug(f"Found time using relative time regex: {m.group(1)}")
                return m.group(1)
        logger.debug("No time found using any strategy within the item.")
        return ""

    results: List[Dict[str, Any]] = []

    # Strategy 1: Use `column-item-video-container-X` as the primary video item container
    video_containers = soup.find_all('div', id=re.compile(r'column-item-video-container-\d+'))
    for container in video_containers:
        data: Dict[str, Any] = {"id": "", "caption": "", "authorHandle": "", "likeCount": 0, "uploadTime": "", "webViewUrl": ""}
        
        # Extract URL and ID
        a = container.find('a', href=re.compile(r'/video/'))
        href = a.get('href') if a and a.get('href') else ""
        if href:
            if href.startswith('/'):
                href = f"https://www.tiktok.com{href}"
            data["webViewUrl"] = href
            data["id"] = _extract_id_from_url(href)

        # Extract caption, author, like count, and upload time from the main container
        data["caption"] = _best_caption_from(container)
        data["authorHandle"] = _best_author_from(container, data["webViewUrl"])
        data["likeCount"] = _best_like_from(container)
        data["uploadTime"] = _best_time_from(container)

        if data["id"] and data["webViewUrl"]:
            logger.debug(f"Extracted video data: ID={data['id']}, Caption='{data['caption']}', Author='{data['authorHandle']}', Likes={data['likeCount']}, UploadTime='{data['uploadTime']}', URL='{data['webViewUrl']}'")
            results.append(data)

    logger.debug(f"Finished parsing HTML. Found {len(results)} videos.")
    return results