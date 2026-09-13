# Akasha Hu Tao H1: Max HP境界・胡桃E変換の独立検証

検証日: 2026-09-13  
対象: `VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1` (`leaderboard_id=1000004605`) の保存済み20 build

## 結論と状態

H1は、この検証範囲では **strongly supported** とする。

- `raw stats.maxHp`は、**Lv90胡桃の基礎HP + 5聖遺物のHP%/実数HP + 護摩R1のHP+20%** で20件すべて表示丸め誤差内に再構築できた。
- 公開プロフィールの実レベルが95/100でもraw Max HPはLv90式に一致する。実プロフィールレベルを使う候補はbuild間に大きな段差を作るため rejected。
- 公開プロフィールでC3以上の11件は表示E Lv13だが、rawの`elementalSkill.rawLevel`は20件すべて10である。実プロフィールのLv10/Lv13を混在させる候補はbuild間残差を約15倍に広げるため rejected。
- Akasha固有のE倍率を表示どおり厳密に6.26%とする点は **unresolved**。固定Lv10はmetadataに強く支持されるが、表示丸め前の内部倍率は公開されていない。Damage残差のばらつきだけでは固定Lv9候補がわずかに小さく、未検証の共通項との交絡が残る。

観測Damage、保存済みraw、既存のH3/H4/H6設定は変更していない。最小二乗scaleは診断列だけに出力し、Damage engineや`ScenarioConfig`へ組み込んでいない。

## 情報源

優先順に次を用いた。

1. [HoYoWiki 胡桃](https://wiki.hoyolab.com/pc/genshin/entry/34/) — 公式。Lv90基礎HP 15,552、基礎ATK 106を確認。
2. [KQM Theorycrafting Library: Hu Tao](https://library.keqingmains.com/characters/pyro/hu-tao) — Eが発動時Max HPを参照し、増加ATKが基礎ATKの400%上限であること、および既知の離散倍率 Lv9 5.96%、Lv10 6.26%、Lv11 6.56%、Lv13 7.15%を確認。C3がE天賦+3であることも確認。
3. [Genshin Impact Wiki: Hu Tao](https://genshin-impact.fandom.com/wiki/Hu_Tao) — Lv90 15,552.31、Lv95 16,104.39、Lv100 16,657.69の比較用高精度表示値。
4. [Akasha対象Leaderboard](https://akasha.cv/leaderboards/1000004605/) と各buildの`/profile/{uid}?build={md5}` — 対象md5の5聖遺物カードに表示されたHP%・実数HP、および保存済み非公式API raw。

公式HoYoWikiはLv90までの表示値を確認できるが、検証日時点のcrawler出力にはLv95/100の行がない。このためLv95/100候補だけは検証済み二次資料の値で比較した。

## 1. raw Max HPの再構築

各プロフィールで対象`md5`を指定し、花・羽・時計・杯・冠の5カードから`hp`と`flathp`を独立に取得した。花のLv20メイン実数HP 4,780と、HP時計のLv20メイン46.6%も部位別列へ含めた。20件中1件だけEM時計である。

比較式は次のとおり。

```text
A = baseHP(Lv90)  × (1 + artifact HP% + Homa R1 20%) + artifact flat HP
B = baseHP(Lv90)  × (1 + artifact HP%)              + artifact flat HP
C = baseHP(Lv100) × (1 + artifact HP% + Homa R1 20%) + artifact flat HP
D = baseHP(profile actual level) × (1 + artifact HP% + Homa R1 20%) + artifact flat HP
```

| 候補 | 平均絶対差 | 最大絶対差 | 平均相対差 | 最大絶対相対差 |
|---|---:|---:|---:|---:|
| A: Lv90 + artifact + Homa R1 | 6.498 HP | **23.335 HP** | +0.0098% | **0.0668%** |
| B: AからHoma 20%を除外 | 3,107.072 HP | 3,121.092 HP | -9.0477% | 10.1532% |
| C: Lv100 + artifact + Homa R1 | 2,091.066 HP | 2,291.009 HP | +6.0748% | 6.1857% |
| D: 実プロフィールlevel + artifact + Homa R1 | 1,002.277 HP | 2,291.009 HP | +2.9006% | 6.1857% |

Aの差は-10.630〜+23.335 HPで、保守的な表示丸め誤差上限の最大40.381 HP以内に20件すべて収まった。HP%各表示値を±0.05 percentage point、実数HP各表示値を±0.5として加算伝播した上限である。HP時計46.6%や花4,780は固定メイン値なので、実際の不確かさはこの上限より小さい可能性がある。

Aを逆算した推定基礎HPは平均15,550.527、範囲15,540.182〜15,557.961だった。Lv90基礎HPを固定して逆算した護摩HP%は平均19.9782%、範囲19.8500〜20.0684%であり、表示丸めを考慮するとR1の20%と整合する。

対象20件のset構成にHPを加える2セット効果は存在しなかった。火魔女4件またはしめ縄4件と自由枠1件が中心で、`artifact_set_hp_pct`は全件0として明示した。

## 2. level正規化境界

rawに`baseHp`フィールドはない。`propMap.level`は公開プロフィールの実レベルで、内訳はLv90が9件、Lv95が3件、Lv100が8件だった。しかし、Lv95/100の11件もAのLv90式に一致する。

別の独立信号として、rawの`stats.baseAtk`は全20件で約714.509である。これはLv90胡桃とLv90護摩の合計に対応し、実プロフィールのLv95/100や実武器精錬とは連動しない。したがって`propMap.level`はLeaderboard計算入力ではなく、プロフィール由来metadataと判断するのが妥当である。

Dの平均相対差を実レベル別に見ると、Lv90群は0.0154%、Lv95群は3.0173%、Lv100群は6.1072%。この階段状誤差はプロフィール実レベルを使わない証拠である。

## 3. E bonusと400% cap

各候補で次を保存した。

```text
uncapped_e_atk_bonus = max_hp × known_talent_ratio
e_atk_cap            = raw base_atk × 4
final_e_atk_bonus    = min(uncapped_e_atk_bonus, e_atk_cap)
```

Lv9、10、11、13のいずれもcap到達は **0 / 20 build**。最も大きいLv13のuncapped値でも2,648.038、最小capは2,858.036で、cap比は最大92.65%だった。このデータセットではcap分岐はE倍率候補の比較へ影響しない。

## 4. E倍率候補とbuild間残差

次表はMax HPにraw観測値を使い、他仮説をbaselineのまま固定したAggregate結果である。相対誤差は`predicted / observed - 1`。標準偏差は母標準偏差である。

| E候補 | 平均相対誤差 | 残差std | observed/predicted ratio std | residual vs Max HP | vs E bonus | vs raw ATK | vs artifact HP% |
|---|---:|---:|---:|---:|---:|---:|---:|
| 固定Lv9 5.96% | -9.4185% | **0.1876%** | **0.2287%** | +0.8172 | +0.8172 | +0.8690 | +0.8340 |
| 固定Lv10 6.26% | -7.1403% | 0.2116% | 0.2457% | +0.9204 | +0.9204 | +0.7448 | +0.9286 |
| 固定Lv11 6.56% | -4.8621% | 0.2431% | 0.2691% | +0.9716 | +0.9716 | +0.6260 | +0.9729 |
| 固定Lv13 7.15% | -0.3817% | 0.3181% | 0.3211% | +0.9991 | +0.9991 | +0.4452 | +0.9913 |
| 実プロフィールLv10/Lv13混合 | -3.4271% | **3.4247%** | **3.7036%** | +0.2004 | +0.8922 | +0.3984 | +0.1978 |

固定Lv13は平均値だけなら観測へ近いが、build間の残差とratioのばらつきはLv10より大きい。これは共通倍率の不足をE倍率で埋める見かけ上の一致であり、Lv13採用の根拠にしない。

実プロフィールでは11件がC3以上で表示E Lv13、9件がLv10である。しかしrawの`elementalSkill.rawLevel`は20件すべて10で、C3群だけ`level=13, boosted=true`となる。実表示レベルをそのまま使う混合候補は残差std 3.4247%となり、固定Lv10の0.2116%より約16倍大きい。対象LeaderboardがC1固定であり、プロフィールC3を計算へ持ち込まないという仮説を強く支持する。

固定候補だけのscale-invariantな残差形状ではLv9が最小だが、Lv9とLv10のscaled residual std差は0.0208 percentage pointに留まる。raw metadataが全件`rawLevel=10`であることと合わせ、表示Lv10をbaselineとして維持する。Damage観測だけから6.26%の内部精度までconfirmedとはしない。

## 5. 診断用scale正規化

各候補について全20件に共通する1個だけを、次の最小二乗で求めた。

```text
scale = Σ(observed_i × predicted_i) / Σ(predicted_i²)
```

| E候補 | diagnostic scale | scale後の相対誤差std | scale後 residual vs Max HP |
|---|---:|---:|---:|
| 固定Lv9 | 1.103970 | **0.2071%** | +0.8172 |
| 固定Lv10 | 1.076884 | 0.2279% | +0.9204 |
| 固定Lv11 | 1.051095 | 0.2556% | +0.9716 |
| 固定Lv13 | 1.003816 | 0.3193% | +0.9991 |
| 実プロフィールLv10/Lv13混合 | 1.034201 | 3.5419% | +0.2004 |

共通scaleは平均的な不足を除くが、build間の形状は変えない。相対誤差への正の定数・正の倍率変換なのでPearson相関が同じになるのは想定どおりである。scale値はCSVの`diagnostic_least_squares_scale`にのみ保存し、本番計算へ適用していない。

## 6. 判断と次の検証

- **Max HP正規化境界: strongly supported** — Aだけが20件すべて表示丸め内。Lv90固定と護摩R1 20%の両方を外す候補は明確に悪化する。
- **プロフィール実レベル使用: rejected** — Lv95/100群だけ3%/6%の段差を作る。
- **プロフィールC3によるE Lv13使用: rejected** — rawLevelは全件10で、混合モデルがbuild間残差を大幅に増やす。
- **Leaderboard固定E Lv10: strongly supported** — C1固定metadataと全件rawLevel10が一致する。
- **E内部倍率が表示値6.26%と完全一致: unresolved** — scale-invariant残差だけではLv9が僅差で小さく、未確定の共通計算項が残る。

Max HP境界とC3除外は十分に分離できたため、次はH3へ進める。H3ではLv90、raw Max HP、固定E Lv10 6.26%をbaselineとして保持し、敵DEF/RESの共通倍率だけを比較する。H3後もMax HP相関が残る場合に限り、Eの内部精度またはHP依存の別項を再検討する。

## 出力データ

- `data/akasha/h1_maxhp_reconstruction.csv`: 1行=1 build。5部位のHP%/実数HP、A〜D、差、丸め上限、プロフィールlevel/C/E metadataを保存。
- `data/akasha/h1_e_bonus_comparison.csv`: 1行=1 build×Max HP候補×E候補。uncapped/cap/final E bonus、観測・予測Aggregate、相対誤差、ratio、相関、診断scaleとscale後残差を保存。

後者は20 build × 5 Max HP入力（raw参照+A〜D）× 5 Eモデル（固定Lv9/10/11/13+プロフィール実Lv）=500行である。
