"""保存済みAkasha leaderboard rawを胡桃検証入力へ変換する。"""

import json
import math
from pathlib import Path

from .hutao_models import AkashaHutaoBuild, HutaoModelError, ObservedComponents


COMPONENT_NAMES = {
    "NA Vape Avg DMG": "n1_vape",
    "NA Avg DMG": "n1_non_vape",
    "CA Vape Avg DMG": "ca_vape",
    "Q Vape Avg DMG": "q_vape",
}


def _finite_number(value: object, path: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise HutaoModelError(f"{path}: 有限の数値が必要です")
    return float(value)


def _stat(row: dict, name: str, path: str) -> float:
    stat = row.get("stats", {}).get(name)
    if not isinstance(stat, dict):
        raise HutaoModelError(f"{path}.stats.{name}: オブジェクトがありません")
    return _finite_number(stat.get("value"), f"{path}.stats.{name}.value")


def build_from_raw_row(row: dict, raw_path: Path, row_index: int = 0) -> AkashaHutaoBuild:
    path = f"{raw_path}.data[{row_index}]"
    calculation = row.get("calculation")
    if not isinstance(calculation, dict):
        raise HutaoModelError(f"{path}.calculation: オブジェクトがありません")
    found: dict[str, float] = {}
    additional = calculation.get("additional")
    if not isinstance(additional, list):
        raise HutaoModelError(f"{path}.calculation.additional: 配列がありません")
    for component in additional:
        if not isinstance(component, dict) or component.get("name") not in COMPONENT_NAMES:
            continue
        found[COMPONENT_NAMES[component["name"]]] = _finite_number(
            component.get("value"), f"{path}.calculation.additional.value")
    missing = set(COMPONENT_NAMES.values()) - set(found)
    if missing:
        raise HutaoModelError(f"{path}.calculation.additional: component不足 {sorted(missing)}")
    rank = row.get("index")
    if type(rank) is not int or rank <= 0:
        raise HutaoModelError(f"{path}.index: 正の整数が必要です")
    raw_sets = row.get("artifactSets", {})
    if not isinstance(raw_sets, dict):
        raise HutaoModelError(f"{path}.artifactSets: オブジェクトが必要です")
    sets = []
    for name, data in raw_sets.items():
        if not isinstance(name, str) or not isinstance(data, dict) or type(data.get("count")) is not int:
            raise HutaoModelError(f"{path}.artifactSets: set countが不正です")
        sets.append((name, data["count"]))
    observed = ObservedComponents(found["n1_vape"], found["n1_non_vape"],
                                  found["ca_vape"], found["q_vape"])
    return AkashaHutaoBuild(
        input_source="akasha_leaderboard_raw",
        leaderboard_id=str(calculation.get("id")), rank=rank,
        uid=str(row["uid"]) if row.get("uid") is not None else None,
        build_md5=str(row["md5"]) if row.get("md5") is not None else None,
        entry_id=str(row["_id"]) if row.get("_id") is not None else None,
        raw_path=str(raw_path), max_hp=_stat(row, "maxHp", path), sheet_atk=_stat(row, "atk", path),
        base_atk=_stat(row, "baseAtk", path), crit_rate=_stat(row, "critRate", path),
        crit_dmg=_stat(row, "critDamage", path), elemental_mastery=_stat(row, "elementalMastery", path),
        pyro_dmg_bonus=_stat(row, "pyroDamageBonus", path), artifact_sets=tuple(sorted(sets)),
        observed=observed, observed_result=_finite_number(calculation.get("result"), f"{path}.calculation.result"),
    )


def load_hutao_builds(raw_root: str | Path, leaderboard_id: str = "1000004605") -> tuple[AkashaHutaoBuild, ...]:
    root = Path(raw_root)
    paths = sorted(root.rglob("page_*.json")) if root.is_dir() else [root]
    if not paths:
        raise FileNotFoundError(f"Akasha raw pageがありません: {root}")
    unique: dict[tuple[str | None, str | None, str | None], AkashaHutaoBuild] = {}
    for raw_path in paths:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise HutaoModelError(f"{raw_path}.data: 配列がありません")
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise HutaoModelError(f"{raw_path}.data[{index}]: オブジェクトが必要です")
            calculation = row.get("calculation")
            if not isinstance(calculation, dict) or str(calculation.get("id")) != leaderboard_id:
                continue
            if not isinstance(calculation.get("additional"), list):
                continue
            build = build_from_raw_row(row, raw_path, index)
            key = (build.uid, build.build_md5, build.entry_id)
            unique[key] = build
    return tuple(sorted(unique.values(), key=lambda build: (build.rank, build.observed_result * -1)))
