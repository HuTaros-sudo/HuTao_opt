import pytest

from genshin_opt.dust_defaults import (DEFAULT_DUST_ROLL_PROBABILITIES_PERCENT,
                                       DEFAULT_DUST_ROLL_VALUES_DISPLAY, roll_value_to_internal)
from genshin_opt.models import Stat


def test_wiki_roll_defaults_cover_all_supported_substats():
    assert DEFAULT_DUST_ROLL_VALUES_DISPLAY[Stat.ATK_FLAT] == (13.62, 15.56, 17.51, 19.45)
    assert DEFAULT_DUST_ROLL_VALUES_DISPLAY[Stat.CRIT_DMG] == (5.44, 6.22, 6.99, 7.77)
    assert DEFAULT_DUST_ROLL_PROBABILITIES_PERCENT == (25.0, 25.0, 25.0, 25.0)


def test_display_percent_roll_is_converted_but_flat_roll_is_not():
    assert roll_value_to_internal(Stat.CRIT_RATE, 2.72) == pytest.approx(0.0272)
    assert roll_value_to_internal(Stat.ELEMENTAL_MASTERY, 16.32) == pytest.approx(16.32)
