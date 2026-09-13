"""optimizerとUIから使うHu Tao Akasha推定スコアの公開API。"""

from collections import Counter
from dataclasses import asdict

from ..models import Artifact, Slot, Stat
from ..stats import aggregate_current_stats
from ..validation import validate_artifact
from .hutao_damage import (CRIMSON_WITCH_2PC_PYRO_BONUS, HOMA_BASE_ATK_FROM_HP,
                           HOMA_BASE_HP_PCT, HOMA_LOW_HP_EXTRA_ATK_FROM_HP,
                           character_base_stats)
from .hutao_engine import debug_build, predict_components
from .hutao_models import (AkashaScoreResult, HypothesisState, HypothesisStatus,
                           HutaoAkashaInput, HutaoModelError, ScenarioConfig)


HOMA_R1_BASE_ATK = 608.0
HOMA_R1_CRIT_DMG = 0.662
HUTAO_BASE_CRIT_RATE = 0.05
HUTAO_LEVEL_90_CRIT_DMG = 0.884
PYRO_RESONANCE_ATK_PCT = 0.25
SHIMENAWA_2PC_ATK_PCT = 0.18
CRIMSON_WITCH = "Crimson Witch of Flames"
SHIMENAWA = "Shimenawa's Reminiscence"
SET_NAME_ALIASES = {"火魔女": CRIMSON_WITCH, "しめ縄": SHIMENAWA}

HYPOTHESIS_STATES = (
    HypothesisState("H1", HypothesisStatus.STRONGLY_SUPPORTED,
                    "Hu Tao Lv90、raw Max HP境界、Leaderboard上のE Talent Lv10"),
    HypothesisState("H3", HypothesisStatus.UNRESOLVED,
                    "enemy level、基礎Pyro RES、VV reductionはbaseline仮説"),
    HypothesisState("H4", HypothesisStatus.STRONGLY_SUPPORTED,
                    "raw EMは聖遺物のみ、外部EM +420、火魔女reaction +15%、全Vape共通倍率"),
    HypothesisState("H5", HypothesisStatus.STRONGLY_SUPPORTED,
                    "raw ATKには聖遺物、護摩、炎共鳴を含み、外部ATKと胡桃Eは未包含"),
    HypothesisState("H6", HypothesisStatus.STRONGLY_SUPPORTED,
                    "raw炎Bonus境界、万葉56.8%、蒼古16%、火魔女stack、しめ縄50%"),
    HypothesisState("H7", HypothesisStatus.STRONGLY_SUPPORTED,
                    "raw CR/CD境界と平均会心倍率。100% clampの実測識別は未解決"),
    HypothesisState("aggregate", HypothesisStatus.CONFIRMED,
                    "4 N1 vape + 7 N1 non-vape + 11 CA vape + set別Q quantity"),
)


def _normalized_set_name(name: str) -> str:
    return SET_NAME_ALIASES.get(name, name)


def _optimizer_build_input(artifacts: tuple[Artifact, ...], scenario: ScenarioConfig) -> HutaoAkashaInput:
    if len(artifacts) != len(Slot) or {artifact.slot for artifact in artifacts} != set(Slot):
        raise HutaoModelError("optimizer buildには5部位を1個ずつ指定してください")
    for index, artifact in enumerate(artifacts):
        validate_artifact(artifact, f"build[{index}]")

    stats = aggregate_current_stats(artifacts)
    set_counts = Counter(_normalized_set_name(artifact.set_name) for artifact in artifacts)
    base_hp, character_base_atk = character_base_stats(scenario.character_level)
    base_atk = character_base_atk + HOMA_R1_BASE_ATK
    hp_pct = stats.get(Stat.HP_PERCENT, 0.0)
    flat_hp = stats.get(Stat.HP_FLAT, 0.0)
    max_hp = base_hp * (1 + hp_pct + HOMA_BASE_HP_PCT) + flat_hp
    artifact_atk_pct = stats.get(Stat.ATK_PERCENT, 0.0)
    artifact_flat_atk = stats.get(Stat.ATK_FLAT, 0.0)
    set_atk_pct = SHIMENAWA_2PC_ATK_PCT if set_counts[SHIMENAWA] >= 2 else 0.0
    homa_atk_pct = HOMA_BASE_ATK_FROM_HP + (HOMA_LOW_HP_EXTRA_ATK_FROM_HP if scenario.low_hp_for_homa else 0.0)
    sheet_atk = (base_atk * (1 + artifact_atk_pct + set_atk_pct + PYRO_RESONANCE_ATK_PCT)
                 + artifact_flat_atk + max_hp * homa_atk_pct)
    raw_pyro_bonus = stats.get(Stat.PYRO_DMG, 0.0)
    if set_counts[CRIMSON_WITCH] >= 2:
        raw_pyro_bonus += CRIMSON_WITCH_2PC_PYRO_BONUS
    return HutaoAkashaInput(
        input_source="optimizer_artifacts", max_hp=max_hp, sheet_atk=sheet_atk, base_atk=base_atk,
        crit_rate=HUTAO_BASE_CRIT_RATE + stats.get(Stat.CRIT_RATE, 0.0),
        crit_dmg=HUTAO_LEVEL_90_CRIT_DMG + HOMA_R1_CRIT_DMG + stats.get(Stat.CRIT_DMG, 0.0),
        elemental_mastery=stats.get(Stat.ELEMENTAL_MASTERY, 0.0), pyro_dmg_bonus=raw_pyro_bonus,
        artifact_sets=tuple(sorted(set_counts.items())),
    )


def normalize_hutao_akasha_input(build: HutaoAkashaInput | tuple[Artifact, ...],
                                 scenario_config: ScenarioConfig | None = None) -> HutaoAkashaInput:
    """保存済みraw入力またはoptimizerの5聖遺物を共通入力へ変換する。"""
    scenario = scenario_config or ScenarioConfig()
    if isinstance(build, HutaoAkashaInput):
        return build
    if isinstance(build, tuple) and all(isinstance(artifact, Artifact) for artifact in build):
        return _optimizer_build_input(build, scenario)
    raise HutaoModelError("buildにはHutaoAkashaInputまたはArtifactのtupleが必要です")


def score_hutao_akasha(build: HutaoAkashaInput | tuple[Artifact, ...],
                       scenario_config: ScenarioConfig | None = None) -> AkashaScoreResult:
    """Hu Tao Akashaの4 componentとaggregate推定値を返す安定公開API。"""
    scenario = scenario_config or ScenarioConfig()
    normalized = normalize_hutao_akasha_input(build, scenario)
    predicted = predict_components(normalized, scenario)
    debug = debug_build(normalized, scenario)
    debug["components"] = {
        "n1_non_vape": predicted.n1_non_vape.as_dict(), "n1_vape": predicted.n1_vape.as_dict(),
        "ca_vape": predicted.ca_vape.as_dict(), "q_vape": predicted.q_vape.as_dict(),
        "aggregate": predicted.aggregate.as_dict(),
    }
    debug["scenario_config"] = asdict(scenario)
    debug["hypothesis_states"] = {state.hypothesis_id: state.status.value for state in HYPOTHESIS_STATES}
    debug["model_status"] = "estimated_not_fully_reproduced"
    return AkashaScoreResult(
        n1_non_vape_avg=predicted.n1_non_vape.value, n1_vape_avg=predicted.n1_vape.value,
        ca_vape_avg=predicted.ca_vape.value, q_vape_avg=predicted.q_vape.value,
        aggregate_score=predicted.aggregate.value, debug_breakdown=debug,
        hypothesis_states=HYPOTHESIS_STATES, is_estimate=True,
    )
