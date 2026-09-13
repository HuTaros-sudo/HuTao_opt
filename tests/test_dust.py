from dataclasses import replace

import pytest

from genshin_opt.dust import (AllocationModel, DustError, GuaranteeTier, ReshapeConditions,
                              ReshapeDistribution, ReshapeOutcome, StatRollDistribution,
                              WeightedRoll, calculate_update_metrics, enhancement_roll_count,
                              reshape_distribution)
from genshin_opt.models import Artifact, Slot, Stat, StatValue, Substat
from genshin_opt.validation import ValidationError


ROLL_VALUES = {
    Stat.CRIT_RATE: 0.01,
    Stat.CRIT_DMG: 0.02,
    Stat.HP_PERCENT: 0.03,
    Stat.ELEMENTAL_MASTERY: 4.0,
}


def reshape_artifact(initial_count: int = 4) -> Artifact:
    substats = (Substat(Stat.CRIT_RATE, 0.08, 0.03), Substat(Stat.CRIT_DMG, 0.16, 0.06),
                Substat(Stat.HP_PERCENT, 0.13, 0.04), Substat(Stat.ELEMENTAL_MASTERY, 24, 8))
    return Artifact("dust-target", Slot.FLOWER, "火魔女", 5, 20,
                    StatValue(Stat.HP_FLAT, 4780), substats, initial_count)


def deterministic_conditions(tier: GuaranteeTier = GuaranteeTier.NORMAL) -> ReshapeConditions:
    distributions = tuple(StatRollDistribution(stat, (WeightedRoll(value, 1.0),))
                          for stat, value in ROLL_VALUES.items())
    return ReshapeConditions((Stat.CRIT_RATE, Stat.CRIT_DMG), tier, distributions,
                             AllocationModel.GO_CAPPED_BINOMIAL)


def test_enhancement_roll_count_distinguishes_initial_three_and_four_stats() -> None:
    assert enhancement_roll_count(reshape_artifact(4)) == 5
    assert enhancement_roll_count(reshape_artifact(3)) == 4


def test_enhancement_roll_count_requires_complete_initial_values() -> None:
    artifact = reshape_artifact()
    incomplete = replace(artifact, substats=(replace(artifact.substats[0], initial_value=None),) + artifact.substats[1:])
    with pytest.raises(ValidationError, match="initial_value"):
        enhancement_roll_count(incomplete)


def test_normal_distribution_matches_documented_capped_binomial_model() -> None:
    distribution = reshape_distribution(reshape_artifact(), deterministic_conditions())
    selected_totals: dict[int, float] = {}
    for outcome in distribution.outcomes:
        selected_count = outcome.count_for(Stat.CRIT_RATE) + outcome.count_for(Stat.CRIT_DMG)
        selected_totals[selected_count] = selected_totals.get(selected_count, 0.0) + outcome.probability

    assert distribution.enhancement_rolls == 5
    assert sum(outcome.probability for outcome in distribution.outcomes) == pytest.approx(1.0)
    assert selected_totals == pytest.approx({2: 0.5, 3: 0.3125, 4: 0.15625, 5: 0.03125})


@pytest.mark.parametrize("tier, minimum", [(GuaranteeTier.NORMAL, 2),
                                            (GuaranteeTier.ADVANCED, 3),
                                            (GuaranteeTier.ABSOLUTE, 4)])
def test_every_outcome_respects_guaranteed_selected_rolls(tier: GuaranteeTier, minimum: int) -> None:
    distribution = reshape_distribution(reshape_artifact(), deterministic_conditions(tier))
    for outcome in distribution.outcomes:
        selected_count = outcome.count_for(Stat.CRIT_RATE) + outcome.count_for(Stat.CRIT_DMG)
        assert selected_count >= minimum
        assert sum(count for _, count in outcome.enhancement_counts) == 5


def test_reshape_keeps_initial_values_and_applies_sampled_rolls() -> None:
    original = reshape_artifact()
    distribution = reshape_distribution(original, deterministic_conditions())
    outcome = distribution.outcomes[0]
    result_by_stat = {sub.stat: sub for sub in outcome.artifact.substats}
    initial_by_stat = {sub.stat: sub.initial_value for sub in original.substats}

    for stat, increment in ROLL_VALUES.items():
        count = outcome.count_for(stat)
        assert result_by_stat[stat].initial_value == initial_by_stat[stat]
        assert result_by_stat[stat].value == pytest.approx(float(initial_by_stat[stat]) + count * increment)
    assert outcome.artifact.main_stat == original.main_stat
    assert outcome.artifact.set_name == original.set_name


def test_roll_value_probabilities_are_used_and_normalized() -> None:
    conditions = deterministic_conditions()
    first = conditions.roll_distributions[0]
    invalid_first = replace(first, rolls=(WeightedRoll(0.01, 0.4), WeightedRoll(0.02, 0.4)))
    invalid = replace(conditions, roll_distributions=(invalid_first,) + conditions.roll_distributions[1:])
    with pytest.raises(DustError, match="合計は1"):
        reshape_distribution(reshape_artifact(), invalid)


def test_weighted_roll_values_affect_the_result_distribution() -> None:
    conditions = deterministic_conditions()
    first = conditions.roll_distributions[0]
    weighted_first = replace(first, rolls=(WeightedRoll(0.01, 0.25), WeightedRoll(0.02, 0.75)))
    weighted = replace(conditions, roll_distributions=(weighted_first,) + conditions.roll_distributions[1:],
                       roll_model_id="artificial_weighted_test")
    distribution = reshape_distribution(reshape_artifact(), weighted)
    expected_crit_rate = sum(outcome.probability * next(sub.value for sub in outcome.artifact.substats
                                                        if sub.stat == Stat.CRIT_RATE)
                             for outcome in distribution.outcomes)
    expected_crit_rolls = 0.5 * (2 * 0.5 + 3 * 0.3125 + 4 * 0.15625 + 5 * 0.03125)
    assert expected_crit_rate == pytest.approx(0.03 + expected_crit_rolls * 0.0175)
    assert distribution.conditions.roll_model_id == "artificial_weighted_test"


def test_update_metrics_distinguish_candidate_and_keep_original() -> None:
    original = reshape_artifact()
    low_substats = (replace(original.substats[0], value=0.08),) + original.substats[1:]
    high_substats = (replace(original.substats[0], value=0.14),) + original.substats[1:]
    low = ReshapeOutcome(replace(original, substats=low_substats), tuple((s.stat, 0) for s in original.substats), 0.25)
    high = ReshapeOutcome(replace(original, substats=high_substats), tuple((s.stat, 0) for s in original.substats), 0.75)
    distribution = ReshapeDistribution(original, deterministic_conditions(), 5, (low, high))

    def crit_rate_score(artifact: Artifact) -> float:
        return next(sub.value for sub in artifact.substats if sub.stat == Stat.CRIT_RATE) * 100

    metrics = calculate_update_metrics(distribution, crit_rate_score)
    assert metrics.original_score == pytest.approx(8.0)
    assert metrics.update_probability == pytest.approx(0.75)
    assert metrics.expected_candidate_score == pytest.approx(12.5)
    assert metrics.expected_kept_score == pytest.approx(12.5)
    assert metrics.expected_improvement == pytest.approx(4.5)
    assert metrics.mean_improvement_when_updated == pytest.approx(6.0)


def test_update_metrics_returns_none_when_no_outcome_improves() -> None:
    original = reshape_artifact()
    outcome = ReshapeOutcome(original, tuple((s.stat, 0) for s in original.substats), 1.0)
    distribution = ReshapeDistribution(original, deterministic_conditions(), 5, (outcome,))
    metrics = calculate_update_metrics(distribution, lambda _: 1.0)
    assert metrics.update_probability == 0
    assert metrics.expected_improvement == 0
    assert metrics.mean_improvement_when_updated is None


def test_update_metrics_rejects_an_unnormalized_distribution() -> None:
    original = reshape_artifact()
    outcome = ReshapeOutcome(original, tuple((s.stat, 0) for s in original.substats), 0.9)
    distribution = ReshapeDistribution(original, deterministic_conditions(), 5, (outcome,))
    with pytest.raises(DustError, match="合計は1"):
        calculate_update_metrics(distribution, lambda _: 1.0)
