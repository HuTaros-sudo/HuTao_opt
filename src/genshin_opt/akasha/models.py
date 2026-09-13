"""Akasha leaderboardのrawページと整形済み観測値。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RawLeaderboardPage:
    page: int
    request_url: str
    fetched_at: str
    body: bytes
    payload: dict


@dataclass(frozen=True)
class LeaderboardObservation:
    leaderboard_id: str
    rank: int
    calculation_result: float
    uid: str | None
    profile_id: str | None
    entry_id: str | None
    build_md5: str | None
    character_id: str | None
    fetched_at: str
    raw_page: str = ""


@dataclass(frozen=True)
class CollectionResult:
    leaderboard_id: str
    raw_directory: str
    csv_path: str
    pages_fetched: int
    observations_saved: int
