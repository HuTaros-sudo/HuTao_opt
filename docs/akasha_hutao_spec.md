# Akasha 胡桃「VV Swirl Hyper Tao Combo, Avg DMG」仕様調査

調査日：2026-09-13（日本時間）  
対象：`VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1`  
Akasha calculation / leaderboard ID：`1000004605`

この文書はPhase Cで必要になる計算要素を整理するための仕様書である。ここでは計算コードを実装せず、原神の一般仕様とAkasha固有の観測事実を分ける。

## 状態の読み方

- **source**：根拠にした公式情報、検証資料、Akasha API観測データ。
- **confirmed**：出典または保存済みAPI応答から直接確認できた内容。ただし、原神で確認済みの一般仕様がAkasha内部でも同じように使われているとは限らない。
- **inferred**：複数の確認事項から導ける、Phase Cで検証すべき仮説。実装時に固定値として無条件に採用しない。
- **unknown**：公開情報だけでは確定できないAkasha固有条件、精度、適用順序など。

数値は表示値と内部値を区別する。KQM等に表示された倍率は丸められている場合があり、`calculation.result`との厳密一致には十分でない可能性がある。

## 1. Akasha対象カテゴリと固定編成

- **source**：[Akasha categories API](https://akasha.cv/api/v2/leaderboards/categories?characterId=10000046)、[対象Leaderboard](https://akasha.cv/leaderboards/1000004605)、[Phase A APIメモ](akasha_api_notes.md)。
- **confirmed**：2026-09-13のcategories応答では、対象名は`VV Swirl Hyper Tao Combo, Avg DMG`、武器カテゴリは`Staff of Homa R1`、calculation IDは`1000004605`だった。説明文は `Average DMG for 11N1CD + Q combo. elegy instructor amber c0r1. kazuha c2r1 @ 1000EM(1420). 4p SR burst uptime 1/3, other sets: 2/3.` である。
- **confirmed**：同じ応答のteammates metadataは、胡桃C1・護摩の杖R1、楓原万葉C2・翠緑4セット・蒼古なる自由への誓いR1、アンバー・教官4セット・終焉を嘆く詩R1を示す。残る1枠はHydroだが、キャラクター名は公開応答から特定できなかった。
- **inferred**：Hydro枠は蒸発用の水付着を供給し、固有のDamage/ATK/EMバフを計算へ加えないダミー条件である可能性が高い。
- **unknown**：カテゴリ説明は`amber c0r1`、teammates metadataはアンバーC6を示しており矛盾する。アンバーC6のATK +15%を含めるかは未確定である。Hydro枠の正体、武器、聖遺物、固有バフも未確定である。

## 2. 胡桃の基礎ステータス

- **source**：[HoYoWiki Hu Tao](https://wiki.hoyolab.com/pc/genshin/entry/34?crawler=Googlebot&lang=)、[KQM TCL Hu Tao](https://library.keqingmains.com/characters/pyro/hu-tao#base-stats)。
- **confirmed**：Lv.90/A6では基礎HP 15,552、基礎ATK 106、基礎DEF 876、基礎会心率5%、合計基礎会心ダメージ88.4%である。88.4%は初期50%と突破38.4%の合計である。
- **confirmed**：2026年時点のKQM表にはLv.100/A6として基礎HP 16,658、基礎ATK 130、基礎DEF 938も掲載されている。
- **inferred**：保存済みLeaderboard行では公開プロフィールの`propMap.level`が100でも、`stats.baseAtk`が約714.509であり、Lv.90胡桃とLv.90護摩の基礎ATK合計に近い。このカテゴリはプロフィール実レベルではなくLv.90へ正規化している可能性が高い。
- **unknown**：Akasha計算で使う胡桃レベルはcategories応答に明記されていない。内部の正確な基礎HP・基礎ATK値と、2026年のLv.100解放後もLv.90固定かは検証が必要である。

必要な中間値は `base_hp`、`character_base_atk`、`weapon_base_atk`、`base_crit_rate`、`base_crit_dmg` とし、プロフィール表示レベルと計算上の固定レベルを別に持つ。

## 3. 胡桃の天賦倍率

- **source**：[KQM TCL Hu Tao full talent values](https://library.keqingmains.com/characters/pyro/hu-tao#full-talent-values)。
- **confirmed**：通常攻撃天賦Lv.10の1段目は83.6%、重撃は242.6%。元素スキル天賦Lv.10のHP→ATK変換は最大HPの6.26%。元素爆発天賦Lv.10は通常時494%、HP 50%以下で617%と表示される。
- **confirmed**：保存済みLeaderboard応答の`talentsLevelMap`では通常攻撃の`rawLevel`が上位観測行で10だった。実キャラクターの凸によるスキル・爆発の+3が表示される行もある。
- **inferred**：カテゴリ固定の胡桃C1なら、計算倍率は通常攻撃・スキル・爆発すべて天賦Lv.10を使う可能性が高い。実プロフィールのC3/C5による+3はランキング計算から除外されると考えられる。
- **unknown**：Akashaが使う倍率の内部精度は不明である。表示上の83.6%、242.6%、6.26%、494%、617%だけでは小数以下の内部値を再現できない可能性がある。爆発が低HP倍率617%を使うかも、カテゴリ説明だけでは確定しない。

必要な倍率はN1、CA、低HP Q、通常HP Q、E変換率で分ける。Blood Blossom倍率は後述の観測内訳に存在しないため、このLeaderboardの合計対象には入れない。

## 4. Staff of Homa R1

- **source**：[HoYoWiki Staff of Homa](https://wiki.hoyolab.com/pc/genshin/entry/1972/?crawler=Googlebot&lang=)、[KQM TCL Polearms — Staff of Homa](https://library.keqingmains.com/equipment/weapons/polearms#staff-of-homa)。
- **confirmed**：Lv.90で基礎ATK 608、会心ダメージ66.2%。R1は最大HP +20%、最大HPの0.8%をATKへ加え、HPが50%未満ならさらに最大HPの1.0%をATKへ加える。
- **inferred**：低HP条件では護摩由来のATK加算は合計 `MaxHP × 1.8%` になる。これはATK%ではなく、最大HPから算出する加算ATKとして扱う必要がある。
- **unknown**：対象計算が常時HP 50%未満を仮定するかはcategories応答に明記されていない。ちょうど50%では護摩の追加1.0%は発動しない一方、胡桃A4と爆発低HP倍率は50%以下で発動するため、境界条件を一つの真偽値にまとめてはいけない。

## 5. 最大HPと胡桃EのATK変換

- **source**：[KQM damage formula — Base Damage](https://library.keqingmains.com/combat-mechanics/damage/damage-formula#base-damage)、[KQM TCL Hu Tao — Guide to Afterlife](https://library.keqingmains.com/characters/pyro/hu-tao#guide-to-afterlife)。
- **confirmed**：一般式は `MaxHP = character_base_hp × (1 + HP%) + flat_HP`。護摩R1のHP +20%もHP%の項に加わる。
- **confirmed**：胡桃Eは発動時の最大HPに天賦倍率を掛けてATKを増やし、その増加量は胡桃の基礎ATKの400%を超えない。ここで基礎ATKはキャラクター基礎ATKと武器基礎ATKの合計である。
- **inferred**：天賦Lv.10なら `e_atk_bonus = min(MaxHP × 0.0626, base_atk × 4)`。攻撃時ATKは、基礎ATK・ATK%・聖遺物の実数ATK・外部ATK%・護摩のHP依存加算・EのHP依存加算を別々に組み立てる必要がある。
- **unknown**：AkashaがE発動時と攻撃時の最大HPを同一として扱うか、内部の6.26%と400% capをどの精度・順序で適用するかは未確認である。

## 6. HP 50%以下・未満の効果

- **source**：[KQM TCL Hu Tao — Sanguine Rouge / Spirit Soother](https://library.keqingmains.com/characters/pyro/hu-tao#ascension-passives)、[KQM Staff of Homa](https://library.keqingmains.com/equipment/weapons/polearms#staff-of-homa)。
- **confirmed**：胡桃A4は現在HPが50%以下のとき炎元素ダメージ +33%。胡桃Qは命中時にHPが50%以下なら高い方の倍率を使う。護摩R1の追加ATKはHPが50%未満のとき発動する。
- **inferred**：Leaderboard名の`Hyper Tao`、護摩採用、低HP運用の一般性から、全攻撃で胡桃A4と護摩低HP効果が有効で、Qも低HP倍率という仮説を最初に検証する価値がある。
- **unknown**：Akashaが仮定する実HP割合、Q直前まで低HPを維持するか、50%境界をどう設定しているかは公開されていない。

## 7. VaporizeとElemental Mastery

- **source**：[KQM damage formula — Amplifying Reaction](https://library.keqingmains.com/combat-mechanics/damage/damage-formula#amplifying-reaction)。
- **confirmed**：炎で水付着へ蒸発を起こす倍率は1.5。増幅反応倍率は `reaction_multiplier × (1 + 2.78 × EM / (1400 + EM) + reaction_bonus)` である。`reaction_bonus`には燃え盛る炎の魔女4セットの蒸発+15%などが入る。
- **inferred**：胡桃の反応時EMは、聖遺物等の本人EMに、終焉R1の+100、教官4の+120、万葉C2のフィールド内+200を加えた値になる。条件が全て有効なら外部加算は合計+420 EMである。
- **unknown**：11回のN1のうち4回だけを蒸発扱いにするAkashaの根拠となるICD/付着列、各ヒットで+420 EMが全て有効か、反応ボーナスの内部精度は不明である。Hydro枠が付着以外の効果を与えるかも不明である。

## 8. CRIT期待値

- **source**：[KQM damage formula — Critical Hits](https://library.keqingmains.com/combat-mechanics/damage/damage-formula#critical-hits)。
- **confirmed**：一般的な平均会心倍率は `1 + clamp(CRIT Rate, 0%, 100%) × CRIT DMG`。会心率には基礎5%と聖遺物等を、会心ダメージには基礎50%、突破、護摩、聖遺物等を含める。
- **inferred**：Leaderboard名と各内訳名の`Avg DMG`は、この平均会心倍率を各ヒットへ適用する意味だと考えられる。
- **unknown**：Akashaが会心率を100%でclampする位置、表示値ではなく内部値を使うか、各ヒットの期待値を出してから合計するかについて実装公開はない。

## 9. Pyro DMG Bonusと攻撃種別DMG Bonus

- **source**：[KQM general damage formula](https://library.keqingmains.com/combat-mechanics/damage/damage-formula#general-formula-for-damage)、[KQM Hu Tao A4](https://library.keqingmains.com/characters/pyro/hu-tao#ascension-passives)、[KQM artifacts](https://library.keqingmains.com/equipment/artifacts)。
- **confirmed**：一般式では炎元素ダメージ、通常/重撃/爆発など該当するDMG Bonusを加算し、`1 + total_DMGBonus`として掛ける。胡桃E中のN1とCAは炎元素ダメージになる。一般的な星5炎杯は46.6%、胡桃A4は低HP時33%、火魔女2セットは15%である。
- **inferred**：各攻撃のDamage Bonusは共通の炎元素枠に、攻撃種別ごとの蒼古16%またはしめ縄50%などを足す構造にする。N1/CA/Qで同じ合計値を使わない。
- **unknown**：Akashaの入力`stats.pyroDamageBonus`が聖遺物の素の値だけか、計算用セット効果まで反映済みかは未確定である。二重加算を避けるため、Phase Bデータでフィールドの意味を検証する必要がある。

## 10. Enemy DEF

- **source**：[KQM damage formula — Enemy Defense](https://library.keqingmains.com/combat-mechanics/damage/damage-formula#enemy-defense)。
- **confirmed**：一般式は `DEF multiplier = (character_level + 100) / ((character_level + 100) + (enemy_level + 100) × (1 - DEF reduction) × (1 - DEF ignore))`。
- **inferred**：胡桃Lv.90、敵Lv.90、DEF減少/無視なしなら倍率は0.5となる。対象編成の公開情報にはDEF減少役が見当たらない。
- **unknown**：Akashaが固定する胡桃レベル、敵レベル、DEF multiplierは説明文にない。0.5は検証前の仮説であり、確定値ではない。

## 11. Enemy RESとViridescent Venerer

- **source**：[KQM Enemy Resistances](https://library.keqingmains.com/combat-mechanics/enemy-mechanics/enemy-resistances)、[KQM artifacts — Viridescent Venerer](https://library.keqingmains.com/equipment/artifacts#viridescent-venerer)。
- **confirmed**：耐性は `base_RES - RES_reduction`。RES倍率は、RES<0なら`1 - RES/2`、0以上75%未満なら`1 - RES`、75%以上なら`1/(4×RES+1)`である。
- **confirmed**：翠緑4セットは装備者が表でSwirlを起こしたとき、Swirlした元素の敵RESを10秒間40%下げる。categories応答は万葉に翠緑4セットを指定している。
- **inferred**：基礎炎RES 10%の標準敵を仮定すると翠緑後は-30%、炎RES倍率は1.15になる。
- **unknown**：Akashaの仮想敵、敵レベル、基礎炎RES、翠緑の継続が11N1CD+Q全体を覆うかは公開されていない。10%と1.15を確定値にしてはいけない。

## 12. Kazuha A4 buff

- **source**：[KQM TCL Kaedehara Kazuha — Poetics of Fuubutsu](https://library.keqingmains.com/characters/anemo/kaedehara-kazuha#ascension-passives)、[Akasha categories API](https://akasha.cv/api/v2/leaderboards/categories?characterId=10000046)。
- **confirmed**：万葉A4はSwirlした元素について、発動時の万葉EM 1につき0.04%の元素ダメージを8秒間チームへ与える。発動後にEMが変化しても既存バフは更新されず、同元素を再度Swirlするとその時点のEMで上書きされる。
- **confirmed**：対象説明文は`kazuha c2r1 @ 1000EM(1420)`と明記する。
- **inferred**：`1420 = 1000 + 万葉C2 200 + 終焉100 + 教官120`と解釈でき、そのSwirl時の炎元素ダメージ加算は `1420 × 0.04% = 56.8%` になる。
- **unknown**：1000が装備素値か、蒼古の武器サブステータス198を含む表示EMか、どの順番で終焉・教官・C2を発動して1420でSwirlするかはAPIにない。Akashaが実際に56.8%を加えているかは実測照合が必要である。

## 13. Kazuha C2

- **source**：[KQM TCL Kaedehara Kazuha — C2 Yamaarashi Tailwind](https://library.keqingmains.com/characters/anemo/kaedehara-kazuha#constellations)。
- **confirmed**：万葉QのAutumn Whirlwind内では、万葉自身のEMが+200され、フィールド内の出場キャラクターのEMも+200される。同効果同士はstackしない。
- **inferred**：万葉がフィールド内で炎SwirlすればA4計算用EMにも+200が入り、胡桃がフィールド内で攻撃すれば蒸発計算用EMにも+200が入る。
- **unknown**：Akashaの抽象コンボが万葉Qフィールド内で11N1CD+Qを全て行うと仮定しているか、バフ時間を無視して全段へ適用するかは不明である。

## 14. Elegy for the End R1

- **source**：[KQM TCL Bows — Elegy for the End](https://library.keqingmains.com/equipment/weapons/bows#elegy-for-the-end)、[Akasha categories API](https://akasha.cv/api/v2/leaderboards/categories?characterId=10000046)。
- **confirmed**：R1は装備者自身のEM +60。スキル/爆発が4回命中して4 Sigilsを消費すると、12秒間、周囲のチームへEM +100とATK +20%を与える。対象categories応答はアンバーの終焉R1を指定する。
- **inferred**：アンバーQの多段命中で終焉を発動し、胡桃の全コンボへEM +100とATK +20%を与える想定だと考えられる。
- **unknown**：最初の4 hitより前後を区別するか、12秒が11N1CD+Q全体を覆うか、Akashaが発動条件を省略して常時有効とするかは不明である。

## 15. Instructor 4pc

- **source**：[KQM artifacts — Instructor](https://library.keqingmains.com/equipment/artifacts#instructor)、[Akasha categories API](https://akasha.cv/api/v2/leaderboards/categories?characterId=10000046)。
- **confirmed**：装備者が表で元素反応を起こすと、全チームのEMを8秒間+120する。発動させた最初のhit/reaction自身には適用されない。対象categories応答はアンバーに教官4セットを指定する。
- **inferred**：アンバーが表で事前に反応を起こし、胡桃の蒸発と万葉のA4用Swirlの双方へ+120を供給する想定と考えられる。
- **unknown**：具体的な発動反応、ローテーション順、8秒のuptime、万葉Swirl時と胡桃全攻撃時の有効性は公開されていない。

## 16. Freedom-Sworn R1

ユーザー指定の最低確認項目外だが、Akashaのteammates metadataに存在し、N1/CAとATKへ直接影響するため必須要素である。

- **source**：[KQM TCL Swords — Freedom-Sworn](https://library.keqingmains.com/equipment/weapons/swords#freedom-sworn)、[Akasha categories API](https://akasha.cv/api/v2/leaderboards/categories?characterId=10000046)。
- **confirmed**：R1で装備者自身の与えるダメージ+10%。2 Sigils獲得後、チームへ12秒間、通常・重撃・落下攻撃DMG +16%とATK +20%を与える。対象categories応答は万葉にR1を指定する。
- **confirmed**：KQMは異なるMillennial Movement武器の効果は併存できるが、同じbuff type同士は上書きされると記録している。
- **inferred**：胡桃には蒼古の通常/重撃+16%、終焉のEM+100、ATK +20%を一つだけ適用する構成が候補になる。終焉と蒼古のATK +20%を足して+40%にはしない。
- **unknown**：Akashaが終焉と蒼古の同種ATK buffをどのように解決しているか、蒼古の発動条件と12秒uptimeをどう扱うかは未確認である。

## 17. Pyro ResonanceとAmber C6

これも一覧外だが、編成メタデータと凸数の矛盾を数値へ落とすために必要である。

- **source**：[KQM Elemental Resonance](https://library.keqingmains.com/combat-mechanics/elemental-effects/elemental-resonance)、[KQM TCL Amber — C6 Wildfire](https://library.keqingmains.com/characters/pyro/amber#constellations)、[Akasha categories API](https://akasha.cv/api/v2/leaderboards/categories?characterId=10000046)。
- **confirmed**：胡桃とアンバーの2 Pyroを含む4人編成では、通常のFervent FlamesはATK +25%。アンバーC6はQ後10秒間チームへATK +15%を与える。
- **inferred**：Pyro Resonance +25%はカテゴリ固定編成に常時入る可能性が高い。
- **unknown**：説明文のAmber C0を採用するならC6 +15%は入らず、teammates metadataのC6を採用するなら入る。この15%は再現誤差が大きいため、最優先の比較仮説とする。

## 18. 胡桃のartifact set effects

- **source**：[KQM artifacts — Crimson Witch of Flames](https://library.keqingmains.com/equipment/artifacts#crimson-witch-of-flames)、[KQM artifacts — Shimenawa's Reminiscence](https://library.keqingmains.com/equipment/artifacts#shimenawas-reminiscence)、保存済みLeaderboard raw。
- **confirmed**：火魔女2セットは炎元素ダメージ+15%。4セットは蒸発・溶解のreaction bonus +15%で、E使用時に2セット効果の50%、すなわち炎元素ダメージ+7.5%を10秒得る。Hu Taoは通常の1回のE使用で1 stackを得る。
- **confirmed**：しめ縄2セットはATK +18%。4セットはE発動時にEnergyが15以上なら15を失い、通常・重撃・落下攻撃DMGを10秒間+50%する。
- **confirmed**：保存済み上位行では火魔女4セットとしめ縄4セットの両方が同じcalculation IDに存在し、しめ縄4セット行だけQのquantityが1/3、それ以外は2/3だった。
- **inferred**：火魔女4では炎+22.5%と蒸発reaction bonus +15%、しめ縄4ではATK +18%とN1/CA DMG +50%をコンボ中へ適用する。
- **unknown**：4セット以外の2+2構成や2026年追加セットについて、Akashaがどのset effectsをこの古いカテゴリで認識するかは公開されていない。初期実装は検証データに現れたセットだけを明示的に対応し、未知セットを無言で0扱いしない設計が必要である。

## 19. `11N1CD + Q` の評価方法

- **source**：[KQM combat notation](https://library.keqingmains.com/theorycrafting#combat-notation)、[対象Leaderboard raw](../data/akasha/raw/1000004605_20260913T043550.493548Z/page_0001.json)、[Akasha categories API](https://akasha.cv/api/v2/leaderboards/categories?characterId=10000046)。
- **confirmed**：`N1CD`は通常1段目、重撃、dash cancelを意味し、`11N1CD`はそれを11回繰り返す。
- **confirmed**：保存済みrank 1の`calculation.additional`は次の4項目だけであり、各`value × quantity`の総和が`calculation.result`と完全一致した。

| component | value | quantity |
| --- | ---: | ---: |
| NA Vape Avg DMG | 58,697.108515079824 | 4 |
| NA Avg DMG | 20,358.56690549663 | 7 |
| CA Vape Avg DMG | 170,204.0722225674 | 11 |
| Q Vape Avg DMG | 408,040.0897958355 | 2/3 |

したがって、非しめ縄4セットについて観測された集約式は次になる。

```text
calculation.result
= 4 × N1_vape_avg
 + 7 × N1_non_vape_avg
 + 11 × CA_vape_avg
 + (2/3) × Q_vape_avg
```

- **confirmed**：保存済みrank 4のしめ縄4セット行では同じN1/CA quantityを使い、Qだけ1/3だった。その総和も`calculation.result`と浮動小数点誤差約`4.7e-10`以内で一致した。
- **confirmed**：Blood Blossom、E発動、万葉/アンバー/Hydro本人のダメージ、Swirlダメージは`calculation.additional`の合計項目にない。
- **inferred**：11回のCAは全て蒸発、11回のN1は4回蒸発・7回非蒸発として固定する。Qは蒸発する。Qの2/3または1/3は複数ローテーションにわたるburst uptimeの期待値であり、確率抽選ではない。
- **unknown**：4回の蒸発N1が11回中のどの位置か、バフの経時失効を考慮するか、Qが低HP倍率か、各`Avg DMG`の内部丸めは不明である。`calculation.result`が小数を保持するため、ゲーム画面の整数丸めを各hitへ適用していない可能性はあるが、まだ確定できない。

## 20. 計算要素の分割案

巨大な`score`関数にせず、後の実装では次の純粋な計算単位に分ける。各単位はAkasha APIから独立してテストできるようにする。

1. **固定シナリオ**：計算上のキャラクターレベル、天賦、武器、編成、敵、低HP条件、buff uptimeを保持する。
2. **入力正規化**：聖遺物のHP/ATK/EM/会心/炎ダメージとset countを、Phase Bの1 build行から組み立てる。
3. **最大HP**：基礎HP、HP%、実数HP、護摩HP+20%から最大HPを返す。
4. **攻撃力**：基礎ATK、ATK%、実数ATK、外部ATK buff、護摩HP変換、胡桃E変換とcapを個別の内訳付きで返す。
5. **会心倍率**：CRIT Rateをclampし、平均会心倍率を返す。
6. **反応倍率**：EM、蒸発1.5、火魔女reaction bonusから増幅反応倍率を返す。
7. **Damage Bonus**：炎元素、通常、重撃、爆発の各bonusを攻撃種別ごとに返す。
8. **敵補正**：DEF multiplierとPyro RES multiplierを別々に返す。
9. **単発ダメージ**：N1非蒸発、N1蒸発、CA蒸発、Q蒸発をそれぞれ計算する。
10. **Akasha集約**：観測済みquantityだけを使い、4つの単発平均ダメージから`calculation.result`を返す。

各段階は値だけでなく内訳を返せる形にし、Akashaとの差を「HP」「ATK」「EM/反応」「DMG Bonus」「DEF/RES」「会心」「combo quantity」のどこで生じたか追跡できるようにする。

## 21. 実装前に解決する仮説

優先度順に、次を実データで切り分ける。

| ID | 仮説 | 比較方法 |
| --- | --- | --- |
| H1 | 胡桃Lv.90、通常/E/Q天賦Lv.10へ正規化 | 実レベル・凸・天賦が異なる複数buildで、同じ聖遺物由来入力に対する内訳を比較 |
| H2 | 全攻撃でHP<50%、胡桃A4、護摩低HP、Q低HP倍率が有効 | 単発N1/CA/Qの観測値を低HP有無の候補式と比較 |
| H3 | 敵Lv.90、基礎炎RES10%、翠緑後-30% | DEF/RES候補を分けて複数buildへ同じ定数が通るか確認 |
| H4 | 胡桃の外部EMは+420、万葉A4は1420 EMで炎+56.8% | EMの異なる複数buildで蒸発/非蒸発比と単発値を比較 |
| H5 | Pyro Resonance +25%、Millennial Movement由来ATKは+20%、Amber C6 +15%なし | ATK buff候補を組み合わせ、全buildに共通するものを確認 |
| H6 | 蒼古のN1/CA +16%が有効 | N1/CAとQの比から攻撃種別bonusを比較 |
| H7 | 火魔女はE 1 stack、しめ縄はN1/CA +50% | 火魔女4としめ縄4の実在buildを別々に照合 |
| H8 | 各hitは内部floatのまま計算し、最後まで整数丸めしない | 高精度係数を得た後、`calculation.additional`の小数部まで比較 |

これらは現時点では実測値を説明する候補であり、Akasha観測値を候補式へ合わせて変更してはならない。候補が合わない場合は、固定値や観測データではなく仮説側を修正する。

