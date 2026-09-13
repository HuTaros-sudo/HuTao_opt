import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from genshin_opt.akasha.api import (AkashaAPIConfig, AkashaLeaderboardClient, AkashaRequestError,
                                    LeaderboardRequest)


def row(rank: int, result: float) -> dict:
    return {"_id": f"entry-{rank}", "uid": f"test-user-{rank}", "md5": f"md5-{rank}",
            "characterId": 10000046, "index": rank,
            "calculation": {"id": "1000004605", "result": result}}


def test_client_pages_with_cursor_and_wait_between_pages() -> None:
    urls = []
    sleeps = []
    responses = [json.dumps({"data": [row(1, 100.0), row(2, 90.0)]}).encode(),
                 json.dumps({"data": [row(3, 80.0)]}).encode()]

    def transport(url: str, timeout: float, headers: dict[str, str]) -> bytes:
        urls.append(url)
        assert timeout == 5
        assert headers["User-Agent"].startswith("genshin-opt")
        return responses.pop(0)

    config = AkashaAPIConfig(timeout_seconds=5, page_delay_seconds=0.25, max_retries=0)
    client = AkashaLeaderboardClient(config, transport=transport, sleep=sleeps.append,
                                    clock=lambda: datetime(2026, 9, 13, tzinfo=timezone.utc))
    pages = tuple(client.iter_pages(LeaderboardRequest("1000004605", max_pages=3, page_size=2)))

    assert len(pages) == 2
    assert sleeps == [0.25]
    assert parse_qs(urlparse(urls[0]).query, keep_blank_values=True)["p"] == [""]
    assert parse_qs(urlparse(urls[1]).query)["p"] == ["lt|90.0"]
    assert pages[0].fetched_at == "2026-09-13T00:00:00Z"


def test_client_stops_after_finite_retries() -> None:
    calls = 0
    sleeps = []

    def failing_transport(url: str, timeout: float, headers: dict[str, str]) -> bytes:
        nonlocal calls
        calls += 1
        raise AkashaRequestError("temporary", retryable=True)

    config = AkashaAPIConfig(max_retries=2, retry_delay_seconds=0.1)
    client = AkashaLeaderboardClient(config, transport=failing_transport, sleep=sleeps.append)
    with pytest.raises(AkashaRequestError, match="temporary"):
        tuple(client.iter_pages(LeaderboardRequest("1000004605")))
    assert calls == 3
    assert sleeps == [0.1, 0.1]


def test_client_does_not_retry_non_retryable_error() -> None:
    calls = 0

    def failing_transport(url: str, timeout: float, headers: dict[str, str]) -> bytes:
        nonlocal calls
        calls += 1
        raise AkashaRequestError("bad request", retryable=False)

    client = AkashaLeaderboardClient(AkashaAPIConfig(max_retries=5), transport=failing_transport)
    with pytest.raises(AkashaRequestError, match="bad request"):
        tuple(client.iter_pages(LeaderboardRequest("1000004605")))
    assert calls == 1


@pytest.mark.parametrize("max_pages,page_size", [(0, 20), (101, 20), (1, 0), (1, 101)])
def test_request_has_bounded_page_limits(max_pages: int, page_size: int) -> None:
    client = AkashaLeaderboardClient(transport=lambda *_: b'{}')
    with pytest.raises(ValueError):
        tuple(client.iter_pages(LeaderboardRequest("1000004605", max_pages, page_size)))
