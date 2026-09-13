from dataclasses import replace

import pytest

from genshin_opt.dust import (AllocationModel, GuaranteeTier, ReshapeConditions, ReshapeDistribution,
                              ReshapeOutcome, StatRollDistribution, WeightedRoll)
from genshin_opt.dust_optimizer import ReshapeDecision, analyze_distribution
from genshin_opt.models import Artifact, Inventory, Slot, Stat, StatValue, Substat
from genshin_opt.optimizer import at_least_set_pieces
from genshin_opt.scoring import toy_build_score


MAIN_STATS = {
    Slot.FLOWER: StatValue(Stat.HP_FLAT, 4780), Slot.PLUME: StatValue(Stat.ATK_FLAT, 311),
    Slot.SANDS: StatValue(Stat.ATK_PERCENT, 0.466), Slot.GOBLET: StatValue(Stat.PYRO_DMG, 0.466),
    Slot.CIRCLET: StatValue(Stat.HEALING_BONUS, 0.359),
}


def reshape_artifact() -> Artifact:
    substats = (Substat(Stat.CRIT_RATE, 0.08, 0.03), Substat(Stat.CRIT_DMG, 0.16, 0.06),
                Substat(Stat.HP_PERCENT, 0.13, 0.04), Substat(Stat.ELEMENTAL_MASTERY, 24, 8))
    return Artifact("dust-target", Slot.FLOWER, "火魔女", 5, 20,
                    StatValue(Stat.HP_FLAT, 4780), substats, 4)


def deterministic_conditions() -> ReshapeConditions:
    values = {Stat.CRIT_RATE: 0.01, Stat.CRIT_DMG: 0.02,
              Stat.HP_PERCENT: 0.03, Stat.ELEMENTAL_MASTERY: 4.0}
    distributions = tuple(StatRollDistribution(stat, (WeightedRoll(value, 1.0),))
                          for stat, value in values.items())
    return ReshapeConditions((Stat.CRIT_RATE, Stat.CRIT_DMG), GuaranteeTier.NORMAL, distributions,
                             AllocationModel.GO_CAPPED_BINOMIAL, "optimizer-test")


def fixed_artifact(slot: Slot, artifact_id: str, set_name: str = "火魔女") -> Artifact:
    substats = (Substat(Stat.CRIT_RATE, 0.001), Substat(Stat.CRIT_DMG, 0.001),
                Substat(Stat.HP_PERCENT, 0.001), Substat(Stat.ELEMENTAL_MASTERY, 1))
    return Artifact(artifact_id, slot, set_name, 5, 20, MAIN_STATS[slot], substats)


def test_analysis_chooses_between_original_and_reshaped_optimal_inventory() -> None:
    target = reshape_artifact()
    alternative = replace(target, id="alternative-flower", substats=(replace(target.substats[0], value=0.09),) + target.substats[1:])
    other_slots = tuple(fixed_artifact(slot, f"fixed-{slot.value}") for slot in Slot if slot != Slot.FLOWER)
    inventory = Inventory(1, (target, alternative) + other_slots)

    low = replace(target, substats=(replace(target.substats[0], value=0.05),) + target.substats[1:])
    high = replace(target, substats=(replace(target.substats[0], value=0.14),) + target.substats[1:])
    counts = tuple((sub.stat, 0) for sub in target.substats)
    outcomes = (ReshapeOutcome(low, counts, 0.25), ReshapeOutcome(high, counts, 0.75))
    distribution = ReshapeDistribution(target, deterministic_conditions(), 5, outcomes)

    def crit_rate_score(build: tuple[Artifact, ...]) -> float:
        return sum(next(sub.value for sub in item.substats if sub.stat == Stat.CRIT_RATE) for item in build) * 100

    analysis = analyze_distribution(inventory, distribution, crit_rate_score, at_least_set_pieces("火魔女", 4))
    assert analysis.original_best.artifact_for(Slot.FLOWER).id == "alternative-flower"
    assert analysis.outcomes[0].decision == ReshapeDecision.KEEP_ORIGINAL
    assert analysis.outcomes[0].chosen_best == analysis.original_best
    assert analysis.outcomes[1].decision == ReshapeDecision.APPLY_RESHAPE
    assert analysis.outcomes[1].chosen_best.artifact_for(Slot.FLOWER).id == target.id
    assert analysis.optimal_set_update_probability == pytest.approx(0.75)
    assert analysis.expected_improvement == pytest.approx(3.75)


def test_analysis_works_with_toy_evaluator_independently_of_ui() -> None:
    target = reshape_artifact()
    other_slots = tuple(fixed_artifact(slot, f"fixed-{slot.value}") for slot in Slot if slot != Slot.FLOWER)
    inventory = Inventory(1, (target,) + other_slots)
    outcome = ReshapeOutcome(target, tuple((sub.stat, 0) for sub in target.substats), 1.0)
    distribution = ReshapeDistribution(target, deterministic_conditions(), 5, (outcome,))
    analysis = analyze_distribution(inventory, distribution, toy_build_score)
    assert analysis.optimal_set_update_probability == 0
    assert analysis.expected_chosen_score == pytest.approx(analysis.original_best.score)
