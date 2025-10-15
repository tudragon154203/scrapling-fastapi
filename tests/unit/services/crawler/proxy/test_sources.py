import os
from pathlib import Path

from app.services.crawler.proxy.sources import ProxyListFileSource


class TestProxyListFileSource:
    def test_load_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        missing_file = tmp_path / "does_not_exist.txt"
        source = ProxyListFileSource(file_path=str(missing_file))

        assert source.load() == []

    def test_load_skips_comments_and_blank_lines(self, tmp_path: Path) -> None:
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("\n# comment\n192.168.0.1:8080\n\n", encoding="utf-8")
        source = ProxyListFileSource(file_path=str(proxy_file))

        assert source.load() == ["socks5://192.168.0.1:8080"]

    def test_load_prefixes_bare_hostnames_with_socks5(self, tmp_path: Path) -> None:
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("example.com:9000", encoding="utf-8")
        source = ProxyListFileSource(file_path=str(proxy_file))

        assert source.load() == ["socks5://example.com:9000"]

    def test_load_preserves_existing_schemes(self, tmp_path: Path) -> None:
        proxy_file = tmp_path / "proxies.txt"
        proxies = [
            "http://example.com:80",
            "https://secure.example.com:443",
            "socks5://proxy.example.com:1080",
            "socks4://legacy.example.com:1080",
        ]
        proxy_file.write_text(os.linesep.join(proxies), encoding="utf-8")
        source = ProxyListFileSource(file_path=str(proxy_file))

        assert source.load() == proxies
