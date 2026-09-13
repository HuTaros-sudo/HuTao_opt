from dataclasses import replace

import pytest

from genshin_opt.models import Artifact, Inventory, Slot, Stat, StatValue, Substat
from genshin_opt.optimizer import OptimizationError, at_least_set_pieces, optimize
from genshin_opt.scoring import toy_build_score, toy_score
from genshin_opt.stats import aggregate_current_stats, to_display_stats


MAIN_STATS = {
    Slot.FLOWER: StatValue(Stat.HP_FLAT, 4780),
    Slot.PLUME: StatValue(Stat.ATK_FLAT, 311),
    Slot.SANDS: StatValue(Stat.ATK_PERCENT, 0.466),
    Slot.GOBLET: StatValue(Stat.PYRO_DMG, 0.466),
    Slot.CIRCLET: StatValue(Stat.HEALING_BONUS, 0.359),
}


def artifact(slot: Slot, choice: str) -> Artifact:
    if choice == "balanced":
        substats = (Substat(Stat.CRIT_RATE, 0.05), Substat(Stat.CRIT_DMG, 0.10),
                    Substat(Stat.HP_PERCENT, 0.01), Substat(Stat.ELEMENTAL_MASTERY, 1))
    else:
        substats = (Substat(Stat.CRIT_RATE, 0.001), Substat(Stat.CRIT_DMG, 0.21),
                    Substat(Stat.HP_PERCENT, 0.001), Substat(Stat.ELEMENTAL_MASTERY, 1))
    return Artifact(f"{slot.value}-{choice}", slot, "人工セット", 5, 20, MAIN_STATS[slot], substats)


def two_choices_per_slot() -> Inventory:
    artifacts = tuple(artifact(slot, choice) for slot in Slot for choice in ("balanced", "high-cv"))
    return Inventory(1, artifacts)


def test_toy_score_has_the_documented_nonlinear_penalty() -> None:
    stats = {Stat.CRIT_RATE: 70.0, Stat.CRIT_DMG: 170.0, Stat.HP_PERCENT: 46.6,
             Stat.ELEMENTAL_MASTERY: 100.0}
    assert toy_score(stats) == pytest.approx(313.98)


def test_stat_aggregation_uses_current_values_and_display_units() -> None:
    base = artifact(Slot.FLOWER, "balanced")
    with_initials = replace(base, substats=tuple(replace(sub, initial_value=sub.value / 2) for sub in base.substats))

    internal = aggregate_current_stats((with_initials,))
    displayed = to_display_stats(internal)

    assert internal[Stat.CRIT_RATE] == pytest.approx(0.05)
    assert displayed[Stat.CRIT_RATE] == pytest.approx(5.0)
    assert displayed[Stat.HP_FLAT] == pytest.approx(4780)


def test_optimizer_finds_global_maximum_that_per_slot_cv_would_miss() -> None:
    inventory = two_choices_per_slot()
    highest_cv_ids = {
        max((a for a in inventory.artifacts if a.slot == slot),
            key=lambda a: 2 * next(s.value for s in a.substats if s.stat == Stat.CRIT_RATE)
            + next(s.value for s in a.substats if s.stat == Stat.CRIT_DMG)).id
        for slot in Slot
    }

    result = optimize(inventory, toy_build_score)
    selected_ids = {artifact.id for artifact in result.artifacts}

    assert result.combinations_evaluated == 32
    assert selected_ids == {f"{slot.value}-balanced" for slot in Slot}
    assert highest_cv_ids == {f"{slot.value}-high-cv" for slot in Slot}
    high_cv_build = tuple(artifact(slot, "high-cv") for slot in Slot)
    assert result.score > toy_build_score(high_cv_build)


def test_optimizer_uses_the_supplied_evaluator() -> None:
    inventory = two_choices_per_slot()

    def prefer_high_cv_count(build: tuple[Artifact, ...]) -> float:
        return sum(item.id.endswith("high-cv") for item in build)

    result = optimize(inventory, prefer_high_cv_count)
    assert all(item.id.endswith("high-cv") for item in result.artifacts)
    assert result.score == 5


def test_optimizer_accepts_a_four_piece_set_constraint() -> None:
    inventory = two_choices_per_slot()
    artifacts = tuple(replace(item, set_name="火魔女" if item.id.endswith("balanced") else "その他")
                      for item in inventory.artifacts)

    def prefer_off_set_count(build: tuple[Artifact, ...]) -> float:
        return sum(item.set_name == "その他" for item in build)

    result = optimize(Inventory(1, artifacts), prefer_off_set_count, at_least_set_pieces("火魔女", 4))
    assert sum(item.set_name == "火魔女" for item in result.artifacts) == 4
    assert sum(item.set_name == "その他" for item in result.artifacts) == 1
    assert result.combinations_evaluated == 6


def test_optimizer_reports_when_no_build_satisfies_constraint() -> None:
    inventory = Inventory(1, tuple(replace(artifact(slot, "balanced"), set_name="火魔女" if slot in list(Slot)[:3] else "その他")
                                   for slot in Slot))
    with pytest.raises(OptimizationError, match="制約を満たす"):
        optimize(inventory, toy_build_score, at_least_set_pieces("火魔女", 4))


def test_result_can_be_looked_up_by_slot() -> None:
    result = optimize(two_choices_per_slot(), toy_build_score)
    assert result.artifact_for(Slot.GOBLET).id == "goblet-balanced"


def test_optimizer_rejects_inventory_with_a_missing_slot() -> None:
    inventory = Inventory(1, tuple(artifact(slot, "balanced") for slot in Slot if slot != Slot.CIRCLET))
    with pytest.raises(OptimizationError, match="circlet"):
        optimize(inventory, toy_build_score)


@pytest.mark.parametrize("bad_score", [float("nan"), float("inf"), True, "100"])
def test_optimizer_rejects_invalid_evaluator_results(bad_score: object) -> None:
    with pytest.raises(OptimizationError, match="有限の数値"):
        optimize(two_choices_per_slot(), lambda _: bad_score)  # type: ignore[return-value]
