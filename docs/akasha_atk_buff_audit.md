# Akasha胡桃 ATK buff監査

検証日: 2026-09-19  
対象: VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1 (calculation ID 1000004605)

## 結論

保存済み20 buildのstats.atkは、聖遺物ATK、しめ縄2pc、護摩R1のHP由来ATK 0.8%と低HP追加1.0%、炎共鳴25%を含む値として最大0.799 ATK以内で再構築できる。Millennial Movement 20%、Amber C6 15%、胡桃Eは含まれない。

ただし、これはraw fieldの境界についての結論である。AkashaのDamage backendがraw stats.atkをそのままprecombat ATKとして使うことを公開仕様から確認できたわけではない。保存済みLeaderboard行にはteam buffの適用順やDamage backendの中間ATKがなく、公開API/画面からも今回それを確認できなかった。この2点を分けて扱う。

約326.9 ATK不足へ効果総量が数値的に最も近い既知の組合せは、raw後の外部ATKを「Millennial 20% + 炎共鳴25%」とする候補である。ただし現行20%からの実増分は25%だけで、不足を解消しない。その25%はrawに含まれる炎共鳴の再加算でもあるため、本番評価関数へ採用しない。

## 対象scenarioから入り得るATK効果

| 効果 | 値 | raw stats.atk | combat時の扱い | 同種buffとのstack | 判定 |
| --- | ---: | --- | --- | --- | --- |
| 炎共鳴 | base ATKの25% | 含む。聖遺物からの再構築で支持 | raw起点では追加しない | 共鳴効果は1回 | raw境界 strongly supported / backend境界 unresolved |
| Elegy Millennial | base ATKの20% | 含まない | 現行baselineで1回追加 | Freedom-Swornの同じATK効果とは重複しない | 効果 strongly supported |
| Freedom-Sworn Millennial | base ATKの20% | 含まない | Elegyと同じATK枠。どちらか1回分 | Elegyの同じATK効果とは重複しない | 効果 strongly supported |
| Amber C6 | base ATKの15% | 含まない | Burst発動後10秒の条件付き。現行baselineは0% | Millennialとは別効果 | ゲーム効果 confirmed / 対象scenarioへの適用 unresolved |
| 聖遺物ATK%・実数ATK | buildごと | 含む | 再加算しない | 通常のATK式へ1回 | strongly supported |
| しめ縄2pc | ATK 18% | 該当buildで含む | 再加算しない | 聖遺物ATK%へ加算 | strongly supported |
| 護摩R1 基本passive | Max HPの0.8%をATKへ | 含む | 再加算しない | 別項 | strongly supported |
| 護摩R1 低HP追加 | Max HPの1.0%をATKへ | 含む | 再加算しない | 基本0.8%と加算 | strongly supported |
| 胡桃E | Max HPの6.26%、base ATK 400% cap | 含まない | raw・外部ATK後へ1回追加 | cap適用 | Talent Lv10 strongly supported |
| その他 | 確認できず | 不明 | 追加しない | 不明 | unknown |

対象カテゴリ説明は既存調査で「elegy instructor amber c0r1. kazuha c2r1 @ 1000EM(1420)」と観測されている。一方、過去に取得したteammates metadataではAmber C6表示との矛盾があった。したがってAmber C6のゲーム効果自体と、対象Leaderboardがその15%を適用するかを分離した。現行baselineの0%は観測比較に基づく仮説であり、Akasha内部仕様としてconfirmedではない。

## Millennial Movementのstacking

Elegy R1とFreedom-Sworn R1はいずれもMillennial Movementの一部としてATK +20%を与える。武器説明には同種buffが重複しない旨があり、KQM Theorycrafting Libraryの検証記録も、異なるMillennial武器の異なる効果は共存できるが、重なる同種効果は後から発動した側が上書きするとしている。

したがって、このscenarioで両武器が発動してもATKは+40%にならない。共存できるのは、たとえばElegyのEM +100とFreedom-Swornの通常・重撃Damage +16%のような異なる効果である。診断CSVには数値確認用として+40%候補を残すが、rejected_same_millennial_effect_does_not_stackと明記した。

- [Elegy for the End](https://genshin-impact.fandom.com/wiki/Elegy_for_the_End)
- [Freedom-Sworn](https://genshin-impact.fandom.com/wiki/Freedom-Sworn)
- [KQM Equipment Evidence: Millennial Movement](https://library.keqingmains.com/evidence/equipment/weapons)
- [Millennial Movement Series](https://genshin-impact.fandom.com/wiki/Millennial_Movement_Series)

## Pyro Resonanceの二つの境界

### raw fieldの意味

20 buildについて次式を使った。

~~~
reconstructed raw ATK
= base ATK × (1 + artifact ATK% + artifact set ATK% + Pyro Resonance 25%)
+ artifact flat ATK
+ Max HP × (Homa 0.8% + Homa low-HP 1.0%)
~~~

rawとの差は平均+0.235 ATK、範囲-0.379〜+0.799 ATKだった。聖遺物カードの表示丸めで説明できる大きさであり、rawが炎共鳴25%を含むというH5結論を再確認した。

### Damage backendへ渡されるATK

確認できた公開Leaderboard rowはcalculation.resultとcalculation.additionalを持つが、backendのprecombat ATKやbuff適用順は公開していない。したがって「rawに炎共鳴が入っている」から「backendがrawを直接使う」とは断定しない。

現在の実装は境界が明確で再現可能な次式を使う。

~~~
final ATK
= raw stats.atk
+ base ATK × one Millennial 20%
+ Hu Tao E bonus
~~~

独立経路ではrawを使わず、聖遺物・base stat・weapon・護摩・炎共鳴を各1回組み立て、その後MillennialとEを各1回加える。この2経路の差が最大0.799 ATKだったため、現行raw経路は独立再構築と整合する。

## 出典と限界

ゲーム効果の数値は以下を参照した。

- [Pyro Resonance / Fervent Flames](https://genshin-impact.fandom.com/wiki/Pyro)
- [Staff of Homa](https://genshin-impact.fandom.com/wiki/Staff_of_Homa)
- [Amber C6](https://genshin-impact.fandom.com/wiki/Amber)
- [Shimenawa's Reminiscence](https://genshin-impact.fandom.com/wiki/Shimenawa%27s_Reminiscence)
- [KQM Hu Tao data](https://library.keqingmains.com/characters/pyro/hu-tao)
- [Akasha-py README](https://github.com/seriaati/akasha-py/blob/main/README.md)

これらはゲーム内説明を転載・検証するcommunity資料であり、Akasha backendの正式仕様ではない。Akasha-pyもLeaderboard結果を読むwrapperで、buff適用順を公開していない。今回、Akashaの公開frontend/APIから追加のATK中間値は確認できなかった。
