# Akasha胡桃 約7.1%共通残差のbase damage側候補

調査日: 2026-09-14  
対象: `VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1`  
目的: 本番式を変更せず、全componentへ共通して作用し得る次の検証対象を絞る

## 観測から分かること

現在の20 build平均相対誤差はAggregate -7.1403%。component別にもN1 non-vape -7.2170%、N1 vape -7.1904%、CA vape -7.1195%、Q vape -7.2010%とほぼ同率である。同一build内のcomponent ratio spreadも小さい。

CRIT境界はH7でstrongly supportedとなり、required/current crit multiplierはほぼ一定だった。順位診断でも共通scale 1.0768838049を掛ければ平均位置だけが動き、順位は変わらなかった。一方、既存H1/H3診断ではAggregate residualとMax HPにPearson `r=+0.920405`が残る。このため、次の調査では「約7.1%の共通位置」と「HPに依存する小さなbuild間残差」を分ける。

一般Damage式では、ATK依存攻撃のbase damageは`Talent% × ATK`であり、その後にDamage Bonus、CRIT、DEF、RES、増幅反応が掛かる。[KQM Damage Formula](https://library.keqingmains.com/combat-mechanics/damage/damage-formula)

## 候補の棚卸し

| 候補 | 現在の入力 | 7.1%を単独説明できる見込み | 次の診断 |
|---|---|---|---|
| N1/CA/Q talent倍率の内部精度 | Lv10表示値 83.6%、242.6%、低HPQ 617% | **低い**。倍率は攻撃ごとに独立で、4 componentのほぼ同率不足を一つの誤りで説明しにくい | 公開された既知の内部値だけでcomponentごとの差を比較 |
| Hu Tao E倍率の内部精度 | Lv10表示値6.26% | **共通項としてはあり得るが、7.1%全量は低い**。Eは最終ATKへ共通に効き、HP相関とも整合する。しかし表示丸めの範囲は小さい | game-data由来の係数精度とE加算前後のATKを独立比較 |
| raw baseAtk `714.5089773` | raw値を外部ATK 20%とE capに使用 | **極めて低い**。表示714との差は0.0713%で、raw precombat ATK自体は既にこの内部値で作られている | 106と608の個別内部値をgame-data資産から特定 |
| raw Max HPからE ATKへの内部精度 | raw `stats.maxHp`を直接使い`×0.0626` | **build依存残差の有力候補**。raw Max HP境界はH1でstrongly supportedだが、HP相関が残る | rawを作った内部HP値、表示丸め、E適用時の丸め順を確認 |
| low HP条件 | A4、Homa、低HPQを有効 | **一括の7.1%説明には不向き**。Q倍率だけはcomponent固有。A4/HomaのON/OFF差は7.1%より大きく、境界検証とも衝突 | Akasha category descriptionまたはbackend metadataを探す |
| Homa low-HP passive | raw ATKに0.8%+1.0%を包含し再加算しない | **低い**。H5でraw境界がstrongly supported。欠落させるとHP依存で全componentが下がる | raw ATK独立再構築の精度を増やす場合だけ再訪 |
| Hu Tao A4 | raw Pyro Bonusには未包含、combatで+33% | **低い**。H6で境界がstrongly supported。追加漏れなら誤差は大きく、既に追加済み | 変更しない |
| 敵DEF/RES以外の一般式共通項 | BaseDMGMultiplier、AdditiveBaseDMGBonus、target DMG reduction等 | **現時点で根拠なし**。Hu Taoの対象4攻撃に共通する追加base damage sourceは確認できない | Akasha backendの中間値が得られた場合だけ検証 |
| H3 DEF/RES | baseline共通倍率0.575 | **大きさは説明可能だがunresolved**。Lv80/RES0/VV40の離散候補は不足の93.23%を説明したが公開根拠がない | backend/category metadataの敵条件を優先調査 |

## talent倍率の精度

[KQM Hu Tao](https://library.keqingmains.com/characters/pyro/hu-tao)はLv10について、N1 83.6%、CA 242.6%、E 6.26%、通常HP Q 494%、低HP Q 617%を表示する。より細かい既知値としてN1 83.65%、CA 242.56%と報告される資料もあるが、現在値との差は約+0.060%と-0.016%である。QやEも表示丸めの内部差だけなら通常は0.1%未満で、7.1%には届かない。

さらに、N1だけの倍率差はN1 vapeとnon-vapeへ同率で効くがCA/Qへは効かない。4 component全部が約7.1%不足するためには、N1、CA、Qの3係数が偶然ほぼ同じ比率で誤っている必要がある。これは検証可能だが、最初の共通原因候補としては弱い。

## E、Max HP、base ATK

KQMはEが発動時Max HPに比例し、増加量がBase ATKの400%を超えないと記録する。Lv10表示値は6.26%である。[KQM Hu Tao](https://library.keqingmains.com/characters/pyro/hu-tao)

E ATKはN1/CA/Qすべての最終ATKへ共通に入るため、componentの同率ずれを作れる。20 buildではcap到達がなく、E加算はMax HPに線形である。従って残差とMax HPの強い相関を追う候補としては最優先である。ただしH1の離散Talent候補ではLv10がbuild間残差形状を最もよく説明した。6.26%を観測に合わせて任意fitする根拠はない。

全20 buildのraw `stats.baseAtk`は **714.5089773** で完全に同一だった。表示値ではHu Tao Lv90が106、Staff of Homa Lv90が608で合計714である。[KQM Hu Tao base stats](https://library.keqingmains.com/characters/pyro/hu-tao)、[KQM Staff of Homa](https://library.keqingmains.com/equipment/weapons/polearms#staff-of-homa)

rawとの差0.5089773はゲーム内部の成長曲線精度を保持した値と推測できる。EnkaのAPI定義でもfight property 4はBase ATK、武器の`FIGHT_PROP_BASE_ATTACK`は武器Base ATKとされるが、Akashaが個別内部値をどう合成したかは公開されていない。[Enka API docs](https://github.com/EnkaNetwork/API-docs/blob/master/docs/gi/api.md)

この差は合計base ATKの0.0713%である。raw `stats.atk`は既に内部base ATKを含み、現在のraw経路でbaseAtkが新たに効く主項は外部ATK20%とE capだけである。cap未到達なので、714と714.5089773の違いが7.1%を作ることはできない。

## low HP、Homa、A4

Staff of Homa R1はMax HP+20%、Max HPの0.8%をATKへ加え、HP 50%未満ならさらに1.0%を加える。[KQM Staff of Homa](https://library.keqingmains.com/equipment/weapons/polearms#staff-of-homa) Hu Tao A4はHP 50%以下でPyro DMG Bonus +33%、Qも50%以下で高倍率になる。[KQM Hu Tao](https://library.keqingmains.com/characters/pyro/hu-tao)

H5/H6ではHoma低HPATKがraw `stats.atk`に既に含まれ、A4はraw `stats.pyroDamageBonus`に含まれずcombat時に追加する境界がstrongly supportedとなった。現在のコードはこの境界どおりである。Homaをもう一度足すのは二重計上になる。A4を外す、またはQだけ通常HPへ変えると、4 componentの同率不足という観測形状を保てない。

## Akasha frontend/API/rawの中間値

確認できた公開frontendはReactの表示コードで、Leaderboard行ではAPIの`row.calculation.result`を丸めて表示し、categoryとchartもAPIから取得している。公開ファイル内に`enemy`はなく、`calculation.additional`を使ったDamage再計算も見つからなかった。[Akasha frontend repository](https://github.com/Peacerekam/Akasha-FE-react)、[Leaderboard表示実装](https://github.com/Peacerekam/Akasha-FE-react/blob/main/src/pages/LeaderboardsPage/LeaderboardsPage.tsx)

保存済みrawの`calculation`直下は`id`、`result`、`additional`だけである。`additional`は4 componentの`name/value/quantity/type`を持つが、pre-crit damage、final ATK、E bonus、talent内部値、DEF、RESなどの途中値はない。top-levelには`stats`、`artifactObjects`、`weapon`、`talentsLevelMap`等があるが、これらは入力・表示用フィールドであり計算途中値ではない。

`akasha-py`もLeaderboard例で`board.calculation.result`を読むwrapperであり、Akasha開発者ではないこと、APIが告知なく頻繁に変わることを明記する。[akasha-py README](https://github.com/seriaati/akasha-py/blob/main/README.md)

従って公開frontend/APIからは、現在の約7.1%をbase damageのどの段階へ帰属させる直接証拠は得られなかった。backend計算実装は確認できない。

## 次の調査順

1. **E加算の内部精度と丸め順**を既知のgame-data値だけで再検証する。raw Max HPをそのまま使い、E coefficient、E加算、final ATKのどこで内部floatまたは丸めを使うかを分ける。目的は平均誤差fitではなく、Max HP相関とbuild間ratio stdが減るかを見ること。
2. **N1/CA/Qの既知の高精度Lv10倍率**を独立候補として比較する。3種を自由fitせず、component ratioの差だけを見る。
3. **raw baseAtk 714.5089773の個別内訳**をgame-data資産から確認する。影響は小さいと予想されるため優先度は低い。
4. **H3の公開根拠**を再探索する。約7.1%の共通位置を説明できる離散候補はH3だが、現状は観測一致しか根拠がない。

本Phaseでは新しい係数、scale、talent値を`ScenarioConfig`や本番評価関数へ追加していない。

