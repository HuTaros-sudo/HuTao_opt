# Akasha胡桃 定数ATK残差の診断

検証日: 2026-09-19  
対象: 保存済みLeaderboard 20 build  
固定条件: H3 baseline、E Talent Lv10、H4/H5/H6の現行値

## 方法

N1 non-vapeの観測値から逆算したrequired_final_atkを使用した。ATK以外のtalent、Damage Bonus、CRIT、DEF、RESは現行baselineのまま固定し、観測値を変更していない。

現行baselineは次式である。

~~~
predicted final ATK
= raw stats.atk
+ base ATK × Millennial 20%
+ Hu Tao E Lv10
~~~

各候補は、raw後に適用する外部ATK構成を置き換えて比較した。CSVでは次の3量を分けている。

- configured_total_external_atk_pct: 候補の外部ATK%総量
- mean_candidate_bundle_atk: その総量をATKへ換算した値
- mean_increment_vs_current_atk: 現行20%から候補へ変えたときの実増分

したがって、20%+25%=45%候補のbundleは321.529 ATKで約326.9に近いが、現行20%からの実増分は25%=178.627 ATKである。45%全部を現行final ATKへ上乗せしていない。

## 離散候補の比較

[atk_buff_candidates.csv](../data/akasha/atk_buff_candidates.csv)に全指標を保存した。近接accuracyはAkasha観測Aggregate差を基準にした。

| 外部ATK候補（総量） | bundle ATK | 現行との差 | requiredとの差平均 | residual std | N1順序 | Aggregate順序 | 0.1% | 0.25% | 0.5% | 仕様上の評価 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 現行MM 20% | 142.902 | 0.000 | +326.910 | 0.0329 | 96.84% | 91.58% | 40.0% | 54.17% | 72.0% | baseline |
| 炎共鳴25%のみ | 178.627 | +35.725 | +291.184 | 0.0329 | 96.84% | 92.11% | 40.0% | 54.17% | 72.0% | rawの炎共鳴を二重計上 |
| MM 20% + 炎共鳴25% | 321.529 | +178.627 | +148.282 | 0.0329 | 98.42% | 94.74% | 50.0% | 62.5% | 80.0% | rawの炎共鳴を二重計上 |
| MM 20% + Amber C6 15% | 250.078 | +107.176 | +219.733 | 0.0329 | 98.42% | 94.21% | 50.0% | 62.5% | 78.0% | Amber適用は未確認 |
| 炎共鳴25% + Amber C6 15% | 285.804 | +142.902 | +184.008 | 0.0329 | 98.42% | 94.74% | 50.0% | 62.5% | 80.0% | 炎共鳴を二重計上、Amber未確認 |
| MM 20% + 炎共鳴25% + Amber 15% | 428.705 | +285.804 | +41.106 | 0.0329 | 99.47% | 97.37% | 50.0% | 79.17% | 90.0% | 炎共鳴二重、Amber未確認 |
| Elegy 20% + Freedom 20% | 285.804 | +142.902 | +184.008 | 0.0329 | 98.42% | 94.74% | 50.0% | 62.5% | 80.0% | 同種Millennialのためstack不可 |
| Elegy 20%のみ | 142.902 | 0.000 | +326.910 | 0.0329 | 96.84% | 91.58% | 40.0% | 54.17% | 72.0% | 有効な1回分 |
| Freedom 20%のみ | 142.902 | 0.000 | +326.910 | 0.0329 | 96.84% | 91.58% | 40.0% | 54.17% | 72.0% | 有効な1回分 |

bundle量だけなら45%候補が326.9 ATKへ最も近い。しかし現行20%はすでにfinal ATKへ入っているため、45%候補へ変更して増えるのは25%だけであり、不足は平均148.282 ATK残る。さらに、その25%はrawへ含まれる炎共鳴の再加算である。数値の近さは外部ATK構成を45%へ変更する根拠にならない。

60%候補は不足を41.106 ATKまで減らし順位も改善するが、raw炎共鳴の二重計上と、適用未確認のAmber C6を同時に含む。これも採用根拠にはならない。

## raw-based経路と独立再構築経路

独立経路は次の順に各項を1回だけ組み立てた。

~~~
independent precombat ATK
= base ATK × (1 + artifact ATK% + artifact set ATK% + Pyro Resonance 25%)
+ artifact flat ATK
+ Max HP × Homa 0.8%
+ Max HP × Homa low-HP 1.0%

independent final ATK
= independent precombat ATK
+ base ATK × one Millennial 20%
+ Hu Tao E Lv10
~~~

現行raw-based経路との差は平均+0.235 ATK、最大絶対差0.799 ATKだった。[constant_atk_residuals.csv](../data/akasha/constant_atk_residuals.csv)にbuild別の聖遺物ATK、護摩、炎共鳴、Millennial、E、両経路のfinal ATKを保存した。

この一致は、raw fieldを起点にしたことで既知のATK項を落としている可能性を支持しない。独立再構築でも約326.9 ATK不足は残る。rawと独立経路の差は聖遺物表示丸めの範囲であり、326.9 ATKの原因にはならない。

## H3との交絡

実測missing ATKと入力値の相関は次の通りである。

| 比較 | Pearson | Spearman |
| --- | ---: | ---: |
| missing vs predicted final ATK | +0.67363 | +0.56992 |
| missing vs raw ATK | +0.99405 | +0.98195 |
| missing vs Max HP | +0.32589 | +0.33534 |

相関係数だけを見るとraw ATKとの関係が強いが、missingの実際の振幅は326.8627〜326.9923 ATK、標準偏差0.0329 ATKにすぎない。非常に狭い範囲の微小変動へ順位相関が付いているため、326.9 ATK本体がraw ATK比例だとは解釈しない。

H3だけが原因なら、共通scale sに対して次になる。

~~~
required final ATK = s × predicted final ATK
missing ATK = (s - 1) × predicted final ATK
~~~

20 buildの最小二乗scaleは1.07763775だった。このH3-onlyモデルが予測するmissing範囲は301.193〜345.956 ATK、標準偏差10.184 ATKである。実測範囲326.863〜326.992 ATK、標準偏差0.0329 ATKとは形が大きく異なる。H3は絶対Damageの共通scaleへ影響し得るが、H3単独では今回のほぼ定数のATK不足を説明できない。

## 判定

1. 約326.9 ATKへbundle量が最も近い既知候補はMillennial 20% + 炎共鳴25%の321.529 ATKである。
2. 現行20%を置き換える候補としての実増分は178.627 ATKに留まり、残り148.282 ATKを説明できない。炎共鳴25%はrawにも含まれる。
3. ElegyとFreedom-SwornのATK +20%は同種Millennial効果なので、両方を+40%としてstackできない。
4. Amber C6を含む候補でも不足を説明し切れず、対象scenarioでC6 15%が有効という公開backend根拠もない。
5. raw-basedと独立再構築は最大0.799 ATK以内で一致し、raw境界の誤解では326.9 ATKを説明できない。
6. H3-onlyならmissingが約44.76 ATK幅で変動するはずだが、実測幅は約0.13 ATKであり、定数残差の形と一致しない。

したがって、本番score_hutao_akasha()を変更する根拠は得られなかった。任意の+326.9 ATK、45.7%、45%補正は追加していない。次に調べる具体候補は、Akasha backendがLeaderboard説明とは別に持つ固定ATK sourceまたはprecombat→combatの未公開中間値である。公開rawに中間値がないため、新しい一次情報かfrontend/backend実装が得られるまではunresolvedとする。
