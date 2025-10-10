from app.services.crawler.proxy.sources import ProxyListFileSource

import pytest

pytestmark = [pytest.mark.unit]


def test_load_returns_empty_list_for_empty_path():
    source = ProxyListFileSource("")

    assert source.load() == []


def test_load_skips_comments_and_blank_lines(tmp_path):
    proxy_file = tmp_path / "proxies.txt"
    proxy_file.write_text(
        "# comment line\n"
        "\n"
        "   \n"
        "socks5://127.0.0.1:1080\n"
        "# another comment\n"
        "socks4://192.168.0.2:9050\n",
        encoding="utf-8",
    )

    source = ProxyListFileSource(str(proxy_file))

    assert source.load() == [
        "socks5://127.0.0.1:1080",
        "socks4://192.168.0.2:9050",
    ]


def test_load_adds_socks5_prefix_for_bare_hosts(tmp_path):
    proxy_file = tmp_path / "proxy-list.txt"
    proxy_file.write_text(
        "127.0.0.1:8080\n"
        "example.com:9050\n"
        "http://already-prefixed\n"
        "https://secure\n",
        encoding="utf-8",
    )

    source = ProxyListFileSource(str(proxy_file))

    assert source.load() == [
        "socks5://127.0.0.1:8080",
        "socks5://example.com:9050",
        "http://already-prefixed",
        "https://secure",
    ]


def test_load_returns_empty_list_when_file_missing(tmp_path):
    missing_path = tmp_path / "missing.txt"
    source = ProxyListFileSource(str(missing_path))

    assert source.load() == []
