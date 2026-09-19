from dataclasses import replace

import pytest

from genshin_opt.models import Artifact, Inventory, Slot, Stat, StatValue, Substat
from genshin_opt.reshape_adoption import (AdoptionVerdict, compare_artifact_adoption,
                                           inventory_with_artifact_case)


MAIN_STATS = {
    Slot.FLOWER: StatValue(Stat.HP_FLAT, 4780), Slot.PLUME: StatValue(Stat.ATK_FLAT, 311),
    Slot.SANDS: StatValue(Stat.HP_PERCENT, 0.466), Slot.GOBLET: StatValue(Stat.PYRO_DMG, 0.466),
    Slot.CIRCLET: StatValue(Stat.CRIT_DMG, 0.622),
}


def artifact(slot: Slot, artifact_id: str, crit_rate: float) -> Artifact:
    values = {Stat.CRIT_RATE: crit_rate, Stat.CRIT_DMG: 0.10, Stat.HP_PERCENT: 0.05,
              Stat.ATK_PERCENT: 0.05, Stat.ELEMENTAL_MASTERY: 20}
    available = [stat for stat in values if stat != MAIN_STATS[slot].stat][:4]
    substats = tuple(Substat(stat, values[stat]) for stat in available)
    return Artifact(artifact_id, slot, "火魔女", 5, 20, MAIN_STATS[slot], substats)


def inventory() -> Inventory:
    target = artifact(Slot.FLOWER, "target", 0.02)
    alternative = artifact(Slot.FLOWER, "alternative", 0.10)
    others = tuple(artifact(slot, slot.value, 0.01) for slot in Slot if slot != Slot.FLOWER)
    return Inventory(1, (target, alternative) + others)


def crit_score(build: tuple[Artifact, ...]) -> float:
    return sum(next(sub.value for sub in item.substats if sub.stat == Stat.CRIT_RATE) for item in build)


def test_case_inventories_replace_one_target_without_duplicate() -> None:
    source = inventory()
    replacement = replace(source.artifacts[0], substats=(Substat(Stat.CRIT_RATE, 0.20),) + source.artifacts[0].substats[1:])
    case = inventory_with_artifact_case(source, "target", replacement)
    assert source is not case
    assert len(case.artifacts) == len(source.artifacts)
    assert sum(item.id == "target" for item in case.artifacts) == 1
    assert next(item for item in case.artifacts if item.id == "target") == replacement


def test_comparison_handles_both_target_artifacts_not_selected() -> None:
    source = inventory()
    original = source.artifacts[0]
    reconstructed = replace(original, substats=(Substat(Stat.CRIT_RATE, 0.03),) + original.substats[1:])
    comparison = compare_artifact_adoption(source, "target", original, reconstructed, crit_score)
    assert comparison.original.inventory is not comparison.reconstructed.inventory
    assert not comparison.original.target_used
    assert not comparison.reconstructed.target_used
    assert comparison.damage_difference == pytest.approx(0)
    assert comparison.verdict == AdoptionVerdict.UNCERTAIN


def test_same_evaluator_is_used_for_both_cases_and_reconstructed_can_win() -> None:
    source = inventory()
    original = replace(source.artifacts[0], substats=(Substat(Stat.CRIT_RATE, 0.12),) + source.artifacts[0].substats[1:])
    reconstructed = replace(original, substats=(Substat(Stat.CRIT_RATE, 0.20),) + original.substats[1:])
    calls = []

    def evaluator(build: tuple[Artifact, ...]) -> float:
        calls.append(tuple(item.id for item in build))
        return crit_score(build)

    comparison = compare_artifact_adoption(source, "target", original, reconstructed, evaluator)
    assert comparison.original.target_used
    assert comparison.reconstructed.target_used
    assert comparison.reconstructed.best.score > comparison.original.best.score
    assert comparison.verdict == AdoptionVerdict.RECONSTRUCTED_BETTER
    assert len(calls) >= 4


def test_half_percent_or_less_is_uncertain() -> None:
    source = inventory()
    original = replace(source.artifacts[0], substats=(Substat(Stat.CRIT_RATE, 0.12),) + source.artifacts[0].substats[1:])
    reconstructed = replace(original, substats=(Substat(Stat.CRIT_RATE, 0.1205),) + original.substats[1:])
    comparison = compare_artifact_adoption(source, "target", original, reconstructed, crit_score)
    assert abs(comparison.improvement_percent) <= 0.5
    assert comparison.verdict == AdoptionVerdict.UNCERTAIN

