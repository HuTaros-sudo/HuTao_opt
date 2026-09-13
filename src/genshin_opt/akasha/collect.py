"""Akasha leaderboardを取得し、rawページと正規化CSVを保存する。"""

from datetime import datetime, timezone
from pathlib import Path

from .api import AkashaLeaderboardClient, LeaderboardRequest
from .models import CollectionResult, LeaderboardObservation
from .storage import observations_from_page, save_manifest, save_observations_csv, save_raw_page


def _run_name(leaderboard_id: str, started_at: datetime) -> str:
    safe_id = "".join(character for character in leaderboard_id if character.isalnum() or character in "-_")
    if not safe_id or safe_id != leaderboard_id:
        raise ValueError("leaderboard_idには英数字、ハイフン、アンダースコアだけを使用してください")
    timestamp = started_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{safe_id}_{timestamp}"


def collect_leaderboard(client: AkashaLeaderboardClient, request: LeaderboardRequest,
                        raw_root: str | Path = "data/akasha/raw",
                        csv_path: str | Path = "data/akasha/leaderboard.csv") -> CollectionResult:
    """取得成功時だけCSVを置換する。途中失敗時も取得済みrawと失敗manifestを残す。"""
    started_at = datetime.now(timezone.utc)
    run_directory = Path(raw_root) / _run_name(request.leaderboard_id, started_at)
    run_directory.mkdir(parents=True, exist_ok=False)
    observations: list[LeaderboardObservation] = []
    page_entries = []
    status = "failed"
    error_message = None
    try:
        for page in client.iter_pages(request):
            raw_path, sha256 = save_raw_page(page, run_directory)
            relative_raw_path = raw_path.relative_to(run_directory).as_posix()
            page_observations = observations_from_page(page, request.leaderboard_id, relative_raw_path)
            observations.extend(page_observations)
            page_entries.append({"page": page.page, "request_url": page.request_url,
                                 "fetched_at": page.fetched_at, "file": relative_raw_path,
                                 "sha256": sha256, "rows": len(page_observations)})
        entry_ids = [observation.entry_id for observation in observations if observation.entry_id is not None]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("ページ間でLeaderboard行IDが重複しています")
        save_observations_csv(tuple(observations), Path(csv_path))
        status = "complete"
    except Exception as error:
        error_message = f"{type(error).__name__}: {error}"
        raise
    finally:
        finished_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        manifest = {"leaderboard_id": request.leaderboard_id, "status": status,
                    "started_at": started_at.isoformat().replace("+00:00", "Z"),
                    "finished_at": finished_at, "max_pages": request.max_pages,
                    "page_size": request.page_size, "variant": request.variant,
                    "pages": page_entries, "observations": len(observations), "error": error_message}
        save_manifest(run_directory, manifest)
    return CollectionResult(request.leaderboard_id, str(run_directory), str(csv_path),
                            len(page_entries), len(observations))
