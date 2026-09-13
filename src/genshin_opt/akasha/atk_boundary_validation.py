"""修正前後のATK入力境界を同じ20 buildで比較する。"""

import csv
import json
import math
from pathlib import Path
from statistics import mean, median

from .h5_validation import ARTIFACT_ATK_BY_UID, reconstruct_atk_stages
from .hutao_engine import debug_build, predict_components
from .hutao_models import AkashaHutaoBuild, ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_validation import relative_error


COMPONENTS = ("n1_non_vape", "n1_vape", "ca_vape", "q_vape", "aggregate")


def observed_values(build: AkashaHutaoBuild) -> dict[str, float]:
    return {
        "n1_non_vape": build.observed.n1_non_vape, "n1_vape": build.observed.n1_vape,
        "ca_vape": build.observed.ca_vape, "q_vape": build.observed.q_vape,
        "aggregate": build.observed_result,
    }


def corrected_predictions(build: AkashaHutaoBuild, config: ScenarioConfig | None = None) -> dict[str, float]:
    predicted = predict_components(build, config)
    return {
        "n1_non_vape": predicted.n1_non_vape.value, "n1_vape": predicted.n1_vape.value,
        "ca_vape": predicted.ca_vape.value, "q_vape": predicted.q_vape.value,
        "aggregate": predicted.aggregate.value,
    }


def legacy_double_counted_predictions(build: AkashaHutaoBuild, config: ScenarioConfig | None = None) -> dict[str, float]:
    """修正前のHoma低HP 1.0%二重加算を、観測値を変えず診断用に再現する。"""
    corrected = corrected_predictions(build, config)
    final_atk = float(debug_build(build, config)["final_atk"])
    legacy_atk = final_atk + build.max_hp * 0.010
    return {component: value * legacy_atk / final_atk for component, value in corrected.items()}


def boundary_residual_rows(builds: tuple[AkashaHutaoBuild, ...], config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    scenario = config or ScenarioConfig()
    rows = []
    for build in builds:
        observed = observed_values(build)
        before = legacy_double_counted_predictions(build, scenario)
        after = corrected_predictions(build, scenario)
        stages = reconstruct_atk_stages(build)
        debug = debug_build(build, scenario)
        row = {
            "leaderboard_id": build.leaderboard_id, "rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5, "max_hp": build.max_hp, "raw_stats_atk": build.sheet_atk,
            "artifact_atk_pct": stages["artifact_atk_pct"], "artifact_flat_atk": stages["artifact_flat_atk"],
            "artifact_set_atk_pct": stages["artifact_set_atk_pct"], "crit_rate": build.crit_rate,
            "crit_dmg": build.crit_dmg, "elemental_mastery": build.elemental_mastery,
            "pyro_dmg_bonus": build.pyro_dmg_bonus,
            "artifact_sets": json.dumps(dict(build.artifact_sets), ensure_ascii=False, sort_keys=True),
            "normalized_precombat_atk": debug["normalized_precombat_atk"],
            "millennial_movement_atk_pct": debug["millennial_movement_atk_pct"],
            "external_combat_atk_bonus": debug["external_combat_atk_bonus"],
            "amber_c6_atk_pct": debug["amber_c6_atk_pct"],
            "hutao_skill_atk_bonus": debug["hutao_skill_atk_bonus"], "final_atk": debug["final_atk"],
            "legacy_double_counted_homa_low_hp_atk": build.max_hp * 0.010,
        }
        for component in COMPONENTS:
            row[f"observed_{component}"] = observed[component]
            row[f"before_{component}"] = before[component]
            row[f"before_{component}_relative_error"] = relative_error(observed[component], before[component])
            row[f"after_{component}"] = after[component]
            row[f"after_{component}_relative_error"] = relative_error(observed[component], after[component])
            row[f"after_{component}_ratio"] = after[component] / observed[component]
        component_ratios = [float(row[f"after_{component}_ratio"]) for component in COMPONENTS[:-1]]
        row["after_component_ratio_spread"] = max(component_ratios) - min(component_ratios)
        rows.append(row)
    return rows


def component_error_summary(rows: list[dict[str, object]], prefix: str = "after") -> list[dict[str, float | str]]:
    summary = []
    for component in COMPONENTS:
        errors = [float(row[f"{prefix}_{component}_relative_error"]) for row in rows]
        summary.append({
            "component": component, "mean_relative_error": mean(errors),
            "median_relative_error": median(errors), "maximum_absolute_relative_error": max(map(abs, errors)),
            "minimum_relative_error": min(errors), "maximum_relative_error": max(errors),
        })
    return summary


def pearson_correlation(rows: list[dict[str, object]], input_field: str,
                        error_field: str = "after_aggregate_relative_error") -> float:
    xs = [float(row[input_field]) for row in rows]
    ys = [float(row[error_field]) for row in rows]
    mean_x, mean_y = mean(xs), mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys))
    return numerator / denominator if denominator else float("nan")


def aggregate_correlations(rows: list[dict[str, object]], prefix: str = "after") -> dict[str, float]:
    inputs = ("max_hp", "raw_stats_atk", "artifact_atk_pct", "artifact_flat_atk", "crit_rate", "crit_dmg",
              "elemental_mastery", "pyro_dmg_bonus")
    error_field = f"{prefix}_aggregate_relative_error"
    return {field: pearson_correlation(rows, field, error_field) for field in inputs}


def save_boundary_residuals(rows: list[dict[str, object]], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(output)
    return output


def run_atk_boundary_validation(raw_root: str | Path = "data/akasha/raw",
                                output_path: str | Path = "data/akasha/atk_boundary_residuals.csv") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    missing = [build.uid for build in builds if build.uid not in ARTIFACT_ATK_BY_UID]
    if missing:
        raise ValueError(f"聖遺物ATK内訳がないbuildです: {missing}")
    rows = boundary_residual_rows(builds)
    save_boundary_residuals(rows, output_path)
    return {
        "build_count": len(rows), "before": component_error_summary(rows, "before"),
        "after": component_error_summary(rows, "after"),
        "before_correlations": aggregate_correlations(rows, "before"),
        "after_correlations": aggregate_correlations(rows, "after"),
        "mean_ratio_spread": mean(float(row["after_component_ratio_spread"]) for row in rows),
        "max_ratio_spread": max(float(row["after_component_ratio_spread"]) for row in rows),
    }

