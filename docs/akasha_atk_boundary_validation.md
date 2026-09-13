# Akasha胡桃 ATK入力境界の修正とbaseline再評価

検証日：2026-09-13  
対象：`VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1`（calculation ID `1000004605`）  
仕様根拠：[H5検証](akasha_h5_validation.md)、[胡桃仕様書](akasha_hutao_spec.md)

## 修正した境界

ATK計算を次の3段階へ分けた。

1. `NormalizedPrecombatAtk`：Akasha Leaderboard rawの `stats.atk` と同じ段階。raw経路は値をそのまま包み、artifact ATK、set ATK、護摩0.8%、護摩低HP1.0%、炎共鳴25%を受け取る引数を持たない。
2. `ExternalCombatAtkBonus`：rawに未包含の戦闘中ATK加算。baselineはMillennial Movement 20%、Amber C6 0%。いずれも `ScenarioConfig` で変更でき、Akasha内部仕様としてconfirmedにはしていない。
3. `HutaoSkillAtkBonus`：胡桃Eの `min(MaxHP × 6.26%, base ATK × 400%)`。rawとは別に1回だけ加える。

`FinalCombatAtk` はこの3型だけを合成する。

```text
final_atk
= normalized_precombat_atk
 + base_atk × (millennial_movement_atk_pct + amber_c6_atk_pct)
 + hutao_skill_atk_bonus
```

baselineのraw経路は具体的に次となる。

```text
final_atk = raw_stats_atk + base_atk × 20% + hutao_e_atk_bonus
```

旧`total_atk`はartifact入力とraw残差入力を同じ引数へ渡せる曖昧な関数だったため削除した。診断用artifact経路は `normalized_precombat_atk_from_artifacts` として分離し、base ATK、聖遺物ATK%、実数ATK、set ATK%、護摩、炎共鳴からraw相当段階を最初から作る。両経路は出所が異なるものの、完成後は同じ意味のnormalized precombat ATKになる。

`low_hp_for_homa` はartifact再構築経路では切り替え可能だが、raw経路の最終ATKには影響しない。rawには護摩低HP1.0%が既に含まれるというH5観測を境界として採用したためである。

## 回帰テスト

次を実在buildまたは純粋関数で固定した。

- rawからHoma 0.8%・低HP1.0%・炎共鳴25%を再加算しない
- `low_hp_for_homa` を切り替えてもraw経路のATKが変わらない
- Millennial Movement 20%を基礎ATKへ1回だけ適用する
- baselineのAmber C6は0%、15%へ変更した場合も1回だけ適用する
- 胡桃Eをrawとは別に1回だけ適用し、400% capも独立に検証する
- artifact再構築経路は護摩と炎共鳴をnormalized precombat段階へ含める

Akashaの観測値は変更していない。

## baseline誤差

[build別CSV](../data/akasha/atk_boundary_residuals.csv)には、同じ20 buildについて修正前後の予測、相対誤差、修正後のcomponent ratio、ATK内訳を保存した。修正前は診断専用関数で旧Homa低HP1.0%二重加算を再現している。

### 修正前

| component | mean | median | max abs | min | max |
| --- | ---: | ---: | ---: | ---: | ---: |
| N1 non-vape | +0.3706% | +0.3820% | 0.9077% | -0.4731% | +0.9077% |
| N1 vape | +0.3994% | +0.4104% | 0.9362% | -0.4412% | +0.9362% |
| CA vape | +0.4760% | +0.4871% | 1.0133% | -0.3652% | +1.0133% |
| Q vape | +0.3879% | +0.3989% | 0.9246% | -0.4526% | +0.9246% |
| Aggregate | **+0.4536%** | +0.4644% | 0.9905% | -0.3875% | +0.9905% |

### ATK境界修正後

| component | mean | median | max abs | min | max |
| --- | ---: | ---: | ---: | ---: | ---: |
| N1 non-vape | -7.2170% | -7.1828% | 7.7707% | -7.7707% | -6.8358% |
| N1 vape | -7.1904% | -7.1565% | 7.7412% | -7.7412% | -6.8094% |
| CA vape | -7.1195% | -7.0857% | 7.6708% | -7.6708% | -6.7383% |
| Q vape | -7.2010% | -7.1672% | 7.7518% | -7.7518% | -6.8202% |
| Aggregate | **-7.1403%** | -7.1066% | 7.6914% | -7.6914% | -6.7594% |

平均誤差が悪化したのは、誤差を小さくしていた約 `MaxHP × 1.0%` の重複項を除いたためである。修正後に約7.1%の一貫した不足が現れたが、今回の目的はATK入力境界を正すことであり、この不足を別の係数で埋めていない。

## Aggregate残差との相関

Pearson相関は20件だけの補助指標であり、単独で仕様を決める根拠にはしない。

| input | 修正前 | 修正後 |
| --- | ---: | ---: |
| Max HP | **+0.9993** | **+0.9204** |
| raw ATK | +0.4190 | +0.7448 |
| artifact ATK% | -0.0946 | +0.2219 |
| artifact flat ATK | -0.1605 | -0.0601 |
| CRIT Rate | +0.0212 | -0.0253 |
| CRIT DMG | -0.4105 | -0.3473 |
| EM | -0.4863 | -0.5210 |
| Pyro DMG Bonus | -0.1166 | -0.3294 |

HP相関は0.9993から0.9204へ低下したため、旧二重加算が作ったほぼ完全な直線関係は弱まった。しかし解消はしていない。修正後も誤差がHPに強く依存するため、Max HPの正規化境界、胡桃EのHP→ATK変換、または全componentに共通する別要素を次に切り分ける必要がある。

## component ratio

修正後の `predicted / observed` は次の通りだった。

| component | 20 build平均ratio | 最小 | 最大 |
| --- | ---: | ---: | ---: |
| N1 non-vape | 0.927830 | 0.922293 | 0.931642 |
| N1 vape | 0.928096 | 0.922588 | 0.931906 |
| CA vape | 0.928805 | 0.923292 | 0.932617 |
| Q vape | 0.927990 | 0.922482 | 0.931798 |

同一build内の4 component ratio spreadは平均0.000975、最大0.001000だった。これはratioで約0.10 percentage point以内であり、4 componentはほぼ同率で不足している。

- vapeだけが外れる形ではない。N1 vapeとN1 non-vapeの平均差は約0.027 percentage point。
- N1/CAだけがQから外れる形ではない。QはN1 vapeと約0.011 percentage point差。
- CAは他より約0.07〜0.10 percentage point高いが、共通の約7.1%不足に比べて小さい。

従って現時点の主残差は、反応だけ、Freedom-SwornのN1/CA bonusだけ、Q倍率だけで説明する形ではない。共通ATK項またはDEF/RESなどの共通乗算項が中心である。

## 次に検証する仮説

最優先は、探索やfitをせずH1の入力正規化と胡桃Eを独立検証することである。具体的には、raw `maxHp` がどのレベル・武器HP効果・外部HP効果を含むかを聖遺物から再構築し、AkashaがEへ掛ける最大HPと天賦倍率をbuild別に照合する。修正後もHP相関が+0.9204あるためである。

その後、全componentがほぼ同率でずれることからH3の敵DEF/RES・キャラクターレベルを定数候補ごとに検証する。H4のEMはvape対non-vape差が小さく、H6はN1/CA対Q差が小さいため、現時点では優先度を下げる。今回はH2/H3/H4/H6、talent倍率、補正係数を変更していない。
