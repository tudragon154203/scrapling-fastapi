from app.services.crawler.proxy.redact import redact_proxy


def test_redact_proxy_with_credentials_and_port_masks_sensitive_parts():
    proxy = "http://user:pass@proxy.example.com:8080"

    assert redact_proxy(proxy) == "http://***:8080"


def test_redact_proxy_with_ipv6_host_preserves_port():
    proxy = "http://user:pass@[2001:db8::1]:3128"

    assert redact_proxy(proxy) == "http://***:3128"


def test_redact_proxy_without_scheme_returns_original_string():
    proxy = "user:pass@proxy.example.com:8080"

    assert redact_proxy(proxy) == proxy


def test_redact_proxy_without_port_keeps_original_value():
    proxy = "http://user:pass@proxy.example.com"

    assert redact_proxy(proxy) == proxy


def test_redact_proxy_none_returns_none():
    assert redact_proxy(None) is None
