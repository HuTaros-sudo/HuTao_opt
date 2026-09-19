# Hu Tao cross-weapon leaderboard research

調査日: 2026-09-19

## 結論

Akashaの公開categories APIには、`VV Swirl Hyper Tao Combo, Avg DMG`の同じカテゴリ内に3つの武器別Leaderboardがある。Homa R1に加え、Staff of the Scarlet Sands R1とBallad of the Fjords R5が公開されている。説明文、team metadata、combo、しめ縄のQ uptime、artifact filterは武器間で一致する。赤砂だけは「1 stack」の武器固有条件が追加される。

公開APIはAkashaの非公式・無保証のエンドポイントとして扱う。`akasha-py`もAPI変更の可能性を明記しており、クライアント実装は`https://akasha.cv/api`を基点にcategoriesとleaderboardsを取得している。

Sources:

- [Akasha categories API: Hu Tao](https://akasha.cv/api/v2/leaderboards/categories?characterId=10000046)
- [akasha-py README](https://github.com/seriaati/akasha-py/blob/main/README.md)
- [akasha-py client implementation](https://github.com/seriaati/akasha-py/blob/main/akasha/client.py)
- [KQM Polearms](https://library.keqingmains.com/equipment/weapons/polearms)
- [KQM weapon evidence](https://library.keqingmains.com/evidence/equipment/weapons)

## Categories

| calculation ID | weapon | refinement | weapon base ATK | raw total base ATK | comparison status |
|---|---|---:|---:|---:|---|
| `1000004605` | Staff of Homa | R1 | 608 | 714.5089773 | eligible baseline |
| `1000004606` | Staff of the Scarlet Sands | R1 | 542 | 648.2641381 | observed, excluded from identification fit |
| `1000004607` | Ballad of the Fjords | R5 | 510 | 616.0403291 | eligible |

`raw total base ATK`は各Leaderboard rawの`stats.baseAtk`であり、20 build内で一定だった。表示値ではHu Tao 106と各武器base ATKの和になるが、Akasha rawは内部精度を含む値を返す。

全カテゴリの共通説明は次の通り。

> Average DMG for 11N1CD + Q combo. elegy instructor amber c0r1. kazuha c2r1 @ 1000EM(1420). 4p SR burst uptime 1/3, other sets: 2/3.

赤砂だけは`Scarlet Sands set to 1 stack for simplicity.`が追加される。KQMの武器資料では、赤砂はEMからATKへ変換し、Elemental Skill命中で追加stackを得る。AkashaのEM入力時点とsnapshot境界を今回独立再構築できないため、赤砂のraw-based unexplained ATKは参考値として保存するが、flat/proportional/affine判定には使わない。

Ballad R5の武器固有効果は3元素以上でEMを加える。主指標のN1 non-vapeはVaporizeを使わず、現在式にもEM項がない。このためN1 non-vapeからのrequired final ATK診断には使える。ただしこれは複数武器対応の本番モデルを意味せず、診断専用の境界である。

## Scenario difference audit

Homaを基準に機械比較した結果、次のflagはBallad・Scarletともすべて`false`だった。

- Kazuha EM
- Kazuha constellation
- Freedom-Sworn
- Amber constellation metadata
- Elegy
- Instructor
- Hydro teammate metadata
- Pyro Resonance condition
- combo
- Q uptime
- artifact set rule

武器だけが異なり、赤砂には前述の1-stack条件だけが加わる。他の公開カテゴリであるDouble HydroやFurina Variantはteamとbuffが異なるため比較対象から除外した。

## Complete team metadata audit

categories APIに記録されたteam slotは次の4枠である。

| slot | character | constellation | weapon | refinement | artifact set | Hu Taoへの既知の影響 |
|---:|---|---:|---|---:|---|---|
| 1 | Hu Tao | C1 | category weapon | category依存 | build依存 | 評価対象 |
| 2 | **unknown Hydro** | unknown | unknown | unknown | `null` | 公開metadataから特定不能 |
| 3 | Kaedehara Kazuha | C2 | Freedom-Sworn | R1 | 4x Viridescent Venerer | C2 EM、A4、VV、Freedom-Sworn |
| 4 | Amber | metadataはC6 | Elegy for the End | R1 | 4x Instructor | Pyro Resonance、Elegy、Instructor。C6は説明文と矛盾 |

「4人目」をteamの最後のslotという意味で読むとAmberである。未特定だった枠は実際には2番目のHydro slotで、APIは元素以外のcharacter名、constellation、weapon、artifact setを公開していない。したがって、この枠からbase-ATK比例buffが来るという証拠は得られない。一方、存在しないとも断定できないため`unknown`を維持する。

Amberについては構造化metadataがC6である一方、カテゴリ説明は`amber c0r1`と書く。C6の+15% ATKをAkasha計算が使うかはmetadataだけでは確定できず、既存baselineの+0%を変更する根拠にはしない。

## Data collection

各Leaderboardから上位20件を1ページだけ取得した。ページング・retryを行わず、既存の過剰アクセス防止方針に従った。取得URLは以下の形式である。

`https://akasha.cv/api/leaderboards?calculationId=<ID>&size=20&page=1&sort=calculation.result&order=-1`

rawにはUID等が含まれるためGit管理外の`data/akasha/`に保存した。整形済みカテゴリ表とbuild別診断も同じくGit管理外に置く。

