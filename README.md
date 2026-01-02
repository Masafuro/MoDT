# MoDT (Modular Docker through MQTT)

MQTTをバックボーンとした、Dockerコンテナによる疎結合なマイクロサービス連携フレームワークです。各機能（ユニット）が独立して動作し、標準化されたメッセージングプロトコルを通じて動的に連携するエコシステムの構築を目的としています。

## 開発進捗 (2026年1月2日時点)

現在、システムの中核となる以下の機能が完成し、正常に動作しています。

### 認証・リダイレクト制御
ログイン成功後のイベント発行から、各アプリの準備状況に応じた自動遷移が確立されています。

### セッション・身元照会システム
セッションIDのみを保持するブラウザに対し、バックエンド側で安全にユーザーIDを特定するフローが構築されています。

### 状態管理（KVストア）基盤
ユーザーごとの設定値をSQLiteで永続化し、MQTT経由で読み書き、および特定のキーやユーザー全データの削除を行う仕組みが完成しています。

### 動的データビューワー
全件取得および削除プロトコルを用いた、ユーザー設定の管理・保守を行うブラウザベースのコンソールが動作しています。

## ユニット構成と詳細ドキュメント

本システムは以下のユニットで構成されています。各ディレクトリ内の README.md に、詳細な仕様、使用トピック、エンドポイントの解説があります。

| ユニット名 | 役割 | 備考 |
| :--- | :--- | :--- |
| common/ | 共通SDK modt パッケージ | パッケージ化により通信規格を一元管理 |
| identify-unit/ | 門番 | ユーザー認証およびセッション管理を担当 |
| db-unit/ | 永続化レイヤー | SQLiteを用いた非同期KVストア機能を提供 |
| viewer-unit/ | 管理コンソール | ユーザー設定の閲覧・更新・削除を行うWebUI |
| dummy-app-unit/ | サンプルアプリ | リダイレクトと連携の動作確認用 |
| monitor/ | 監視ユニット | 全MQTT通信のリアルタイム可視化 |
| broker | メッセージハブ | Mosquittoによる通信の統制 |

## 標準プロトコル仕様

ユニット間の通信は、common/modt パッケージで定義されたトピックおよびペイロード形式に厳格に従います。詳細は common/README.md を参照してください。

### 1. 認証とリダイレクト
認証成功時には `modt/auth/success` が発行され、各アプリは `modt/app/ready` を通じて遷移先URLを通知します。

### 2. セッション身元照会
セッションIDの妥当性を確認するために `modt/session/query` が送信され、それに対して認証ユニットが `modt/session/info` を返信します。

### 3. 状態管理 (KVストア)
データの読み書きは `modt/state/get` および `set` で行い、全件取得には `all/get` を使用します。また、今回新設された `modt/state/delete` による個別削除と `modt/state/clear` による一括消去がサポートされています。

## 開発用SDKの実装例

共通ライブラリをパッケージ化したことで、インポート文が `from common import modt` に統一されました。Webフレームワークを利用するユニットでは、通信を維持するために `loop_start()` を明示的に呼び出す必要があります。

```python
from common import modt

# クライアントの初期化と接続
client = modt.get_mqtt_client(client_id="my-service")
modt.connect_broker(client)

# Webアプリの場合はバックグラウンドループを開始
client.loop_start()

# 削除リクエストの送信例
payload = modt.create_state_delete_payload("user-uuid", "target-key")
client.publish(modt.TOPIC_STATE_DELETE, payload)
```
## 実行環境の基本方針
### ネットワークとログ
すべてのコンテナは modt-network 内で相互通信します。Pythonユニットはリアルタイムなログ取得のために PYTHONUNBUFFERED=1 を設定します。

### ビルド重視の運用
ソースコードの変更を確実に反映し、再現性のない不具合を防ぐため、常に docker-compose up --build によるビルドを伴う起動を原則とします。

### クリーンなボリューム構成
ホスト側のフォルダ汚染を防ぐため、ユニット全体の同期（マウント）は行わず、必要な資産のみを個別にマウントします。共通SDKは ../common:/app/common として接続し、PYTHONPATH を通じて利用します。

### 各ユニットの個別開発ガイド
開発者は担当するユニットディレクトリにおいて、独立してビルドとテストを行うことが可能です。

### 開発フロー
まず broker ディレクトリでブローカーを起動し、次に各ユニットディレクトリへ移動してビルドコマンドを実行します。

> docker-compose up --build

### 標準的な docker-compose.yml テンプレート
以下の構成を維持することで、SDKの参照とディレクトリの清潔さを両立させます。

```yaml
services:
  unit-app:
    build: .
    container_name: modt-unit-name
    volumes:
      - ../common:/app/common
      - ./data:/app/data  # 永続化が必要な場合
    environment:
      - PYTHONPATH=/app
      - MODT_BROKER_HOST=broker
    env_file:
      - ../.env
      - .env
    networks:
      - modt-network

networks:
  modt-network:
    external: true
```

### ユニット用 Dockerfile の標準仕様
軽量な python:3.11-slim をベースとし、OSのシグナルを正しく受け取るために python main.py を直接実行します。

```Dockerfile

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]

```