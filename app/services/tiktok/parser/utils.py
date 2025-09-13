"""
Common utilities and helpers for TikTok parsing
"""


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
