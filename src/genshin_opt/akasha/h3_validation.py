"""H3の敵DEF・Pyro RES離散候補を、他仮説を固定して比較する。"""

import csv
import math
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, median, pstdev

from .hutao_damage import enemy_def_multiplier, enemy_res_multiplier
from .hutao_engine import predict_components
from .hutao_models import AkashaHutaoBuild, ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_validation import relative_error


CHARACTER_LEVEL = 90
BASELINE_ENEMY_LEVEL = 90
BASELINE_BASE_PYRO_RES = 0.10
BASELINE_VV_REDUCTION = 0.40
E_SKILL_HP_TO_ATK = 0.0626
COMPONENTS = ("n1_non_vape", "n1_vape", "ca_vape", "q_vape", "aggregate")


@dataclass(frozen=True)
class EnemyCandidate:
    candidate_id: str
    enemy_level: int
    base_pyro_res: float
    vv_res_reduction: float

    @property
    def vv_enabled(self) -> bool:
        return self.vv_res_reduction != 0


def make_candidates() -> tuple[EnemyCandidate, ...]:
    candidates = []
    for enemy_level in (80, 90, 100):
        for base_res in (0.0, 0.10):
            for vv_reduction in (0.40, 0.0):
                res_label = f"res{int(base_res * 100)}"
                vv_label = "vv40" if vv_reduction else "no_vv"
                candidates.append(EnemyCandidate(f"enemy{enemy_level}_{res_label}_{vv_label}", enemy_level,
                                                  base_res, vv_reduction))
    return tuple(candidates)


def enemy_multiplier_breakdown(candidate: EnemyCandidate) -> dict[str, float]:
    defense = enemy_def_multiplier(CHARACTER_LEVEL, candidate.enemy_level)
    resistance = enemy_res_multiplier(candidate.base_pyro_res, candidate.vv_res_reduction)
    res_after_vv = candidate.base_pyro_res - candidate.vv_res_reduction
    return {
        "def_multiplier": defense.value, "res_after_vv": res_after_vv,
        "res_multiplier": resistance.value, "common_enemy_multiplier": defense.value * resistance.value,
    }


def baseline_candidate() -> EnemyCandidate:
    return EnemyCandidate("enemy90_res10_vv40", BASELINE_ENEMY_LEVEL, BASELINE_BASE_PYRO_RES,
                          BASELINE_VV_REDUCTION)


def _observed(build: AkashaHutaoBuild) -> dict[str, float]:
    return {
        "n1_non_vape": build.observed.n1_non_vape, "n1_vape": build.observed.n1_vape,
        "ca_vape": build.observed.ca_vape, "q_vape": build.observed.q_vape,
        "aggregate": build.observed_result,
    }


def _predicted(build: AkashaHutaoBuild, candidate: EnemyCandidate,
               base_config: ScenarioConfig) -> dict[str, float]:
    config = replace(base_config, character_level=CHARACTER_LEVEL, enemy_level=candidate.enemy_level,
                     enemy_base_pyro_res=candidate.base_pyro_res, vv_res_reduction=candidate.vv_res_reduction)
    predicted = predict_components(build, config)
    return {
        "n1_non_vape": predicted.n1_non_vape.value, "n1_vape": predicted.n1_vape.value,
        "ca_vape": predicted.ca_vape.value, "q_vape": predicted.q_vape.value,
        "aggregate": predicted.aggregate.value,
    }


def _pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = mean(xs), mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator if denominator else float("nan")


def build_residual_rows(builds: tuple[AkashaHutaoBuild, ...], candidates: tuple[EnemyCandidate, ...] | None = None,
                        base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    scenario = base_config or ScenarioConfig()
    rows = []
    for candidate in candidates or make_candidates():
        multiplier = enemy_multiplier_breakdown(candidate)
        group = []
        for build in builds:
            observed = _observed(build)
            predicted = _predicted(build, candidate, scenario)
            e_bonus = min(build.max_hp * E_SKILL_HP_TO_ATK, build.base_atk * 4)
            row = {
                "leaderboard_id": build.leaderboard_id, "candidate_id": candidate.candidate_id,
                "rank": build.rank, "uid": build.uid, "build_md5": build.build_md5,
                "character_level": CHARACTER_LEVEL, "enemy_level": candidate.enemy_level,
                "base_pyro_res": candidate.base_pyro_res, "vv_res_reduction": candidate.vv_res_reduction,
                "vv_enabled": candidate.vv_enabled, **multiplier, "max_hp": build.max_hp,
                "e_atk_bonus": e_bonus, "raw_stats_atk": build.sheet_atk,
                "elemental_mastery": build.elemental_mastery, "crit_rate": build.crit_rate,
                "crit_dmg": build.crit_dmg,
            }
            for component in COMPONENTS:
                row[f"observed_{component}"] = observed[component]
                row[f"predicted_{component}"] = predicted[component]
                row[f"{component}_relative_error"] = relative_error(observed[component], predicted[component])
                row[f"{component}_observed_to_predicted_ratio"] = observed[component] / predicted[component]
                row[f"{component}_absolute_damage_error"] = abs(predicted[component] - observed[component])
            ratios = [predicted[name] / observed[name] for name in COMPONENTS[:-1]]
            row["component_ratio_spread"] = max(ratios) - min(ratios)
            row["component_ratio_relative_spread"] = max(ratios) / min(ratios) - 1
            group.append(row)
        aggregate_errors = [float(row["aggregate_relative_error"]) for row in group]
        inputs = ("max_hp", "e_atk_bonus", "raw_stats_atk", "elemental_mastery", "crit_rate", "crit_dmg")
        for row in group:
            for field in inputs:
                row[f"aggregate_residual_vs_{field}_pearson"] = _pearson(
                    [float(item[field]) for item in group], aggregate_errors)
        rows.extend(group)
    return rows


def _least_squares_scale(rows: list[dict[str, object]], candidate_id: str,
                         component: str = "aggregate") -> float:
    group = [row for row in rows if row["candidate_id"] == candidate_id]
    observed = [float(row[f"observed_{component}"]) for row in group]
    predicted = [float(row[f"predicted_{component}"]) for row in group]
    return sum(o * p for o, p in zip(observed, predicted, strict=True)) / sum(p * p for p in predicted)


def candidate_comparison_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    baseline = baseline_candidate()
    baseline_multiplier = enemy_multiplier_breakdown(baseline)["common_enemy_multiplier"]
    required_scale = _least_squares_scale(rows, baseline.candidate_id)
    result = []
    candidate_ids = list(dict.fromkeys(str(row["candidate_id"]) for row in rows))
    for candidate_id in candidate_ids:
        group = [row for row in rows if row["candidate_id"] == candidate_id]
        candidate_multiplier = float(group[0]["common_enemy_multiplier"])
        scale_change = candidate_multiplier / baseline_multiplier
        remaining_scale = required_scale / scale_change
        explained_fraction = ((scale_change - 1) / (required_scale - 1)
                              if not math.isclose(required_scale, 1.0) else float("nan"))
        candidate_scale = _least_squares_scale(rows, candidate_id)
        for component in COMPONENTS:
            errors = [float(row[f"{component}_relative_error"]) for row in group]
            ratios = [float(row[f"{component}_observed_to_predicted_ratio"]) for row in group]
            damage_errors = [float(row[f"{component}_absolute_damage_error"]) for row in group]
            component_scale = _least_squares_scale(rows, candidate_id, component)
            scaled_errors = [component_scale * float(row[f"predicted_{component}"]) /
                             float(row[f"observed_{component}"]) - 1 for row in group]
            result.append({
                "candidate_id": candidate_id, "character_level": CHARACTER_LEVEL,
                "enemy_level": group[0]["enemy_level"], "base_pyro_res": group[0]["base_pyro_res"],
                "vv_res_reduction": group[0]["vv_res_reduction"], "vv_enabled": group[0]["vv_enabled"],
                "def_multiplier": group[0]["def_multiplier"], "res_after_vv": group[0]["res_after_vv"],
                "res_multiplier": group[0]["res_multiplier"], "common_enemy_multiplier": candidate_multiplier,
                "component": component, "build_count": len(group), "mean_relative_error": mean(errors),
                "median_relative_error": median(errors), "residual_std": pstdev(errors),
                "maximum_absolute_relative_error": max(map(abs, errors)),
                "maximum_absolute_damage_error": max(damage_errors),
                "observed_to_predicted_ratio_std": pstdev(ratios),
                "component_least_squares_scale": component_scale,
                "scale_normalized_residual_std": pstdev(scaled_errors),
                "mean_component_ratio_spread": mean(float(row["component_ratio_spread"]) for row in group),
                "mean_component_ratio_relative_spread": mean(float(row["component_ratio_relative_spread"]) for row in group),
                "baseline_required_common_scale": required_scale, "candidate_h3_scale_change": scale_change,
                "remaining_unexplained_scale": remaining_scale,
                "fraction_of_required_excess_scale_explained": explained_fraction,
                "candidate_least_squares_remaining_scale": candidate_scale,
            })
    return result


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run_h3_validation(raw_root: str | Path = "data/akasha/raw",
                      output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    residuals = build_residual_rows(builds)
    comparisons = candidate_comparison_rows(residuals)
    output = Path(output_root)
    _write_csv(comparisons, output / "h3_candidate_comparison.csv")
    _write_csv(residuals, output / "h3_build_residuals.csv")
    aggregate = [row for row in comparisons if row["component"] == "aggregate"]
    return {"build_count": len(builds), "candidate_count": len(make_candidates()),
            "comparison_rows": len(comparisons), "residual_rows": len(residuals),
            "aggregate_candidates": aggregate}
