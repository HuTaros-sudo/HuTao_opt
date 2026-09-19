from pathlib import Path

from streamlit.testing.v1 import AppTest

import genshin_opt


def test_package_import():
    assert genshin_opt.__file__ is not None


def test_app_startup():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)

    assert not app.exception
    assert [element.value for element in app.title] == ["原神 聖遺物最適化ツール"]
    assert any(element.value == "Optimizer" for element in app.subheader)
    assert any(element.value == "聖啓の塵" for element in app.subheader)
    metric_labels = {element.label for element in app.metric}
    assert "Akasha推定Damage" in metric_labels
    assert "N1 non-vape Avg DMG" in metric_labels
    assert not app.error


def test_production_gui_does_not_reference_toy_score_and_shares_akasha_evaluator():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")
    assert "toy_build_score" not in source
    assert "if current_score.is_estimate:" in source
    assert "optimize(scoring_inventory, score_function, constraint)" in source
    assert "optimize(successful_inventory, score_function, constraint)" in source
    assert "analyze_reshape(scoring_inventory, target, conditions, score_function, constraint)" in source


def test_simple_dust_defaults_are_editable_and_update_expected_damage():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    probability = next(field for field in app.number_input if field.label == "更新確率（%）")
    width = next(field for field in app.number_input if field.label.startswith("更新時の改善幅"))
    assert probability.value == 25.0
    assert width.value == 2.72
    expected_before = next(metric.value for metric in app.metric if metric.label == "期待Damage")
    probability.set_value(50.0).run(timeout=15)
    expected_after = next(metric.value for metric in app.metric if metric.label == "期待Damage")
    assert float(expected_after) > float(expected_before)
    width = next(field for field in app.number_input if field.label.startswith("更新時の改善幅"))
    width.set_value(0.0).run(timeout=15)
    expected_zero = next(metric.value for metric in app.metric if metric.label == "期待Damage")
    current = next(metric.value for metric in app.metric if metric.label == "現在Damage")
    assert expected_zero == current


def test_app_calculates_reshape_and_optimal_set_decision():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    app.radio[0].set_value("詳細再構築モード").run(timeout=15)
    for field in app.number_input:
        if "更新幅（" in field.label:
            field.set_value(1.0)
    app.button[0].click().run(timeout=15)

    assert not app.exception
    assert not app.error
    metric_labels = {element.label for element in app.metric}
    assert "更新確率" in metric_labels
    assert "元に戻せることを考慮した期待Damage" in metric_labels
    assert "期待改善率" in metric_labels
    assert "更新時だけの平均改善率" in metric_labels


def test_adoption_gui_copies_original_and_uses_akasha_score() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    app.radio[0].set_value("再構築結果の採用判定").run(timeout=15)
    original_value = next(field for field in app.number_input if field.label.startswith("substat 1値"))
    original_value.set_value(12.34).run(timeout=15)
    copy_button = next(button for button in app.button if button.label == "元の聖遺物を再構築後へコピー")
    copy_button.click().run(timeout=15)
    matching = [field.value for field in app.number_input if field.label.startswith("substat 1値")]
    assert matching == [12.34, 12.34]
    compare_button = next(button for button in app.button if button.label == "採用判定を実行")
    compare_button.click().run(timeout=15)
    metric_labels = {metric.label for metric in app.metric}
    assert "元の場合の最適Akasha推定Damage" in metric_labels
    assert "再構築後の最適Akasha推定Damage" in metric_labels
    assert "判定" in metric_labels
    assert any(metric.label == "判定" and metric.value == "差が小さく、現モデルでは判定不確実" for metric in app.metric)
    source = app_path.read_text(encoding="utf-8")
    assert "compare_artifact_adoption(scoring_inventory" in source
    assert "reconstructed_artifact, score_function, constraint" in source
    assert not app.exception
    assert not app.error
