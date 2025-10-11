"""Fetch parameters data class for Scrapling adapter."""

from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional


@dataclass
class FetchParams(MutableMapping[str, Any]):
    """Stateful mapping of Scrapling fetch keyword arguments."""

    _values: Dict[str, Any] = field(default_factory=dict)
    geoip_enabled: bool = field(init=False)
    wait_selector: Optional[str] = field(init=False)
    network_idle_enabled: bool = field(init=False)

    def __post_init__(self) -> None:
        # Always copy user-provided mappings so mutations stay local.
        self._values = dict(self._values or {})
        self._refresh_state()

    # -- MutableMapping protocol -------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._values[key] = value
        self._refresh_state()

    def __delitem__(self, key: str) -> None:
        del self._values[key]
        self._refresh_state()

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    # -- Convenience helpers -----------------------------------------------------
    def _refresh_state(self) -> None:
        self.geoip_enabled = bool(self._values.get("geoip"))
        self.wait_selector = self._values.get("wait_selector")
        self.network_idle_enabled = bool(self._values.get("network_idle", False))

    def as_kwargs(self) -> Dict[str, Any]:
        """Return a shallow copy suitable for **kwargs expansion."""
        return dict(self._values)

    def copy(self) -> "FetchParams":
        """Clone the current parameters for safe mutation."""
        return FetchParams(self._values)

    def without_geoip(self) -> "FetchParams":
        """Produce a copy with geoip removed."""
        if "geoip" not in self._values:
            return self.copy()
        clone = dict(self._values)
        clone.pop("geoip", None)
        return FetchParams(clone)

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        return self._values.get(key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        result = self._values.setdefault(key, default)
        self._refresh_state()
        return result

    def update(self, mapping: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        if mapping:
            self._values.update(mapping)
        if kwargs:
            self._values.update(kwargs)
        self._refresh_state()

    def items(self):
        return self._values.items()

    def __contains__(self, item: object) -> bool:
        return item in self._values

    @property
    def allows_http_fallback(self) -> bool:
        """Return True when HTTP fallback is viable for timeout errors."""
        return self.wait_selector is not None and not self.network_idle_enabled
