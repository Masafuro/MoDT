# viewer-unit

MoDT エコシステムにおいて、ユーザーが自身の状態（KVデータ）をブラウザから閲覧・更新するためのWebインターフェースを提供するユニットです。

## 概要

このユニットは Flask サーバーとして動作し、ブラウザからの HTTP リクエストをトリガーに MQTT ブローカーを介して他のユニット（identify-unit, db-unit）と通信します。MQTT の非同期な応答を待機し、最終的に一つの HTML 画面として集約してレスポンスを返す「アグリゲーター」の役割を担います。

## 主な機能

* **セッション解決**: ブラウザから受け取った `session_id` をもとに、`identify-unit` へユーザー情報の照会を行います。
* **データ一覧表示**: 特定された `user_id` に紐付くすべてのキー・バリューペアを `db-unit` から取得し、テーブル形式で表示します。
* **動的データ更新**: 任意のキー名と値を入力することで、`db-unit` に対してデータの保存（SET）リクエストを発行します。

## エンドポイント仕様

### 1. GET /view-data?session_id={uuid}
ユーザーデータの閲覧画面を表示します。
* **内部シーケンス**:
    1. `modt/session/query` をパブリッシュし、`user_id` を取得。
    2. `user_id` 判明後、`modt/state/all/get` をパブリッシュ。
    3. `db-unit` からの返答（`modt/state/all/value`）を待機。
    4. すべてのデータが揃った段階で `index.html` をレンダリング。

### 2. POST /update-data
フォームからの入力を受け取り、データを更新します。
* **処理内容**:
    1. フォームより `session_id`, `user_id`, `new_key`, `new_value` を受信。
    2. `modt/state/set` トピックへ更新メッセージをパブリッシュ。
    3. データベースの書き込み時間を考慮して 0.5秒待機した後、`view-data` へリダイレクト。

## 使用トピック

### 送信 (Publish)
* `modt/session/query`: セッション照会リクエスト
* `modt/state/all/get`: 全データ取得リクエスト
* `modt/state/set`: データ更新・保存リクエスト

### 受信 (Subscribe)
* `modt/session/info`: セッション照会結果
* `modt/state/all/value`: 全データ取得結果

## 技術的特徴

* **リクエストコンテキスト管理**: MQTT は非同期通信であるため、`request_context` 辞書を使用して HTTP リクエストと MQTT のレスポンスを紐付け、ループ処理によるポーリングで同期を実現しています。
* **SDKの活用**: 共通ライブラリ `modt.py` を使用し、ペイロードの生成やパース、ブローカー接続の標準化を行っています。

## 配置構成

Flask の仕様に基づき、以下のディレクトリ構成で運用されます。
* `/app/main.py`: アプリケーション本体
* `/app/templates/index.html`: 表示用テンプレート
* `/app/common/modt.py`: 共通モジュール（マウントによる共有）