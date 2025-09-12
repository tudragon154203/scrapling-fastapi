"""
TikTok HTML parsing utilities
"""
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import json


def parse_like_count(like_text: str) -> int:
    """
    Parse like count from text format (e.g., "15.9K" -> 15900, "1.2M" -> 1200000)
    """
    if not like_text or like_text.strip() == "":
        return 0
    
    try:
        like_text = like_text.strip().lower()
        
        # Handle numbers with K (thousands) or M (millions)
        if 'k' in like_text:
            # Remove 'k' and convert to float, then multiply by 1000
            number = float(like_text.replace('k', ''))
            return int(number * 1000)
        elif 'm' in like_text:
            # Remove 'm' and convert to float, then multiply by 1000000
            number = float(like_text.replace('m', ''))
            return int(number * 1000000)
        else:
            # Regular integer
            return int(float(like_text))
    except (ValueError, TypeError):
        return 0


def _from_sigi_state(html: str) -> List[Dict[str, Any]]:
    """Try to extract videos from TikTok's SIGI_STATE JSON if present."""
    results: List[Dict[str, Any]] = []

    try:
        # Common patterns:
        #   <script id="SIGI_STATE" type="application/json">{...}</script>
        #   window['SIGI_STATE'] = {...};
        #   window.SIGI_STATE = {...};
        import re
        import logging
        
        logger = logging.getLogger(__name__)

        # Try tag with id first for Next.js pages
        m = re.search(r'<script[^>]+id=["\']SIGI_STATE["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
        raw_json: Optional[str] = m.group(1) if m else None
        if not raw_json:
            # Try assignment variants
            m = re.search(r"SIGI_STATE\s*[:=]\s*(\{.*?\})\s*[;\n]", html, re.DOTALL)
            raw_json = m.group(1) if m else None

        if not raw_json:
            logger.debug("No SIGI_STATE JSON found in HTML")
            return results

        logger.debug(f"Found SIGI_STATE JSON, length: {len(raw_json)}")
        data = json.loads(raw_json)

        # Prefer ItemModule which maps id -> item
        item_module = (data or {}).get("ItemModule") or {}
        user_module = (data or {}).get("UserModule") or {}
        users = (user_module.get("users") if isinstance(user_module, dict) else None) or {}

        def _author_from_item(it: Dict[str, Any]) -> str:
            # Try direct author field
            a = str(it.get("author") or it.get("authorName") or "").strip()
            if a:
                return a.lstrip("@")
            # Try author id mapping
            uid = str(it.get("authorId") or "").strip()
            if uid and isinstance(users, dict):
                for _, u in users.items():
                    try:
                        if str(u.get("id") or u.get("uid") or "").strip() == uid:
                            h = str(u.get("uniqueId") or u.get("nickname") or u.get("username") or "").strip()
                            return h.lstrip("@")
                    except Exception:
                        continue
            return ""

        for vid, it in (item_module.items() if isinstance(item_module, dict) else []):
            try:
                video_id = str(it.get("id") or vid or "").strip()
                if not video_id:
                    continue
                author_handle = _author_from_item(it)
                caption = str(it.get("desc") or it.get("title") or "").strip()

                # Stats -> likeCount
                stats = it.get("stats") or {}
                like_count = int(stats.get("diggCount") or stats.get("likeCount") or 0)

                # Time -> uploadTime string
                ct = str(it.get("createTime") or "").strip()
                upload_time = ""
                if ct.isdigit():
                    try:
                        import datetime as _dt
                        ts = _dt.datetime.utcfromtimestamp(int(ct))
                        upload_time = ts.strftime("%Y-%m-%d")
                    except Exception:
                        upload_time = ct
                elif ct:
                    upload_time = ct

                if author_handle:
                    url = f"https://www.tiktok.com/@{author_handle}/video/{video_id}"
                else:
                    url = f"https://www.tiktok.com/video/{video_id}"

                results.append({
                    "id": video_id,
                    "caption": caption,
                    "authorHandle": author_handle,
                    "likeCount": like_count,
                    "uploadTime": upload_time or "",
                    "webViewUrl": url,
                })
            except Exception:
                continue

    except Exception:
        # Ignore parsing errors; fall back to DOM heuristics
        return []

    return results


def extract_video_data_from_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Extract video data from TikTok search HTML.

    Order of strategies (most reliable first):
    1) Parse embedded SIGI_STATE JSON (structured, complete fields)
    2) Parse DOM via data-e2e search item blocks
    3) Fallback to demo container structure heuristics
    """
    # Strategy 0: Try embedded JSON first (fast, most accurate when available)
    try:
        json_items = _from_sigi_state(html_content)
        if json_items:
            return json_items
    except Exception:
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
    except Exception:
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
    except Exception:
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
            if re.match(r'^#[a-zA-Z0-9_\.]+$', txt):
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
        return 0

    def _best_time_from(item) -> str:
        # Prefer <time> tag
        for el in item.select('time, small, span, div') or []:
            txt = el.get_text(strip=True) if el else ""
            if not txt:
                continue
            # Full date
            m = re.search(r'(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}-\d{1,2}-\d{4})', txt)
            if m:
                return m.group(1)
            # Partial date
            m = re.search(r'(\d{1,2}-\d{1,2})', txt)
            if m:
                return m.group(1)
            # Relative
            m = re.search(r'(\d+\s*(?:days?|hours?|minutes?|weeks?|months?|years?)\s*ago)', txt, re.IGNORECASE)
            if m:
                return m.group(1)
        return ""

    results: List[Dict[str, Any]] = []

    # Strategy 1: data-e2e search items (modern desktop)
    # Support multiple known containers seen across builds/regions
    container_selectors = [
        "[data-e2e='search_video-item']",
        "[data-e2e='search_top-item']",
        "[data-e2e='search-card-desc']",
    ]
    video_items = []
    _seen = set()
    for sel in container_selectors:
        for el in soup.select(sel) or []:
            key = id(el)
            if key in _seen:
                continue
            _seen.add(key)
            video_items.append(el)
    for item in video_items:
        data: Dict[str, Any] = {"id": "", "caption": "", "authorHandle": "", "likeCount": 0, "uploadTime": "", "webViewUrl": ""}
        a = item.find('a', href=re.compile(r'/video/'))
        # If anchor not found within the selected node, try its nearest search container
        if not a:
            try:
                container = item.find_parent(attrs={"data-e2e": "search_top-item"}) or item.find_parent(attrs={"data-e2e": "search_video-item"})
                if container:
                    a = container.find('a', href=re.compile(r'/video/'))
            except Exception:
                a = None
        href = a.get('href') if a and a.get('href') else ""
        if href:
            if href.startswith('/'):
                href = f"https://www.tiktok.com{href}"
            data["webViewUrl"] = href
            data["id"] = _extract_id_from_url(href)
        # Caption/author from local container; if missing, try parent search item
        data["caption"] = _best_caption_from(item)
        data["authorHandle"] = _best_author_from(item, data["webViewUrl"]) if data["webViewUrl"] else _best_author_from(item, "")
        if (not data["caption"]) or (not data["authorHandle"]):
            parent = None
            try:
                if a:
                    parent = a.find_parent(attrs={"data-e2e": "search_top-item"}) or a.find_parent(attrs={"data-e2e": "search_video-item"})
            except Exception:
                parent = None
            ctx = parent or item
            if not data["caption"]:
                data["caption"] = _best_caption_from(ctx)
            if not data["authorHandle"]:
                data["authorHandle"] = _best_author_from(ctx, data["webViewUrl"]) if data["webViewUrl"] else _best_author_from(ctx, "")
        data["likeCount"] = _best_like_from(item)
        data["uploadTime"] = _best_time_from(item)
        if data["id"] and data["webViewUrl"]:
            results.append(data)

    # Strategy 2: Demo/test HTML structure
    if not results:
        containers = soup.find_all('div', id=re.compile(r'column-item-video-container-\d+'))
        for container in containers:
            data: Dict[str, Any] = {"id": "", "caption": "", "authorHandle": "", "likeCount": 0, "uploadTime": "", "webViewUrl": ""}
            a = container.find('a', href=re.compile(r'/video/')) or container.select_one('a[href*="/video/"]')
            href = a.get('href') if a and a.get('href') else ""
            if href:
                if href.startswith('/'):
                    href = f"https://www.tiktok.com{href}"
                data["webViewUrl"] = href
                data["id"] = _extract_id_from_url(href)
            data["caption"] = _best_caption_from(container)
            data["authorHandle"] = _best_author_from(container, data["webViewUrl"]) if data["webViewUrl"] else ""
            data["likeCount"] = _best_like_from(container)
            data["uploadTime"] = _best_time_from(container)
            if data["id"] and data["webViewUrl"]:
                results.append(data)

    return results
