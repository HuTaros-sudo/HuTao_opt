"""聖遺物のデータ型。割合は46.6%を0.466として保持する。"""

from dataclasses import dataclass
from enum import StrEnum


class Slot(StrEnum):
    FLOWER = "flower"
    PLUME = "plume"
    SANDS = "sands"
    GOBLET = "goblet"
    CIRCLET = "circlet"


class Stat(StrEnum):
    HP_FLAT = "hp_flat"
    ATK_FLAT = "atk_flat"
    DEF_FLAT = "def_flat"
    HP_PERCENT = "hp_percent"
    ATK_PERCENT = "atk_percent"
    DEF_PERCENT = "def_percent"
    ELEMENTAL_MASTERY = "elemental_mastery"
    ENERGY_RECHARGE = "energy_recharge"
    CRIT_RATE = "crit_rate"
    CRIT_DMG = "crit_dmg"
    PYRO_DMG = "pyro_dmg"
    HYDRO_DMG = "hydro_dmg"
    CRYO_DMG = "cryo_dmg"
    ELECTRO_DMG = "electro_dmg"
    ANEMO_DMG = "anemo_dmg"
    GEO_DMG = "geo_dmg"
    DENDRO_DMG = "dendro_dmg"
    PHYSICAL_DMG = "physical_dmg"
    HEALING_BONUS = "healing_bonus"


@dataclass(frozen=True)
class StatValue:
    stat: Stat
    value: float


@dataclass(frozen=True)
class Substat:
    stat: Stat
    value: float
    initial_value: float | None = None


@dataclass(frozen=True)
class Artifact:
    id: str
    slot: Slot
    set_name: str
    rarity: int
    level: int
    main_stat: StatValue
    substats: tuple[Substat, ...]
    initial_substat_count: int | None = None


@dataclass(frozen=True)
class Inventory:
    schema_version: int
    artifacts: tuple[Artifact, ...]
