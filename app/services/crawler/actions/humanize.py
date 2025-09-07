import logging
import random
import time

from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)

def human_pause(min_s: float, max_s: float):
    delay = random.uniform(min_s, max_s)
    logger.debug(f"Human pause: chosen delay {delay:.2f}s")
    time.sleep(delay)

def move_mouse_to_locator(page, locator, steps_range=None, pre_hover=True):
    """Move the mouse toward the center of a locator with human-like steps.

    Falls back silently if the underlying page/locator does not support
    required operations (e.g., bounding_box, mouse.move) in this environment.
    Applies a probability gate to avoid excessive mouse motion.
    """
    # Probability gate to reduce mouse movements
    try:
        s = get_settings()
        move_prob = getattr(s, "auspost_mouse_move_prob", 0.5)
        if random.random() > move_prob:
            logger.debug("Mouse move: skipped by probability gate")
            return
    except Exception:
        pass
    try:
        box = locator.bounding_box()
    except Exception as e:
        logger.debug(f"Mouse move: locator.bounding_box not available ({type(e).__name__}); skipping")
        return
    if not box:
        logger.debug("Mouse move: locator has no bounding box, skipping")
        return
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    if steps_range is None:
        s = get_settings()
        steps_min = getattr(s, "auspost_mouse_steps_min", 12)
        steps_max = getattr(s, "auspost_mouse_steps_max", 28)
        steps_range = (steps_min, steps_max)
    steps = random.randint(*steps_range)
    logger.debug(f"Mouse move: to ({cx:.1f}, {cy:.1f}) with {steps} steps, pre_hover={pre_hover}")
    try:
        if pre_hover:
            locator.hover()
        page.mouse.move(cx, cy, steps=steps)
    except Exception as e:
        logger.debug(f"Mouse move: page.mouse.move not available ({type(e).__name__}); skipping")

def jitter_mouse(page, locator=None, radius_px=None, steps=None):
    """Small mouse wiggle near a locator center using settings defaults.

    If a locator is provided and has a bounding box, jitter around its center.
    If no locator is provided or has no box, skip jitter.
    Applies a probability gate to reduce jitter frequency.
    """
    s = get_settings()
    # Probability gate
    try:
        jitter_prob = getattr(s, "auspost_mouse_jitter_prob", 0.5)
        if random.random() > jitter_prob:
            logger.debug("Jitter mouse: skipped by probability gate")
            return
    except Exception:
        pass
    if radius_px is None:
        radius_px = getattr(s, "auspost_jitter_radius_px", 3)
    if steps is None:
        steps = getattr(s, "auspost_jitter_steps", 2)
    # move around locator center if available
    try:
        box = locator.bounding_box() if locator is not None else None
    except Exception:
        box = None
    if not box:
        logger.debug("Jitter mouse: no locator box, skipping")
        return
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    dx = random.randint(-radius_px, radius_px)
    dy = random.randint(-radius_px, radius_px)
    tx = cx + dx
    ty = cy + dy
    logger.debug(f"Jitter mouse: target ({tx:.1f}, {ty:.1f}) with {steps} steps (radius={radius_px})")
    page.mouse.move(tx, ty, steps=steps)

def click_like_human(locator, hover_first=True):
    logger.debug(f"Human click: hover_first={hover_first}")
    if hover_first:
        locator.hover()
    locator.click()

def type_like_human(locator, text, delay_ms_range=None):
    """Type text with a per-char delay from settings unless overridden."""
    if delay_ms_range is None:
        s = get_settings()
        dmin = getattr(s, "auspost_typing_delay_ms_min", 60)
        dmax = getattr(s, "auspost_typing_delay_ms_max", 140)
        delay_ms_range = (dmin, dmax)
    delay = random.randint(*delay_ms_range)
    logger.debug(f"Human type: text length {len(text)}, delay {delay}ms")
    locator.fill("")
    locator.type(text, delay=delay)

def scroll_noise(page, cycles_range=(1,3), dy_range=(120,480)):
    s = get_settings()
    # Master scroll toggle
    if not getattr(s, "auspost_humanize_scroll", True):
        logger.debug("Scroll noise disabled by settings; skipping")
        return
    # Probability gate to reduce how often we scroll
    try:
        scroll_prob = getattr(s, "auspost_scroll_prob", 0.25)
        if random.random() > scroll_prob:
            logger.debug("Scroll noise: skipped by probability gate")
            return
    except Exception:
        pass
    # Small cycles and dy bounds from settings
    try:
        cmin = max(1, int(getattr(s, "auspost_scroll_cycles_min", 1)))
        cmax = max(cmin, int(getattr(s, "auspost_scroll_cycles_max", 1)))
    except Exception:
        cmin, cmax = 1, 1
    cycles = random.randint(cmin, cmax)
    logger.debug(f"Scroll noise: {cycles} cycles")
    try:
        dymin = int(getattr(s, "auspost_scroll_dy_min", 80))
        dymax = int(getattr(s, "auspost_scroll_dy_max", 180))
        if dymin > dymax:
            dymin, dymax = 80, 180
    except Exception:
        dymin, dymax = 80, 180
    for i in range(cycles):
        dy = random.randint(dymin, dymax)
        if random.random() < 0.25:
            dy = -dy  # occasional upward scroll
        logger.debug(f"Scroll cycle {i+1}: dy={dy}")
        try:
            page.mouse.wheel(0, dy)
        except Exception as e:
            logger.debug(f"Scroll noise: page.mouse.wheel not available ({type(e).__name__}); skipping rest")
            break
        time.sleep(random.uniform(0.08, 0.18))
