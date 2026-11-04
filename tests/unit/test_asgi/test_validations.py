import pytest

from litestar import get
from litestar.testing import create_test_client


@pytest.mark.parametrize(
    "host, should_pass",
    [
        pytest.param(b"foo\nbar", False, id="bare-lf"),
        pytest.param(b"foo\rbar", False, id="bare-cr"),
        pytest.param(b"foo\r\nbar", False, id="crlf"),
        pytest.param(b"foo\x00bar", False, id="nul-byte"),
        pytest.param(b"\x7fMe!", False, id="del-character"),
        pytest.param(b"", True, id="empty-host-when-no-authority"),
        pytest.param(b"127.0.0.1", True, id="ipv4-loopback"),
        pytest.param(b"255.255.255.255", True, id="ipv4-broadcast"),
        pytest.param(b"[::]", True, id="ipv6-unspecified"),
        pytest.param(b"[2001:db8::1.2.3.4]", True, id="pv6-with-embedded-ipv4"),
        pytest.param(b"[v1.fe80::a+b]", True, id="ipvfuture-literal"),
        pytest.param(b"xn--nxasmq6b.example", True, id="dn-as-punycode"),
        pytest.param("exämple.com".encode(), False, id="raw-utf8"),
        # cases motivated by CVE-2023-29406
        # https://nvd.nist.gov/vuln/detail/CVE-2023-29406
        pytest.param(b"example.com\r\nX-Injected: evil", False, id="cve:header-injection-via-host"),
        pytest.param(b"example.com\r\n\r\nGET /admin", False, id="cve:request-smuggling-via-host"),
        pytest.param(b"evil.com\r\nContent-Length: 0", False, id="cve:crlf-plus-fake-content-length"),
        pytest.param(b"evil.com\nSet-Cookie: pwned=1", False, id="cve:bare-lf-plus-cookie-injection"),
        pytest.param(b"example.com\tfoo", False, id="cve:htab-smuggling"),
        pytest.param(b"example.com\x0bfoo", False, id="cve:vertical-tab"),
        pytest.param(b"example.com\x0cfoo", False, id="cve:form-feed"),
        # cases based from Django's host validation behavior
        # https://github.com/django/django/blob/41357f42c52ff7677af3d93b59b0aa6574b0ac19/tests/requests_tests/tests.py#L1306-L1460
        # (BSD-3-Clause, Copyright (c) Django Software Foundation and individual contributors.)
        pytest.param(b"example.com", True, id="django-legit:plain"),
        pytest.param(b"example.com:80", True, id="django-legit:with-port"),
        pytest.param(b"12.34.56.78", True, id="django-legit:ipv4"),
        pytest.param(b"12.34.56.78:443", True, id="django-legit:ipv4-with-port"),
        pytest.param(b"[2001:19f0:feee::dead:beef:cafe]", True, id="django-legit:ipv6"),
        pytest.param(b"[2001:19f0:feee::dead:beef:cafe]:8080", True, id="django-legit:ipv6-with-port"),
        pytest.param(b"xn--4ca9at.com", True, id="django-legit:punycode-for-öäü.com"),
        pytest.param(b"example.com@evil.tld", True, id="django-poisoned:userinfo-injection-byte-ok"),
        pytest.param(b"example.com:dr.frankenstein@evil.tld", True, id="django-poisoned:userinfo-in-port-byte-ok"),
        pytest.param(
            b"example.com:dr.frankenstein@evil.tld:80", True, id="django-poisoned:userinfo-double-colon-byte-ok"
        ),
        pytest.param(b"example.com:80/badpath", False, id="django-poisoned:path-injection-byte-rejects"),
        pytest.param(
            b"example.com: recovermypassword.com", False, id="django-poisoned:password-reset-smuggling-byte-rejects"
        ),
        # cases adapted from Go's
        # https://github.com/golang/go/blob/e827d41c0a2ea392c117a790cdfed0022e419424/src/net/http/http_test.go#L49-L80
        # (BSD-3-Clause, Copyright 2014 The Go Authors)
        pytest.param(b"www.google.com", True, id="go-clean-host:baseline"),
        pytest.param(b"www.google.com foo", False, id="go-clean-host:trailing-junk-after-space-formerly-truncated"),
        pytest.param(b"www.google.com/foo", False, id="go-clean-host:path-like-suffix-same-attack-class"),
        pytest.param(b" first character is a space", False, id="go-clean-host:leading-space-formerly-empty-string"),
        pytest.param(b"[1::6]:8080", True, id="go-clean-host:bracketed-ipv6-with-port"),
        pytest.param(b"xn--c1ae0ajs.xn--p1ai", True, id="go-clean-host:punycode-cyrillic"),
        pytest.param(b"xn--bcher-kva.de", True, id="go-clean-host:punycode-german-umlaut"),
        pytest.param(b"xn--bcher-kva.de:8080", True, id="go-clean-host:punycode-with-port"),
    ],
)
async def test_valid_host_header(host: bytes, should_pass: bool) -> None:
    @get("/")
    async def empty_handler() -> None:
        pass

    with create_test_client([empty_handler]) as client:
        res = client.get("/", headers={b"Host": host})
        assert res.status_code == (200 if should_pass else 400)
