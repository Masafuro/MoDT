# MoDT (Modularized Docker-compose Toolkit)

MQTTを基盤とし、Dockerコンテナによる疎結合な連携を実現するアプリケーションフレームワークです。各機能が独立したユニットとして存在し、メッセージングを通じて動的に組み合わさるシステムを目指しています。

## 開発進捗
令和7年12月30日の時点で、認証ユニットからアプリケーションユニットへの自動リダイレクトフローの構築が完了しました。具体的には、ログイン成功後のイベント発行、ダミーアプリによる準備完了通知、そしてWebSocketを用いたブラウザの自動遷移までの一連の連鎖が正常に動作することを確認済みです。現在はシステムの核となるオーケストレーションの仕組みが確立された段階にあります。

## 標準リダイレクトプロトコル仕様

認証からアプリケーション起動までのメッセージ交換は、以下の規格に厳格に従って行われます。

### 1. 認証成功通知 (modt/auth/success)
認証ユニットがユーザーを特定した際に発行するメッセージです。

| キー名 | 型 | 内容説明 |
| :--- | :--- | :--- |
| user_id | string | データベース上のユーザー固有識別子。 |
| session_id | string | ブラウザのWebSocket接続を特定するためのUUID。 |
| role | string | ユーザーの権限（user, admin等）。 |
| timestamp | string | ISO 8601形式のイベント発生時刻。 |

### 2. アプリ準備完了通知 (modt/app/ready)
アプリ側が受け入れ準備を終えた際に発行するメッセージです。認証ユニットはこの session_id を参照してブラウザをリダイレクトさせます。

| キー名 | 型 | 内容説明 |
| :--- | :--- | :--- |
| session_id | string | 認証成功通知から引き継いだ識別子。一致が必須。 |
| redirect_url | string | ブラウザが最終的に遷移すべきフルパスのURL。 |
| app_name | string | 通知を発行したアプリケーションユニットの名称。 |

## ブローカー接続サンプルプログラム

Pythonを用いて新しいユニットを作成する場合、以下の実装を標準的なテンプレートとして利用します。Paho MQTT 2.0以降の仕様変更に対応した記述となっています。

```python
import os
import json
import paho.mqtt.client as mqtt

# 環境変数から接続情報を取得（docker-composeと連動）
MQTT_HOST = os.getenv("MODT_BROKER_HOST", "broker")

def on_connect(client, userdata, flags, rc, properties=None):
    # 接続成功時に必要なトピックを購読
    print(f"Connected with result code {rc}")
    client.subscribe("modt/auth/success")

def on_message(client, userdata, msg):
    # メッセージ受信時の処理ロジック
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received topic: {msg.topic}, payload: {payload}")
    except Exception as e:
        print(f"Error parsing message: {e}")

# クライアントの初期化（APIバージョンを明示的に指定）
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except AttributeError:
    client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

# ブローカーへの接続とループの開始
client.connect(MQTT_HOST, 1883, 60)
client.loop_start()
```
## 開発方針
各モジュールは完全に独立したDockerイメージとして構築され、すべての連携はMQTTによる非同期通信を介して行われます。実運用を想定し、MQTTブローカーは外部へポートを公開せず、Dockerネットワークの内部通信に限定することでセキュリティを確保します。また、Python製のユニットではリアルタイムなログ出力を保証するため、環境変数 PYTHONUNBUFFERED=1 を設定することを基本とします。

## ユニット構成の概要
本システムは、メッセージの橋渡しを行う broker、すべての通信を監視・記録する monitor、ユーザーの入り口となる identify-unit、そして具体的な業務機能を提供するアプリケーションユニット群から構成されます。各ディレクトリにはそれぞれの役割に応じた Dockerfile とソースコードが配置されており、ルートの docker-compose.yml によって一元的に管理されています。