
## MoDT SDK (common/modt.py) 仕様書

本モジュールは、Modularized Docker through mqtT (MoDT) フレームワークにおけるユニット間の通信を抽象化し、プロトコルの厳格な運用を支援するための開発キットです。本SDKを利用することで、Paho MQTTのバージョン差異の吸収、ブローカーへの接続管理、および規格に準拠したペイロードの生成を容易に行うことができます。

### 提供機能一覧

| 関数名 | 引数 | 説明 |
| --- | --- | --- |
| `get_mqtt_client` | なし | Paho MQTTのバージョン（1.x / 2.x）を自動判別し、適切なクライアントオブジェクトを生成して返します。 |
| `connect_broker` | client | 環境変数 `MODT_BROKER_HOST` を参照してブローカーに接続し、非同期ループを開始します。 |
| `parse_payload` | payload_str | 受信した文字列をJSONとして解析し、データオブジェクトとエラー内容をペアで返します。 |
| `create_auth_success_payload` | user_id, session_id, role | 認証成功時に発行する `modt/auth/success` トピック用の標準ペイロードを生成します。 |
| `create_app_ready_payload` | app_name, redirect_url, session_id | アプリ準備完了時に発行する `modt/app/ready` トピック用の標準ペイロードを生成します。 |

---

### 実装サンプル：認証ユニット (identify-app)

認証ユニット側では、ログイン成功時に標準的なペイロードを生成して発行するために本SDKを利用します。これにより、すべてのアプリケーションユニットが共通して解釈可能な形式で通知を送出することが保証されます。

```python
from common import modt

# クライアントの初期化と接続
mqtt_client = modt.get_mqtt_client()
modt.connect_broker(mqtt_client)

# ログイン成功時の処理例
def handle_login_success(user):
    session_id = generate_uuid() # 任意のUUID生成
    
    # SDKを使用して規格準拠のペイロードを作成
    payload = modt.create_auth_success_payload(
        user_id=str(user.id),
        session_id=session_id,
        role=user.role
    )
    
    # メッセージの発行
    mqtt_client.publish("modt/auth/success", payload)

```

---

### 実装サンプル：アプリケーションユニット (dummy-app)

アプリケーションユニット側では、認証通知の受信解析と、自身の準備完了報告を行う際にSDKを活用します。

```python
from common import modt

def on_message(client, userdata, msg):
    if msg.topic == "modt/auth/success":
        # 受信データの解析
        data, error = modt.parse_payload(msg.payload.decode())
        if error: return

        # アプリ側の準備完了メッセージを作成
        payload = modt.create_app_ready_payload(
            app_name="my-app",
            redirect_url="http://localhost:5001/",
            session_id=data.get("session_id")
        )
        
        # 認証ユニットへリダイレクト準備完了を通知
        client.publish("modt/app/ready", payload)

mqtt_client = modt.get_mqtt_client()
mqtt_client.on_message = on_message
modt.connect_broker(mqtt_client)
mqtt_client.subscribe("modt/auth/success")

```

---

### 導入および環境設定

本SDKを有効にするためには、各ユニットのプログラムからアクセス可能なパスに `common` ディレクトリを配置する必要があります。通常はDocker Composeのボリューム機能を利用して、ホスト側の `./common` ディレクトリを各コンテナの `/app/common` にマウントする構成を推奨します。また、ディレクトリ内にはPythonパッケージとして認識させるための `__init__.py` ファイルが必須となります。

本ドキュメントの規定に従って各ユニットを実装することで、MoDTシステム内での円滑な連動と、将来的なプロトコル拡張に対する柔軟な対応力が確保されます。

---

