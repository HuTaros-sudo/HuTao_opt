# Akasha Hu Tao H3: 敵DEF・Pyro RES条件の事前調査

調査日: 2026-09-13  
対象Leaderboard: `1000004605` — `VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1`

この文書は候補値を決めるための事前調査であり、Akasha観測Damageへの一致から敵条件を確定するものではない。

## 調査した公開情報

### Akasha公開ページ・API metadata

- [Akasha Leaderboards一覧](https://akasha.cv/leaderboards)は、ランキング前にキャラクターを通常Lv90/90、crowned talent、低凸、R1武器など同一状態へresetし、同じteam buffを適用すると説明している。
- [対象Leaderboard](https://akasha.cv/leaderboards/1000004605/)の2026-09-13時点の表示説明は、`Average DMG for 11N1CD + Q combo. elegy instructor amber c0r1. kazuha c2r1 @ 1000EM(1420). 4p SR burst uptime 1/3, other sets: 2/3.` である。
- 対象ページの名前に`VV Swirl`が含まれ、team欄にはKazuhaが表示される。ただし、敵レベル、敵種、基礎Pyro RES、適用後RES、DEF reduction/ignoreは説明にない。
- `GET /api/v2/leaderboards/categories?characterId=10000046`で以前保存・確認したcategory metadata、および`GET /api/leaderboards`の保存済み20行を`enemy`、`resistance`、`defense`、`level`で確認した。`propMap.level`などキャラクター側のlevelはあるが、敵レベル・敵RES・敵DEFを表すフィールドは確認できなかった。
- 現行frontendは`/static/js/main.c56e59bd.js`を読み込んでいることをページDOMから確認したが、公開source repositoryやsource mapは確認できなかった。画面の表示内容にも敵条件はない。

### GitHub・既存wrapper・issue検索

- [`akasha-py`](https://github.com/seriaati/akasha-py)のLeaderboard取得例と固定コミットのmodel/clientを確認した。wrapperは`calculation.result`、`additional`、build stats等を読むが、敵レベル・敵RESの型やparameterは持っていない。またREADMEはAkasha APIが予告なく頻繁に変わるという開発者からの注意を記載している。
- GitHubおよびWeb検索で`akasha.cv enemyLevel`、`enemy resistance Akasha System`、対象Leaderboard名との組合せを調べたが、Akasha内部の敵条件を示す公開実装・issue・開発者説明は見つからなかった。
- Akashaの計算backend実装は公開されていると確認できなかった。第三者wrapperの不在フィールドは「Akashaがその条件を使わない」証拠ではなく、APIが公開していないことだけを示す。

### 検証済み原神計算資料

- [KQM Damage Formula](https://library.keqingmains.com/combat-mechanics/damage/damage-formula#enemy-defense)は次のDEF倍率を示す。

  ```text
  DEF multiplier = (character level + 100)
      / ((character level + 100) + (enemy level + 100)
         × (1 - DEF reduction) × (1 - DEF ignore))
  ```

- 同資料の[Enemy Resistance](https://library.keqingmains.com/combat-mechanics/damage/damage-formula#enemy-resistance)はRES倍率の3分岐を示す。

  ```text
  RES < 0:       1 - RES / 2
  0 <= RES < .75: 1 - RES
  RES >= .75:    1 / (4 × RES + 1)
  ```

- [KQM Enemy Resistances](https://library.keqingmains.com/combat-mechanics/enemy-mechanics/enemy-resistances)は最も一般的な敵基礎RESが10%であること、翠緑4セットがSwirlした元素のRESを40%下げることを記載している。
- [KQM Viridescent Venerer](https://library.keqingmains.com/equipment/artifacts#viridescent-venerer)も4pcの40% RES低下と、装備者がon-fieldでSwirlを起こす必要があることを記載している。

### 一般的なcalculator条件

- 公開されている一般的なGenshin calculatorは敵レベルと元素RESをユーザー入力にするものが多い。検索で確認したcalculator例では、Lv90敵と一般敵の10% RESを例または初期条件にしていた。
- Lv80/90/100は、Lv90固定キャラクターに対する低い・同レベル・高い敵という離散比較に使える。Lv87など観測値へ合わせた任意レベルを候補にする根拠は見つからなかった。
- 基礎RES 0%と10%は、無耐性の理論対照とKQMが示す一般敵条件として比較できる。3.7%などの任意値を使う根拠はない。

## 状態整理

### confirmed

- 原神のDEF倍率式とRES倍率のpiecewise式。
- 翠緑4pcは、条件を満たすSwirlで該当元素RESを40%低下させる。
- 一般的な敵の基礎RESとして10%が最も多い。
- 対象Leaderboardの名称は`VV Swirl`で、公開説明はKazuha編成を明記する。
- Akasha公開ページと保存済みAPI応答には、敵レベル・敵RESの明示値がない。

### inferred

- `VV Swirl`という名称から、Pyro RESへ翠緑40%低下を適用する候補が最優先である。
- Akasha全体の「usually level 90/90」という説明と従来calculator慣行から、敵Lv90・基礎RES10%は妥当なbaseline候補である。
- 対象team metadataにDEF reduction/ignore役は確認できないため、両方0を維持する。

### unknown

- Akasha内部で実際に固定された敵レベル。
- 想定敵の基礎Pyro RESが0%か10%か、または特定敵の別値か。
- `VV Swirl`が名称だけでなく、全4 componentへ常時40%低下として実装されているか。
- Leaderboard作成時点と現行backendで敵条件が同じか。

## 検証へ渡す離散候補

character levelはH1に従い90固定、DEF reduction/ignoreは0固定とする。次の直積12候補だけを比較する。

- enemy level: 80 / 90 / 100
- base Pyro RES: 0% / 10%
- VV reduction: 40% / 0%

Lv90・10%・VV40%をbaselineとする。VVなしは対象名と反する可能性が高いが、40%適用の効果量を分離する対照群として残す。観測値から連続的なenemy levelやRESを逆算して候補追加しない。
