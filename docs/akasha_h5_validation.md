# Akasha胡桃 H5（external ATK%）検証

検証日：2026-09-13  
対象：`VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1`（calculation ID `1000004605`）  
判定：**strongly supported**

## 結論

`external_atk_pct=20%` が最も小さい誤差になる直接の理由は、保存済みLeaderboard rawの `stats.atk` が通常のプロフィール表示ATKではなく、少なくとも次を含む計算用の中間ATKだからである。

- 聖遺物ATK%・実数ATK
- しめ縄2セットのATK +18%（該当buildのみ）
- 護摩R1の最大HP由来ATK 0.8%
- 護摩R1の低HP追加ATK 1.0%
- 炎共鳴ATK +25%

一方、Millennial Movement由来ATK +20%はrawへまだ含まれていない。したがって、既存のraw増分型エンジンへ渡す残りの外部ATKは20%になる。これは「炎共鳴がシナリオに存在しない」という意味ではなく、炎共鳴がrawへ既に入っているため再加算しない、という意味である。

ただし、現在のエンジンはrawが護摩0.8%だけを含むと仮定し、低HP分1.0%を再加算している。この二重加算のため、20%モデルの残差はHPとほぼ完全に連動している。H5を他の仮説から独立に完全確定するには、このATK入力境界を直した後でH1〜H4/H6〜H8を再検証する必要がある。このためH5全体の判定は `confirmed` ではなく `strongly supported` とした。

## データと方法

観測Damageには[保存済みLeaderboard raw](../data/akasha/raw/1000004605_20260913T043550.493548Z/page_0001.json)の20 buildをそのまま使用した。`calculation.result` や `calculation.additional` は変更していない。

聖遺物ATK%と実数ATKは、rawの省略済み `artifactObjects` から推測せず、各行の `uid` と `md5` で `https://akasha.cv/profile/{uid}?build={md5}` を開き、表示された5聖遺物のsubstat classと数値を2026-09-13に読み取った。20 buildを1回ずつ確認し、過剰な再取得や無限retryは行っていない。Akashaプロフィールの表示値はATK%が小数第1位、実数ATKが整数へ丸められるため、再構築値には最大1 ATK程度の表示丸め差を見込む。

固定仕様とバフ値の出典は[Akasha胡桃仕様書](akasha_hutao_spec.md)のStaff of Homa、Elegy、Freedom-Sworn、Pyro Resonance、Amber C6、artifact setの各節を使用した。対象カテゴリの説明は `elegy instructor amber c0r1. kazuha c2r1 @ 1000EM(1420)` である。カテゴリ説明のAmber C0とteammates metadataのC6表示が矛盾するため、Amber C6は候補Eとして数値比較した。

## ATK内訳の再構築

表示丸めされた聖遺物値から次の段階を分けた。

```text
profile_normalized_candidate
= base_atk × (1 + artifact_atk_pct + set_atk_pct)
 + artifact_flat_atk
 + max_hp × 0.8%                 # Homa base passive

raw_atk_candidate
= profile_normalized_candidate
 + max_hp × 1.0%                 # Homa low-HP passive
 + base_atk × 25%                # Pyro Resonance

combat_atk_candidate
= raw_atk_candidate
 + base_atk × 20%                # one Millennial Movement ATK buff
 + Hu Tao E ATK
```

キャラクター基礎ATKの表示値106と護摩Lv.90基礎ATK608の合計表示値は714だが、rawの `stats.baseAtk` は全buildで `714.5089773` だった。計算には後者を使い、表示値と内部値を混同していない。胡桃Eは `min(max_hp × 6.26%, base_atk × 400%)` として別段階に保持した。

20 buildでraw ATK候補を比較した結果は次の通りである。誤差は `candidate - raw stats.atk`。

| raw ATK候補 | 平均誤差 (ATK) | 平均絶対誤差 | 最大絶対誤差 |
| --- | ---: | ---: | ---: |
| profile候補のみ | -522.501 | 522.501 | 548.200 |
| profile + 炎共鳴25% | -343.874 | 343.874 | 369.573 |
| profile + 護摩低HP1.0% | -178.392 | 178.392 | 179.006 |
| profile + 護摩低HP1.0% + 炎共鳴25% | **+0.235** | **0.325** | **0.799** |
| 上記 + Millennial 20% | +143.137 | 143.137 | 143.700 |
| 上記 + Amber C6 15% | +107.412 | 107.412 | 107.975 |

最後の0.799以下という差は、聖遺物カードの表示丸め範囲と整合する。rawにMillennial 20%やAmber C6 15%まで含める候補は、全buildでそれぞれ基礎ATKの20%または15%だけ過大になる。

例として、異なる構成の5 buildを示す。`set ATK%` はしめ縄2セットだけである。

| rank | artifact ATK% | flat ATK | set ATK% | raw stats.atk | 再構築raw ATK | 差 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 5.3% | 311 | 0% | 1851.207 | 1851.564 | +0.357 |
| 2 | 0.0% | 311 | 0% | 1854.930 | 1854.930 | -0.000 |
| 4（しめ縄4） | 9.9% | 325 | 18% | 2051.173 | 2051.482 | +0.309 |
| 13（EM時計） | 8.2% | 311 | 0% | 1814.975 | 1815.261 | +0.286 |
| 20 | 11.1% | 344 | 0% | 1901.927 | 1901.999 | +0.073 |

プロフィールカードの表示ATKもrawとは別である。たとえばrank 1のカードは、公開プロフィール側の実レベル・実武器精錬を反映したATK `1456` を表示したのに対し、同じ `uid/md5` のLeaderboard rawはLv.90・護摩R1へ正規化された `1851.2066` を保持した。従って、プロフィール表示用stats、Leaderboard計算用 `stats.atk`、胡桃E後の最終戦闘ATKを分けて扱う必要がある。

## 候補モデル比較

[h5_model_comparison.csv](../data/akasha/h5_model_comparison.csv)には、各候補・各componentについて20 buildの平均相対誤差、中央値、最大絶対相対誤差を保存した。

まず既存エンジンと過去の45%/20%比較を再現する `raw_increment` を示す。この経路はrawを起点にする診断用で、独立再構築した最終ATKではない。

| model | externalの解釈 | Aggregate平均 | 中央値 | 最大絶対誤差 |
| --- | --- | ---: | ---: | ---: |
| A | 炎共鳴25% + Millennial 20% = 45% | +4.4003% | +4.4009% | 4.8035% |
| B | Millennial 20%のみ | **+0.4536%** | **+0.4644%** | **0.9905%** |
| C | 炎共鳴25%のみ | +1.2429% | +1.2521% | 1.7380% |
| D | 0% | -2.7038% | -2.6744% | 3.7877% |
| E | Millennial 20% + Amber C6 15% = 35% | +2.8216% | +2.8337% | 3.2674% |

model Bのcomponent別結果は次の通りである。

| component | 平均誤差 | 中央値 | 最大絶対誤差 |
| --- | ---: | ---: | ---: |
| N1 non-vape | +0.3706% | +0.3820% | 0.9077% |
| N1 vape | +0.3994% | +0.4104% | 0.9362% |
| CA vape | +0.4760% | +0.4871% | 1.0133% |
| Q vape | +0.3879% | +0.3989% | 0.9246% |
| Aggregate | +0.4536% | +0.4644% | 0.9905% |

CSVには `artifact_reconstructed` も併記した。この経路はraw ATKを最終ATKとして使わず、聖遺物から全ATKを組み直す。同じ未調整のH1〜H8を使ったためmodel AでもAggregate平均は-7.1351%だった。この差を任意係数で埋めていない。raw増分model Bの良さには、護摩低HPATKの二重加算と他の未解決仮説との相殺が含まれることを示す結果であり、20%を単なるfit値として固定できない理由でもある。

## 残差とcomponent比

[h5_residuals.csv](../data/akasha/h5_residuals.csv)はmodel Bのbuild別観測値、予測値、相対誤差、`predicted / observed`、ATK再構築内訳を保存する。Aggregate誤差の範囲は-0.3875%から+0.9905%だった。

Aggregate誤差とのPearson相関は次の通りである。サンプル数20なので、相関は仕様決定ではなく残差形状の補助にだけ使う。

| input | Pearson r |
| --- | ---: |
| HP | **+0.9993** |
| raw stats.atk | +0.4190 |
| artifact ATK% | -0.0946 |
| artifact flat ATK | -0.1605 |
| CRIT Rate | +0.0212 |
| CRIT DMG | -0.4105 |
| EM | -0.4863 |
| Pyro DMG Bonus | -0.1166 |

HP相関は全componentで `r=0.99919〜0.99926` と再現し、ATK%・実数ATKとの相関は弱かった。これは現在のraw増分経路が `max_hp × 1.0%` を二重加算する構造と一致する。会心・EMとの中程度の相関は上位20件という選抜済み標本内の共変動を含み、因果根拠にはしない。

各build内の4 component ratioの最大値と最小値の差は平均0.001055、最大0.001080だった。4 componentはほぼ共通比率で動くため、主因は攻撃種別固有のtalent倍率やDamage Bonusではなく、共通ATK項または共通乗算項である。CAだけ平均誤差が約0.08〜0.11ポイント高い小差は残るが、H5の判断を覆す規模ではない。

artifact set別では火魔女系19件のAggregate平均誤差+0.4447%、しめ縄4の1件+0.6230%だった。しめ縄は1件しかないためset差を一般化しない。

## H5判定

**strongly supported**：20件すべてで、raw ATKが「護摩低HPを含むプロフィール正規化候補 + 炎共鳴25%」に最大0.799 ATK以内で一致した。rawへさらにMillennial 20%またはAmber C6 15%を含める候補は明確に過大である。raw増分比較でも、残りのMillennial 20%だけを加えるmodel Bが5候補中最良で、Amber C6を加えるmodel Eは悪化した。

次に検証すべきなのはH5の係数変更ではなく、ATK入力境界である。コア計算を聖遺物内訳から組み立て、rawに含まれる護摩低HP1.0%と炎共鳴25%を再加算しない形へ変更した後、H2（低HP条件）とH4/H6（EM・Damage Bonus）を再評価する。今回、20%に合わせる補正係数や自動最適化は導入していない。
