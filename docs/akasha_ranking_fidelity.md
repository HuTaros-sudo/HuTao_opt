# Akasha胡桃 推定Damageの順位再現性能

検証日: 2026-09-14  
対象: `VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1` (`leaderboard_id=1000004605`)  
標本: 保存済みLeaderboard rawの20 build

## 評価方法

各buildについて、観測値をAkasha `calculation.result`、予測値を`score_hutao_akasha(build, ScenarioConfig()).aggregate_score`とした。APIの`rank`には同順位表記が含まれる保存時点があるため、順位指標には`calculation.result`を降順に並べ直した順位を使った。API順位は監査用にCSVへ残した。

相対誤差は`predicted / observed - 1`。同点は平均順位を与え、Kendallはtau-bを使用する。観測同点のペアはordering accuracyの分母から除く。近接ペアの差は、2値の大きい方を分母にした`abs(A - B) / max(abs(A), abs(B))`である。

## 全体結果

| 指標 | 結果 |
|---|---:|
| Pearson correlation | **0.981689** |
| Spearman rank correlation | **0.938346** |
| Kendall tau-b | **0.831579** |
| 順位位置が完全一致 | **11 / 20 build** |
| Pairwise ordering accuracy | **174 / 190 = 91.5789%** |
| Aggregate平均相対誤差 | **-7.1403%** |

上位8 buildはすべて正しい順位位置だった。20件全体では11件が完全一致し、最大順位差は5位だった。build別の観測値、予測値、両順位と順位差は[`ranking_fidelity.csv`](../data/akasha/ranking_fidelity.csv)に保存した。

## 近接build

| Akasha Damage差 | ペア数 | Ordering accuracy |
|---|---:|---:|
| 0.1%未満 | 10 | **40.0000%** |
| 0.25%未満 | 24 | **54.1667%** |
| 0.5%未満 | 50 | **72.0000%** |
| 1.0%未満 | 84 | **80.9524%** |
| 全pair | 190 | **91.5789%** |

全体相関は高い一方、0.1%未満は偶然水準を下回り、0.25%未満は偶然水準に近い。この標本では、聖啓の塵による0.1〜0.25%の推定改善をAkasha上の順位改善として信頼できない。0.5%未満でも28%のペアが逆転した。全ペアの入力と判定は[`pairwise_ordering.csv`](../data/akasha/pairwise_ordering.csv)に保存した。

## 共通scale診断

最小二乗の共通scaleは **1.0768838049** だった。これは診断専用で、評価関数やGUIには組み込んでいない。

- scale前の平均相対誤差: -7.140290%
- scale後の平均相対誤差: -0.000882%
- scale前後で予測順位が変化したbuild: 0件
- scale前後でorderingが変化したpair: 0件

正の共通scaleはすべての予測値を同率で動かすため、数学的にも順位を変えない。したがって約7.1%の共通不足は絶対Damageの問題であり、順位誤りの直接原因はbuild依存残差である。scale後もbuild別誤差は残る。

## optimizer用途の判断

現評価関数は、候補間の推定Damage差が十分大きい場合の暫定optimizerには使える。全体のpairwise accuracy 91.6%と上位8件の位置一致は、大きな差の並べ替えには有用であることを示す。

一方、聖啓の塵で想定される0.1〜0.5%の微差には精度が足りない。GUIは結果を「Akasha推定Damage」と表示し、0.5%未満の差を確定的なAkasha順位改善として扱わない運用が必要である。特に0.25%未満は採否判断の参考値に留める。

Akasha公式ページは、Leaderboardが聖遺物強度比較用であり、キャラクターを同じ状態とteam buffへ正規化すると説明している。ただし個々の計算式は公開していない。[Akasha Leaderboards](https://akasha.cv/leaderboards?sort=addDate)

