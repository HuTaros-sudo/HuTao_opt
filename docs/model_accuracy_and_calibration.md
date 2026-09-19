# Model accuracy and calibration

更新日: 2026-09-19

## Model layers

本プロジェクトは、Hu Tao Akasha評価を次の3層に分離する。

1. **Core Model v1 (`physics_based_estimate`)**: ゲーム式と、これまで境界検証した入力からDamageを計算する。公開APIは`score_hutao_akasha()`である。
2. **Empirical calibration (`empirical_homa_r1_calibration`)**: CoreのaggregateへLeaderboard固有の正の定数scaleを掛け、絶対表示値を保存済みAkasha snapshotへ近づける。
3. **Uncertainty**: 保存済みbuildで観測した絶対誤差と順位誤差を表示する。Akasha内部仕様の確率ではない。

較正はCoreのATK式、Damage式、component、optimizer評価関数へ入れない。`raw_score = score_hutao_akasha(...).aggregate_score`としたとき、表示専用値だけを`calibrated_score = raw_score × calibration_scale`で求める。

## Core Model v1で固定する仕様

ゲーム仕様またはaggregate観測から確認済みとして扱うもの:

- Hu Tao Lv90、Staff of Homa R1を対象とする正規化
- 4 N1 vape + 7 N1 non-vape + 11 CA vape
- Q quantityは4pc Shimenawaで1/3、その他で2/3
- DEF関数とRESのpiecewise関数を別々に適用する構造
- 正の共通scaleがbuild順位と改善率を変えない数学的性質

Akasha観測から`strongly_supported`として固定するもの:

- H1: raw Max HP境界、LeaderboardのHu Tao E Talent Lv10、表示倍率6.26%
- H4: raw EM境界、external EM baseline、Vaporize入力境界
- H5: raw ATK境界とcombat ATKの分離
- H6: raw Pyro Damage Bonus境界、Kazuha A4、Freedom-Sworn、set固有Damage Bonus
- H7: raw CR/CD境界と期待会心倍率

未解決のまま固定baselineを使うもの:

- H3: enemy level、DEF/RESのAkasha固有条件
- Akasha backendの内部丸め・中間値
- anonymous Hydro slotの完全なmetadata
- Homaで観測された約326.9 ATK相当の定数残差
- cross-weaponで見えたaffineまたはweapon-specificな差

約326.9 ATKをCoreへ足さなかった理由は、Homaだけではflat ATKとbase-ATK比例項を識別できず、Ballad比較後も純flat・純比例のどちらにも一致しなかったためである。2武器水準のaffine fitは2パラメータで必ずカテゴリ平均を通るため、仕様の証拠にならない。未知部分を任意係数で埋めると、ゲーム式と観測補正の責務が混ざる。

## Homa R1 Calibration Profile

| field | value |
|---|---|
| leaderboard ID | `1000004605` |
| weapon | Staff of Homa R1 |
| sample date | 2026-09-13 |
| sample count | 20 |
| full-sample scale | 1.0768838049202214 |
| validation error | Leave-One-Out mean absolute relative error 0.188197% |
| status | `empirical_homa_r1_calibration` |

このprofileはHoma R1の該当Leaderboard専用である。Ballad of the Fjords、Staff of the Scarlet Sands、他のteam/categoryへは適用しない。APIはleaderboard IDとweaponの両方を検査し、不一致時はエラーにする。

## Leave-One-Out validation

各foldで19 buildだけから最小二乗common scaleを求め、除外した1 buildのAggregateを予測した。

| metric | result |
|---|---:|
| fitted scale minimum | 1.0765542591 |
| fitted scale maximum | 1.0771120600 |
| fitted scale mean | 1.0768838460 |
| fitted scale median | 1.0769037484 |
| fitted scale std | 0.0001277453 |
| validation mean relative error | -0.000851% |
| validation median relative error | +0.037220% |
| validation MAE | 0.188197% |
| validation max absolute error | 0.624792% |
| validation residual std | 0.239708% |
| median absolute relative error | 0.172429% |
| empirical 80% interval | -0.237158% ～ +0.230275% |
| empirical 90% interval | -0.353931% ～ +0.348240% |

intervalは20個のLeave-One-Out relative residualの実測quantileである。正規分布やAkasha内部の確率を仮定していない。これは**保存済みvalidation buildに対する経験的誤差**であり、新しいbuildや別カテゴリに同じ範囲を保証しない。

## Relative ordering and comparison guidance

保存済み20 buildのpairwise validation結果:

| observed Damage gap | pairwise ordering accuracy |
|---|---:|
| 0.1%未満 | 40.00% |
| 0.25%未満 | 54.17% |
| 0.5%未満 | 72.00% |
| 1.0%未満 | 80.95% |
| 全pair | 91.58% |

GUIの経験的な目安:

| Core Damage差 | label |
|---|---|
| 0.25%未満 | `very uncertain` |
| 0.25%以上0.5%未満 | `uncertain` |
| 0.5%以上1.0%未満 | `moderate confidence` |
| 1.0%以上 | `higher confidence` |

このlabelはvalidation datasetを要約したもので、個別比較が正しい確率ではない。特に0.1〜0.5%の更新を確実な改善として扱う用途には現在の順位精度が不足する。

## GUI and optimizer behavior

GUIの「Akasha表示補正を使用」は絶対Damageの表示だけを切り替える。ONでは「Akasha較正推定Damage」、OFFでは「Core推定Damage」を表示する。詳細欄でCore値、scale、較正値、model statusを確認できる。

optimizer、詳細dust列挙、簡易dust、元Artifactと再構築後Artifactの採用判定は、常にCore Model v1を評価関数として使う。正の共通scaleは順位も改善率も変えない。採用判定の±0.5%閾値とconfidence labelもCoreの相対差に基づく。

Model status:

- Core model: `physics_based_estimate`
- Calibration: `empirical_homa_r1_calibration`
- Akasha backend: `partially_unresolved`
- H3: `unresolved`
- Absolute score: `calibrated estimate`
- Relative ordering: `empirically validated`

## Appropriate uses and limits

現在モデルを使える用途:

- Homa R1該当シナリオで、候補間に十分な差がある聖遺物最適化
- Core modelによる再構築前後の一貫した相対比較
- Homa R1 snapshotへ近い桁感で絶対Damageを表示する参考値
- モデル誤差を明示した探索・実験

慎重に扱う用途:

- 0.1〜0.5%程度の聖啓の塵更新判断
- 別武器、別team、別Leaderboardへの絶対Damage較正
- Akasha順位の厳密な再現
- Akasha backendと完全一致するDamageとしての表示

## Reverse engineering pause

次の新情報が得られるまでは、ブラックボックス式の追加推測を主要タスクにしない。

- Akasha backendまたはintermediate values
- controlled weapon-switch experiment
- unknown Hydro slot metadata
- 安全に武器固有処理を再現できる第3武器カテゴリ

その間はCore Model v1、Leaderboard別calibration、validation由来uncertaintyを独立して保守する。
