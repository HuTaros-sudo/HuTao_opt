"""Akashaのrawレスポンスと整形済みCSVを別々に保存する。"""

import csv
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path

from .api import AkashaAPIError
from .models import LeaderboardObservation, RawLeaderboardPage


CSV_FIELDS = ("leaderboard_id", "rank", "calculation_result", "uid", "profile_id", "entry_id",
              "build_md5", "character_id", "fetched_at", "raw_page")


def observations_from_page(page: RawLeaderboardPage, leaderboard_id: str,
                           raw_page: str = "") -> tuple[LeaderboardObservation, ...]:
    observations = []
    for index, row in enumerate(page.payload["data"]):
        path = f"page[{page.page}].data[{index}]"
        if not isinstance(row, dict):
            raise AkashaAPIError(f"{path}: オブジェクトではありません")
        calculation = row.get("calculation")
        if not isinstance(calculation, dict):
            raise AkashaAPIError(f"{path}.calculation: オブジェクトがありません")
        if str(calculation.get("id")) != leaderboard_id:
            raise AkashaAPIError(f"{path}.calculation.id: 要求したleaderboard IDと一致しません")
        rank = row.get("index")
        result = calculation.get("result")
        if type(rank) is not int or rank <= 0:
            raise AkashaAPIError(f"{path}.index: 正の整数ではありません")
        if type(result) not in (int, float) or not math.isfinite(result):
            raise AkashaAPIError(f"{path}.calculation.result: 有限の数値ではありません")
        uid = str(row["uid"]) if row.get("uid") is not None else None
        observations.append(LeaderboardObservation(
            leaderboard_id=leaderboard_id, rank=rank, calculation_result=float(result), uid=uid,
            profile_id=None, entry_id=str(row["_id"]) if row.get("_id") is not None else None,
            build_md5=str(row["md5"]) if row.get("md5") is not None else None,
            character_id=str(row["characterId"]) if row.get("characterId") is not None else None,
            fetched_at=page.fetched_at, raw_page=raw_page,
        ))
    return tuple(observations)


def save_raw_page(page: RawLeaderboardPage, run_directory: Path) -> tuple[Path, str]:
    run_directory.mkdir(parents=True, exist_ok=True)
    path = run_directory / f"page_{page.page:04d}.json"
    path.write_bytes(page.body)
    return path, hashlib.sha256(page.body).hexdigest()


def save_observations_csv(observations: tuple[LeaderboardObservation, ...], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(asdict(observation) for observation in observations)
    temporary.replace(path)


def save_manifest(run_directory: Path, manifest: dict) -> Path:
    path = run_directory / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
