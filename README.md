# MoDT (Modular Docker through MQTT)

MQTTをバックボーンとした、Dockerコンテナによる疎結合なマイクロサービス連携フレームワークです。各機能（ユニット）が独立して動作し、標準化されたメッセージングプロトコルを通じて動的に連携するエコシステムの構築を目的としています。

## 開発進捗 (2025年12月31日時点)

現在、システムの中核となる以下の機能が完成し、正常に動作しています。

* **認証・リダイレクト制御**: ログイン成功後のイベント発行から、各アプリの準備状況に応じた自動遷移。
* **セッション・身元照会システム**: セッションIDのみを保持するブラウザに対し、バックエンド側で安全にユーザーIDを特定するフロー。
* **状態管理（KVストア）基盤**: ユーザーごとの設定値をSQLiteで永続化し、MQTT経由で読み書きする仕組み。
* **動的データビューワー**: 全件取得プロトコルを用いた、ユーザー設定の一覧表示およびブラウザからの更新機能。

## ユニット構成と詳細ドキュメント

本システムは以下のユニットで構成されています。各ディレクトリ内の `README.md` に、それぞれの詳細な仕様、使用トピック、エンドポイントの解説があります。

* **[common/](common/)**: 共通SDK `modt.py`。システム全体の「法律」となる通信規格を定義。
* **[identify-unit/](identify-unit/)**: ユーザー認証およびセッション・ユーザーIDの紐付けを管理する「門番」。
* **[db-unit/](db-unit/)**: SQLiteを用いた状態保持。非同期KVストア機能を提供。
* **[viewer-unit/](viewer-unit/)**: ユーザー設定の閲覧・更新を行う動的なWeb管理コンソール。
* **[dummy-app-unit/](dummy-app-unit/)**: リダイレクトと連携の動作確認用サンプルアプリケーション。
* **[monitor/](monitor/)**: システム内の全MQTT通信をリアルタイムで可視化するデバッグ・監視ユニット。
* **broker**: Mosquittoによるメッセージハブ。内部ネットワーク通信を統制。

## 標準プロトコル仕様

ユニット間の通信は、`common/modt.py` で定義されたトピックおよびペイロード形式に厳格に従います。詳細は [common/README.md](common/README.md) を参照してください。

### 1. 認証とリダイレクト
* `modt/auth/success`: 認証ユニットが発行。
* `modt/app/ready`: 各アプリユニットが発行。遷移先URLを通知。

### 2. セッション身元照会
* `modt/session/query`: セッションIDから実ユーザー情報を求めるリクエスト。
* `modt/session/info`: 照会に対する回答（user_id, role, status）。

### 3. 状態管理 (KVストア)
* `modt/state/all/get`: ユーザーに紐付く全データの取得リクエスト。
* `modt/state/all/value`: 辞書形式による全データの一括返信。
* `modt/state/get` / `set`: 特定キーに対する単一値の読み書き。

## 開発用SDKの実装例

共通ライブラリ `modt.py` を使用することで、プロトコルを意識せずに開発が可能です。

```python
import modt

# クライアントの初期化
client = modt.get_mqtt_client(client_id="my-service")
modt.connect_broker(client)

# メッセージ送信（例：全件取得リクエスト）
payload = modt.create_state_all_get_payload("user-uuid-here")
client.publish(modt.TOPIC_STATE_ALL_GET, payload)
```

## 実行環境の基本設定
- ネットワーク: すべてのコンテナは modt-network 内で相互通信します。
- ログ出力: Pythonユニットは PYTHONUNBUFFERED=1 を設定し、リアルタイムなログ取得を保証します。
- 共有ライブラリ: ./common ディレクトリを各コンテナにマウントし、PYTHONPATH を通して modt.py を利用可能にします。

## 各ユニットの個別開発ガイド

MoDT（Modular Docker through MQTT）システムでは、全体の整合性を維持しながら、特定のユニットを独立させて開発・検証することが可能です。このモジュール化された開発手法を採用することで、開発者は担当する機能に集中し、迅速なビルドとテストのサイクルを回すことができます。

### 開発フローと実行コマンド

個別のユニットを開発する際は、まずシステム全体の通信路となる共有ネットワークとブローカーを確立する必要があります。以下のコマンドを実行して、基盤となるインフラをバックグラウンドで起動してください。

> cd broker
> docker-compose up -d

次に、開発対象のユニットディレクトリへ移動します。ユニットを起動する際は、ソースコードの変更を確実に反映させるためにビルドを伴う起動コマンドを推奨します。以下のコマンドを実行することで、コンテナが立ち上がり、自動的に共有ネットワークへ合流します。

> docker-compose up --build

開発が一段落し、特定のユニットのみを停止してリソースを解放したい場合は、そのユニットのディレクトリで以下のコマンドを実行してください。

> docker-compose down

各ユニットのディレクトリに配置する構成ファイルは、親ディレクトリに存在する共通資産を正しく取得しつつ、独立性を保つための特定の記述ルールに従います。具体的には、networksセクションにおいて modt-network を external: true として定義し、自前でネットワークを作成せずに既存の広場を利用するように設定します。また、共通SDKである modt.py を利用するために、ボリュームマウントを使用して ../common をコンテナ内の /app/common に割り当てます。これと同時に環境変数 PYTHONPATH を /app に設定することで、プログラム内のインポート文が正しく機能するように調整します。環境変数ファイルについては、ルートディレクトリの .env とユニット固有の .env の両方を読み込むよう指定し、システム全体の定数とユニット固有の設定を共存させます。標準的な設定のテンプレートは以下の通りです。

```yaml
services:
  unit-app:
    build: .
    container_name: modt-unit-name
    volumes:
      - ../common:/app/common
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

各ユニットのビルド定義は、実行環境を最小限に保つために python:3.11-slim などの軽量なイメージをベースに使用します。Dockerfile内部では、そのユニットの動作に直接関係のないミドルウェアのインストールは行わず、純粋なPython実行環境の構築に専念します。

ビルド手順としては、まず requirements.txt をコピーして依存ライブラリをインストールし、その後にユニット内のソースコードをコピーします。共通SDKの実体は開発時にDocker Composeによって注入されるため、Dockerfile内で親ディレクトリを参照しようとする記述は避ける必要があります。最後に、アプリケーションの起動はシェルスクリプトを介さず直接 python main.py を実行する形式をとり、OSからのシグナルを正しく受け取れるように構成します。

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ユニット固有のソースコードをコピー
COPY . .

# アプリケーションの直接起動
CMD ["python", "main.py"]

```