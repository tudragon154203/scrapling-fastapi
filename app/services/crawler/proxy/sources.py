from typing import List, Optional

from app.services.common.interfaces import IProxyListSource


class ProxyListFileSource(IProxyListSource):
    """Source for loading proxy lists from files."""

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path

    def load(self) -> List[str]:
        """Load proxy list from file as socks5:// URLs by default."""
        if not self.file_path:
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                proxies = []
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if not line.startswith(("http://", "https://", "socks5://", "socks4://")):
                        line = f"socks5://{line}"
                    proxies.append(line)
                return proxies
        except Exception:
            return []
