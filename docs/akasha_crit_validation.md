# Akasha胡桃 CRIT入力境界・期待会心倍率の検証

検証日：2026-09-13  
対象：`VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1`（calculation ID `1000004605`）  
標本：保存済みLeaderboard rawの20 build

## 検証条件

H1/H4/H5/H6でstrongly supportedとなったMax HP、E、ATK、external EM、Vaporize、Damage Bonus境界は固定した。H3はenemy Lv90、基礎Pyro RES 10%、VV 40%のbaselineを維持した。敵条件、talent倍率、任意補正係数は変更していない。

一般的な平均会心倍率と基礎値の根拠は[KQM Critical Hits](https://library.keqingmains.com/combat-mechanics/damage/damage-formula#critical-hits)、[KQM Hu Tao base stats](https://library.keqingmains.com/characters/pyro/hu-tao#base-stats)、[KQM Staff of Homa](https://library.keqingmains.com/equipment/weapons/polearms#staff-of-homa)および[既存仕様書](akasha_hutao_spec.md)である。

## 1. raw CRIT入力境界

表示仕様値から期待される境界は次である。

```text
raw CRIT Rate
= Hu Tao基礎 5%
 + artifact CRIT Rate
 + その他固定CRIT Rate 0%

raw CRIT DMG
= 基礎 50%
 + Hu Tao突破 38.4%
 + Staff of Homa R1 66.2%
 + artifact CRIT DMG
```

Leaderboard rawには5聖遺物の全substatは含まれないが、artifact-onlyの`critValue`が含まれる。そこで20件についてrawから固定値を除いたartifact CR/CDと、`critValue = 2 × artifact CR + artifact CD`の整合性を比較した。

- 上記境界で再構築したraw CRIT Rate差：全件0
- 上記境界で再構築したraw CRIT DMG差：全件0
- 再構築artifact CVとraw `critValue`の差：全件 **-0.049990〜-0.049996 CV**
- raw `critValue`とraw CDから逆算したCR差：およそ **+0.025 percentage points**
- raw `critValue`とraw CRから逆算したCD差：およそ **+0.050 percentage points**

全buildでほぼ同じ0.05 CV差なので、聖遺物差ではなく表示仕様値とAkasha内部基礎値の小数精度差と考えられる。ただし、その差を胡桃突破と護摩のどちらへ帰属させるかはrawから一意に決められない。観測Damageへ合わせた固定値のfitは行わなかった。

build別内訳は[`crit_input_reconstruction.csv`](../data/akasha/crit_input_reconstruction.csv)に保存した。

## 2. 期待会心倍率候補

現在の予測Damageを現行会心倍率で割ってpre-crit Damageを固定し、会心倍率だけを差し替えた。

| 候補 | 定義 | Aggregate平均誤差 | 残差std | 最大絶対誤差 |
|---|---|---:|---:|---:|
| A | raw CR、`1 + CR × CD`、clampなし | -7.1182% | 0.2020% | 7.6914% |
| **B** | **raw CR、`1 + clamp(CR, 0, 1) × CD`** | **-7.1403%** | **0.2116%** | **7.6914%** |
| C | 現行エンジンへraw CR/CDを直接入力 | -7.1403% | 0.2116% | 7.6914% |
| D | raw `critValue`と固定CDから再構築したCRをclamp | -7.1234% | 0.2128% | 7.6730% |

BとCは同じ計算である。Dとの差は表示仕様値と内部精度の約0.025 CR percentage pointsだけであり、約7.1%不足を説明しない。一般式と入力境界からB/Cを最有力とする。

## 3. required CRIT multiplier

各buildで次を計算した。

```text
predicted pre-crit aggregate = predicted aggregate / current crit multiplier
required crit multiplier = observed aggregate / predicted pre-crit aggregate
required / current = observed aggregate / predicted aggregate
```

| 診断値 | 平均 | 中央値 | std | 最小 | 最大 |
|---|---:|---:|---:|---:|---:|
| required/current crit multiplier | 1.076899 | 1.076503 | 0.002457 | 1.072494 | 1.083323 |

必要倍率はbuildごとに絶対値が異なるが、currentに対する比は約1.077付近へ集中する。この比を会心補正として実装すると、根拠のない共通補正係数になるため採用しない。

component別required multiplierも[`crit_multiplier_residuals.csv`](../data/akasha/crit_multiplier_residuals.csv)へ保存した。

## 4. Aggregate残差との相関

| 入力 | Aggregate relative residualとのPearson r |
|---|---:|
| raw CRIT Rate | **-0.0253** |
| raw CRIT DMG | **-0.3473** |
| current crit multiplier | **-0.4881** |

CRIT Rateとの相関はほぼない。CDと合成倍率には弱〜中程度の負相関があるが、標本20件であり、既に強いMax HP相関を持つ残差やstat間相関と交絡する。さらにrequired/current比のstdは0.2457 percentage pointsに留まり、合法的な離散会心式候補による平均誤差の改善も最大0.022 percentage pointsだけである。従って会心式を主要因とは判断しない。

## 5. CRIT Rate 100%超え

100%を超えるbuildは1件だけだった。

- rank 10のbuild
- raw CRIT Rate：100.6600%
- raw CRIT DMG：259.4300%
- clamp倍率：3.594300
- clampなし倍率：3.611422
- clampなしによるそのbuildのDamage増加：0.4764%

20件平均ではclampなし候補が-7.1182%、clamp候補が-7.1403%となる。1件だけで、他の未解決共通項とHP依存残差が残るため、Akasha内部のclamp有無を観測だけから確定できない。一般的な期待会心式は100% clampを使うためbaselineは変更しない。

## 6. 判定

このPhaseのH7（CRIT境界・期待値）は **strongly supported** と判定する。

- raw CRは胡桃基礎5%と聖遺物CRを含む。
- raw CDは基礎50%、突破38.4%、護摩R1 66.2%、聖遺物CDを含む。
- Akashaの`Avg DMG`は`1 + clamp(CR, 0, 1) × CD`を使う現在の構造が最有力。
- 内部固定値には約0.05 CV相当の未解決な小数精度差がある。
- clamp有無は100%超えが1件だけなので、保存標本だけではunresolved。

約7.1%不足は会心入力や会心期待値式では説明できない。次に検証すべき共通項は、全componentへ共通するbase damage側である。H3の離散敵条件は既に不足を十分説明しなかったため、表示値ではなく内部精度を含むHu TaoのN1/CA/Q talent倍率をfitせず既知の公式離散値で再確認するか、raw Max HPからE ATKへ渡る内部値と現在残るHP相関を再点検する必要がある。
