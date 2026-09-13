"""共通scaleを除いたAkasha build依存残差を診断する。"""

import csv
import math
from dataclasses import replace
from pathlib import Path
from statistics import mean, pstdev

from .h1_validation import ARTIFACT_HP_BY_UID, E_SKILL_RATIOS
from .hutao_damage import DISPLAYED_LEVEL_10_TALENTS
from .hutao_models import AkashaHutaoBuild, ScenarioConfig, TalentMultipliers
from .hutao_raw import load_hutao_builds
from .hutao_score import score_hutao_akasha
from .ranking_validation import NEARBY_THRESHOLDS, _descending_ranks, _pearson


BASE_ATK_CANDIDATES = {"raw_internal_714.5089773": 714.5089773, "displayed_714": 714.0}


def _spearman(xs: list[float], ys: list[float]) -> float:
    return _pearson(_descending_ranks(xs), _descending_ranks(ys))


def _common_scale(observed: list[float], predicted: list[float]) -> float:
    return sum(obs * pred for obs, pred in zip(observed, predicted, strict=True)) / sum(pred**2 for pred in predicted)


def _hp_inputs(build: AkashaHutaoBuild) -> tuple[float, float]:
    artifacts = ARTIFACT_HP_BY_UID[build.uid or ""]
    return sum(item.hp_pct for item in artifacts), sum(item.flat_hp for item in artifacts)


def residual_rows(builds: tuple[AkashaHutaoBuild, ...], config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    scenario = config or ScenarioConfig()
    predicted = [score_hutao_akasha(build, scenario).aggregate_score for build in builds]
    observed = [build.observed_result for build in builds]
    scale = _common_scale(observed, predicted)
    rows = []
    for build, obs, pred in zip(builds, observed, predicted, strict=True):
        result = score_hutao_akasha(build, scenario)
        debug = result.debug_breakdown
        hp_pct, flat_hp = _hp_inputs(build)
        e_bonus = float(debug["hutao_e_atk"])
        final_atk = float(debug["final_atk"])
        rows.append({
            "leaderboard_id": build.leaderboard_id, "api_rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5,
            "artifact_set": "shimenawa_4pc" if build.has_shimenawa_4pc else "crimson_witch_4pc",
            "max_hp": build.max_hp, "raw_atk": build.sheet_atk, "e_atk_bonus": e_bonus,
            "artifact_hp_pct_display_reconstruction": hp_pct,
            "artifact_flat_hp_display_reconstruction": flat_hp, "artifact_em": build.elemental_mastery,
            "crit_rate": build.crit_rate, "crit_dmg": build.crit_dmg,
            "pyro_dmg_bonus": build.pyro_dmg_bonus, "total_crit_multiplier": debug["crit_multiplier"],
            "max_hp_div_raw_atk": build.max_hp / build.sheet_atk,
            "e_bonus_div_final_atk": e_bonus / final_atk, "final_atk": final_atk,
            "predicted_aggregate": pred, "observed_aggregate": obs, "diagnostic_common_scale": scale,
            "observed_div_predicted": obs / pred,
            "scale_removed_ratio_residual": obs / pred - scale,
            "scaled_prediction_relative_error": scale * pred / obs - 1,
        })
    return rows


CORRELATION_FIELDS = (
    "max_hp", "raw_atk", "e_atk_bonus", "artifact_hp_pct_display_reconstruction",
    "artifact_flat_hp_display_reconstruction", "artifact_em", "crit_rate", "crit_dmg",
    "pyro_dmg_bonus", "total_crit_multiplier", "max_hp_div_raw_atk", "e_bonus_div_final_atk",
    "predicted_aggregate", "observed_aggregate",
)


def correlation_rows(rows: list[dict[str, object]], scope: str = "all_20") -> list[dict[str, object]]:
    selected = rows if scope == "all_20" else [row for row in rows if row["artifact_set"] == "crimson_witch_4pc"]
    residuals = [float(row["scale_removed_ratio_residual"]) for row in selected]
    return [{
        "scope": scope, "build_count": len(selected), "input": field,
        "pearson": _pearson([float(row[field]) for row in selected], residuals),
        "spearman": _spearman([float(row[field]) for row in selected], residuals),
    } for field in CORRELATION_FIELDS]


def _candidate_metrics(builds: tuple[AkashaHutaoBuild, ...], predicted: list[float]) -> dict[str, object]:
    observed = [build.observed_result for build in builds]
    scale = _common_scale(observed, predicted)
    residuals = [obs / pred - scale for obs, pred in zip(observed, predicted, strict=True)]
    correct = 0
    total = 0
    close_correct = {threshold: 0 for threshold in NEARBY_THRESHOLDS}
    close_total = {threshold: 0 for threshold in NEARBY_THRESHOLDS}
    for left in range(len(builds)):
        for right in range(left + 1, len(builds)):
            observed_difference = observed[left] - observed[right]
            predicted_difference = predicted[left] - predicted[right]
            if observed_difference == 0:
                continue
            is_correct = (observed_difference > 0) == (predicted_difference > 0)
            correct += is_correct
            total += 1
            gap = abs(observed_difference) / max(abs(observed[left]), abs(observed[right]))
            for threshold in NEARBY_THRESHOLDS:
                if gap < threshold:
                    close_total[threshold] += 1
                    close_correct[threshold] += is_correct
    metrics = {
        "diagnostic_common_scale": scale, "scale_removed_residual_std": pstdev(residuals),
        "pearson": _pearson(observed, predicted),
        "spearman": _pearson(_descending_ranks(observed), _descending_ranks(predicted)),
        "pairwise_ordering_accuracy": correct / total,
    }
    for threshold in NEARBY_THRESHOLDS:
        key = f"under_{threshold * 100:g}_percent"
        metrics[f"{key}_pair_count"] = close_total[threshold]
        metrics[f"{key}_accuracy"] = close_correct[threshold] / close_total[threshold] if close_total[threshold] else None
    return metrics


def _talent_override(skill_ratio: float) -> TalentMultipliers:
    baseline = DISPLAYED_LEVEL_10_TALENTS
    return TalentMultipliers(baseline.n1, baseline.charged, skill_ratio,
                             baseline.burst_normal_hp, baseline.burst_low_hp)


def candidate_comparison_rows(builds: tuple[AkashaHutaoBuild, ...],
                              base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    scenario = base_config or ScenarioConfig()
    candidates: list[tuple[str, str, ScenarioConfig, float | None]] = []
    for level, ratio in E_SKILL_RATIOS.items():
        config = replace(scenario, skill_talent_level=level, talent_multiplier_override=_talent_override(ratio))
        candidates.append(("e_talent_level", f"e_lv{level}", config, None))
    for name, base_atk in BASE_ATK_CANDIDATES.items():
        candidates.append(("base_atk", name, scenario, base_atk))

    rows = []
    for candidate_kind, candidate_name, config, base_atk in candidates:
        for scope in ("all_20", "crimson_witch_19"):
            scoped_builds = builds if scope == "all_20" else tuple(build for build in builds if not build.has_shimenawa_4pc)
            candidate_builds = tuple(replace(build, base_atk=base_atk) if base_atk is not None else build
                                     for build in scoped_builds)
            predicted = [score_hutao_akasha(build, config).aggregate_score for build in candidate_builds]
            metrics = _candidate_metrics(scoped_builds, predicted)
            rows.append({
                "candidate_kind": candidate_kind, "candidate": candidate_name, "scope": scope,
                "build_count": len(scoped_builds),
                "skill_talent_level": config.skill_talent_level if candidate_kind == "e_talent_level" else 10,
                "skill_hp_to_atk_ratio": (config.talent_multiplier_override.skill_hp_to_atk
                                           if config.talent_multiplier_override else E_SKILL_RATIOS[10]),
                "base_atk": base_atk if base_atk is not None else 714.5089773, **metrics,
            })
    return rows


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run_build_residual_validation(raw_root: str | Path = "data/akasha/raw",
                                  output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    rows = residual_rows(builds)
    candidates = candidate_comparison_rows(builds)
    output = Path(output_root)
    _write_csv(rows, output / "build_dependent_residuals.csv")
    _write_csv(candidates, output / "e_candidate_ranking_comparison.csv")
    return {
        "build_count": len(rows), "common_scale": rows[0]["diagnostic_common_scale"],
        "scale_removed_residual_std": pstdev(float(row["scale_removed_ratio_residual"]) for row in rows),
        "correlations_all": correlation_rows(rows, "all_20"),
        "correlations_crimson_witch": correlation_rows(rows, "crimson_witch_19"),
        "candidate_comparison": candidates,
    }
