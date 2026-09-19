"""Core Model v1と分離した、Leaderboard別の経験的表示較正。"""

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev

from .hutao_models import AkashaHutaoBuild, ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_score import score_hutao_akasha


HOMA_R1_LEADERBOARD_ID = "1000004605"
HOMA_R1_WEAPON = "Staff of Homa R1"
REFERENCE_ALL_BUILD_SCALE = 1.0768838049


class UnsupportedCalibrationError(ValueError):
    """較正profileを異なるLeaderboardまたは武器へ適用しようとした。"""


@dataclass(frozen=True)
class CalibrationProfile:
    leaderboard_id: str
    weapon: str
    sample_date: str
    sample_count: int
    scale: float
    validation_error: float
    status: str

    def __post_init__(self) -> None:
        if not self.leaderboard_id or not self.weapon or not self.sample_date:
            raise ValueError("CalibrationProfileの識別情報は空にできません")
        if type(self.sample_count) is not int or self.sample_count <= 0:
            raise ValueError("sample_countは正の整数が必要です")
        if not math.isfinite(self.scale) or self.scale <= 0:
            raise ValueError("calibration scaleは正の有限値が必要です")
        if not math.isfinite(self.validation_error) or self.validation_error < 0:
            raise ValueError("validation_errorは0以上の有限値が必要です")


@dataclass(frozen=True)
class CalibratedScore:
    core_score: float
    calibrated_score: float
    profile: CalibrationProfile
    debug_breakdown: dict[str, object]


@dataclass(frozen=True)
class ComparisonConfidence:
    label: str
    relative_difference: float
    evidence_note: str


HOMA_R1_CALIBRATION = CalibrationProfile(
    leaderboard_id=HOMA_R1_LEADERBOARD_ID, weapon=HOMA_R1_WEAPON, sample_date="2026-09-13",
    sample_count=20, scale=1.0768838049202214, validation_error=0.0018819693836047147,
    status="empirical_homa_r1_calibration",
)


def calibrate_score(core_score: float, profile: CalibrationProfile, leaderboard_id: str, weapon: str) -> CalibratedScore:
    """正の共通scaleを表示値だけへ適用し、core計算には戻さない。"""
    if leaderboard_id != profile.leaderboard_id or weapon != profile.weapon:
        raise UnsupportedCalibrationError(
            f"この較正は{profile.leaderboard_id} / {profile.weapon}専用です: {leaderboard_id} / {weapon}")
    if type(core_score) not in (int, float) or not math.isfinite(core_score):
        raise ValueError("core scoreは有限の数値が必要です")
    calibrated = float(core_score) * profile.scale
    debug = {
        "core_model": "physics_based_estimate", "calibration": profile.status,
        "akasha_backend": "partially_unresolved", "H3": "unresolved",
        "absolute_score": "calibrated_estimate", "relative_ordering": "empirically_validated",
        "calibration_scale": profile.scale, "leaderboard_id": profile.leaderboard_id,
        "weapon": profile.weapon, "sample_date": profile.sample_date, "sample_count": profile.sample_count,
    }
    return CalibratedScore(float(core_score), calibrated, profile, debug)


def comparison_confidence(relative_difference: float) -> ComparisonConfidence:
    """20-build pairwise validationに基づく経験的な差の目安を返す。"""
    if type(relative_difference) not in (int, float) or not math.isfinite(relative_difference):
        raise ValueError("relative_differenceは有限の数値が必要です")
    gap = abs(float(relative_difference))
    if gap < 0.0025:
        label = "very uncertain"
        note = "0.25%未満。保存済み近接buildでは順位誤判定が多い範囲です。"
    elif gap < 0.005:
        label = "uncertain"
        note = "0.25%以上0.5%未満。保存済みvalidationでも慎重な判断が必要です。"
    elif gap < 0.01:
        label = "moderate confidence"
        note = "0.5%以上1.0%未満。近接buildより安定しますが誤判定は残ります。"
    else:
        label = "higher confidence"
        note = "1.0%以上。保存済みvalidationでは相対的に安定した範囲です。"
    return ComparisonConfidence(label, float(relative_difference), note)


def fit_common_scale(observed: list[float], predicted: list[float]) -> float:
    if len(observed) != len(predicted) or not observed:
        raise ValueError("observedとpredictedは同じ長さの非空配列が必要です")
    denominator = sum(value**2 for value in predicted)
    if denominator <= 0:
        raise ValueError("predictedの二乗和は正である必要があります")
    return sum(obs * pred for obs, pred in zip(observed, predicted, strict=True)) / denominator


def _quantile(values: list[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise ValueError("quantileには非空配列と0〜1の確率が必要です")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def leave_one_out_validation(builds: tuple[AkashaHutaoBuild, ...], config: ScenarioConfig | None = None) -> tuple[list[dict[str, object]], dict[str, object]]:
    if len(builds) < 3:
        raise ValueError("Leave-One-Out validationには3 build以上が必要です")
    if any(build.leaderboard_id != HOMA_R1_LEADERBOARD_ID for build in builds):
        raise UnsupportedCalibrationError("Homa R1 calibrationへ別Leaderboardを混在できません")
    scenario = config or ScenarioConfig()
    observed = [build.observed_result for build in builds]
    predicted = [score_hutao_akasha(build, scenario).aggregate_score for build in builds]
    full_scale = fit_common_scale(observed, predicted)
    rows = []
    for index, build in enumerate(builds):
        train_observed = observed[:index] + observed[index + 1:]
        train_predicted = predicted[:index] + predicted[index + 1:]
        scale = fit_common_scale(train_observed, train_predicted)
        calibrated = scale * predicted[index]
        relative_error = calibrated / observed[index] - 1
        rows.append({
            "leaderboard_id": build.leaderboard_id, "api_rank": build.rank,
            "train_sample_count": len(train_observed), "fitted_scale": scale,
            "observed_aggregate": observed[index], "core_predicted_aggregate": predicted[index],
            "calibrated_validation_prediction": calibrated, "validation_relative_error": relative_error,
            "validation_absolute_relative_error": abs(relative_error),
        })
    scales = [float(row["fitted_scale"]) for row in rows]
    errors = [float(row["validation_relative_error"]) for row in rows]
    absolute_errors = [abs(value) for value in errors]
    summary = {
        "method": "leave_one_out", "sample_count": len(builds), "full_sample_scale": full_scale,
        "reference_scale": REFERENCE_ALL_BUILD_SCALE, "scale_min": min(scales), "scale_max": max(scales),
        "scale_mean": mean(scales), "scale_median": median(scales), "scale_std": pstdev(scales),
        "validation_mean_relative_error": mean(errors), "validation_median_relative_error": median(errors),
        "validation_mae": mean(absolute_errors), "validation_max_absolute_error": max(absolute_errors),
        "validation_residual_std": pstdev(errors), "median_absolute_relative_error": median(absolute_errors),
        "empirical_80_interval_low": _quantile(errors, 0.10),
        "empirical_80_interval_high": _quantile(errors, 0.90),
        "empirical_90_interval_low": _quantile(errors, 0.05),
        "empirical_90_interval_high": _quantile(errors, 0.95),
        "uncertainty_description": "保存済みvalidation buildに対する経験的誤差",
    }
    return rows, summary


def write_validation_csv(rows: list[dict[str, object]], path: str | Path) -> None:
    if not rows:
        raise ValueError("保存するvalidation rowがありません")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(output)


def run_homa_calibration_validation(raw_root: str | Path = "data/akasha/raw",
                                    output_path: str | Path = "data/akasha/homa_calibration_loo.csv") -> dict[str, object]:
    builds = load_hutao_builds(raw_root, HOMA_R1_LEADERBOARD_ID)
    rows, summary = leave_one_out_validation(builds)
    write_validation_csv(rows, output_path)
    return {"rows": rows, "summary": summary}
