# 原神 聖遺物最適化ツール

PythonとStreamlitで作る、ローカル用の試作品です。
現在は聖遺物のデータ型、入力検証、手入力JSONの読込、小規模な全探索、聖啓の塵の確率計算とStreamlit画面まで実装しています。通常GUIは胡桃の「Akasha推定Damage」で現在装備、最適装備、再構築後の採否を同じ基準で比較します。人工評価関数はoptimizer自体のテスト用途として残しています。

Akasha観測データは、指定Leaderboardの順位と`calculation.result`を非公式公開エンドポイントから低頻度で取得し、raw JSONと整形済みCSVへ分離保存できます。Hu Tao用Damage計算は検証済み境界と未解決仮説を分けた推定段階で、Akashaの完全再現ではありません。

## 公開データの扱い

`.gitignore`は、ユーザーが入力した所持聖遺物、Akashaから取得したraw、派生CSV、公開playerのUID・build識別子を含むローカル観測値をGit管理から除外します。公開用サンプルとして追跡する入力データは`data/sample_inventory.json`だけです。Akashaデータを再取得した後は、`data/akasha/`を誤って強制追加しないでください。

Akasha rawを必要とする診断テストは、rawがない公開cloneでは収集対象外になります。`data/akasha/raw/`へ観測データを取得すると自動的に有効になり、ローカルでは全診断を実行できます。

APIキーなどを将来使う場合は`.env`または`.streamlit/secrets.toml`へ保存します。これらはGit管理から除外されています。秘密値をソースコード、README、テストfixtureへ直接書かないでください。

## 必要な環境

- Python 3.11以上（動作確認には3.12を使用）
- Windows PowerShell

以下のコマンドは、プロジェクトのルートフォルダーで実行してください。

```powershell
cd path\to\Genshin_opt
```

## 初回セットアップ

通常のPython環境では、次のコマンドで仮想環境を作ります。

```powershell
python -m venv .venv
```

続いて依存パッケージをインストールします。インターネット接続が必要です。
すでにこの作業で作成された`.venv`がある場合、仮想環境の作成は不要です。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

仮想環境のPythonを直接指定するため、Activate.ps1の実行やPowerShellの実行ポリシー変更は不要です。
依存パッケージはStreamlitとpytestの2つです。requirements.txtでは許容バージョン範囲を指定しており、完全な固定ではありません。

## 起動

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

ブラウザーで「原神 聖遺物最適化ツール」と表示されれば成功です。
自動で開かない場合は、ターミナルに表示されるURL（通常は http://127.0.0.1:8501 ）を開いてください。
停止するには、起動したターミナルで`Ctrl+C`を押します。

画面では所持聖遺物JSONを入力し、火魔女として扱う`set_name`を選びます。「現在装備を選択」で各部位を指定すると、現在装備の4 componentとAggregateが表示されます。火魔女4セット制約を有効にすると、全探索結果は火魔女4部位以上を満たします。表示値はAkasha完全再現値ではなく「Akasha推定Damage」です。

## テスト

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

データ読込、入力検証、初期値の任意入力と再構築用チェック、全探索optimizer、再構築後の再最適化、パッケージのimport、Streamlitの起動・入力・計算を確認します。
ブラウザーを開いたり、別途Streamlitサーバーを起動したりする必要はありません。

## Akasha Leaderboard観測データ

対象「VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1」の2026-09-13時点のLeaderboard IDは`1000004605`です。上位20件を1ページ取得する例です。

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m genshin_opt.akasha.cli 1000004605 --max-pages 1 --page-size 20
```

rawレスポンスは時刻別の`data/akasha/raw/.../page_0001.json`、取得条件とSHA-256は同じ場所の`manifest.json`、最低限の観測列は`data/akasha/leaderboard.csv`へ保存されます。CSVは取得がすべて成功した場合だけ置き換えます。

既定ではページ間に1秒待機し、一時エラーの再試行は2回までです。複数ページは`--max-pages`で明示的に指定します。詳細と非公式APIの不安定箇所は`docs/akasha_api_notes.md`を参照してください。

保存済みrawに対して、`docs/akasha_hutao_spec.md`の初期仮説で4つの単発Damageと合計を比較できます。

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m genshin_opt.akasha.hutao_validate
```

結果は`data/akasha/hutao_component_comparison.csv`へ保存されます。`--debug-rank 1`を指定するとrank 1のHP、ATK、会心、EM、Damage Bonus、DEF、RESなどの途中値も表示します。Leaderboard rawだけでは聖遺物由来のATK%と実数ATKを分離できないため、debugの`flat_atk`は`sheet ATK - base ATK`の残差です。

保存済み20 buildの相対順位性能は次で再生成できます。

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m genshin_opt.akasha.ranking_validate
```

`data/akasha/ranking_fidelity.csv`と`data/akasha/pairwise_ordering.csv`を更新します。共通scaleは診断列だけで、本番評価関数には適用しません。

### Hu Tao Akasha推定スコアの公開API

`score_hutao_akasha(build, scenario_config)`は4 component、aggregate、途中計算、仮説状態を`AkashaScoreResult`で返します。`build`には保存済み`HutaoAkashaInput`のほか、optimizerが渡す5聖遺物のtupleをそのまま指定できます。

```python
from genshin_opt.akasha import ScenarioConfig, score_hutao_akasha
from genshin_opt.optimizer import at_least_set_pieces, optimize

config = ScenarioConfig()
score_function = lambda build: score_hutao_akasha(build, config).aggregate_score
result = optimize(inventory, score_function, at_least_set_pieces("火魔女", 4))
```

optimizerはHu TaoやAkashaの仕様を参照しない。公開API側で、5聖遺物からLv90 Hu Tao・Staff of Homa R1のMax HP、raw相当ATK、会心、EM、raw炎Bonus、セット構成を作る。セット名は`火魔女`と`Crimson Witch of Flames`、`しめ縄`と`Shimenawa's Reminiscence`を同義として扱う。

既定の`ScenarioConfig`は現在のbaselineを表す。H3は未解決なので、enemy level、基礎Pyro RES、VV reductionを差し替えられる。H4の外部EM +420とVaporize境界はstrongly supportedだが、診断継続のため設定値は差し替え可能である。結果の`is_estimate`は`True`で、`hypothesis_states`と`debug_breakdown["model_status"]`からUIでも未完成状態を判別できる。

## 所持聖遺物の手入力

JSONファイルをテキストエディターで編集するか、Streamlit画面の「所持聖遺物JSON」を開いて直接編集します。
`data/sample_inventory.json`を`data/inventory.json`などへコピーして入力してください。
サンプルは全5部位の人工データです。数値は説明・テスト用で、実ゲームに存在するロールの組み合わせを保証しません。
「人工セットA」なども実在セットではありません。

```powershell
Copy-Item data/sample_inventory.json data/inventory.json
```

JSONはUTF-8で保存します（BOM付きも可）。`schema_version`は`1`を指定し、`artifacts`に聖遺物を並べます。
以下は1件の入力例です。

```json
{
  "schema_version": 1,
  "artifacts": [
    {
      "id": "my-flower-001",
      "slot": "flower",
      "set_name": "自分で決めたセット名",
      "rarity": 5,
      "level": 20,
      "main_stat": {"stat": "hp_flat", "value": 4780},
      "substats": [
        {"stat": "crit_rate", "value": 0.105},
        {"stat": "crit_dmg", "value": 0.14},
        {"stat": "hp_percent", "value": 0.10},
        {"stat": "elemental_mastery", "value": 40}
      ]
    }
  ]
}
```

| 項目 | 入力方法 |
| --- | --- |
| `id` | 所持品内で重複しない文字列。読込で自動変更しません |
| `slot` | 花=`flower`、羽=`plume`、砂=`sands`、杯=`goblet`、冠=`circlet` |
| `set_name` | 空でない自由なセット名。同じセットには同じ表記を使ってください |
| `rarity` | 現在の対応範囲は★5のみ（`5`） |
| `level` | 0〜20の整数 |
| `main_stat` | 種類`stat`と現在値`value` |
| `substats` | 現在有効なサブステータス。Lv.0〜3は3〜4種類、Lv.4以上は4種類 |
| `initial_substat_count` | 任意。初期に有効だったサブステータス数（`3`または`4`） |
| 各サブの`initial_value` | 任意。その種類が最初に有効になった時点の値 |

割合は**46.6%なら`0.466`、会心率3.5%なら`0.035`**と入力します。
元素チャージ効率は聖遺物による増加分のみを入れます（+5%なら`0.05`）。キャラクターの基礎100%は含めません。
HP・攻撃力・防御力の実数値と元素熟知は、そのままの数値です。数値を引用符で囲まないでください。

サブステータスの種類は次の10種類です。

| 表示 | `stat` |
| --- | --- |
| HP・攻撃力・防御力の実数値 | `hp_flat`・`atk_flat`・`def_flat` |
| HP%・攻撃力%・防御力% | `hp_percent`・`atk_percent`・`def_percent` |
| 元素熟知 | `elemental_mastery` |
| 元素チャージ効率 | `energy_recharge` |
| 会心率・会心ダメージ | `crit_rate`・`crit_dmg` |

メイン専用として、`pyro_dmg`・`hydro_dmg`・`cryo_dmg`・`electro_dmg`・`anemo_dmg`・`geo_dmg`・`dendro_dmg`・`physical_dmg`・`healing_bonus`もあります。
部位に合うメイン種類か、メインとサブが同じ種類でないかも検証します。

### 初期値の入力

通常の読込では、`initial_value`と`initial_substat_count`の両方を省略できます。
`null`も未入力として扱い、一部の初期値だけ入力しておくこともできます。現在値から初期値を推測・補完しません。

再構築の候補では、サンプルの羽のように全4種類の初期値と初期の種類数を入力してください。

```json
{"stat": "crit_rate", "value": 0.105, "initial_value": 0.035}
```

初期3種類の聖遺物では、4種類目の`initial_value`はLv.4で有効になった時の値を表します。
`initial_substat_count`は`3`のままにします。これは入力データの定義で、初期値の取得はユーザーが行います。

`validate_for_reshape()`だけが、Lv.20・全初期値・初期の種類数を必須とします。
この関数は将来の再構築用データの不足を検出するものです。抽選モデルの確定や、エリクシル産の指定種類など、再構築計算に必要な条件をすべて検証する関数ではありません。

### JSONの読込確認

PowerShellで次を実行すると、人工データの読込と件数を確認できます。
`PYTHONPATH`は、このターミナルで`src`内のパッケージをimportできるようにする設定です。

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -c "from genshin_opt.storage import load_inventory; inventory = load_inventory('data/sample_inventory.json'); print(len(inventory.artifacts))"
```

結果は`5`です。自分のデータはファイル名を`data/inventory.json`へ変更して確認します。
Pythonから使う場合は以下の形です（同じ`PYTHONPATH`設定が必要）。

```python
from genshin_opt.storage import load_inventory
from genshin_opt.validation import validate_for_reshape

inventory = load_inventory("data/sample_inventory.json")
artifact = inventory.artifacts[1]  # 初期値をすべて入力した人工データの羽
validate_for_reshape(artifact)
```

読込時は自動で通常検証を行います。Pythonで`Artifact`を直接作った場合は、`validate_artifact()`または`validate_inventory()`を呼んでください。
型は変更不可のdataclass、内部の配列はtupleです。型注釈だけで不正値を自動拒否する設計ではありません。

## 人工評価と全探索

`optimize(inventory, evaluate)`は全5部位から1個ずつ選び、渡された`evaluate`が最大になる組み合わせを返します。
optimizerは胡桃やAkashaの計算式を知りません。評価関数を差し替えられるため、実ゲームの式が未完成でも組み合わせ探索を単独でテストできます。

現在の`toy_build_score()`は、現在値だけを集計し、割合を画面表示と同じ百分率へ変換してから次の人工式を使います。

```text
base = 2 * 会心率 + 会心ダメージ + 0.3 * HP% + 0.05 * 元素熟知
score = base - 0.5 * abs(会心ダメージ - 2 * 会心率)
```

これはoptimizerの動作確認専用で、原神の火力式ではありません。サブステータスの`initial_value`は集計に含めません。

```python
from genshin_opt.optimizer import optimize
from genshin_opt.scoring import toy_build_score
from genshin_opt.storage import load_inventory

inventory = load_inventory("data/sample_inventory.json")
result = optimize(inventory, toy_build_score)
print(result.score, [artifact.id for artifact in result.artifacts])
```

この全探索は候補数の積だけ評価を行います。大規模所持品向けの枝刈りや高速化はまだありません。

### 火魔女4セット制約

`set_name`を「火魔女」と「その他」に分けて入力し、`at_least_set_pieces()`をoptimizerへ渡します。
火魔女が4部位以上なら有効なので、自由枠が火魔女になった5部位構成も探索対象です。

```python
from genshin_opt.optimizer import at_least_set_pieces, optimize

constraint = at_least_set_pieces("火魔女", 4)
result = optimize(inventory, toy_build_score, constraint)
```

## 聖啓の塵の確率計算

`src/genshin_opt/dust.py`は再構築条件、結果分布、更新指標のデータ型と計算を提供します。
Lv.20の初期4種類は5回、初期3種類は4回を再配分対象として扱い、各結果では入力された`initial_value`を固定して新しい強化値を加えます。

強化先には`go_capped_binomial`モデルを使います。優先2種類への合計回数を`K=max(Binomial(N, 1/2), g)`とする、Genshin Optimizerの既存実装から導出した仮定です。公式確率として確定したものではありません。
ロール増加量と確率も公式確認できていないため、`StatRollDistribution`として呼び出し側から全4種類分を渡します。`roll_model_id`には、その値をどの仮定や資料から作ったか識別できる名前を指定できます。計算結果は使用モデルを含む`ReshapeConditions`を保持します。

`calculate_update_metrics()`は任意の聖遺物評価関数を受け取り、次を返します。

- 更新確率 `P(S > S0)`
- 再構築候補の期待値 `E[S]`
- 元を保持できる場合の期待値 `E[max(S0, S)]`
- 期待改善量 `E[max(0, S - S0)]`
- 更新した場合の平均改善量

この処理はoptimizerやAkashaに依存しません。他の4部位を評価関数のクロージャーに保持すれば、1部位を再構築したときのビルド全体の評価にも利用できます。

### Streamlitでの再構築計算

画面には「簡易期待値モード」と「詳細再構築モード」があります。簡易モードでは対象サブステータス、更新幅の段階、更新確率、更新時の改善幅を指定します。更新確率は25%、更新幅は低・中・高・最高の既定ロール値が初期入力され、どちらも数値欄から編集できます。成功後の聖遺物を所持品へ入れて再最適化し、失敗時または悪化時は元を保持する前提で期待Damageを即時表示します。

詳細モードでは次の順序で入力します。

1. 「所持聖遺物JSON」に所持品を入力する。
2. 火魔女として扱う`set_name`を選ぶ。
3. 再構築対象と優先する2種類、通常・上級・絶対の保証段階を選ぶ。
4. 対象の4種類それぞれについて、4段階の更新幅と確率を数値入力する。
5. 「再構築を計算」を押す。

割合の更新幅は%表示で入力します。たとえば会心率2.72%はGUIでは`2.72`と入力し、内部で`0.0272`へ変換します。4段階の初期確率は各25%で、合計100%になるよう編集します。

各再構築結果について、対象を置き換えた所持品全体を再びoptimizerへ渡します。通常GUIではoptimizerと塵の両方が同じAkasha推定Damage評価関数を使います。元の所持品の最適推定Damageを上回れば「再構築後を採用」、同点以下なら「元を保持」と判定します。これにより、対象が現在の最適5部位に入っていない場合も、新しい最適セットへ入る確率を計算できます。

### 検証の範囲

- 必須・未知の項目、JSONキーの重複、IDの重複、部位・ステータスの種類を検証します。
- 文字列数値・真偽値・NaN・無限大・0以下のステータス値は拒否します。
- 現在の入力仕様では、聖遺物単体の割合を`0 < value <= 1`に制限します。これは単位ミス対策の入力上限で、ゲームの正確な最大値表ではありません。
- 入力された初期値は正の数かつ現在値以下が必要です。Lv.0〜3では現在値との一致も確認します。
- 空の所持品、5部位がそろっていない所持品、同じ部位の複数個を許可します。装備可能な5部位がそろうかの判定は今後のoptimizerで行います。
- ステータスの厳密な上限・刻み幅、強化回数と現在値の整合、実在セット名は未検証です。

入力エラーは`ValidationError`で、例として`artifacts[0].substats[1].initial_value`のように場所を示します。
配列の番号は0から始まります。ファイルが存在しない場合などは通常の`FileNotFoundError`・`OSError`です。

一般の部位・強化ルールの参考：[原神Wikiの聖遺物](https://wikiwiki.jp/genshinwiki/%E8%81%96%E9%81%BA%E7%89%A9)、[KQM Artifacts Guide](https://keqingmains.com/misc/artifacts/)。再構築の未確定事項は`docs/dust_spec.md`を参照してください。

## ファイル構成

```text
app.py                     Streamlitの画面
requirements.txt           依存パッケージ
pyproject.toml             プロジェクト情報とpytest設定
src/genshin_opt/models.py   データ型
src/genshin_opt/validation.py 入力検証・再構築用データの必須チェック
src/genshin_opt/storage.py  JSON読込
src/genshin_opt/stats.py    現在ステータスの集計と表示単位への変換
src/genshin_opt/scoring.py  optimizer検証用の人工評価関数
src/genshin_opt/optimizer.py 評価関数を受け取る小規模な全探索
src/genshin_opt/dust.py     聖啓の塵の条件・結果分布・更新指標
src/genshin_opt/dust_input.py 手入力から抽選条件への変換
src/genshin_opt/dust_optimizer.py 再構築後の所持品の再最適化と採否判断
src/genshin_opt/akasha/       Akasha観測データのHTTP取得・整形・保存・CLI
data/sample_inventory.json  全5部位の人工データ
tests/test_inventory.py    データ・検証・JSONのテスト
tests/test_optimizer.py    集計・人工評価・全探索のテスト
tests/test_dust.py         再構築分布と更新確率・期待値の独立テスト
tests/test_dust_input.py   抽選条件の手入力変換テスト
tests/test_dust_optimizer.py 再構築結果とoptimizerの連携テスト
tests/test_startup.py      起動確認テスト
tests/test_akasha_api.py   ページング、待機、有限リトライのテスト
tests/test_akasha_storage.py raw・CSV分離保存と失敗時動作のテスト
docs/dust_spec.md           聖啓の塵の仕様調査
docs/akasha_api_notes.md    Akasha非公式APIの調査記録
docs/akasha_ranking_fidelity.md Akasha順位再現性能
docs/akasha_common_residual_research.md 共通残差候補の調査
```

今後、計算ロジックは`src/genshin_opt/`へ追加し、Streamlitは入力・表示のみを担当します。
Akasha推定Damageには未解決のH3と約7.1%の絶対値不足が残ります。近接buildの順位精度を検証しながら、未知の補正係数を使わず原因を一つずつ切り分けます。

