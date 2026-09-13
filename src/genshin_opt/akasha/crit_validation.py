"""raw CRIT境界と期待会心倍率だけを診断する。"""

import csv
import json
import math
from pathlib import Path
from statistics import mean, median, pstdev

from .hutao_models import AkashaHutaoBuild, ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_score import score_hutao_akasha
from .hutao_validation import relative_error


HUTAO_BASE_CRIT_RATE = 0.05
BASE_CRIT_DMG = 0.50
HUTAO_ASCENSION_CRIT_DMG = 0.384
HOMA_R1_CRIT_DMG = 0.662
FIXED_CRIT_DMG = BASE_CRIT_DMG + HUTAO_ASCENSION_CRIT_DMG + HOMA_R1_CRIT_DMG


def _raw_row(build: AkashaHutaoBuild) -> dict[str, object]:
    payload = json.loads(Path(build.raw_path).read_text(encoding="utf-8"))
    return next(row for row in payload["data"] if str(row.get("uid")) == build.uid and row.get("md5") == build.build_md5)


def input_reconstruction_rows(builds: tuple[AkashaHutaoBuild, ...]) -> list[dict[str, object]]:
    rows = []
    for build in builds:
        raw = _raw_row(build)
        artifact_cr_from_raw = build.crit_rate - HUTAO_BASE_CRIT_RATE
        artifact_cd_from_raw = build.crit_dmg - FIXED_CRIT_DMG
        raw_artifact_cv = float(raw["critValue"])
        reconstructed_artifact_cv = 100 * (2 * artifact_cr_from_raw + artifact_cd_from_raw)
        artifact_cr_from_cv_and_cd = (raw_artifact_cv / 100 - artifact_cd_from_raw) / 2
        reconstructed_cr_from_cv = HUTAO_BASE_CRIT_RATE + artifact_cr_from_cv_and_cd
        artifact_cd_from_cv_and_cr = raw_artifact_cv / 100 - 2 * artifact_cr_from_raw
        reconstructed_cd_from_cv = FIXED_CRIT_DMG + artifact_cd_from_cv_and_cr
        rows.append({
            "leaderboard_id": build.leaderboard_id, "rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5, "raw_stats_crit_rate": build.crit_rate,
            "hutao_base_crit_rate": HUTAO_BASE_CRIT_RATE,
            "artifact_crit_rate_from_raw_boundary": artifact_cr_from_raw, "other_fixed_crit_rate": 0.0,
            "reconstructed_crit_rate": HUTAO_BASE_CRIT_RATE + artifact_cr_from_raw,
            "crit_rate_difference": HUTAO_BASE_CRIT_RATE + artifact_cr_from_raw - build.crit_rate,
            "raw_stats_crit_damage": build.crit_dmg, "base_crit_damage": BASE_CRIT_DMG,
            "hutao_ascension_crit_damage": HUTAO_ASCENSION_CRIT_DMG, "homa_r1_crit_damage": HOMA_R1_CRIT_DMG,
            "artifact_crit_damage_from_raw_boundary": artifact_cd_from_raw,
            "reconstructed_crit_damage": FIXED_CRIT_DMG + artifact_cd_from_raw,
            "crit_damage_difference": FIXED_CRIT_DMG + artifact_cd_from_raw - build.crit_dmg,
            "raw_artifact_crit_value": raw_artifact_cv, "reconstructed_artifact_crit_value": reconstructed_artifact_cv,
            "artifact_crit_value_difference": reconstructed_artifact_cv - raw_artifact_cv,
            "artifact_crit_rate_from_cv_and_raw_cd": artifact_cr_from_cv_and_cd,
            "reconstructed_crit_rate_from_cv": reconstructed_cr_from_cv,
            "crit_rate_from_cv_difference": reconstructed_cr_from_cv - build.crit_rate,
            "artifact_crit_damage_from_cv_and_raw_cr": artifact_cd_from_cv_and_cr,
            "reconstructed_crit_damage_from_cv": reconstructed_cd_from_cv,
            "crit_damage_from_cv_difference": reconstructed_cd_from_cv - build.crit_dmg,
        })
    return rows


def _pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = mean(xs), mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator if denominator else float("nan")


def multiplier_residual_rows(builds: tuple[AkashaHutaoBuild, ...],
                             config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    scenario = config or ScenarioConfig()
    reconstruction = {row["uid"]: row for row in input_reconstruction_rows(builds)}
    rows = []
    for build in builds:
        result = score_hutao_akasha(build, scenario)
        current = float(result.debug_breakdown["crit_multiplier"])
        no_clamp = 1 + build.crit_rate * build.crit_dmg
        clamped = 1 + min(max(build.crit_rate, 0.0), 1.0) * build.crit_dmg
        reconstructed_cr = float(reconstruction[build.uid]["reconstructed_crit_rate_from_cv"])
        reconstructed = 1 + min(max(reconstructed_cr, 0.0), 1.0) * build.crit_dmg
        precrit_aggregate = result.aggregate_score / current
        required = build.observed_result / precrit_aggregate
        row = {
            "leaderboard_id": build.leaderboard_id, "rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5, "raw_crit_rate": build.crit_rate,
            "raw_crit_damage": build.crit_dmg, "crit_rate_exceeds_100": build.crit_rate > 1,
            "a_raw_no_clamp_multiplier": no_clamp, "b_raw_clamped_multiplier": clamped,
            "c_current_raw_multiplier": current, "d_reconstructed_cr_multiplier": reconstructed,
            "predicted_precrit_aggregate": precrit_aggregate,
            "observed_aggregate": build.observed_result, "predicted_aggregate": result.aggregate_score,
            "required_crit_multiplier": required, "current_crit_multiplier": current,
            "required_to_current_ratio": required / current,
            "current_aggregate_relative_error": relative_error(build.observed_result, result.aggregate_score),
        }
        for candidate in ("a_raw_no_clamp_multiplier", "b_raw_clamped_multiplier",
                          "c_current_raw_multiplier", "d_reconstructed_cr_multiplier"):
            predicted = precrit_aggregate * float(row[candidate])
            row[f"{candidate}_predicted_aggregate"] = predicted
            row[f"{candidate}_aggregate_relative_error"] = relative_error(build.observed_result, predicted)
        component_inputs = {
            "n1_non_vape": (build.observed.n1_non_vape, result.n1_non_vape_avg),
            "n1_vape": (build.observed.n1_vape, result.n1_vape_avg),
            "ca_vape": (build.observed.ca_vape, result.ca_vape_avg),
            "q_vape": (build.observed.q_vape, result.q_vape_avg),
        }
        for name, (observed, predicted) in component_inputs.items():
            precrit = predicted / current
            row[f"{name}_required_crit_multiplier"] = observed / precrit
            row[f"{name}_required_to_current_ratio"] = observed / predicted
        rows.append(row)

    residuals = [float(row["current_aggregate_relative_error"]) for row in rows]
    correlations = {
        "aggregate_residual_vs_crit_rate_pearson": _pearson([float(row["raw_crit_rate"]) for row in rows], residuals),
        "aggregate_residual_vs_crit_damage_pearson": _pearson([float(row["raw_crit_damage"]) for row in rows], residuals),
        "aggregate_residual_vs_current_crit_multiplier_pearson": _pearson(
            [float(row["current_crit_multiplier"]) for row in rows], residuals),
    }
    ratios = [float(row["required_to_current_ratio"]) for row in rows]
    for row in rows:
        row.update(correlations)
        row["required_to_current_ratio_mean"] = mean(ratios)
        row["required_to_current_ratio_median"] = median(ratios)
        row["required_to_current_ratio_std"] = pstdev(ratios)
        row["required_to_current_ratio_minimum"] = min(ratios)
        row["required_to_current_ratio_maximum"] = max(ratios)
    return rows


def candidate_summaries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries = []
    for candidate in ("a_raw_no_clamp_multiplier", "b_raw_clamped_multiplier",
                      "c_current_raw_multiplier", "d_reconstructed_cr_multiplier"):
        errors = [float(row[f"{candidate}_aggregate_relative_error"]) for row in rows]
        summaries.append({
            "candidate": candidate, "mean_relative_error": mean(errors),
            "median_relative_error": median(errors), "residual_std": pstdev(errors),
            "maximum_absolute_relative_error": max(map(abs, errors)),
        })
    return summaries


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run_crit_validation(raw_root: str | Path = "data/akasha/raw",
                        output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    input_rows = input_reconstruction_rows(builds)
    residual_rows = multiplier_residual_rows(builds)
    output = Path(output_root)
    _write_csv(input_rows, output / "crit_input_reconstruction.csv")
    _write_csv(residual_rows, output / "crit_multiplier_residuals.csv")
    first = residual_rows[0]
    return {
        "build_count": len(builds), "crit_rate_over_100_count": sum(build.crit_rate > 1 for build in builds),
        "candidate_summaries": candidate_summaries(residual_rows),
        "required_to_current": {
            "mean": first["required_to_current_ratio_mean"], "median": first["required_to_current_ratio_median"],
            "std": first["required_to_current_ratio_std"], "min": first["required_to_current_ratio_minimum"],
            "max": first["required_to_current_ratio_maximum"],
        },
        "correlations": {
            "crit_rate": first["aggregate_residual_vs_crit_rate_pearson"],
            "crit_damage": first["aggregate_residual_vs_crit_damage_pearson"],
            "crit_multiplier": first["aggregate_residual_vs_current_crit_multiplier_pearson"],
        },
    }
