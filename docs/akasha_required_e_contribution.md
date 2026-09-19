# required final ATK / required E contribution 診断

## 目的と固定条件

保存済みLeaderboard 20 buildについて、N1 non-vapeだけを使い、ATK以外の現在のbaselineを固定して必要ATKを逆算した。Vaporizeを含まないためH4の影響は受けない。H1/H4/H5/H6は現行実装を維持し、H3はenemy Lv90・base Pyro RES 10%・VV 40%のunresolved baselineのままである。EはLeaderboard metadataが支持するTalent Lv10、表示倍率6.26%を本番値として維持した。任意倍率や補正係数は本番評価関数へ追加していない。

入力はGit管理外の保存済みAkasha rawである。出力CSVも公開player識別子を含むため`.gitignore`対象の`data/akasha/`へ保存する。

## 逆算式

現行エンジンのN1 non-vapeは、内部丸めなしのbaselineで次式になる。

```text
predicted N1 non-vape
= final ATK
× N1 talent multiplier
× Damage Bonus multiplier
× CRIT expectation multiplier
× enemy DEF multiplier
× enemy RES multiplier
× 1.0
```

buildごとにATK以外の積を`fixed_non_atk_multiplier`として固定し、次のように解いた。

```text
required final ATK = observed N1 non-vape / fixed_non_atk_multiplier
required E ATK bonus
= required final ATK
- normalized precombat ATK
- external combat ATK bonus
```

`normalized precombat ATK`はraw `stats.atk`そのものであり、artifact ATK、炎共鳴、Homa 0.8%、Homa low-HP 1.0%を再加算していない。`external combat ATK bonus`は現在のbaselineでMillennial Movement 20%、Amber C6 0%である。

## build別結果

`data/akasha/required_final_atk.csv`に20 buildの逆算結果を保存した。

| 指標 | 最小 | 最大 | 平均 |
| --- | ---: | ---: | ---: |
| required final ATK | 4206.332 | 4782.985 | 4533.534 |
| predicted final ATK | 3879.469 | 4456.032 | - |
| required E ATK bonus | 2248.455 | 2645.472 | 2481.034 |
| required - predicted E | 326.863 | 326.992 | 326.910 |
| required E / Max HP | 7.1428% | 7.3248% | 7.2119% |

`required E / Max HP`を切片なしのE倍率と解釈すると7%台に見えるが、これは妥当ではない。required Eには、現在のATK境界で説明されないほぼ一定の約326.91 ATKも押し込まれているためである。

## 線形診断

20 buildへ次の診断回帰を行った。

```text
required E ATK bonus ≈ slope × Max HP + intercept
```

| slope | intercept | R² | regression residual std |
| ---: | ---: | ---: | ---: |
| 0.06260699 | 326.66925 | 0.9999998951 | 0.03107 ATK |

slopeは表示Talent Lv10の6.26%とほぼ一致する。一方、約326.67 ATKの正の切片がある。したがってbuild依存形状は「E倍率が大きく違う」よりも、「Lv10のHP比例項に、ほぼbuild非依存の加算ATKが不足している」形で説明される。

## 既知のE倍率候補

`data/akasha/required_e_contribution.csv`には、各build×4候補のrequired Eとの差とN1予測を保存した。`build-dependent residual std`は`required E - candidate E`の20 build間標準偏差、ordering accuracyはobserved/predicted N1 non-vapeの全pair比較である。

| E候補 | 倍率 | requiredとの差平均 | 絶対差平均 | residual std | residual vs Max HP | N1 ordering accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Lv9 | 5.96% | +430.143 | 430.143 | 4.608 | +0.99998 | 97.3684% |
| Lv10 | 6.26% | +326.910 | 326.910 | **0.033** | +0.32589 | 96.8421% |
| Lv11 | 6.56% | +223.677 | 223.677 | 4.586 | -0.99998 | 96.8421% |
| Lv13 | 7.15% | +20.652 | 20.978 | 13.627 | -1.00000 | 95.7895% |

Lv13は平均絶対差だけなら小さいが、HPに応じた系統残差を増やし、順位性能も悪化する。Lv9はN1順位がわずかに良いが、残差がMax HPへほぼ完全相関し、Leaderboard metadataとも矛盾する。build依存残差stdが最小なのはLv10であり、Lv10を本番採用した現状を変更する根拠はない。

## Homaとの切り分け

診断表にはHoma 0.8%、low-HP 1.0%、合計1.8%のMax HP由来ATKを表示した。合計値は552.535〜666.667 ATKであるが、raw ATKへ含まれるためDamage計算へ再加算していない。

`required - predicted E`とMax HP、Homa合計ATK、predicted E ATKのPearson相関は、いずれも約+0.32589だった。3変数は同じMax HPの定数倍なので、この相関だけではHomaとEを識別できない。ただしrequired E回帰のslopeが6.26%と一致し、残差が326.863〜326.992 ATKのほぼ定数であるため、Homa 1.8%またはE倍率の内部精度差のようなHP比例誤差の形には近くない。

## 判断と次の検証候補

今回の診断はE Talent Lv10を支持する。約7.1%のDamage不足をE倍率へ押し込むと誤ってLv13付近に見えるが、切片を許したbuild間診断ではLv10 slopeと約326.67 ATKの不足へ分離できた。本番`score_hutao_akasha()`は変更していない。

次は、約326.9 ATKというほぼ一定の不足を説明できる項目を1つずつ検証する。

1. Akasha raw `stats.atk`と戦闘計算用ATKの間に、base ATKへ比例する固定combat buffが未加算か確認する。326.91 / 714.5089773は約45.75%であるが、この比を補正値として採用しない。
2. N1 non-vapeの観測値またはrawに、現在未確認の固定ATK加算・チームbuff metadataがないかfrontend/APIの中間値を再調査する。
3. H3の共通乗算誤差がATK逆算で偶然ほぼ定数に見える可能性を、raw ATK・final ATKとの残差相関で分離する。
4. Homa/EはMax HP比例項としてまとめて感度分析し、既知係数だけでは約326.9の定数残差を作れないことを再確認する。
