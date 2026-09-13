# Akasha胡桃 H4 external EM・Vaporize入力境界の検証

検証日：2026-09-13  
対象：`VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1`（calculation ID `1000004605`）  
標本：保存済みLeaderboard rawの20 build（火魔女4セット19件、しめ縄4セット1件）

## 検証条件

H1/H5/H6で採用したMax HP、胡桃E、ATK、Damage Bonus境界は変更していない。H3はenemy Lv90、基礎Pyro RES 10%、VV 40%のbaselineを維持した。万葉A4は1420 EM由来56.8%、Freedom-SwornはN1/CA 16%のままである。talent倍率や補正係数も変更していない。

対象Leaderboardの公開説明は`elegy instructor amber c0r1. kazuha c2r1 @ 1000EM(1420)`と指定する。[Akasha Leaderboard](https://akasha.cv/leaderboards/1000004605/)、[既存仕様書](akasha_hutao_spec.md)

比較したexternal EMは、既知効果だけから作った次の5候補である。

| 候補 | 内訳 |
|---:|---|
| +0 | 外部EMなし |
| +100 | Elegyのみ |
| +220 | Elegy +100 + Instructor +120 |
| +300 | Elegy +100 + Kazuha C2 +200 |
| +420 | Elegy +100 + Instructor +120 + Kazuha C2 +200 |

任意のEMをcontinuous fitしていない。ゲーム効果の根拠は[KQM Elegy for the End](https://library.keqingmains.com/equipment/weapons/bows#elegy-for-the-end)、[KQM Instructor](https://library.keqingmains.com/equipment/artifacts#instructor)、[KQM Kazuha C2](https://library.keqingmains.com/characters/anemo/kaedehara-kazuha#constellations)、[KQM Crimson Witch](https://library.keqingmains.com/equipment/artifacts#crimson-witch-of-flames)である。

## 1. raw EMの入力境界

保存済みrawの`stats.elementalMastery`は **39.6300〜275.0800** だった。Hu Tao自身とStaff of Homaには固定EMがなく、この標本のraw EMで残るbuild依存源は聖遺物である。rank 1の対象buildでは、Akashaプロフィールの表示EM 119と聖遺物集計119が、rawの118.89と表示丸めの範囲で一致する。公開playerのUIDとbuild識別子はローカル観測データだけに保持する。

さらにraw EMが100未満のbuildを複数含み、最小値は39.63である。聖遺物EMは非負なので、全buildへ適用されるElegy +100、Instructor +120、Kazuha C2 +200のどれかがrawに含まれていれば、この値は成立しない。したがって対象rawの境界は次である。

```text
raw stats.elementalMastery = artifact EM
character fixed EM = 0
weapon fixed EM = 0

final reaction EM
= raw stats.elementalMastery
 + Elegy 100
 + Instructor 120
 + Kazuha C2 200
```

この境界は保存標本と公開プロフィールについてstrongly supportedだが、Akashaが公開した永続API契約としてconfirmedとはしない。

## 2. N1 vape / non-vape比によるexternal EM比較

主指標は次のrelative ratio errorである。

```text
observed ratio  = observed N1 vape / observed N1 non-vape
predicted ratio = predicted N1 vape / predicted N1 non-vape
ratio error     = predicted ratio / observed ratio - 1
```

同じN1間の比なので、ATK、CRIT、DEF、RES、Pyro Damage Bonus、talent倍率が相殺される。まずCrimson Witch reaction bonusを有効に固定してexternal EMだけを比較した。

| external EM | ratio平均誤差 | ratio中央値誤差 | ratio std | 最大絶対ratio誤差 | Aggregate平均誤差 |
|---:|---:|---:|---:|---:|---:|
| +0 | -29.6388% | -29.8560% | 2.3698% | 33.2181% | -33.1030% |
| +100 | -21.1655% | -21.3168% | 1.6572% | 23.6574% | -25.6879% |
| +220 | -12.2955% | -12.3810% | 0.9420% | 13.7055% | -17.9255% |
| +300 | -7.0378% | -7.0862% | 0.5331% | 7.8336% | -13.3244% |
| **+420** | **+0.0287%** | **+0.0286%** | **0.0012%** | **0.0320%** | **-7.1403%** |

+420だけが全20 buildのN1比をほぼ一定かつ0付近で説明した。平均Damageの近さではなく、共通項を除いたratio形状で選択している。

候補別集計は[`h4_em_candidates.csv`](../data/akasha/h4_em_candidates.csv)へ保存した。

## 3. Crimson Witch reaction bonus +15%

external EMを最有力の+420へ固定し、火魔女4セットのVaporize reaction bonusを有効・無効で比較した。しめ縄buildにはどちらの設定でもreaction bonusを加えていない。

| +420 EM候補 | N1 ratio平均誤差 | 中央値 | std | 最大絶対誤差 | Aggregate平均誤差 |
|---|---:|---:|---:|---:|---:|
| **火魔女へ+15%** | **+0.0287%** | **+0.0286%** | **0.0012%** | **0.0320%** | **-7.1403%** |
| 適用なし | -7.4364% | -7.8300% | 1.7246% | 8.1403% | -13.6753% |

適用なし候補のstdが大きいのは、19件の火魔女だけが悪化し、しめ縄1件は設定変更の影響を受けないためである。火魔女にだけ+15%を後付けする境界が強く支持される。

全10組合せのbuild別値は[`h4_vape_ratio_residuals.csv`](../data/akasha/h4_vape_ratio_residuals.csv)へ保存した。

## 4. CA・Qへの同一Vaporize倍率

最有力の+420 EM・火魔女+15%候補で、CA vapeとQ vapeもN1 non-vapeに対するratioとして比較した。

| Vape component / N1 non-vape | 平均ratio誤差 |
|---|---:|
| N1 vape | +0.0287% |
| CA vape | +0.1051% |
| Q vape | +0.0172% |

3 componentはいずれも0.11%以内であり、N1専用のVaporize倍率は必要ない。同じfinal reaction EMとVaporize倍率をN1、CA、Qへ通す現在の構造が支持される。CAの小さな相対差は残るが、H4用の別倍率を導入する根拠にはならない。

## 5. 判定と残存誤差

H4は **strongly supported** と判定する。

- raw `stats.elementalMastery`はartifact EMだけを含む。
- Elegy +100、Instructor +120、Kazuha C2 +200はraw未包含で、戦闘時に合計+420を追加する。
- Crimson Witch reaction bonus +15%は火魔女4セットだけへ追加する。
- 同じVaporize倍率をN1、CA、Qへ使用する。

ただしAkashaの内部精度やbuff発動順が公開されていないためconfirmedとはしない。+420候補でもN1 ratioに平均+0.0287%の微差があり、これを任意EMや補正係数で埋めていない。

H4を切り分けた後もAggregate平均誤差は **-7.1403%** のままである。Vape/non-vape比はほぼ一致するため、主要な残差はEMやVaporize固有項ではなく、N1 non-vapeを含む全componentへ共通するscale、または既に観測されたHP依存の入力差である。H3は未解決のままだが、既存の離散候補ではこの不足を十分説明できていない。
