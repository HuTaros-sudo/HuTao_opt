# 原神 聖遺物最適化ツール

> Work in Progress

原神の胡桃向けに、所持している聖遺物からダメージを基準として最適な組み合わせを探索する個人制作ツールです。

主にAkasha Systemの「VV Swirl Hyper Tao Combo, Avg DMG / Staff of Homa R1」リーダーボードを対象としており、火魔女4セットを前提にしています。

現在は以下の機能を実装しています。

- 所持聖遺物から火魔女4セットを満たす最適構成を探索
- Akashaの公開情報を参考にした胡桃のDamage推定
- 聖啓の塵による再構築後の更新確率・期待値の計算
- 再構築後の聖遺物を所持品へ加えた状態での再最適化
- 現在装備・最適装備・再構築後候補の比較

Akashaの評価式は公開されている情報と観測データから推定しており、完全再現ではありません。現在も検証中です。

なお他プレイヤーの識別情報はローカルにのみ保持し、リポジトリには含めていません。

## Motivation

聖遺物の組み合わせが多く、手作業で最適構成を比較するのが難しかったため作成しました。

また、聖啓の塵による再構築では、変更後のステータスだけを見るのではなく、所持している聖遺物全体を含めて再最適化した場合に実際に更新になるかを比較したかったため、その計算も実装しています。

## Development

PythonとStreamlitを使用しています。

実装にはOpenAI Codexを利用しています。私は主に、要件定義、原神の仕様整理、計算方法・評価方法の設計、生成された実装の確認、および修正方針の決定を担当しています。

現在は個人用として開発しているため、対象キャラクターや装備条件を一般化する予定はありません。また、仕様変更や不具合が含まれる可能性があります。

## 現在の制限

- 胡桃 Lv.90 / Staff of Homa R1を前提としています
- 火魔女4セットを前提としています
- AkashaのDamage計算は推定値です
- Akashaの非公式公開エンドポイントを利用する機能があります
- 大規模な所持品向けの枝刈りや高速化は未実装です

## 必要な環境

- Python 3.11以上
- Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 起動

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

## テスト

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 技術詳細

詳細な仕様や検証内容は`docs/`以下にまとめています。

- `docs/technical_details.md` — 技術詳細、使い方全般
- `docs/dust_spec.md` — 聖啓の塵の再構築モデル
- `docs/akasha_api_notes.md` — Akasha非公式APIの調査記録
- `docs/akasha_ranking_fidelity.md` — Akasha順位再現性能
- `docs/akasha_common_residual_research.md` — Damage計算の残差調査

所持聖遺物JSONの入力仕様や内部APIについても、詳細ドキュメントへ分離する予定です。

## 注意事項

このプロジェクトは非公式の個人制作ツールであり、HoYoverseおよびAkasha Systemとは関係ありません。

ゲーム内データや外部サービスの仕様変更により、計算結果やデータ取得機能が正しく動作しなくなる可能性があります。

## License

MIT License. 詳細は [LICENSE](./LICENSE) を参照してください。