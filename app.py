"""ローカル試作用のStreamlit画面。計算処理はsrc/genshin_optに置く。"""

import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from genshin_opt.dust import DustError, GuaranteeTier  # noqa: E402
from genshin_opt.dust_defaults import (DEFAULT_DUST_ROLL_PROBABILITIES_PERCENT,
                                       DEFAULT_DUST_ROLL_VALUES_DISPLAY,
                                       DEFAULT_DUST_UPDATE_PROBABILITY_PERCENT, DUST_ROLL_TIERS,
                                       roll_value_to_internal)  # noqa: E402
from genshin_opt.dust_input import reshape_conditions_from_dict  # noqa: E402
from genshin_opt.dust_optimizer import ReshapeDecision, analyze_reshape, replace_inventory_artifact  # noqa: E402
from genshin_opt.akasha import ScenarioConfig, score_hutao_akasha  # noqa: E402
from genshin_opt.models import Artifact, Inventory, Slot, Stat, Substat  # noqa: E402
from genshin_opt.optimizer import OptimizationError, at_least_set_pieces, optimize  # noqa: E402
from genshin_opt.storage import loads_inventory  # noqa: E402
from genshin_opt.validation import PERCENT_TYPES, ValidationError, validate_for_reshape  # noqa: E402


STAT_LABELS = {
    Stat.HP_FLAT: "HP実数", Stat.ATK_FLAT: "攻撃力実数", Stat.DEF_FLAT: "防御力実数",
    Stat.HP_PERCENT: "HP%", Stat.ATK_PERCENT: "攻撃力%", Stat.DEF_PERCENT: "防御力%",
    Stat.ELEMENTAL_MASTERY: "元素熟知", Stat.ENERGY_RECHARGE: "元素チャージ効率",
    Stat.CRIT_RATE: "会心率", Stat.CRIT_DMG: "会心ダメージ",
}
TIER_LABELS = {
    GuaranteeTier.NORMAL: "通常（優先2種類に合計2回以上）",
    GuaranteeTier.ADVANCED: "上級（合計3回以上）",
    GuaranteeTier.ABSOLUTE: "絶対（合計4回以上）",
}
TIER_INPUT_NAMES = {
    GuaranteeTier.NORMAL: "normal", GuaranteeTier.ADVANCED: "advanced",
    GuaranteeTier.ABSOLUTE: "absolute",
}


def artifact_rows(artifacts: tuple[Artifact, ...]) -> list[dict[str, object]]:
    return [{"部位": artifact.slot.value, "ID": artifact.id, "セット": artifact.set_name,
             "メイン": f"{artifact.main_stat.stat.value}: {artifact.main_stat.value}"}
            for artifact in artifacts]


def display_substats(artifact: Artifact) -> str:
    parts = []
    for substat in artifact.substats:
        value = substat.value * 100 if substat.stat in PERCENT_TYPES else substat.value
        suffix = "%" if substat.stat in PERCENT_TYPES else ""
        parts.append(f"{STAT_LABELS.get(substat.stat, substat.stat.value)} {value:.4g}{suffix}")
    return " / ".join(parts)


def reshape_candidates(artifacts: tuple[Artifact, ...]) -> tuple[Artifact, ...]:
    candidates = []
    for artifact in artifacts:
        try:
            validate_for_reshape(artifact)
        except ValidationError:
            continue
        candidates.append(artifact)
    return tuple(candidates)


def classify_crimson_witch(inventory: Inventory, witch_set_name: str) -> Inventory:
    """GUIで指定されたセットだけを、評価APIが認識する火魔女名へ正規化する。"""
    artifacts = tuple(replace(artifact, set_name="火魔女") if artifact.set_name == witch_set_name else artifact
                      for artifact in inventory.artifacts)
    return Inventory(inventory.schema_version, artifacts)


st.set_page_config(page_title="原神 聖遺物最適化ツール", layout="wide")
st.title("原神 聖遺物最適化ツール")
st.caption("対象: VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1")

sample_json = (PROJECT_ROOT / "data" / "sample_inventory.json").read_text(encoding="utf-8")
with st.expander("所持聖遺物JSON", expanded=False):
    inventory_text = st.text_area("JSONを直接編集", value=sample_json, height=320)

try:
    inventory = loads_inventory(inventory_text)
except ValidationError as error:
    st.error(f"所持聖遺物を読み込めません: {error}")
    st.stop()

st.subheader("Optimizer")
set_names = sorted({artifact.set_name for artifact in inventory.artifacts})
default_set = Counter(artifact.set_name for artifact in inventory.artifacts).most_common(1)[0][0] if set_names else "火魔女"
use_four_piece = st.checkbox("火魔女4セット制約を使う", value=True)
witch_set_name = st.selectbox("火魔女として扱うset_name", set_names, index=set_names.index(default_set)) if set_names else "火魔女"
scoring_inventory = classify_crimson_witch(inventory, witch_set_name)
constraint = at_least_set_pieces("火魔女", 4) if use_four_piece else None
st.caption("選択したset_nameを火魔女、それ以外を自由枠として扱い、火魔女4部位以上を必須にします。")

config = ScenarioConfig()
score_function = lambda build: score_hutao_akasha(build, config).aggregate_score

with st.expander("現在装備を選択", expanded=False):
    current_artifacts = []
    for slot in Slot:
        slot_artifacts = tuple(artifact for artifact in scoring_inventory.artifacts if artifact.slot == slot)
        if not slot_artifacts:
            st.error(f"現在装備を選べません。{slot.value}の候補がありません。")
            st.stop()
        selected_id = st.selectbox(slot.value, tuple(artifact.id for artifact in slot_artifacts), key=f"equipped-{slot.value}")
        current_artifacts.append(next(artifact for artifact in slot_artifacts if artifact.id == selected_id))
current_build = tuple(current_artifacts)
current_score = score_hutao_akasha(current_build, config)
if current_score.is_estimate:
    st.warning("現在の計算モデルはAkashaを完全再現したものではありません。画面のDamageは「Akasha推定Damage」です。")

st.markdown("#### 現在装備")
current_columns = st.columns(5)
current_columns[0].metric("Akasha推定Damage", f"{current_score.aggregate_score:.2f}")
current_columns[1].metric("N1 non-vape Avg DMG", f"{current_score.n1_non_vape_avg:.2f}")
current_columns[2].metric("N1 vape Avg DMG", f"{current_score.n1_vape_avg:.2f}")
current_columns[3].metric("CA vape Avg DMG", f"{current_score.ca_vape_avg:.2f}")
current_columns[4].metric("Q vape Avg DMG", f"{current_score.q_vape_avg:.2f}")
st.caption(f"model status: {current_score.debug_breakdown['model_status']}")

with st.expander("計算モデルの仮説状態", expanded=False):
    st.dataframe([{"仮説": state.hypothesis_id, "状態": state.status.value, "内容": state.summary}
                  for state in current_score.hypothesis_states if state.hypothesis_id.startswith("H")],
                 use_container_width=True, hide_index=True)

try:
    original_best = optimize(scoring_inventory, score_function, constraint)
except (ValidationError, OptimizationError) as error:
    st.error(f"最適化できません: {error}")
    st.stop()

damage_difference = original_best.score - current_score.aggregate_score
improvement_rate = damage_difference / current_score.aggregate_score if current_score.aggregate_score else 0.0
score_column, best_column, difference_column, rate_column, count_column = st.columns(5)
score_column.metric("現在装備の推定Damage", f"{current_score.aggregate_score:.2f}")
best_column.metric("最適装備の推定Damage", f"{original_best.score:.2f}")
difference_column.metric("Damage差", f"{damage_difference:+.2f}")
rate_column.metric("改善率", f"{improvement_rate:+.4%}")
count_column.metric("評価した組み合わせ", original_best.combinations_evaluated)
st.dataframe(artifact_rows(original_best.artifacts), use_container_width=True, hide_index=True)

st.subheader("聖啓の塵")
candidates = reshape_candidates(scoring_inventory.artifacts)
if not candidates:
    st.info("Lv.20、初期3/4種類、全サブステータスのinitial_valueがそろった聖遺物がありません。")
    st.stop()

candidate_by_id = {artifact.id: artifact for artifact in candidates}
target_id = st.selectbox("再構築する聖遺物", tuple(candidate_by_id),
                         format_func=lambda artifact_id: f"{artifact_id} ({candidate_by_id[artifact_id].slot.value})")
target = candidate_by_id[target_id]
st.write(f"現在値: {display_substats(target)}")
dust_mode = st.radio("計算モード", ("簡易期待値モード", "詳細再構築モード"), horizontal=True)
target_stats = tuple(substat.stat for substat in target.substats)

if dust_mode == "簡易期待値モード":
    st.caption("既定値は初期値です。更新確率と更新幅は編集可能で、変更すると期待Damageへ即時反映されます。")
    simple_stat = st.selectbox("更新するサブステータス", target_stats,
                               format_func=lambda stat: STAT_LABELS.get(stat, stat.value))
    roll_tier = st.selectbox("更新幅の段階", DUST_ROLL_TIERS)
    tier_index = DUST_ROLL_TIERS.index(roll_tier)
    default_width = DEFAULT_DUST_ROLL_VALUES_DISPLAY[simple_stat][tier_index]
    width_unit = "%" if simple_stat in PERCENT_TYPES else "実数値"
    input_column, width_column = st.columns(2)
    update_probability_percent = input_column.number_input(
        "更新確率（%）", min_value=0.0, max_value=100.0, value=DEFAULT_DUST_UPDATE_PROBABILITY_PERCENT,
        step=0.1, help="初期値。編集可能。0〜100%で入力します。")
    improvement_width = width_column.number_input(
        f"更新時の改善幅（{width_unit}）", min_value=0.0, value=float(default_width), step=0.01,
        key=f"simple-width-{target.id}-{simple_stat.value}-{roll_tier}", help="初期値。編集可能。")
    internal_width = roll_value_to_internal(simple_stat, improvement_width)
    updated_substats = tuple(Substat(substat.stat, substat.value + internal_width, substat.initial_value)
                             if substat.stat == simple_stat else substat for substat in target.substats)
    successful_artifact = replace(target, substats=updated_substats)
    successful_inventory = replace_inventory_artifact(scoring_inventory, target.id, successful_artifact)
    successful_best = optimize(successful_inventory, score_function, constraint)
    current_damage = original_best.score
    successful_damage = successful_best.score
    kept_success_damage = max(current_damage, successful_damage)
    probability = update_probability_percent / 100
    expected_damage = probability * kept_success_damage + (1 - probability) * current_damage
    expected_improvement_rate = expected_damage / current_damage - 1 if current_damage else 0.0
    first_row = st.columns(4)
    first_row[0].metric("入力した更新確率", f"{update_probability_percent:.2f}%")
    first_row[1].metric("入力した更新幅", f"{improvement_width:.2f}{width_unit}")
    first_row[2].metric("現在Damage", f"{current_damage:.2f}")
    first_row[3].metric("更新成功時Damage", f"{successful_damage:.2f}")
    second_row = st.columns(3)
    second_row[0].metric("失敗時Damage", f"{current_damage:.2f}")
    second_row[1].metric("期待Damage", f"{expected_damage:.2f}")
    second_row[2].metric("期待改善率", f"{expected_improvement_rate:.4%}")
    st.caption("元に戻せるため、失敗時は現在Damageを維持します。成功時も現在Damageより低ければ元を保持します。")
else:
    st.caption("全再構築結果を列挙する既存モデルです。4段階の更新確率と更新幅は初期値入りで編集できます。")
    with st.form("reshape_conditions"):
        default_selected = tuple(stat for stat in (Stat.CRIT_RATE, Stat.CRIT_DMG) if stat in target_stats)
        if len(default_selected) < 2:
            default_selected = target_stats[:2]
        selected_stats = st.multiselect("優先する追加ステータス（2種類）", target_stats, default=list(default_selected),
                                        max_selections=2, format_func=lambda stat: STAT_LABELS.get(stat, stat.value))
        tier = st.selectbox("保証段階", tuple(GuaranteeTier), format_func=lambda value: TIER_LABELS[value])
        roll_model_id = st.text_input("ロール値モデルID", value="wiki_default_editable")
        st.caption("更新幅は表示単位です。割合ステータスは%、実数ステータスは実数値で入力します。各確率の合計は100%にします。")
        roll_inputs: dict[Stat, tuple[list[float], list[float]]] = {}
        for stat in target_stats:
            label = STAT_LABELS.get(stat, stat.value)
            unit = "%" if stat in PERCENT_TYPES else "実数値"
            st.markdown(f"**{label}（更新幅: {unit}）**")
            value_columns = st.columns(4)
            values = [value_columns[index].number_input(
                f"{label} 更新幅（{roll_tier}）", min_value=0.0,
                value=float(DEFAULT_DUST_ROLL_VALUES_DISPLAY[stat][index]), step=0.01,
                key=f"detail-value-{target.id}-{stat.value}-{roll_tier}")
                for index, roll_tier in enumerate(DUST_ROLL_TIERS)]
            probability_columns = st.columns(4)
            probabilities = [probability_columns[index].number_input(
                f"{label} 更新確率（{roll_tier}、%）", min_value=0.0, max_value=100.0,
                value=DEFAULT_DUST_ROLL_PROBABILITIES_PERCENT[index], step=0.1,
                key=f"detail-probability-{target.id}-{stat.value}-{roll_tier}")
                for index, roll_tier in enumerate(DUST_ROLL_TIERS)]
            roll_inputs[stat] = (values, probabilities)
        max_rows = st.number_input("表示する結果の最大件数", min_value=10, max_value=5000, value=100, step=10)
        calculate = st.form_submit_button("再構築を計算")

    if calculate:
        try:
            if len(selected_stats) != 2:
                raise ValidationError("優先する追加ステータスを2種類選んでください")
            raw_distributions = []
            for stat in target_stats:
                values, probabilities = roll_inputs[stat]
                rolls = [{"value": roll_value_to_internal(stat, value), "probability": probability / 100}
                         for value, probability in zip(values, probabilities, strict=True) if probability > 0]
                raw_distributions.append({"stat": stat.value, "rolls": rolls})
            raw_conditions = {
                "selected_stats": [stat.value for stat in selected_stats], "guarantee_tier": TIER_INPUT_NAMES[tier],
                "allocation_model": "go_capped_binomial", "roll_model_id": roll_model_id,
                "roll_distributions": raw_distributions,
            }
            conditions = reshape_conditions_from_dict(raw_conditions)
            analysis = analyze_reshape(scoring_inventory, target, conditions, score_function, constraint)
        except (ValidationError, DustError, OptimizationError, ValueError) as error:
            st.error(f"再構築を計算できません: {error}")
        else:
            baseline_damage = analysis.original_best.score
            expected_improvement_rate = analysis.expected_improvement / baseline_damage if baseline_damage else 0.0
            conditional_improvement = (analysis.expected_improvement / analysis.optimal_set_update_probability
                                       if analysis.optimal_set_update_probability else 0.0)
            conditional_improvement_rate = conditional_improvement / baseline_damage if baseline_damage else 0.0
            update_column, chosen_column, improvement_column, conditional_column = st.columns(4)
            update_column.metric("更新確率", f"{analysis.optimal_set_update_probability:.2%}")
            chosen_column.metric("元に戻せることを考慮した期待Damage", f"{analysis.expected_chosen_score:.2f}")
            improvement_column.metric("期待改善率", f"{expected_improvement_rate:.4%}")
            conditional_column.metric("更新時だけの平均改善率", f"{conditional_improvement_rate:.4%}")
            st.caption(f"全{len(analysis.outcomes)}結果。Akasha推定Damageが現在の最適値を厳密に上回る場合だけ再構築後を採用します。")

            sorted_outcomes = sorted(analysis.outcomes, key=lambda item: item.reshape_outcome.probability, reverse=True)
            rows = []
            for outcome in sorted_outcomes[:int(max_rows)]:
                decision = "再構築後を採用" if outcome.decision == ReshapeDecision.APPLY_RESHAPE else "元を保持"
                rows.append({"確率": outcome.reshape_outcome.probability, "判断": decision,
                             "再構築後所持品の最適推定Damage": outcome.reshaped_inventory_best.score,
                             "選択後の推定Damage": outcome.chosen_best.score,
                             "再構築後サブステータス": display_substats(outcome.reshape_outcome.artifact),
                             "選択後の最適5部位": " / ".join(item.id for item in outcome.chosen_best.artifacts)})
            st.dataframe(rows, use_container_width=True, hide_index=True,
                         column_config={"確率": st.column_config.NumberColumn(format="%.6f")})
