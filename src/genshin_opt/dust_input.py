"""手入力を聖啓の塵の抽選条件へ変換する。Streamlitには依存しない。"""

from .dust import AllocationModel, GuaranteeTier, ReshapeConditions, StatRollDistribution, WeightedRoll
from .models import Stat
from .storage import check_fields, parse_enum
from .validation import ValidationError, require


TIER_NAMES = {
    "normal": GuaranteeTier.NORMAL,
    "advanced": GuaranteeTier.ADVANCED,
    "absolute": GuaranteeTier.ABSOLUTE,
}


def parse_number_list(text: str, path: str) -> tuple[float, ...]:
    """カンマ区切りの有限な数値を読む。正値などの抽選規則はdust側で検証する。"""
    require(isinstance(text, str) and bool(text.strip()), path, "カンマ区切りの数値を入力してください")
    values = []
    for index, part in enumerate(text.split(",")):
        try:
            value = float(part.strip())
        except ValueError as error:
            raise ValidationError(f"{path}[{index}]: 数値を入力してください") from error
        require(value == value and abs(value) != float("inf"), f"{path}[{index}]", "有限の数値を入力してください")
        values.append(value)
    return tuple(values)


def reshape_conditions_from_dict(data: object) -> ReshapeConditions:
    """厳密なキー構造の手入力dictからReshapeConditionsを作る。"""
    root = check_fields(data, {"selected_stats", "guarantee_tier", "roll_distributions"},
                        {"allocation_model", "roll_model_id"}, "conditions")
    require(isinstance(root["selected_stats"], list) and len(root["selected_stats"]) == 2,
            "conditions.selected_stats", "2種類の配列が必要です")
    selected = tuple(parse_enum(Stat, value, f"conditions.selected_stats[{index}]")
                     for index, value in enumerate(root["selected_stats"]))
    tier_name = root["guarantee_tier"]
    require(isinstance(tier_name, str) and tier_name in TIER_NAMES, "conditions.guarantee_tier",
            "normal、advanced、absoluteのいずれかが必要です")
    try:
        allocation_model = AllocationModel(root.get("allocation_model", AllocationModel.GO_CAPPED_BINOMIAL))
    except (TypeError, ValueError) as error:
        raise ValidationError("conditions.allocation_model: 未対応の確率モデルです") from error
    require(isinstance(root["roll_distributions"], list), "conditions.roll_distributions", "配列が必要です")

    distributions = []
    for index, raw_distribution in enumerate(root["roll_distributions"]):
        path = f"conditions.roll_distributions[{index}]"
        raw_distribution = check_fields(raw_distribution, {"stat", "rolls"}, set(), path)
        stat = parse_enum(Stat, raw_distribution["stat"], f"{path}.stat")
        require(isinstance(raw_distribution["rolls"], list), f"{path}.rolls", "配列が必要です")
        rolls = []
        for roll_index, raw_roll in enumerate(raw_distribution["rolls"]):
            roll_path = f"{path}.rolls[{roll_index}]"
            raw_roll = check_fields(raw_roll, {"value", "probability"}, set(), roll_path)
            rolls.append(WeightedRoll(raw_roll["value"], raw_roll["probability"]))
        distributions.append(StatRollDistribution(stat, tuple(rolls)))
    return ReshapeConditions(selected, TIER_NAMES[tier_name], tuple(distributions), allocation_model,
                             root.get("roll_model_id", "caller_supplied"))


def roll_distribution_from_text(stat: Stat, values_text: str, probabilities_text: str) -> StatRollDistribution:
    """画面の2つのカンマ区切り欄から1種類分のロール分布を作る。"""
    values = parse_number_list(values_text, f"{stat.value}.values")
    probabilities = parse_number_list(probabilities_text, f"{stat.value}.probabilities")
    require(len(values) == len(probabilities), stat.value, "ロール値と確率の個数を一致させてください")
    return StatRollDistribution(stat, tuple(WeightedRoll(value, probability)
                                             for value, probability in zip(values, probabilities)))
