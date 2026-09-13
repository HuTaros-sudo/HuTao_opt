import pytest

from genshin_opt.dust import AllocationModel, GuaranteeTier
from genshin_opt.dust_input import parse_number_list, reshape_conditions_from_dict, roll_distribution_from_text
from genshin_opt.models import Stat
from genshin_opt.validation import ValidationError


def condition_dict() -> dict:
    return {
        "selected_stats": ["crit_rate", "crit_dmg"],
        "guarantee_tier": "advanced",
        "allocation_model": "go_capped_binomial",
        "roll_model_id": "manual-test",
        "roll_distributions": [
            {"stat": stat, "rolls": [{"value": value, "probability": 1.0}]}
            for stat, value in (("crit_rate", 0.03), ("crit_dmg", 0.06),
                                ("hp_percent", 0.05), ("elemental_mastery", 20))
        ],
    }


def test_manual_dict_builds_reshape_conditions() -> None:
    conditions = reshape_conditions_from_dict(condition_dict())
    assert conditions.selected_stats == (Stat.CRIT_RATE, Stat.CRIT_DMG)
    assert conditions.guarantee_tier == GuaranteeTier.ADVANCED
    assert conditions.allocation_model == AllocationModel.GO_CAPPED_BINOMIAL
    assert conditions.roll_model_id == "manual-test"
    assert conditions.roll_distributions[0].rolls[0].value == 0.03


def test_manual_dict_rejects_unknown_fields() -> None:
    raw = condition_dict()
    raw["unknown"] = True
    with pytest.raises(ValidationError, match="未知"):
        reshape_conditions_from_dict(raw)


def test_number_list_and_roll_distribution_parse_comma_separated_input() -> None:
    assert parse_number_list("0.7, 0.8,0.9,1", "values") == (0.7, 0.8, 0.9, 1.0)
    distribution = roll_distribution_from_text(Stat.CRIT_RATE, "0.0272,0.0311", "0.25,0.75")
    assert distribution.stat == Stat.CRIT_RATE
    assert tuple(roll.probability for roll in distribution.rolls) == (0.25, 0.75)


def test_roll_distribution_requires_same_number_of_values_and_probabilities() -> None:
    with pytest.raises(ValidationError, match="個数"):
        roll_distribution_from_text(Stat.CRIT_RATE, "0.0272,0.0311", "1")
