"""Akashaの非公式公開エンドポイントを低頻度で読むHTTPクライアント。"""

import json
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import RawLeaderboardPage


class AkashaAPIError(RuntimeError):
    """HTTP、JSON、または非公式API形式のエラー。"""


class AkashaRequestError(AkashaAPIError):
    def __init__(self, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class AkashaAPIConfig:
    base_url: str = "https://akasha.cv/api"
    leaderboard_endpoint: str = "leaderboards"
    timeout_seconds: float = 20.0
    page_delay_seconds: float = 1.0
    max_retries: int = 2
    retry_delay_seconds: float = 2.0
    user_agent: str = "genshin-opt-akasha-observer/0.1"


@dataclass(frozen=True)
class LeaderboardRequest:
    leaderboard_id: str
    max_pages: int = 1
    page_size: int = 20
    variant: str = ""


Transport = Callable[[str, float, Mapping[str, str]], bytes]
Sleep = Callable[[float], None]
Clock = Callable[[], datetime]


def urllib_transport(url: str, timeout: float, headers: Mapping[str, str]) -> bytes:
    request = Request(url, headers=dict(headers), method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as error:
        retryable = error.code == 429 or 500 <= error.code < 600
        raise AkashaRequestError(f"Akasha API HTTP {error.code}: {url}", retryable) from error
    except (URLError, TimeoutError, OSError) as error:
        raise AkashaRequestError(f"Akasha APIへ接続できません: {error}", True) from error


class AkashaLeaderboardClient:
    def __init__(self, config: AkashaAPIConfig | None = None, transport: Transport = urllib_transport,
                 sleep: Sleep = time.sleep, clock: Clock | None = None) -> None:
        self.config = config or AkashaAPIConfig()
        self.transport = transport
        self.sleep = sleep
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._validate_config()

    def _validate_config(self) -> None:
        config = self.config
        if not config.base_url.startswith(("https://", "http://")):
            raise ValueError("base_urlはhttpまたはhttps URLにしてください")
        if not config.leaderboard_endpoint.strip("/"):
            raise ValueError("leaderboard_endpointが空です")
        if config.timeout_seconds <= 0 or config.page_delay_seconds < 0 or config.retry_delay_seconds < 0:
            raise ValueError("timeoutは正、待機時間は0以上にしてください")
        if type(config.max_retries) is not int or not 0 <= config.max_retries <= 5:
            raise ValueError("max_retriesは0〜5にしてください")

    @staticmethod
    def _validate_request(request: LeaderboardRequest) -> None:
        if not isinstance(request.leaderboard_id, str) or not request.leaderboard_id.strip():
            raise ValueError("leaderboard_idが空です")
        if type(request.max_pages) is not int or not 1 <= request.max_pages <= 100:
            raise ValueError("max_pagesは1〜100にしてください")
        if type(request.page_size) is not int or not 1 <= request.page_size <= 100:
            raise ValueError("page_sizeは1〜100にしてください")

    def _url(self, request: LeaderboardRequest, page: int, cursor: str) -> str:
        endpoint = self.config.leaderboard_endpoint.strip("/")
        params = {"calculationId": request.leaderboard_id, "size": str(request.page_size),
                  "page": str(page), "sort": "calculation.result", "order": "-1",
                  "variant": request.variant, "p": cursor, "uids": "", "filter": ""}
        return f"{self.config.base_url.rstrip('/')}/{endpoint}?{urlencode(params)}"

    def _fetch(self, url: str) -> bytes:
        headers = {"Accept": "application/json", "User-Agent": self.config.user_agent}
        for attempt in range(self.config.max_retries + 1):
            try:
                return self.transport(url, self.config.timeout_seconds, headers)
            except AkashaRequestError as error:
                if not error.retryable or attempt >= self.config.max_retries:
                    raise
                self.sleep(self.config.retry_delay_seconds)
        raise AssertionError("有限リトライのループを抜けました")

    def iter_pages(self, request: LeaderboardRequest) -> Iterator[RawLeaderboardPage]:
        """最大ページ数まで取得し、ページ間待機を挟んでrawページを返す。"""
        self._validate_request(request)
        cursor = ""
        for page_number in range(1, request.max_pages + 1):
            if page_number > 1:
                self.sleep(self.config.page_delay_seconds)
            url = self._url(request, page_number, cursor)
            body = self._fetch(url)
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise AkashaAPIError(f"Akasha APIのJSONを読めません: page={page_number}") from error
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise AkashaAPIError(f"Akasha API応答にdata配列がありません: page={page_number}")
            fetched_at = self.clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            yield RawLeaderboardPage(page_number, url, fetched_at, body, payload)
            rows = payload["data"]
            if not rows or len(rows) < request.page_size:
                break
            try:
                cursor = f"lt|{rows[-1]['calculation']['result']}"
            except (KeyError, TypeError) as error:
                raise AkashaAPIError(f"次ページ用cursorを作れません: page={page_number}") from error
