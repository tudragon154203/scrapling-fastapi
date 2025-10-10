"""
JSON extraction for TikTok parsing
"""
import re
import logging
import json
from typing import List, Dict, Any, Optional
import datetime as _dt

logger = logging.getLogger(__name__)


def _from_sigi_state(html: str) -> List[Dict[str, Any]]:
    """Try to extract videos from TikTok's SIGI_STATE JSON if present."""
    results: List[Dict[str, Any]] = []
    try:
        # Common patterns:
        #   <script id="SIGI_STATE" type="application/json">{...}</script>
        #   window['SIGI_STATE'] = {...};
        #   window.SIGI_STATE = {...};
        logger.debug(f"Attempting to extract SIGI_STATE from HTML (length: {len(html)})")
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
    except Exception as e:
        logger.warning(f"Error extracting from SIGI_STATE: {e}")
        # Ignore parsing errors; fall back to DOM heuristics
        return []
    return results
