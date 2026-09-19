"""既知のATK buffとAkasha raw ATK境界を離散候補だけで監査する。"""

import csv
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, pstdev

from .h5_validation import (ARTIFACT_ATK_BY_UID, MILLENNIAL_MOVEMENT_ATK_PCT,
                            PYRO_RESONANCE_ATK_PCT, artifact_set_atk_pct, reconstruct_atk_stages)
from .hutao_damage import HOMA_BASE_ATK_FROM_HP, HOMA_LOW_HP_EXTRA_ATK_FROM_HP
from .hutao_models import AkashaHutaoBuild, ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_score import score_hutao_akasha
from .ranking_validation import _descending_ranks, _pearson
from .required_e_validation import required_final_atk_rows


NEARBY_THRESHOLDS = (0.001, 0.0025, 0.005)


@dataclass(frozen=True)
class AtkBuffCandidate:
    name: str
    description: str
    raw_millennial_pct: float = 0.0
    raw_pyro_pct: float = 0.0
    raw_amber_pct: float = 0.0
    independent_millennial_pct: float = 0.0
    independent_pyro_pct: float = 0.0
    independent_amber_pct: float = 0.0
    rules_status: str = "diagnostic"

    @property
    def raw_added_pct(self) -> float:
        return self.raw_millennial_pct + self.raw_pyro_pct + self.raw_amber_pct


ATK_BUFF_CANDIDATES = (
    AtkBuffCandidate("current_mm20", "現行baseline: raw ATK + Millennial 20%", .20,
                     independent_millennial_pct=.20, rules_status="supported_boundary_baseline"),
    AtkBuffCandidate("pyro25_only", "raw ATK + Pyro Resonance 25%", raw_pyro_pct=.25,
                     independent_pyro_pct=.25),
    AtkBuffCandidate("mm20_pyro25", "raw ATK + Millennial 20% + Pyro Resonance 25%", .20, .25,
                     independent_millennial_pct=.20, independent_pyro_pct=.25,
                     rules_status="numerical_candidate_but_raw_pyro_double_count"),
    AtkBuffCandidate("mm20_amber15", "raw ATK + Millennial 20% + Amber C6 15%", .20,
                     raw_amber_pct=.15, independent_millennial_pct=.20, independent_amber_pct=.15),
    AtkBuffCandidate("pyro25_amber15", "raw ATK + Pyro Resonance 25% + Amber C6 15%", raw_pyro_pct=.25,
                     raw_amber_pct=.15, independent_pyro_pct=.25, independent_amber_pct=.15),
    AtkBuffCandidate("mm20_pyro25_amber15", "raw ATK + Millennial 20% + Pyro 25% + Amber C6 15%", .20, .25, .15,
                     .20, .25, .15),
    AtkBuffCandidate("millennial40_rejected", "raw ATK + Elegy 20% + Freedom-Sworn 20%", .40,
                     independent_millennial_pct=.40,
                     rules_status="rejected_same_millennial_effect_does_not_stack"),
    AtkBuffCandidate("elegy20_only", "raw ATK + Elegy Millennial 20%", .20,
                     independent_millennial_pct=.20,
                     rules_status="same_atk_result_as_one_millennial_source"),
    AtkBuffCandidate("freedom20_only", "raw ATK + Freedom-Sworn Millennial 20%", .20,
                     independent_millennial_pct=.20,
                     rules_status="same_atk_result_as_one_millennial_source"),
)


def _spearman(xs: list[float], ys: list[float]) -> float:
    return _pearson(_descending_ranks(xs), _descending_ranks(ys))


def _pair_accuracy(observed: list[float], predicted: list[float], threshold: float | None = None) -> tuple[int, float | None]:
    correct = total = 0
    for left in range(len(observed)):
        for right in range(left + 1, len(observed)):
            difference = observed[left] - observed[right]
            if difference == 0:
                continue
            relative_gap = abs(difference) / max(abs(observed[left]), abs(observed[right]))
            if threshold is not None and relative_gap >= threshold:
                continue
            predicted_difference = predicted[left] - predicted[right]
            correct += (difference > 0) == (predicted_difference > 0)
            total += 1
    return total, correct / total if total else None


def _independent_sheet_atk(build: AkashaHutaoBuild, candidate: AtkBuffCandidate) -> float:
    artifact = ARTIFACT_ATK_BY_UID[build.uid or ""]
    homa_pct = HOMA_BASE_ATK_FROM_HP + HOMA_LOW_HP_EXTRA_ATK_FROM_HP
    precombat_pct = (artifact.artifact_atk_pct + artifact_set_atk_pct(build) + PYRO_RESONANCE_ATK_PCT
                     + candidate.independent_pyro_pct)
    return build.base_atk * (1 + precombat_pct) + artifact.artifact_flat_atk + build.max_hp * homa_pct


def _candidate_scores(builds: tuple[AkashaHutaoBuild, ...], candidate: AtkBuffCandidate,
                      base_config: ScenarioConfig) -> tuple[list[object], list[object]]:
    raw_config = replace(base_config, external_atk_pct=candidate.raw_millennial_pct + candidate.raw_pyro_pct,
                         amber_c6_atk_pct=candidate.raw_amber_pct)
    independent_config = replace(base_config, external_atk_pct=candidate.independent_millennial_pct,
                                 amber_c6_atk_pct=candidate.independent_amber_pct)
    raw_scores = [score_hutao_akasha(build, raw_config) for build in builds]
    independent_scores = []
    for build in builds:
        reconstructed = replace(build, sheet_atk=_independent_sheet_atk(build, candidate))
        independent_scores.append(score_hutao_akasha(reconstructed, independent_config))
    return raw_scores, independent_scores


def candidate_comparison_rows(builds: tuple[AkashaHutaoBuild, ...], required: list[dict[str, object]],
                              base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    scenario = base_config or ScenarioConfig()
    observed_n1 = [build.observed.n1_non_vape for build in builds]
    observed_aggregate = [build.observed_result for build in builds]
    rows = []
    for candidate in ATK_BUFF_CANDIDATES:
        raw_scores, independent_scores = _candidate_scores(builds, candidate, scenario)
        raw_final = [float(score.debug_breakdown["final_atk"]) for score in raw_scores]
        independent_final = [float(score.debug_breakdown["final_atk"]) for score in independent_scores]
        required_final = [float(row["required_final_atk"]) for row in required]
        gaps = [needed - predicted for needed, predicted in zip(required_final, raw_final, strict=True)]
        additions = [build.base_atk * candidate.raw_added_pct for build in builds]
        predicted_n1 = [score.n1_non_vape_avg for score in raw_scores]
        predicted_aggregate = [score.aggregate_score for score in raw_scores]
        _, n1_accuracy = _pair_accuracy(observed_n1, predicted_n1)
        _, aggregate_accuracy = _pair_accuracy(observed_aggregate, predicted_aggregate)
        row = {
            "candidate": candidate.name, "description": candidate.description,
            "rules_status": candidate.rules_status, "configured_total_external_atk_pct": candidate.raw_added_pct,
            "increment_vs_current_atk_pct": candidate.raw_added_pct - scenario.external_atk_pct,
            "raw_millennial_pct": candidate.raw_millennial_pct, "raw_pyro_pct": candidate.raw_pyro_pct,
            "raw_amber_pct": candidate.raw_amber_pct, "mean_candidate_bundle_atk": mean(additions),
            "mean_increment_vs_current_atk": mean(build.base_atk * (candidate.raw_added_pct - scenario.external_atk_pct) for build in builds),
            "mean_required_minus_candidate_atk": mean(gaps), "min_required_minus_candidate_atk": min(gaps),
            "max_required_minus_candidate_atk": max(gaps), "required_gap_std": pstdev(gaps),
            "required_gap_vs_max_hp_pearson": _pearson([build.max_hp for build in builds], gaps),
            "required_gap_vs_max_hp_spearman": _spearman([build.max_hp for build in builds], gaps),
            "n1_non_vape_ordering_accuracy": n1_accuracy,
            "aggregate_ordering_accuracy": aggregate_accuracy,
            "independent_minus_raw_final_atk_mean": mean(i - r for i, r in zip(independent_final, raw_final, strict=True)),
            "independent_minus_raw_final_atk_max_abs": max(abs(i - r) for i, r in zip(independent_final, raw_final, strict=True)),
        }
        for threshold in NEARBY_THRESHOLDS:
            count, accuracy = _pair_accuracy(observed_aggregate, predicted_aggregate, threshold)
            label = f"{threshold * 100:g}_percent"
            row[f"near_{label}_pair_count"] = count
            row[f"near_{label}_accuracy"] = accuracy
        rows.append(row)
    return rows


def constant_residual_rows(builds: tuple[AkashaHutaoBuild, ...], required: list[dict[str, object]],
                           base_config: ScenarioConfig | None = None) -> tuple[list[dict[str, object]], dict[str, float]]:
    scenario = base_config or ScenarioConfig()
    baseline = next(item for item in ATK_BUFF_CANDIDATES if item.name == "current_mm20")
    raw_scores, independent_scores = _candidate_scores(builds, baseline, scenario)
    actual_missing = [float(row["required_final_atk"]) - float(score.debug_breakdown["final_atk"])
                      for row, score in zip(required, raw_scores, strict=True)]
    predicted_final = [float(score.debug_breakdown["final_atk"]) for score in raw_scores]
    required_final = [float(row["required_final_atk"]) for row in required]
    h3_scale = sum(req * pred for req, pred in zip(required_final, predicted_final, strict=True)) / sum(value**2 for value in predicted_final)
    h3_missing = [(h3_scale - 1) * value for value in predicted_final]
    rows = []
    for build, needed, raw_score, independent_score, missing, expected_h3 in zip(
            builds, required, raw_scores, independent_scores, actual_missing, h3_missing, strict=True):
        stages = reconstruct_atk_stages(build)
        artifact = ARTIFACT_ATK_BY_UID[build.uid or ""]
        raw_final = float(raw_score.debug_breakdown["final_atk"])
        independent_final = float(independent_score.debug_breakdown["final_atk"])
        rows.append({
            "leaderboard_id": build.leaderboard_id, "api_rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5, "raw_max_hp": build.max_hp, "base_atk": build.base_atk,
            "raw_stats_atk": build.sheet_atk, "artifact_atk_pct": artifact.artifact_atk_pct,
            "artifact_flat_atk": artifact.artifact_flat_atk, "artifact_set_atk_pct": artifact_set_atk_pct(build),
            "homa_base_hp_atk": stages["homa_base_hp_atk"], "homa_low_hp_atk": stages["homa_low_hp_atk"],
            "independent_pyro_resonance_atk": build.base_atk * PYRO_RESONANCE_ATK_PCT,
            "independent_millennial_atk": build.base_atk * MILLENNIAL_MOVEMENT_ATK_PCT,
            "independent_raw_equivalent_atk": stages["raw_atk_reconstructed"],
            "independent_raw_minus_observed_raw": stages["raw_atk_reconstruction_error"],
            "predicted_e_atk_bonus": needed["predicted_e_atk_bonus"],
            "raw_based_predicted_final_atk": raw_final, "independent_predicted_final_atk": independent_final,
            "independent_minus_raw_final_atk": independent_final - raw_final,
            "required_final_atk": needed["required_final_atk"], "actual_missing_atk": missing,
            "diagnostic_h3_common_scale": h3_scale, "h3_only_expected_missing_atk": expected_h3,
        })
    summary = {
        "actual_missing_min": min(actual_missing), "actual_missing_max": max(actual_missing),
        "actual_missing_std": pstdev(actual_missing), "h3_common_scale": h3_scale,
        "h3_expected_missing_min": min(h3_missing), "h3_expected_missing_max": max(h3_missing),
        "h3_expected_missing_std": pstdev(h3_missing),
        "missing_vs_predicted_final_pearson": _pearson(predicted_final, actual_missing),
        "missing_vs_predicted_final_spearman": _spearman(predicted_final, actual_missing),
        "missing_vs_raw_atk_pearson": _pearson([build.sheet_atk for build in builds], actual_missing),
        "missing_vs_raw_atk_spearman": _spearman([build.sheet_atk for build in builds], actual_missing),
        "missing_vs_max_hp_pearson": _pearson([build.max_hp for build in builds], actual_missing),
        "missing_vs_max_hp_spearman": _spearman([build.max_hp for build in builds], actual_missing),
        "independent_minus_raw_mean": mean(float(row["independent_minus_raw_final_atk"]) for row in rows),
        "independent_minus_raw_max_abs": max(abs(float(row["independent_minus_raw_final_atk"])) for row in rows),
    }
    return rows, summary


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run_atk_buff_validation(raw_root: str | Path = "data/akasha/raw",
                            output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    missing = [build.uid for build in builds if build.uid not in ARTIFACT_ATK_BY_UID]
    if missing:
        raise ValueError(f"聖遺物ATK内訳がないbuildです: {missing}")
    required = required_final_atk_rows(builds)
    candidates = candidate_comparison_rows(builds, required)
    residuals, residual_summary = constant_residual_rows(builds, required)
    output = Path(output_root)
    _write_csv(candidates, output / "atk_buff_candidates.csv")
    _write_csv(residuals, output / "constant_atk_residuals.csv")
    return {"build_count": len(builds), "candidate_rows": candidates, "residual_summary": residual_summary}
