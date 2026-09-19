# Cross-weapon missing ATK identification

調査日: 2026-09-19

## Scope and formula

本番`score_hutao_akasha()`は変更していない。各buildのobserved N1 non-vapeを使い、ATK以外の現在の乗算項を固定して次を計算した。

```text
required_final_atk = observed_n1_non_vape / fixed_non_atk_multiplier
unexplained_atk = required_final_atk - predicted_final_atk
predicted_final_atk = raw_stats_atk + base_atk * 20% + max_hp * 6.26%
```

20%は現在baselineのMillennial Movement 1回分である。HomaのHP由来ATK、Pyro Resonance、artifact ATKはraw `stats.atk`へ既に含まれるという既存境界を維持し、再加算していない。敵条件、E倍率、EM、Vaporize、Damage Bonus、talent倍率も変更していない。

## Category results

| weapon category | base ATK | builds | unexplained ATK mean | std | range | unexplained/base ATK | fit use |
|---|---:|---:|---:|---:|---:|---:|---|
| Staff of Homa R1 | 714.5089773 | 20 | 326.909733 | 0.032860 | 326.862737–326.992311 | 0.457531 | yes |
| Staff of the Scarlet Sands R1 | 648.2641381 | 20 | 495.587766 | 24.650901 | 457.098330–538.918494 | 0.764484 | **no** |
| Ballad of the Fjords R5 | 616.0403291 | 20 | 311.685394 | 0.039461 | 311.638822–311.793777 | 0.505950 | yes |

赤砂の大きなbuild間変動はEM→ATK武器passiveを現在診断式が再現していないためであり、定数残差の形を判定する材料にできない。BalladはN1 non-vapeにEMの直接項がないため、HomaとBalladの40件を識別fitへ使った。

## Diagnostic model comparison

fitは診断専用であり、本番式へ追加しない。

| model | equation | fitted parameter | R² | residual std | category mean residual max |
|---|---|---|---:|---:|---:|
| A flat | `missing = c` | c = 319.297563 | 0.000000 | 7.612256 | 7.612169 |
| B proportional | `missing = p × baseAtk` | p = 0.478176 | -3.403596 | 15.930562 | 17.109474 |
| C affine | `missing = p × baseAtk + c` | p = 0.154611, c = 216.438765 | 0.999977 | 0.036311 | ~0 |
| D weapon-specific | category mean | Homa/Ballad別平均 | 0.999977 | 0.036311 | ~0 |

Model AはModel Bより残差が小さいため、**純粋なbase ATK比例だけ**という説明はこの2カテゴリでは支持されない。ただしHomaとBalladのmissing ATK平均は15.224339 ATK異なり、厳密なflat定数でもない。

Model Cは数値上もっともよく合うが、eligibleなbase ATKが2水準しかないため、傾きと切片の2パラメータでカテゴリ平均を必ず通る飽和fitである。Model Dと同じ残差になり、affine効果と武器固有差を識別できない。R²の高さをゲーム仕様の証拠として扱ってはならない。

## Interpretation of the four hypotheses

- **A: fixed flat ATK missing** — strict model is rejected by the 15.224 ATK category difference, although it is closer than pure proportional.
- **B: base-ATK proportional buff missing** — pure proportional model is rejected relative to flat; `missing/baseAtk` isHoma 45.7531%、Ballad 50.5950%で一定ではない。
- **C: weapon-specific processing error** — plausible and unresolved. HomaとBalladはMax HP・EM・CRITの武器境界が異なる。赤砂では未実装のEM→ATK境界が明確に大きな変動を作る。
- **D: another common damage term** — unresolved. 2つのbase ATK水準だけでは、共通乗算項とaffineなATK換算の交絡を完全には除けない。

結論は、**現在の公開データだけではflat、affine、weapon-specific/common-termの正体を一意に識別できない**である。比較可能なBalladカテゴリは見つかったため「完全に別カテゴリがない」状態ではないが、独立な3番目の武器水準を赤砂から安全に得られない。

## Team ATK source audit

公開metadataから新しい確定ATK sourceは見つからなかった。

- Pyro Resonance +25%: Hu Tao + Amberにより成立。既存診断ではraw ATK側。
- Elegy Millennial Movement +20%: Amber R1から戦闘中に適用する既存baseline。
- Freedom-Sworn: Kazuha R1。Millennial Movementの同名ATK効果はElegyと重複しないという既存監査を維持し、2回加算しない。
- Amber C6 +15%: metadataはC6だがdescriptionはC0。適用有無は矛盾しており未解決、baselineは0%。
- Instructor: EM効果でありATK sourceではない。
- unknown Hydro slot: character、weapon、constellation、artifact setが非公開。ATK buff sourceの有無はunknown。

約45.75%に近い効果を数値から逆算して採用することはしていない。

## Production decision and next experiment

本番評価関数を変更できる証拠は得られなかった。`score_hutao_akasha()`の出力はビット一致回帰で不変を確認する。

次の識別実験は以下の順が有効である。

1. 同一artifact入力をAkasha上でHomaとBalladへ切り替えるcontrolled build experiment。
2. EM→ATKの入力時点と1-stack snapshotを独立再構築し、赤砂を3番目のbase ATK水準として利用する。
3. unknown Hydro slotのbackend/frontend metadataを追加取得する。
4. Akasha backendのprecombat/final ATK中間値を公開情報から探す。

生成データ:

- `data/akasha/cross_weapon_categories.csv`: category平均、scenario差flag、fit採否
- `data/akasha/cross_weapon_missing_atk.csv`: 60 buildの観測値、raw stats、required final ATK、unexplained ATK。UID等を含むためGit管理外

