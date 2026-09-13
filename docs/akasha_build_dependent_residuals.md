# Akasha胡桃 build依存残差の診断

検証日: 2026-09-14  
対象: `VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1`  
標本: 保存済み20 build（火魔女4pc 19件、しめ縄4pc 1件）

## 方法

baselineは`score_hutao_akasha(build, ScenarioConfig())`で、H3はenemy Lv90 / base Pyro RES 10% / VV 40%のunresolved状態を維持した。共通scaleを本番評価関数へ追加していない。

診断用scaleは、全buildについて`observed ≈ scale × predicted`となる最小二乗値である。build依存残差を次で定義した。

```text
common_scale = Σ(observed × predicted) / Σ(predicted²)
ratio_residual = observed / predicted - common_scale
```

この符号では、負の残差は「そのbuildで予測が共通scaleから見て相対的に高い」ことを表す。従来の`predicted / observed - 1`とは符号が反転する点に注意する。

## baseline残差

| 診断値 | 結果 |
|---|---:|
| common scale | 1.0768838049 |
| scale除去後ratio residual std | **0.00245724（0.245724%）** |
| 火魔女19件だけのresidual std | **0.00238130（0.238130%）** |
| 火魔女19件のresidual範囲 | -0.439012%〜+0.643897% |
| しめ縄1件のresidual | -0.350181% |

しめ縄は1件だけなのでset効果を一般化しない。火魔女19件だけでもほぼ同じ残差幅が残り、set差だけが順位誤差の原因ではない。

build別の入力・比率・残差は[`build_dependent_residuals.csv`](../data/akasha/build_dependent_residuals.csv)に保存した。HP%とflat HPは、H1でAkashaカードの表示値から独立再構築した値であり、内部floatそのものではない。

## 入力との相関

### 全20 build

| 入力 | Pearson | Spearman |
|---|---:|---:|
| Max HP | **-0.9205** | **-0.9414** |
| raw ATK | -0.7443 | -0.6737 |
| E ATK bonus | **-0.9205** | **-0.9414** |
| artifact HP% | **-0.9285** | **-0.9296** |
| artifact flat HP | +0.0261 | +0.1771 |
| artifact EM | +0.5224 | +0.3654 |
| CRIT Rate | +0.0248 | -0.0887 |
| CRIT DMG | +0.3469 | +0.4526 |
| Pyro DMG Bonus | +0.3283 | +0.0977 |
| total crit multiplier | +0.4870 | +0.4150 |
| Max HP / raw ATK | -0.4598 | -0.4962 |
| E bonus / final ATK | -0.5047 | -0.5308 |
| predicted aggregate | -0.2597 | -0.2571 |
| observed aggregate | -0.0710 | +0.0226 |

### 火魔女19 build

| 入力 | Pearson | Spearman |
|---|---:|---:|
| Max HP / E ATK bonus | **-0.9393** | **-0.9456** |
| artifact HP% | **-0.9390** | **-0.9319** |
| raw ATK | -0.7170 | -0.6211 |
| Max HP / raw ATK | -0.5973 | -0.6228 |
| E bonus / final ATK | -0.6351 | -0.6632 |
| artifact EM | +0.5508 | +0.3842 |
| total crit multiplier | +0.5541 | +0.5211 |
| Pyro DMG Bonus | +0.0368 | -0.0404 |
| observed aggregate | -0.0038 | +0.1175 |

set差を除いてもMax HP、E bonus、artifact HP%が最も強い。E bonusは現在`Max HP × 6.26%`でcap未到達なので、Max HPと完全な線形関係にあり、この標本だけでは両者を別要因として識別できない。raw ATKにもHomaのMax HP依存ATKが入るため、HPとraw ATKの相関も交絡する。

PearsonとSpearmanがともに強く、火魔女だけでも維持されるため、HP依存性は単一の外れ値だけでは説明しにくい。ただし20件しかなく、HP%、EM、会心、raw ATKのstat配分にも相関があるので、この相関だけでE式を変更しない。

## E倍率の離散候補

N1/CA/Q倍率、敵条件、ATK境界などを固定し、Eの既知Talent倍率だけをLv9 5.96%、Lv10 6.26%、Lv11 6.56%、Lv13 7.15%へ切り替えた。各候補ごとに別の診断scaleを除き、絶対Damageの近さではなく残差stdとorderingを比較した。

### 全20 build

| E候補 | residual std | 全pair | <0.1% | <0.25% | <0.5% |
|---|---:|---:|---:|---:|---:|
| **Lv9 5.96%** | **0.228750%** | **92.6316%** | **50.00%** | **58.33%** | **74.00%** |
| Lv10 6.26% | 0.245724% | 91.5789% | 40.00% | 54.17% | 72.00% |
| Lv11 6.56% | 0.269087% | 90.0000% | 30.00% | 50.00% | 66.00% |
| Lv13 7.15% | 0.321119% | 89.4737% | 30.00% | 50.00% | 66.00% |

### 火魔女19 build

| E候補 | residual std | 全pair | <0.1% | <0.25% | <0.5% |
|---|---:|---:|---:|---:|---:|
| **Lv9 5.96%** | **0.213047%** | **91.8129%** | **44.44%** | **54.55%** | **71.74%** |
| Lv10 6.26% | 0.238130% | 90.6433% | 33.33% | 50.00% | 69.57% |
| Lv11 6.56% | 0.267449% | 88.8889% | 22.22% | 45.45% | 63.04% |
| Lv13 7.15% | 0.326531% | 88.3041% | 22.22% | 45.45% | 63.04% |

順位だけではLv9が最良で、E倍率が上がるほど残差stdとorderingが一方向に悪化した。これは高HP buildを現在モデルが相対的に高く評価しているという相関結果と整合する。

ただし、LeaderboardはLv10固定であることがH1でstrongly supportedであり、rawの`talentsLevelMap`も全件Lv10を示す。Lv9を本番値へ採用すると既知条件と衝突する。従ってこの結果は「AkashaがLv9を使用する」証拠ではなく、現在のbase damage経路に別のHP依存の過大評価があり、Lv9がその代理補正になっている可能性を示す。

## baseAtk候補

| 候補 | residual std | 全pair | <0.1% | <0.25% | <0.5% |
|---|---:|---:|---:|---:|---:|
| raw 714.5089773 | **0.245724%** | 91.5789% | 40.00% | 54.17% | 72.00% |
| 表示値714 | 0.245813% | 91.5789% | 40.00% | 54.17% | 72.00% |

火魔女19件でもraw値0.238130%、表示値0.238216%で、順位と全近接accuracyは完全に同じだった。表示値714は残差stdをわずかに悪化させる。raw `stats.baseAtk`を保持する現在の境界が妥当で、baseAtk内部値は近接順位誤差の主要因ではない。

全候補の数値は[`e_candidate_ranking_comparison.csv`](../data/akasha/e_candidate_ranking_comparison.csv)に保存した。baseAtk候補も`candidate_kind=base_atk`として同じ診断表へ含めた。

## 判定と次の候補

最も強いbuild依存要因は **Max HPに連動するATK寄与**である。ただし、現在のデータでは次の要素が同時にMax HPへ比例する。

- raw ATK内のHoma 0.8% + low-HP 1.0%
- Hu Tao EのMax HP × 6.26%
- artifact HP%によるraw Max HP

次に修正値を入れる前に、各buildについて共通倍率を除いた`required final ATK`を逆算し、`raw ATK + external ATK`を差し引いたrequired E contributionの傾きと切片を診断するべきである。これは原因区分用であり、傾きを任意のE倍率として本番採用してはいけない。その後、raw ATKに含まれるHoma HP由来部分の内部精度と、raw Max HPからEへ渡す丸め順を独立に再確認する。

H3は引き続きunresolvedであり、共通scaleは本番評価関数へ入れていない。Lv10 6.26%もbaselineのまま維持した。

