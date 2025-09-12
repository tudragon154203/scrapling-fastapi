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
    Extract video data from HTML content using data-e2e attributes for TikTok search results.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all video items using data-e2e attribute
    video_items = soup.find_all(attrs={"data-e2e": "search_video-item"})
    
    results = []
    
    for item in video_items:
        video_data = {
            "id": "",
            "caption": "",
            "authorHandle": "",
            "likeCount": 0,
            "uploadTime": "",
            "webViewUrl": ""
        }
        
        # Extract web view URL from links within the item
        url_element = item.find('a', href=re.compile(r'/video/'))
        if url_element and url_element.get('href'):
            href = url_element.get('href')
            # Convert relative URLs to absolute if needed
            if href.startswith('/'):
                href = f"https://www.tiktok.com{href}"
            video_data["webViewUrl"] = href
            
            # Extract ID from webViewUrl
            if href:
                path_parts = href.split('/')
                for i in range(len(path_parts) - 1, -1, -1):
                    if path_parts[i] and not path_parts[i].startswith('http'):
                        video_data["id"] = path_parts[i]
                        break
        
        # Extract caption using data-e2e attribute
        caption_element = item.find(attrs={"data-e2e": "search-card-video-caption"})
        if caption_element and caption_element.get_text(strip=True):
            video_data["caption"] = caption_element.get_text(strip=True)
        
        # Extract author handle from user link or unique ID
        user_link_element = item.find(attrs={"data-e2e": "search-card-user-link"})
        if user_link_element and user_link_element.get('href'):
            href = user_link_element.get('href')
            if href.startswith('/@'):
                video_data["authorHandle"] = href[2:]  # Remove leading '/@'
        
        # Alternative: extract from user unique ID element
        if not video_data["authorHandle"]:
            user_id_element = item.find(attrs={"data-e2e": "search-card-user-unique-id"})
            if user_id_element and user_id_element.get_text(strip=True):
                text = user_id_element.get_text(strip=True)
                if text.startswith('@'):
                    video_data["authorHandle"] = text[1:]  # Remove leading '@'
        
        # Fallback: extract from webViewUrl
        if not video_data["authorHandle"] and video_data["webViewUrl"]:
            match = re.search(r'/@([^/]+)/', video_data["webViewUrl"])
            if match:
                video_data["authorHandle"] = match.group(1)
        
        # Extract like count - look for numbers with K/M suffixes in the item
        # TikTok search results often don't show like counts directly in the HTML
        # so we'll need to rely on other methods or leave this as 0
        
        # Only add to results if we have at least the essential data
        if video_data["id"] and video_data["webViewUrl"]:
            results.append(video_data)
    
    return results
