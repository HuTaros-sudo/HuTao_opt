"""N1 non-vape観測値からrequired final ATKとrequired E寄与を逆算する診断。"""

import csv
import math
from dataclasses import replace
from pathlib import Path
from statistics import mean, pstdev

from .h1_validation import E_SKILL_RATIOS
from .hutao_damage import (DISPLAYED_LEVEL_10_TALENTS, HOMA_BASE_ATK_FROM_HP,
                           HOMA_LOW_HP_EXTRA_ATK_FROM_HP)
from .hutao_models import AkashaHutaoBuild, ScenarioConfig, TalentMultipliers
from .hutao_raw import load_hutao_builds
from .hutao_score import score_hutao_akasha


E_LEVELS = (9, 10, 11, 13)


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("相関には同じ長さの2要素以上が必要です")
    x_mean, y_mean = mean(xs), mean(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(sum((x - x_mean) ** 2 for x in xs) * sum((y - y_mean) ** 2 for y in ys))
    return numerator / denominator if denominator else float("nan")


def _talent_override(skill_ratio: float) -> TalentMultipliers:
    talents = DISPLAYED_LEVEL_10_TALENTS
    return TalentMultipliers(talents.n1, talents.charged, skill_ratio,
                             talents.burst_normal_hp, talents.burst_low_hp)


def required_final_atk_rows(builds: tuple[AkashaHutaoBuild, ...],
                            config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    """N1 non-vapeのATK以外の乗算項を固定し、必要final ATKを代数的に解く。"""
    scenario = config or ScenarioConfig()
    rows = []
    for build in builds:
        score = score_hutao_akasha(build, scenario)
        debug = score.debug_breakdown
        component = debug["components"]["n1_non_vape"]
        fixed_multiplier = (float(component["talent_multiplier"]) * float(component["damage_bonus_multiplier"])
                            * float(component["crit_multiplier"]) * float(component["def_multiplier"])
                            * float(component["res_multiplier"]) * float(component["reaction_multiplier"]))
        if fixed_multiplier <= 0:
            raise ValueError("N1 non-vapeの固定乗算項は正である必要があります")
        required_final = build.observed.n1_non_vape / fixed_multiplier
        normalized = float(debug["normalized_precombat_atk"])
        external = float(debug["external_combat_atk_bonus"])
        predicted_e = float(debug["hutao_e_atk"])
        required_e = required_final - normalized - external
        max_hp = float(debug["max_hp"])
        homa_base = max_hp * HOMA_BASE_ATK_FROM_HP
        homa_low_hp = max_hp * HOMA_LOW_HP_EXTRA_ATK_FROM_HP if scenario.low_hp_for_homa else 0.0
        rows.append({
            "leaderboard_id": build.leaderboard_id, "api_rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5, "artifact_set": "shimenawa_4pc" if build.has_shimenawa_4pc else "crimson_witch_4pc",
            "raw_max_hp": max_hp, "normalized_precombat_atk": normalized,
            "external_combat_atk_bonus": external, "predicted_e_atk_bonus": predicted_e,
            "required_e_atk_bonus": required_e, "required_minus_predicted_e": required_e - predicted_e,
            "required_div_predicted_e": required_e / predicted_e,
            "required_e_div_max_hp": required_e / max_hp, "predicted_final_atk": float(debug["final_atk"]),
            "required_final_atk": required_final, "observed_n1_non_vape": build.observed.n1_non_vape,
            "predicted_n1_non_vape": score.n1_non_vape_avg, "fixed_non_atk_multiplier": fixed_multiplier,
            "homa_base_hp_atk": homa_base, "homa_low_hp_atk": homa_low_hp,
            "homa_total_hp_atk": homa_base + homa_low_hp,
            "homa_base_coefficient": HOMA_BASE_ATK_FROM_HP,
            "homa_low_hp_coefficient": HOMA_LOW_HP_EXTRA_ATK_FROM_HP if scenario.low_hp_for_homa else 0.0,
            "predicted_e_coefficient": E_SKILL_RATIOS[10],
        })
    return rows


def linear_diagnostic(rows: list[dict[str, object]]) -> dict[str, float]:
    xs = [float(row["raw_max_hp"]) for row in rows]
    ys = [float(row["required_e_atk_bonus"]) for row in rows]
    x_mean, y_mean = mean(xs), mean(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True)) / denominator
    intercept = y_mean - slope * x_mean
    residuals = [y - (slope * x + intercept) for x, y in zip(xs, ys, strict=True)]
    total = sum((y - y_mean) ** 2 for y in ys)
    return {"slope": slope, "intercept": intercept, "r_squared": 1 - sum(value**2 for value in residuals) / total,
            "residual_std": pstdev(residuals)}


def _pairwise_ordering_accuracy(observed: list[float], predicted: list[float]) -> float:
    correct = total = 0
    for left in range(len(observed)):
        for right in range(left + 1, len(observed)):
            if observed[left] == observed[right]:
                continue
            correct += (observed[left] > observed[right]) == (predicted[left] > predicted[right])
            total += 1
    return correct / total if total else float("nan")


def e_candidate_rows(builds: tuple[AkashaHutaoBuild, ...], required_rows: list[dict[str, object]],
                     config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    scenario = config or ScenarioConfig()
    if len(builds) != len(required_rows):
        raise ValueError("buildとrequired rowの件数が一致しません")
    rows = []
    for level in E_LEVELS:
        ratio = E_SKILL_RATIOS[level]
        candidate_config = replace(scenario, skill_talent_level=level,
                                   talent_multiplier_override=_talent_override(ratio))
        for build, required in zip(builds, required_rows, strict=True):
            score = score_hutao_akasha(build, candidate_config)
            candidate_e = float(score.debug_breakdown["hutao_e_atk"])
            rows.append({
                "candidate_level": level, "candidate_ratio": ratio, "api_rank": build.rank,
                "uid": build.uid, "raw_max_hp": build.max_hp,
                "required_e_atk_bonus": required["required_e_atk_bonus"],
                "candidate_e_atk_bonus": candidate_e,
                "required_minus_candidate_e": float(required["required_e_atk_bonus"]) - candidate_e,
                "observed_n1_non_vape": build.observed.n1_non_vape,
                "predicted_n1_non_vape": score.n1_non_vape_avg,
            })
    return rows


def e_candidate_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries = []
    for level in E_LEVELS:
        selected = [row for row in rows if row["candidate_level"] == level]
        residuals = [float(row["required_minus_candidate_e"]) for row in selected]
        max_hps = [float(row["raw_max_hp"]) for row in selected]
        observed = [float(row["observed_n1_non_vape"]) for row in selected]
        predicted = [float(row["predicted_n1_non_vape"]) for row in selected]
        summaries.append({
            "candidate_level": level, "candidate_ratio": E_SKILL_RATIOS[level],
            "mean_required_minus_candidate_e": mean(residuals),
            "mean_absolute_required_minus_candidate_e": mean(abs(value) for value in residuals),
            "build_dependent_residual_std": pstdev(residuals),
            "residual_vs_max_hp_pearson": _pearson(max_hps, residuals),
            "n1_pairwise_ordering_accuracy": _pairwise_ordering_accuracy(observed, predicted),
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


def run_required_e_validation(raw_root: str | Path = "data/akasha/raw",
                              output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    required = required_final_atk_rows(builds)
    candidates = e_candidate_rows(builds, required)
    output = Path(output_root)
    _write_csv(required, output / "required_final_atk.csv")
    _write_csv(candidates, output / "required_e_contribution.csv")
    residuals = [float(row["required_minus_predicted_e"]) for row in required]
    max_hps = [float(row["raw_max_hp"]) for row in required]
    homa = [float(row["homa_total_hp_atk"]) for row in required]
    predicted_e = [float(row["predicted_e_atk_bonus"]) for row in required]
    return {
        "build_count": len(required), "required_rows": required,
        "linear_diagnostic": linear_diagnostic(required), "candidate_summary": e_candidate_summary(candidates),
        "required_residual_vs_max_hp": _pearson(max_hps, residuals),
        "required_residual_vs_homa": _pearson(homa, residuals),
        "required_residual_vs_predicted_e": _pearson(predicted_e, residuals),
    }

