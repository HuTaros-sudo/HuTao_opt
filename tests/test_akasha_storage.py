import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from genshin_opt.akasha.api import AkashaAPIConfig, AkashaLeaderboardClient, LeaderboardRequest
from genshin_opt.akasha.collect import collect_leaderboard


def response_body() -> bytes:
    payload = {
        "ttl": 0,
        "data": [
            {"_id": "entry-1", "uid": "test-user-1", "md5": "build-hash",
             "characterId": 10000046, "index": 1,
             "calculation": {"id": "1000004605", "result": 123456.75}},
            {"_id": "entry-2", "index": 2,
             "calculation": {"id": "1000004605", "result": 2509462.6024736445}},
        ],
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def test_collection_keeps_raw_bytes_separate_from_normalized_csv(tmp_path: Path) -> None:
    body = response_body()
    client = AkashaLeaderboardClient(AkashaAPIConfig(max_retries=0), transport=lambda *_: body,
                                    clock=lambda: datetime(2026, 9, 13, 1, 2, 3, tzinfo=timezone.utc))
    csv_path = tmp_path / "leaderboard.csv"
    result = collect_leaderboard(client, LeaderboardRequest("1000004605", 1, 20),
                                 tmp_path / "raw", csv_path)

    raw_path = Path(result.raw_directory) / "page_0001.json"
    assert raw_path.read_bytes() == body
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["leaderboard_id"] == "1000004605"
    assert rows[0]["rank"] == "1"
    assert rows[0]["calculation_result"] == "123456.75"
    assert rows[0]["uid"] == "test-user-1"
    assert rows[0]["profile_id"] == ""
    assert rows[0]["entry_id"] == "entry-1"
    assert rows[0]["build_md5"] == "build-hash"
    assert rows[0]["character_id"] == "10000046"
    assert rows[1]["uid"] == ""
    manifest = json.loads((Path(result.raw_directory) / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["pages"][0]["sha256"]
    assert result.observations_saved == 2


def test_collection_allows_tied_ranks(tmp_path: Path) -> None:
    payload = json.loads(response_body())
    payload["data"][1]["index"] = 1
    body = json.dumps(payload).encode()
    client = AkashaLeaderboardClient(AkashaAPIConfig(max_retries=0), transport=lambda *_: body)
    result = collect_leaderboard(client, LeaderboardRequest("1000004605", 1, 20),
                                 tmp_path / "raw", tmp_path / "leaderboard.csv")
    assert result.observations_saved == 2


def test_failed_later_page_keeps_raw_and_manifest_but_not_csv(tmp_path: Path) -> None:
    calls = 0

    def transport(url: str, timeout: float, headers: dict[str, str]) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 1:
            payload = json.loads(response_body())
            payload["data"] = payload["data"][:1]
            return json.dumps(payload).encode()
        raise RuntimeError("second page failed")

    client = AkashaLeaderboardClient(AkashaAPIConfig(max_retries=0, page_delay_seconds=0), transport=transport)
    with pytest.raises(RuntimeError, match="second page failed"):
        collect_leaderboard(client, LeaderboardRequest("1000004605", 2, 1),
                            tmp_path / "raw", tmp_path / "leaderboard.csv")

    run_directory = next((tmp_path / "raw").iterdir())
    assert (run_directory / "page_0001.json").exists()
    manifest = json.loads((run_directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["observations"] == 1
    assert "second page failed" in manifest["error"]
    assert not (tmp_path / "leaderboard.csv").exists()
