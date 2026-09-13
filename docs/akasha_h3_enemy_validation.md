# Akasha Hu Tao H3: 敵DEF・Pyro RES離散候補の検証

検証日: 2026-09-13  
対象: `VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1` (`leaderboard_id=1000004605`) の保存済み20 build

## 結論

H3は **unresolved** とする。

離散候補中では`enemy Lv80 / base Pyro RES 0% / VV 40%`が最も観測に近く、baselineの約7.1%不足のうち必要な共通倍率増分の93.23%を説明した。しかしAkashaの公開説明・API metadata・確認できたGitHub実装には、敵Lv80または基礎RES 0%を示す値がない。さらにDamageから観測できるのは`DEF multiplier × RES multiplier`の積だけで、DEFとRESを分離同定できない。この候補をAkasha仕様として固定しない。

H1/H5で固定したLv90胡桃、護摩R1、raw Max HP、E Lv10 6.26%、修正済みATK境界、Millennial Movement 20%、Amber C6 0%は変更していない。H4/H6、EM、Kazuha/Freedom-Sworn、Vaporize、N1/CA/Q倍率、観測値も変更していない。

事前のWeb調査と状態区分は[akasha_h3_enemy_research.md](akasha_h3_enemy_research.md)に分離した。

## 1. 計算方法

既存の`enemy_def_multiplier()`と`enemy_res_multiplier()`を別々に呼び、統合関数へ変更していない。

```text
DEF multiplier = (character Lv + 100)
  / ((character Lv + 100) + (enemy Lv + 100)
     × (1 - DEF reduction) × (1 - DEF ignore))

RES after VV = base Pyro RES - VV reduction

RES multiplier =
  1 - RES / 2           if RES < 0
  1 - RES               if 0 <= RES < 0.75
  1 / (4 × RES + 1)     if RES >= 0.75

common enemy multiplier = DEF multiplier × RES multiplier
```

character Lv90、DEF reduction 0、DEF ignore 0を全候補で固定した。

## 2. 理論倍率

| Candidate | Enemy Lv | Base RES | VV | DEF multiplier | RES after VV | RES multiplier | Common multiplier |
|---|---:|---:|---:|---:|---:|---:|---:|
| enemy80_res0_vv40 | 80 | 0% | 40% | 0.513514 | -40% | 1.200000 | **0.616216** |
| enemy80_res0_no_vv | 80 | 0% | 0% | 0.513514 | 0% | 1.000000 | 0.513514 |
| enemy80_res10_vv40 | 80 | 10% | 40% | 0.513514 | -30% | 1.150000 | 0.590541 |
| enemy80_res10_no_vv | 80 | 10% | 0% | 0.513514 | 10% | 0.900000 | 0.462162 |
| enemy90_res0_vv40 | 90 | 0% | 40% | 0.500000 | -40% | 1.200000 | 0.600000 |
| enemy90_res0_no_vv | 90 | 0% | 0% | 0.500000 | 0% | 1.000000 | 0.500000 |
| **enemy90_res10_vv40 (baseline)** | **90** | **10%** | **40%** | **0.500000** | **-30%** | **1.150000** | **0.575000** |
| enemy90_res10_no_vv | 90 | 10% | 0% | 0.500000 | 10% | 0.900000 | 0.450000 |
| enemy100_res0_vv40 | 100 | 0% | 40% | 0.487179 | -40% | 1.200000 | 0.584615 |
| enemy100_res0_no_vv | 100 | 0% | 0% | 0.487179 | 0% | 1.000000 | 0.487179 |
| enemy100_res10_vv40 | 100 | 10% | 40% | 0.487179 | -30% | 1.150000 | 0.560256 |
| enemy100_res10_no_vv | 100 | 10% | 0% | 0.487179 | 10% | 0.900000 | 0.438462 |

baselineでは同レベルかつDEF減少なしなのでDEF倍率は正確に0.5となる。基礎RES 10%から翠緑40%を引くと-30%で、負RES分岐`1 - (-0.30)/2`によりRES倍率は1.15となる。

## 3. 20 buildのAggregate比較

相対誤差は`predicted / observed - 1`。残差stdは20 buildの母標準偏差である。

| Candidate | Common | Aggregate平均誤差 | 残差std | H3 scale change | Remaining scale | 必要増分の説明率 |
|---|---:|---:|---:|---:|---:|---:|
| enemy80_res0_vv40 | 0.616216 | **-0.4841%** | 0.2268% | 1.071680 | **1.004855** | **93.23%** |
| enemy80_res0_no_vv | 0.513514 | -17.0701% | 0.1890% | 0.893067 | 1.205826 | -139.08% |
| enemy80_res10_vv40 | 0.590541 | -4.6306% | 0.2173% | 1.027027 | 1.048545 | 35.15% |
| enemy80_res10_no_vv | 0.462162 | -25.3631% | 0.1701% | 0.803760 | 1.339807 | -255.24% |
| enemy90_res0_vv40 | 0.600000 | -3.1029% | 0.2208% | 1.043478 | 1.032014 | 56.55% |
| enemy90_res0_no_vv | 0.500000 | -19.2524% | 0.1840% | 0.869565 | 1.238416 | -169.65% |
| **enemy90_res10_vv40** | **0.575000** | **-7.1403%** | **0.2116%** | **1.000000** | **1.076884** | **0.00%** |
| enemy90_res10_no_vv | 0.450000 | -27.3272% | 0.1656% | 0.782609 | 1.376018 | -282.75% |
| enemy100_res0_vv40 | 0.584615 | -5.5875% | 0.2151% | 1.016722 | 1.059172 | 21.75% |
| enemy100_res0_no_vv | 0.487179 | -21.3229% | 0.1793% | 0.847269 | 1.271006 | -198.65% |
| enemy100_res10_vv40 | 0.560256 | -9.5213% | 0.2062% | 0.974359 | 1.105223 | -33.35% |
| enemy100_res10_no_vv | 0.438462 | -29.1906% | 0.1614% | 0.762542 | 1.412229 | -308.85% |

`H3 scale change = candidate common / baseline common`、`Remaining scale = baseline required scale / H3 scale change`である。説明率が負の候補は不足を改善せず悪化させる。

baselineのAggregateに対するleast-squares required common scaleは **1.076883805**。連続的な敵レベルやRESへ逆算せず、診断値としてのみ保存した。最良離散候補のscale changeは1.071680376で、適用後も約0.4855%の共通scaleが残る。

候補ごとにleast-squares scaleを除いて再計算したAggregate residual stdは全候補で **0.227863%**だった。つまりH3変更は平均位置だけを動かし、build間残差形状を改善していない。

## 4. Component別残差

| Component | Baseline平均誤差 | Baseline std | Lv80/RES0/VV平均誤差 | Lv80/RES0/VV std |
|---|---:|---:|---:|---:|
| N1 non-vape | -7.2170% | 0.2115% | -0.5663% | 0.2267% |
| N1 vape | -7.1904% | 0.2113% | -0.5377% | 0.2264% |
| CA vape | -7.1195% | 0.2114% | -0.4618% | 0.2266% |
| Q vape | -7.2010% | 0.2112% | -0.5492% | 0.2264% |
| Aggregate | -7.1403% | 0.2116% | -0.4841% | 0.2268% |

最良候補でも全componentが同じ倍率で移動する。CAだけが他より約0.08〜0.10 percentage point高いという既存の小差は維持され、H3はその差を説明しない。

同一build内4 componentの`predicted / observed` relative ratio spread平均は、baselineも最良候補も **0.105076%**で完全に同じだった。絶対rangeは共通倍率に比例して0.097492%から0.104480%へ変わるだけである。

## 5. H1由来残差との分離

| 相関対象 | Baseline | Lv80/RES0/VV40 |
|---|---:|---:|
| Max HP | **+0.920405** | **+0.920405** |
| E ATK bonus | +0.920405 | +0.920405 |
| raw ATK | +0.744788 | +0.744788 |
| EM | -0.521030 | -0.521030 |
| CRIT Rate | -0.025265 | -0.025265 |
| CRIT DMG | -0.347326 | -0.347326 |

H3は全buildへ同じ正の倍率を掛けるため、Pearson相関は数値誤差を除いて変化しない。最良候補で平均不足が-0.48%まで縮んでもMax HP相関+0.9204は残る。したがって「共通倍率の大部分はこのH3候補と同じ大きさで説明できるが、HP依存の小さな残差は別に残る」と整理する。

## 6. H3の判定

- **confirmed**: DEF式、RES piecewise式、翠緑4pcの40%低下、各離散候補の理論倍率。
- **strongly supported**: 対象名とKazuha編成からVVが有効であること。VVなし候補は全てbaselineより大幅に悪化する。
- **unresolved**: Akasha固有の敵レベルと基礎Pyro RES。観測上はLv80/0%/VV40%が最良だが、公開metadataによる裏付けがなく、DEFとRESも積として交絡する。
- **rejected**: この20 buildと現在固定した他仮説の下では、VVなしを約7.1%不足の説明に使うこと。

H3全体は **unresolved**。本番baselineは資料上もっとも標準的なLv90/10%/VV40%のまま維持する。観測一致だけを理由にLv80/0%へ変更しない。

## 7. 次に検証する仮説

次は全componentへ共通し得る要素を、公開team metadataと時間条件から一つずつ確認する必要がある。H4/H6を同時に動かさず、まずH6のKazuha/Freedom-Sworn Damage Bonus境界を独立検証するのが適切である。特に、rawのPyro DMG Bonusに何が含まれ、Kazuha A4およびFreedom-Swornの通常・重撃Bonusをどの段階で追加するかを再構築する。

H3の候補を変更してもMax HP相関は解消しないため、H6検証後も相関が残る場合はH1の表示E倍率内部精度を再訪する。ただし複数仮説を同時fitしない。

## 8. 出力データ

- `data/akasha/h3_candidate_comparison.csv`: 1行=H3候補×component、合計60行。理論倍率、誤差統計、required scale、説明率を保存。
- `data/akasha/h3_build_residuals.csv`: 1行=H3候補×build、合計240行。5 componentの観測・予測・残差・ratio、component spread、入力相関を保存。
