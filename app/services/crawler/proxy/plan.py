from typing import List, Dict, Any
import random

from app.services.common.interfaces import IAttemptPlanner


class AttemptPlanner(IAttemptPlanner):
    """Planner for crawl attempts that builds execution plans with proxy rotation."""

    def build_plan(self, settings, public_proxies: List[str]) -> List[Dict[str, Any]]:
        """Build the attempt plan for retry strategy."""
        plan: List[Dict[str, Any]] = []

        # Always start with direct connection
        plan.append({"mode": "direct", "proxy": None})

        pubs = list(public_proxies)
        if getattr(settings, "proxy_rotation_mode", "sequential") == "random" and pubs:
            random.shuffle(pubs)

        remaining = max(0, int(getattr(settings, "max_retries", 1)) - 1)
        include_private = bool(getattr(settings, "private_proxy_url", None))
        reserve_final_direct = remaining > 1

        slots_for_public = remaining - (1 if include_private else 0) - (1 if reserve_final_direct else 0)
        slots_for_public = max(0, slots_for_public)
        for proxy in pubs[:slots_for_public]:
            plan.append({"mode": "public", "proxy": proxy})

        if include_private and len(plan) < getattr(settings, "max_retries", 1):
            plan.append({"mode": "private", "proxy": settings.private_proxy_url})

        if reserve_final_direct and len(plan) < getattr(settings, "max_retries", 1):
            plan.append({"mode": "direct", "proxy": None})

        proxy_index = 0
        while len(plan) < getattr(settings, "max_retries", 1):
            if proxy_index < len(pubs):
                plan.append({"mode": "public", "proxy": pubs[proxy_index]})
                proxy_index += 1
            else:
                plan.append({"mode": "direct", "proxy": None})

        return plan
