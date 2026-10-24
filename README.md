# まるたいスタンプラリー / 整理版

## ファイル構成

- `app.py`: 設定、保存、写真合成、地図、全画面。番号付きの5セクションに整理。
- `requirements.txt`: 使用ライブラリ（検証時のバージョンで固定）。
- `setup.sql`: Supabase初期設定。一度SQL Editorで実行。
- `assets/tai_stamp.png`: 写真に押すスタンプ。
- `data/facilities.csv`: 施設CSVの形式見本（サンプル3件）。
- `README.md`: この説明。

画面や処理を修正する場合は、基本的にapp.pyだけを編集します。
正式ロゴがあればassets/logo.pngに置くと自動表示されます。
SQLite、pages、services、components、GitHub Actionsは不要です。

## 保存先と利用範囲

- 施設情報・訪問履歴: Supabase Database（facilities / visits）。
- 元写真・スタンプ入り写真: Supabase Storageの非公開バケットvisit-photos。
- Streamlitサーバーのローカルディスクには利用記録を保存しません。
- 家族で同じ記録帳を共有する構成です。利用者ごとの記録分離はありません。
- 写真を見る前に合言葉で認証します。写真URLの有効期限は1時間です。
- SERVICE_ROLE_KEYはStreamlitのSecretsにだけ設定し、GitHubへ書かないでください。

## 起動手順

1. 専用のSupabaseプロジェクトでsetup.sqlをSQL Editorから実行します。
   既存の同名テーブルを使う場合は、内容を事前に確認してください。
2. このフォルダの中身をGitHubへアップロードします。
   旧pages/・services/・components/・直下map_service.pyは配置不要です。
   既存リポジトリを使う場合は古いpages/を削除し、Streamlitの自動ページ検出との混在を避けてください。
3. Streamlit Community Cloudの起動ファイルをapp.pyに指定します。
4. StreamlitのSecretsに次の3項目を設定します。

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SERVER_SIDE_KEY"
APP_PASSWORD = "家族用の長い合言葉"
```

5. 起動後、合言葉を入力します。
6. 下部の「その他」→「施設データの設定」から施設CSVを登録します。

ローカル起動の場合は同じ設定を.streamlit/secrets.tomlへ保存し、
`python -m pip install -r requirements.txt`の後に`streamlit run app.py`を実行します。

## 施設CSV

必須列: name,category,ward,address,latitude,longitude。
その他の列: id,has_open_air_bath,has_natural_hot_spring,website_url,active。
施設種別: sento / super_sento / spa / other。
露天風呂・天然温泉: true=あり、false=なし、空欄=未登録。
緯度・経度が空欄なら施設一覧には出ますが地図には出ません。
IDはUUIDを使用します。空欄なら施設名＋住所から同じUUIDを生成します。
名称・住所を変更する際は、元のIDを残して訪問記録との対応を維持してください。
同じIDは更新し、CSVにない施設は削除しません。active=falseで非表示にできます。
同梱の施設CSVは正式施設の一覧ではありません。サンプルです。

## 維持した機能・修正点

- ホーム、地図、露天風呂検索、施設一覧／詳細、写真付き訪問登録、スタンプ帳。
- 施設種別・露天風呂・天然温泉・区・訪問状態の絞り込み。
- 同じ施設への複数訪問、訪問施設数・区別件数・達成表示。
- 写真の向き補正、JPEG変換、スタンプと日付合成、元写真の別保存。
- スタンプ帳の4種類の並べ替え、訪問済み／未訪問マーカー。
- 詳細リンクのviewパラメータ統一、施設詳細の地図中心を対象施設へ修正。
- 露天風呂・天然温泉の「なし」と「未登録」を区別。
- APIの件数上限で取得が途切れないページ取得。
- CSV全件を検証してから登録。写真保存に失敗した場合の後片付け。

## 既存データについて

添付ZIPには実際のSQLite訪問履歴・保存写真は含まれていません。
過去のSQLiteデータ・写真の自動移行は実装していません。
この版を既存アプリへ入れ替えるだけでは、旧ローカル記録はSupabaseへ移りません。
既存Supabase版とテーブル名・写真パス列名は揃えています。
旧pages等は削除前にバックアップしてください。

## 検証の範囲

構文、既存画像テスト、地図生成、CSV検証、保存処理の模擬テスト、
Streamlitの各画面をテスト用データで確認。
実際のSupabaseへの接続・書き込みは未検証です（接続設定未提供）。
