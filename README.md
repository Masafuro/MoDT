# MoDT (Modular Docker through MQTT)

MQTTをバックボーンとした、Dockerコンテナによる疎結合なマイクロサービス連携フレームワークです。各機能（ユニット）が独立して動作し、標準化されたメッセージングプロトコルを通じて動的に連携するエコシステムの構築を目的としています。

## 開発進捗 (2025年12月31日時点)

現在、システムの中核となる以下の機能が完成し、正常に動作しています。

* **認証・リダイレクト制御**: ログイン成功後のイベント発行から、各アプリの準備状況に応じた自動遷移。
* **セッション・身元照会システム**: セッションIDのみを保持するブラウザに対し、バックエンド側で安全にユーザーIDを特定するフロー。
* **状態管理（KVストア）基盤**: ユーザーごとの設定値をSQLiteで永続化し、MQTT経由で読み書きする仕組み。
* **動的データビューワー**: 全件取得プロトコルを用いた、ユーザー設定の一覧表示およびブラウザからの更新機能。

## 標準プロトコル仕様

ユニット間の通信は、`common/modt.py` で定義された以下のトピックとペイロード形式に厳格に従います。

### 1. 認証とリダイレクト
* **modt/auth/success**: 認証ユニットが発行。ユーザーIDとセッションIDを通知。
* **modt/app/ready**: アプリ側が発行。セッションIDを照合し、遷移先URLを認証ユニットへ通知。

### 2. セッション身元照会
* **modt/session/query**: セッションIDからユーザー情報を求めるリクエスト。
* **modt/session/info**: 照会に対する回答。ユーザーID、ロール、ステータスを含む。

### 3. 状態管理 (KVストア)
* **modt/state/get / set**: 特定のキーに対する値の取得および保存。
* **modt/state/value**: 取得リクエストに対する単一値の返信。
* **modt/state/all/get**: ユーザーに紐付く全データの取得リクエスト。
* **modt/state/all/value**: ユーザーの全KVデータを辞書形式で返信。

## 開発用SDK (common/modt.py)

開発効率の向上とプロトコル遵守のため、共通ライブラリ `modt.py` を使用してください。

### SDKを利用した実装例
```python
import modt

# クライアントの初期化
client = modt.get_mqtt_client(client_id="my-app-unit")

def on_message(client, userdata, msg):
    data, error = modt.parse_payload(msg.payload.decode())
    if error: return

    if msg.topic == modt.TOPIC_SESSION_INFO:
        # セッション照会結果の処理
        user_id = data.get("user_id")
        print(f"User identified: {user_id}")

client.on_message = on_message
modt.connect_broker(client)

# トピックの購読
client.subscribe(modt.TOPIC_SESSION_INFO)

# メッセージの送信
payload = modt.create_session_query_payload("session-uuid-here")
client.publish(modt.TOPIC_SESSION_QUERY, payload)
```

### ユニット構成
- broker: Mosquittoによるメッセージハブ。内部ネットワークのみで通信。
- monitor: 全トピックのログをリアルタイムで監視・表示。
- identify-unit: ユーザー認証およびセッションとユーザーIDの紐付け管理。
- db-unit: SQLiteを用いた状態保持。KVストアとしての機能を提供。
- viewer-unit: ユーザー設定の閲覧・更新を行うWebコンソール。
- dummy-app-unit: リダイレクトと連携の動作確認用サンプルアプリ。

### 実行環境の基本設定
- ネットワーク: すべてのコンテナは modt-network 内で相互通信します。
- ログ出力: Pythonユニットは PYTHONUNBUFFERED=1 を設定し、リアルタイムなログ取得を保証します。
- 共有ライブラリ: ./common ディレクトリを各コンテナにマウントし、PYTHONPATH を通して modt.py を利用可能にします。