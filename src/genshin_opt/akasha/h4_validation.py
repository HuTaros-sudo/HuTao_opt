"""H4のexternal EMとVaporize入力境界をN1比で診断する。"""

import csv
from dataclasses import replace
from pathlib import Path
from statistics import mean, median, pstdev

from .hutao_models import AkashaHutaoBuild, ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_score import score_hutao_akasha
from .hutao_validation import relative_error


EXTERNAL_EM_CANDIDATES = {
    "em_0": (0.0, "none"), "em_100_elegy": (100.0, "Elegy"),
    "em_220_elegy_instructor": (220.0, "Elegy + Instructor"),
    "em_300_elegy_kazuha_c2": (300.0, "Elegy + Kazuha C2"),
    "em_420_all": (420.0, "Elegy + Instructor + Kazuha C2"),
}


def _candidate_rows(builds: tuple[AkashaHutaoBuild, ...], configs: dict[str, ScenarioConfig],
                    stage: str) -> list[dict[str, object]]:
    rows = []
    for candidate_id, config in configs.items():
        group = []
        for build in builds:
            result = score_hutao_akasha(build, config)
            observed_n1_ratio = build.observed.n1_vape / build.observed.n1_non_vape
            predicted_n1_ratio = result.n1_vape_avg / result.n1_non_vape_avg
            observed_ca_ratio = build.observed.ca_vape / build.observed.n1_non_vape
            predicted_ca_ratio = result.ca_vape_avg / result.n1_non_vape_avg
            observed_q_ratio = build.observed.q_vape / build.observed.n1_non_vape
            predicted_q_ratio = result.q_vape_avg / result.n1_non_vape_avg
            row = {
                "stage": stage, "candidate_id": candidate_id, "leaderboard_id": build.leaderboard_id,
                "rank": build.rank, "uid": build.uid, "build_md5": build.build_md5,
                "raw_stats_elemental_mastery": build.elemental_mastery,
                "artifact_em_input": build.elemental_mastery, "character_fixed_em": 0.0,
                "weapon_fixed_em": 0.0, "external_em_added": config.hutao_external_em,
                "final_reaction_em": build.elemental_mastery + config.hutao_external_em,
                "elegy_em": 100.0 if config.hutao_external_em in (100, 220, 300, 420) else 0.0,
                "instructor_em": 120.0 if config.hutao_external_em in (220, 420) else 0.0,
                "kazuha_c2_em": 200.0 if config.hutao_external_em in (300, 420) else 0.0,
                "has_crimson_witch_4pc": build.has_crimson_witch_4pc,
                "crimson_witch_reaction_bonus_enabled": config.apply_crimson_witch_vape_bonus,
                "crimson_witch_reaction_bonus": (config.crimson_witch_vape_bonus
                                                  if build.has_crimson_witch_4pc and config.apply_crimson_witch_vape_bonus else 0.0),
                "observed_n1_vape_to_non_vape_ratio": observed_n1_ratio,
                "predicted_n1_vape_to_non_vape_ratio": predicted_n1_ratio,
                "n1_ratio_error": predicted_n1_ratio - observed_n1_ratio,
                "n1_ratio_relative_error": relative_error(observed_n1_ratio, predicted_n1_ratio),
                "observed_ca_vape_to_n1_non_vape_ratio": observed_ca_ratio,
                "predicted_ca_vape_to_n1_non_vape_ratio": predicted_ca_ratio,
                "ca_ratio_relative_error": relative_error(observed_ca_ratio, predicted_ca_ratio),
                "observed_q_vape_to_n1_non_vape_ratio": observed_q_ratio,
                "predicted_q_vape_to_n1_non_vape_ratio": predicted_q_ratio,
                "q_ratio_relative_error": relative_error(observed_q_ratio, predicted_q_ratio),
                "n1_non_vape_relative_error": relative_error(build.observed.n1_non_vape, result.n1_non_vape_avg),
                "n1_vape_relative_error": relative_error(build.observed.n1_vape, result.n1_vape_avg),
                "ca_vape_relative_error": relative_error(build.observed.ca_vape, result.ca_vape_avg),
                "q_vape_relative_error": relative_error(build.observed.q_vape, result.q_vape_avg),
                "aggregate_relative_error": relative_error(build.observed_result, result.aggregate_score),
                "vaporize_multiplier": result.debug_breakdown["vaporize_multiplier"],
            }
            group.append(row)
        metric_columns = ("n1_ratio_relative_error", "ca_ratio_relative_error", "q_ratio_relative_error",
                          "aggregate_relative_error")
        for metric in metric_columns:
            values = [float(row[metric]) for row in group]
            for row in group:
                row[f"{metric}_mean"] = mean(values)
                row[f"{metric}_median"] = median(values)
                row[f"{metric}_std"] = pstdev(values)
                row[f"{metric}_maximum_absolute"] = max(map(abs, values))
        rows.extend(group)
    return rows


def em_candidate_rows(builds: tuple[AkashaHutaoBuild, ...], base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    baseline = base_config or ScenarioConfig()
    configs = {candidate_id: replace(baseline, hutao_external_em=em, apply_crimson_witch_vape_bonus=True)
               for candidate_id, (em, _) in EXTERNAL_EM_CANDIDATES.items()}
    return _candidate_rows(builds, configs, "external_em_with_crimson_bonus")


def vape_ratio_residual_rows(builds: tuple[AkashaHutaoBuild, ...],
                             base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    baseline = base_config or ScenarioConfig()
    configs = {}
    for candidate_id, (em, _) in EXTERNAL_EM_CANDIDATES.items():
        configs[f"{candidate_id}_cw_on"] = replace(
            baseline, hutao_external_em=em, apply_crimson_witch_vape_bonus=True)
        configs[f"{candidate_id}_cw_off"] = replace(
            baseline, hutao_external_em=em, apply_crimson_witch_vape_bonus=False)
    return _candidate_rows(builds, configs, "external_em_x_crimson_reaction_bonus")


def candidate_summaries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries = []
    for candidate_id in dict.fromkeys(str(row["candidate_id"]) for row in rows):
        group = [row for row in rows if row["candidate_id"] == candidate_id]
        first = group[0]
        summaries.append({
            "candidate_id": candidate_id, "build_count": len(group),
            "external_em": first["external_em_added"],
            "crimson_witch_reaction_bonus_enabled": first["crimson_witch_reaction_bonus_enabled"],
            "n1_ratio_mean_error": first["n1_ratio_relative_error_mean"],
            "n1_ratio_median_error": first["n1_ratio_relative_error_median"],
            "n1_ratio_std": first["n1_ratio_relative_error_std"],
            "n1_ratio_maximum_absolute_error": first["n1_ratio_relative_error_maximum_absolute"],
            "ca_ratio_mean_error": first["ca_ratio_relative_error_mean"],
            "q_ratio_mean_error": first["q_ratio_relative_error_mean"],
            "aggregate_mean_error": first["aggregate_relative_error_mean"],
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


def run_h4_validation(raw_root: str | Path = "data/akasha/raw",
                      output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    em_rows = em_candidate_rows(builds)
    ratio_rows = vape_ratio_residual_rows(builds)
    output = Path(output_root)
    _write_csv(candidate_summaries(em_rows), output / "h4_em_candidates.csv")
    _write_csv(ratio_rows, output / "h4_vape_ratio_residuals.csv")
    return {
        "build_count": len(builds), "em_candidates": candidate_summaries(em_rows),
        "all_candidates": candidate_summaries(ratio_rows),
        "raw_em_min": min(build.elemental_mastery for build in builds),
        "raw_em_max": max(build.elemental_mastery for build in builds),
    }
