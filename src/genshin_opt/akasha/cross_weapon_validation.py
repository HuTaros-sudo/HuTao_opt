"""異なる武器base ATKを使うHu Tao Leaderboardの診断専用処理。"""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

from .hutao_models import AkashaHutaoBuild
from .hutao_raw import build_from_raw_row, load_hutao_builds
from .required_e_validation import required_final_atk_rows


@dataclass(frozen=True)
class CrossWeaponCategory:
    leaderboard_id: str
    leaderboard_name: str
    weapon: str
    refinement: int
    weapon_base_atk: float
    raw_total_base_atk: float
    scenario_description: str
    weapon_specific_condition: str
    identification_eligible: bool
    exclusion_reason: str = ""


SCENARIO_DESCRIPTION = (
    "Average DMG for 11N1CD + Q combo. elegy instructor amber c0r1. "
    "kazuha c2r1 @ 1000EM(1420). 4p SR burst uptime 1/3, other sets: 2/3."
)

CATEGORIES = (
    CrossWeaponCategory("1000004605", "VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1",
                        "Staff of Homa", 1, 608.0, 714.5089773, SCENARIO_DESCRIPTION, "low-HP passive active", True),
    CrossWeaponCategory("1000004606", "VV Swirl Hyper Tao Combo, Avg DMG / Staff of the Scarlet Sands R1",
                        "Staff of the Scarlet Sands", 1, 542.0, 648.2641381, SCENARIO_DESCRIPTION,
                        "Scarlet Sands is set to 1 stack for simplicity", False,
                        "EM-to-ATK passive and its snapshot/input boundary are not independently reconstructed"),
    CrossWeaponCategory("1000004607", "VV Swirl Hyper Tao Combo, Avg DMG / Ballad of the Fjords R5",
                        "Ballad of the Fjords", 5, 510.0, 616.0403291, SCENARIO_DESCRIPTION,
                        "three-element passive supplies EM only; N1 non-vape has no direct EM term", True),
)


def category_by_id(leaderboard_id: str) -> CrossWeaponCategory:
    try:
        return next(category for category in CATEGORIES if category.leaderboard_id == leaderboard_id)
    except StopIteration as error:
        raise ValueError(f"未登録のcross-weapon leaderboardです: {leaderboard_id}") from error


def parse_jina_api_payload(path: str | Path) -> dict:
    """Jina read-only proxyが付加した見出しを除いてAkasha JSONを読む。"""
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    marker = "Markdown Content:\n"
    if marker not in text:
        raise ValueError(f"Jina payload markerがありません: {source}")
    payload = json.loads(text.split(marker, 1)[1])
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError(f"Akasha data配列がありません: {source}")
    return payload


def load_jina_builds(path: str | Path, leaderboard_id: str) -> tuple[AkashaHutaoBuild, ...]:
    source = Path(path)
    payload = parse_jina_api_payload(source)
    builds = []
    for index, row in enumerate(payload["data"]):
        if not isinstance(row, dict):
            continue
        calculation = row.get("calculation")
        if isinstance(calculation, dict) and str(calculation.get("id")) == leaderboard_id:
            builds.append(build_from_raw_row(row, source, index))
    return tuple(sorted(builds, key=lambda build: build.rank))


def scenario_difference_flags(category: CrossWeaponCategory, baseline: CrossWeaponCategory | None = None) -> dict[str, bool]:
    baseline = baseline or CATEGORIES[0]
    description_changed = category.scenario_description != baseline.scenario_description
    return {
        "kazuha_em_diff": description_changed, "kazuha_constellation_diff": description_changed,
        "freedom_sworn_diff": description_changed, "amber_constellation_diff": description_changed,
        "elegy_diff": description_changed, "instructor_diff": description_changed,
        "hydro_teammate_diff": False, "pyro_resonance_diff": description_changed,
        "combo_diff": description_changed, "q_uptime_diff": description_changed,
        "artifact_set_rule_diff": description_changed,
    }


def cross_weapon_missing_rows(builds_by_id: dict[str, tuple[AkashaHutaoBuild, ...]]) -> list[dict[str, object]]:
    rows = []
    for category in CATEGORIES:
        builds = builds_by_id.get(category.leaderboard_id, ())
        for build, required in zip(builds, required_final_atk_rows(builds), strict=True):
            unexplained = float(required["required_final_atk"]) - float(required["predicted_final_atk"])
            rows.append({
                "leaderboard_id": category.leaderboard_id, "leaderboard_name": category.leaderboard_name,
                "weapon": category.weapon, "weapon_refinement": category.refinement,
                "weapon_base_atk": category.weapon_base_atk, "character_base_atk_display": 106.0,
                "raw_total_base_atk": build.base_atk, "rank": build.rank, "uid": build.uid,
                "build_md5": build.build_md5, "diagnostic_eligible": category.identification_eligible,
                "exclusion_reason": category.exclusion_reason, "observed_n1_non_vape": build.observed.n1_non_vape,
                "observed_n1_vape": build.observed.n1_vape, "observed_ca_vape": build.observed.ca_vape,
                "observed_q_vape": build.observed.q_vape, "observed_aggregate": build.observed_result,
                "raw_max_hp": build.max_hp, "raw_atk": build.sheet_atk, "raw_crit_rate": build.crit_rate,
                "raw_crit_damage": build.crit_dmg, "raw_elemental_mastery": build.elemental_mastery,
                "raw_pyro_damage_bonus": build.pyro_dmg_bonus,
                "normalized_precombat_atk": required["normalized_precombat_atk"],
                "external_combat_atk_bonus": required["external_combat_atk_bonus"],
                "predicted_e_atk_bonus": required["predicted_e_atk_bonus"],
                "predicted_final_atk": required["predicted_final_atk"],
                "required_final_atk": required["required_final_atk"], "unexplained_atk": unexplained,
                "unexplained_atk_div_base_atk": unexplained / build.base_atk,
            })
    return rows


def category_summaries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries = []
    for category in CATEGORIES:
        selected = [row for row in rows if row["leaderboard_id"] == category.leaderboard_id]
        if not selected:
            continue
        values = [float(row["unexplained_atk"]) for row in selected]
        ratios = [float(row["unexplained_atk_div_base_atk"]) for row in selected]
        flags = scenario_difference_flags(category)
        summaries.append({
            "leaderboard_id": category.leaderboard_id, "leaderboard_name": category.leaderboard_name,
            "weapon": category.weapon, "weapon_refinement": category.refinement,
            "weapon_base_atk": category.weapon_base_atk, "character_base_atk_display": 106.0,
            "raw_total_base_atk": category.raw_total_base_atk, "build_count": len(selected),
            "unexplained_atk_mean": mean(values), "unexplained_atk_std": pstdev(values),
            "unexplained_atk_min": min(values), "unexplained_atk_max": max(values),
            "unexplained_div_base_atk_mean": mean(ratios),
            "identification_eligible": category.identification_eligible,
            "exclusion_reason": category.exclusion_reason, "scenario_description": category.scenario_description,
            "weapon_specific_condition": category.weapon_specific_condition, **flags,
        })
    return summaries


def _fit_metrics(actual: list[float], predicted: list[float]) -> dict[str, float]:
    residuals = [value - estimate for value, estimate in zip(actual, predicted, strict=True)]
    actual_mean = mean(actual)
    total = sum((value - actual_mean) ** 2 for value in actual)
    r_squared = 1 - sum(value**2 for value in residuals) / total if total else float("nan")
    return {"r_squared": r_squared, "residual_std": pstdev(residuals),
            "max_abs_category_mean_residual": float("nan")}


def missing_atk_model_comparison(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """識別可能としたカテゴリだけでflat/proportional/affine/category別を診断fitする。"""
    eligible = [row for row in rows if row["diagnostic_eligible"]]
    xs = [float(row["raw_total_base_atk"]) for row in eligible]
    ys = [float(row["unexplained_atk"]) for row in eligible]
    categories = [str(row["leaderboard_id"]) for row in eligible]
    constant = mean(ys)
    proportional = sum(x * y for x, y in zip(xs, ys, strict=True)) / sum(x * x for x in xs)
    x_mean, y_mean = mean(xs), mean(ys)
    affine_slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True)) / sum((x - x_mean) ** 2 for x in xs)
    affine_intercept = y_mean - affine_slope * x_mean
    category_means = {name: mean(y for y, category in zip(ys, categories, strict=True) if category == name)
                      for name in set(categories)}
    candidates = (
        ("A_flat", 0.0, constant, [constant] * len(xs)),
        ("B_base_atk_proportional", proportional, 0.0, [proportional * x for x in xs]),
        ("C_affine", affine_slope, affine_intercept, [affine_slope * x + affine_intercept for x in xs]),
        ("D_weapon_category", float("nan"), float("nan"), [category_means[name] for name in categories]),
    )
    results = []
    for name, slope, intercept, predicted in candidates:
        metrics = _fit_metrics(ys, predicted)
        residuals = [value - estimate for value, estimate in zip(ys, predicted, strict=True)]
        category_residuals = [abs(mean(residual for residual, category in zip(residuals, categories, strict=True)
                                      if category == name_id)) for name_id in set(categories)]
        metrics["max_abs_category_mean_residual"] = max(category_residuals)
        results.append({"model": name, "slope": slope, "intercept": intercept, **metrics})
    return results


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    if not rows:
        raise ValueError(f"CSVへ保存する行がありません: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run_cross_weapon_validation(homa_raw_root: str | Path = "data/akasha/raw",
                                scarlet_jina: str | Path = "data/akasha/cross_1000004606_jina.txt",
                                fjords_jina: str | Path = "data/akasha/cross_1000004607_jina.txt",
                                output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds_by_id = {
        "1000004605": load_hutao_builds(homa_raw_root, "1000004605"),
        "1000004606": load_jina_builds(scarlet_jina, "1000004606"),
        "1000004607": load_jina_builds(fjords_jina, "1000004607"),
    }
    rows = cross_weapon_missing_rows(builds_by_id)
    summaries = category_summaries(rows)
    models = missing_atk_model_comparison(rows)
    output = Path(output_root)
    _write_csv(summaries, output / "cross_weapon_categories.csv")
    _write_csv(rows, output / "cross_weapon_missing_atk.csv")
    return {"builds_by_id": builds_by_id, "rows": rows, "category_summaries": summaries,
            "model_comparison": models}
