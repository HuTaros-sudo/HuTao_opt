# Akasha胡桃 H6 Damage Bonus入力境界の検証

検証日：2026-09-13  
対象：`VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1`（calculation ID `1000004605`）  
標本：保存済みLeaderboard rawの20 build（火魔女4セット19件、しめ縄4セット1件）

## 検証範囲と根拠

この検証ではH1/H5のMax HP、胡桃E、ATK入力境界を維持し、H3はenemy Lv90、基礎Pyro RES 10%、VV 40%のbaselineを使った。EM、Vaporize、N1/CA/Q倍率、敵条件、ATK条件は変更していない。

ゲーム仕様の根拠は[KQM Hu Tao A4](https://library.keqingmains.com/characters/pyro/hu-tao#ascension-passives)、[KQM Kazuha A4](https://library.keqingmains.com/characters/anemo/kaedehara-kazuha#ascension-passives)、[KQM Freedom-Sworn](https://library.keqingmains.com/equipment/weapons/swords#freedom-sworn)、[KQM artifacts](https://library.keqingmains.com/equipment/artifacts)である。対象Leaderboardの公開説明はAkasha categories応答で `kazuha c2r1 @ 1000EM(1420)` と指定する。各効果の数値と一般式は[Akasha胡桃仕様書](akasha_hutao_spec.md)に記録済みである。

次の区分を維持した。

```text
common pyro bonus
= raw stats.pyroDamageBonus
 + Hu Tao A4（raw未包含）
 + Kazuha A4（raw未包含）
 + Crimson Witch E 1 stack（raw未包含）

N1 / CA attack-type bonus
= Freedom-Sworn 16%
 + Shimenawa 4pc 50%（該当buildのみ）

Q attack-type bonus = 0%
```

コードでは`CommonPyroDamageBonus`と`AttackTypeDamageBonus`を別型にし、Qへ通常・重撃Bonusを渡さない境界にした。

## 1. raw `stats.pyroDamageBonus` の再構築

20件すべての杯main statはPyro DMG Bonusだった。火魔女4セット19件のraw値は約61.6%、しめ縄4セット1件は約46.6%だった。元素Damage Bonusを与える聖遺物substatは存在せず、この標本に杯と火魔女2セット以外の静的な聖遺物由来Pyro Bonusはなかった。

候補式は次の通りである。

| 候補 | 再構築式 | 平均絶対差 | 最大絶対差 |
|---|---|---:|---:|
| **A** | **炎杯46.6% + 火魔女2pc 15%（該当時）** | **0.00000055 percentage points** | **0.00000098 pp** |
| B | A + 胡桃A4 33% | 33.0000 pp | 33.0000 pp |
| C | B + 火魔女4pc E 1 stack 7.5% | 40.1250 pp | 40.5000 pp |
| D | C + 万葉A4 56.8% | 96.9250 pp | 97.3000 pp |

候補AはAPIの浮動小数表現差だけで20件すべてに一致した。したがって、この保存標本のrawには炎杯と火魔女2セットの静的Bonusが含まれ、次は含まれない。

- 胡桃A4 33%
- 火魔女4セットのE 1 stack 7.5%
- 万葉A4
- しめ縄4セットの通常・重撃50%
- 蒼古の通常・重撃16%

最後の2項は炎元素Bonusではなく攻撃種別Bonusであり、raw Pyroフィールドに入れず戦闘計算時に該当攻撃へ加える。

build別の観測値、構成要素、4候補との差は[`h6_raw_pyro_bonus.csv`](../data/akasha/h6_raw_pyro_bonus.csv)に保存した。

## 2. 万葉A4の離散候補

raw境界を候補Aに固定し、蒼古16%としめ縄50%は従来baselineのまま、万葉A4だけを0%、1000 EM由来40.0%、1420 EM由来56.8%で比較した。誤差は`(predicted - observed) / observed`である。

| 万葉A4候補 | N1 non-vape平均 | N1 vape平均 | CA平均 | Q平均 | Aggregate平均 | Aggregate残差std | N1/CA対Q ratio gap | build内ratio spread |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| raw包含として追加0% | -26.3005% | -26.2793% | -26.2230% | -27.6574% | -26.3725% | 0.4433% | +1.4009 pp | 1.9886% |
| 1000 EM = +40.0% | -12.8614% | -12.8364% | -12.7699% | -13.2515% | -12.8287% | 0.2542% | +0.4421 pp | 0.5554% |
| **1420 EM = +56.8%** | **-7.2170%** | **-7.1904%** | **-7.1196%** | **-7.2010%** | **-7.1403%** | **0.2116%** | **+0.0394 pp** | **0.1051%** |

`N1/CA対Q ratio gap`は、各buildのN1平均・CA平均predicted/observed ratioとQ ratioとの差を20件で平均した値である。`build内ratio spread`は4 componentの最大ratioと最小ratioの差を、最小ratioで割った相対spreadの平均である。

1420 EM候補は公開説明と一致し、平均誤差、build間残差、component間ratio差のすべてで3候補中最良だった。任意のDamage Bonusはfitしていない。一方、全componentへ共通する約7.1%の不足は残るため、この結果だけで未解決の共通倍率を万葉A4へ帰属させることはできない。

全build・全候補の観測値、予測値、relative error、ratioは[`h6_kazuha_candidates.csv`](../data/akasha/h6_kazuha_candidates.csv)に保存した。

## 3. Freedom-Sworn 16%の独立比較

万葉A4を最有力の1420 EM候補へ一時固定し、Freedom-Swornの通常・重撃16%だけを有効・無効で比較した。Qには両候補とも適用していない。

| Freedom-Sworn | N1平均残差 | CA平均残差 | Q平均残差 | N1/CA対Q ratio gap | build内ratio spread | Aggregate平均 | Aggregate残差std |
|---|---:|---:|---:|---:|---:|---:|---:|
| **N1/CA +16%** | **-7.2037%** | **-7.1196%** | **-7.2010%** | **+0.0394 pp** | **0.1051%** | **-7.1403%** | **0.2116%** |
| 適用なし | -12.5801% | -12.5008% | -7.2010% | -5.3394 pp | 6.1686% | -11.9554% | 0.2125% |

16%を外してもQは完全に不変だが、N1/CAだけが約5.38 percentage points追加で不足する。+16%ではN1/CAとQのratio gapが0.0394 ppまで縮むため、対象計算でFreedom-Sworn 16%をN1/CAへ後付けする候補が強く支持される。

## 4. しめ縄4セットの単独ケース

該当buildはrank 4の1件だけだった。万葉56.8%・蒼古16%を維持し、しめ縄50%だけを比較した。

| しめ縄4pc | N1 non-vape | N1 vape | CA | Q | Aggregate | N1/CA対Q ratio gap | build内ratio spread |
|---|---:|---:|---:|---:|---:|---:|---:|
| **N1/CA +50%** | **-6.9191%** | **-6.8901%** | **-6.8191%** | **-6.9008%** | **-6.8365%** | **+0.0390 pp** | **0.1074%** |
| 適用なし | -22.3094% | -22.2853% | -22.2260% | -6.9008% | -21.5090% | -15.3608 pp | 19.8333% |

Qが不変のままN1/CAだけ整合するため、この1 buildについては50%をattack-type-specific bonusとして後付けする扱いが強く支持される。標本が1件なので、Akashaの全しめ縄buildへ一般化したconfirmed判定にはしない。

Freedom-Sworn全20件としめ縄単独比較は[`h6_freedom_sworn_candidates.csv`](../data/akasha/h6_freedom_sworn_candidates.csv)に保存した。

## 5. 残差形状と判定

採用した一時baseline（rawは静的聖遺物Bonus、胡桃A4 33%、火魔女stack 7.5%、万葉A4 56.8%、N1/CAへ蒼古16%、しめ縄buildのみさらに50%）は、H6検証前の数値設定と同じである。そのためAggregate平均誤差は **-7.1403%**、Aggregate residualとMax HPのPearson相関は **+0.9204** のままである。H6境界を正しく分離したこと自体は、この残存する共通不足とHP依存残差を解消しない。

4 componentの平均残差はN1 non-vape -7.2170%、N1 vape -7.1904%、CA vape -7.1196%、Q vape -7.2010%で、同一build内のratioは平均0.1051%の範囲に収まる。したがって現在の主要残差はN1/CA/Q固有のDamage Bonus欠落という形ではなく、ほぼ共通である。

H6全体の判定は **strongly supported** とする。

- raw Pyro境界は保存済み20件に数値上ほぼ完全一致し、観測標本についてconfirmed。ただしAkasha API全般の契約として公開された仕様ではない。
- 万葉A4 1420 EM = 56.8%は公開説明と離散比較の両方からstrongly supported。
- Freedom-Sworn 16%のN1/CA適用はcomponent ratio差からstrongly supported。Qへの適用はrejected。
- しめ縄50%のN1/CA後付けは対象1件でstrongly supportedだが、標本不足のため一般仕様としてはunresolved。
- rawに胡桃A4、火魔女stack、万葉A4、蒼古、しめ縄を含める候補はrejected。

次はH6を動かさず、全componentへほぼ同率で残る約7.1%を説明し得る仮説を一つずつ検証する。H3の離散候補では不足を十分説明できなかったため、H4の外部EMとVaporize境界を非蒸発componentから分離して検証するのが適切である。H4はvapeだけを動かすため、N1 non-vapeとQ/CA/N1の共通不足を同時に埋める補正として扱わない。
