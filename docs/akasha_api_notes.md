# Akasha Leaderboard 観測APIメモ

調査日：2026-09-13（日本時間）  
対象：Phase Aの観測データ取得。Damage計算式は対象外。

## 対象Leaderboard

`GET https://akasha.cv/api/v2/leaderboards/categories?characterId=10000046`の2026-09-13時点の応答で、次の対応を確認した。

| 項目 | 観測値 |
| --- | --- |
| Character | Hu Tao |
| Leaderboard | VV Swirl Hyper Tao Combo, Avg DMG |
| Weapon | Staff of Homa R1 |
| leaderboard / calculation ID | `1000004605` |

これはAkashaの非公式公開エンドポイントから得た観測値であり、固定された公式API仕様ではない。

## 使用するエンドポイント

取得機能が呼ぶのは次の1種類だけである。

```text
GET https://akasha.cv/api/leaderboards
```

送信するquery parameterは次のとおり。

| parameter | 値・役割 |
| --- | --- |
| `calculationId` | ユーザーが指定したLeaderboard ID |
| `size` | 1ページの件数。CLIでは1〜100 |
| `page` | 1から始まるページ番号 |
| `sort` | `calculation.result` |
| `order` | `-1` |
| `variant` | 任意。既定は空文字列 |
| `p` | 最初は空。次ページは`lt|{前ページ末尾のcalculation.result}` |
| `uids`・`filter` | 現在は空文字列 |

このparameter構成とcursor方式は、`akasha-py`の固定コミット`1a660789a04eca3033fd03d78d1c1a9df6278160`にある[`AkashaAPI._fetch_leaderboards()`](https://github.com/seriaati/akasha-py/blob/1a660789a04eca3033fd03d78d1c1a9df6278160/akasha/client.py#L129-L176)と[`LeaderboardPaginator`](https://github.com/seriaati/akasha-py/blob/1a660789a04eca3033fd03d78d1c1a9df6278160/akasha/paginators/leaderboard.py#L9-L60)を参考にした。`akasha-py`自体もAkasha公式SDKではない。

## 保存するフィールド

rawレスポンスは変更せず`data/akasha/raw/{leaderboard_id}_{UTC時刻}/page_NNNN.json`へ保存する。同じディレクトリの`manifest.json`にはrequest URL、取得日時、SHA-256、行数、完了・失敗状態を記録する。

`data/akasha/leaderboard.csv`には次の列を保存する。

| CSV列 | API上の取得元 | 用途 |
| --- | --- | --- |
| `leaderboard_id` | 要求値および`calculation.id` | Leaderboard識別 |
| `rank` | `index` | 順位 |
| `calculation_result` | `calculation.result` | 将来の再現対象となる観測値 |
| `uid` | `uid` | 公開プロフィール・build取得用 |
| `profile_id` | 現在は空欄 | UIDとは別のprofile ID用の予約列 |
| `entry_id` | `_id` | Leaderboard行の識別子 |
| `build_md5` | `md5` | build・聖遺物取得用 |
| `character_id` | `characterId` | キャラクター識別 |
| `fetched_at` | クライアントがUTCで記録 | 観測日時 |
| `raw_page` | ローカルrawファイル名 | 出典ページへの対応 |

`akasha-py`のモデルも`_id`、`uid`、`index`、`md5`、`characterId`、`calculation.id`、`calculation.result`をLeaderboard行から読む。[`LeaderboardCalc`](https://github.com/seriaati/akasha-py/blob/1a660789a04eca3033fd03d78d1c1a9df6278160/akasha/models/leaderboard.py#L14-L17)、[`Leaderboard`](https://github.com/seriaati/akasha-py/blob/1a660789a04eca3033fd03d78d1c1a9df6278160/akasha/models/leaderboard.py#L87-L104)

## 取得できるがCSVへ整形しないフィールド

2026-09-13の対象Leaderboard応答では、raw行に以下も含まれていた。

- `calculation.additional`
- `artifactObjects`、`artifactSets`
- `constellation`、`stats`、`talentsLevelMap`
- `weapon`、`owner`、`propMap`

Phase Aでは観測値の保全を優先し、これらの形式を確定スキーマとして扱わない。raw JSONには残るため、後の調査で再解析できる。

## 取得できない、または今回取得しない情報

- UIDとは別のprofile IDはLeaderboard応答で確認できず、CSVでは空欄にする。
- 5個の聖遺物の全詳細はLeaderboard応答だけでは得られない。`akasha-py`には`GET /api/artifacts/{uid}/{md5}`の実装があるが、Phase Aでは呼ばない。[`get_artifacts()`](https://github.com/seriaati/akasha-py/blob/1a660789a04eca3033fd03d78d1c1a9df6278160/akasha/client.py#L226-L235)
- Leaderboard全件数は応答の`totalRowsHash`だけでは決まらない。追加の`getCollectionSize`リクエストは送らない。
- `calculation.result`を作る式、内部丸め、バフ条件は取得・推測しない。
- APIの正式なschema version、rate limit、互換性保証は確認できていない。

## リクエスト抑制と失敗時の動作

- 既定値は20件、1ページ、ページ間1秒である。
- 1回のCLI実行は最大100ページ、1ページ最大100件に制限する。
- 429、5xx、接続・timeoutだけを再試行対象とし、既定2回、最大5回で停止する。
- 4xxは429を除き再試行しない。
- 後続ページが失敗した場合、取得済みrawと`status=failed`のmanifestを残し、整形済みCSVは置き換えない。
- 成功した場合だけCSVを一時ファイルから置き換える。

## 壊れやすい箇所

Akashaは公開APIの安定性を保証していない。`akasha-py`のREADMEにも、wrapperは開発途中であり、Akasha側APIが予告なく頻繁に変わるため壊れる可能性があると明記されている。[`akasha-py README`](https://github.com/seriaati/akasha-py/blob/1a660789a04eca3033fd03d78d1c1a9df6278160/README.md#important-notes)

特に次が破損点になる。

- endpoint pathとquery parameter名
- `data` wrapperの有無
- `index`、`calculation.result`、`uid`、`md5`などのフィールド名と型
- `p=lt|result`という未文書化cursor
- 同じ`calculation.result`が複数行ある境界でのページング
- 同順位を表す重複`index`。2026-09-13の対象上位20件では順位10が2行あり、順位は一意キーにできない
- Leaderboard IDとvariantの扱い

取得時は各行の`calculation.id`が要求IDと一致することを検証する。形式変更を推測で補完せず、rawと失敗manifestを残して停止する。

## CLI

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m genshin_opt.akasha.cli 1000004605 --max-pages 1 --page-size 20
```

複数ページを取得する場合も、まず少数ページで形式を確認し、`--page-delay`を短くしすぎない。
