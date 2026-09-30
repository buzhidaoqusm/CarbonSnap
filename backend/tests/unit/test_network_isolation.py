"""The suite must not depend on the proxy settings of the machine running it.

block_network lets connections to localhost through. A developer proxy on
localhost (HTTP_PROXY=http://127.0.0.1:10808, or the Windows registry proxy)
turned every un-mocked LLM call into a connection that waited out the LLM
timeout instead of failing at once: the suite went from ~230 s to ~850 s.
"""

from __future__ import annotations

from httpx._utils import get_environment_proxies


def test_http_clients_see_no_proxy():
    assert get_environment_proxies() == {}
