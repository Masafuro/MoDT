# MoDT Common SDK (modt.py)

MoDT (Modular Docker through MQTT) フレームワークにおける共通基盤ライブラリです。各ユニット間の通信規格を標準化し、MQTT クライアントの管理やペイロードの生成を一元化します。

## 概要

このライブラリは、マイクロサービス間の非同期通信において「どのトピックで」「どのようなデータ形式で」やり取りするかというプロトコルを定義します。すべてのユニットはこの SDK を通じてメッセージを構成することで、システム全体の整合性を保ちます。

## 主要なトピック定義

システム全体で利用されるトピックは定数として定義されています。

### 認証・セッション関連
* `TOPIC_AUTH_SUCCESS`: 認証成功通知 ("modt/auth/success")
* `TOPIC_APP_READY`: アプリ準備完了通知 ("modt/app/ready")
* `TOPIC_SESSION_QUERY`: セッション照会リクエスト ("modt/session/query")
* `TOPIC_SESSION_INFO`: セッション照会回答 ("modt/session/info")

### 状態管理 (KVストア) 関連
* `TOPIC_STATE_GET`: 単一キー取得リクエスト ("modt/state/get")
* `TOPIC_STATE_SET`: 値保存リクエスト ("modt/state/set")
* `TOPIC_STATE_VAL`: 単一値返信 ("modt/state/value")
* `TOPIC_STATE_ALL_GET`: 全データ取得リクエスト ("modt/state/all/get")
* `TOPIC_STATE_ALL_VAL`: 全データ返信 ("modt/state/all/value")

## 共通関数

### クライアント管理
* **`get_mqtt_client(client_id)`**: Paho MQTT のバージョン差異（v1/v2）を吸収したクライアントオブジェクトを生成します。
* **`connect_broker(client)`**: 環境変数 `MODT_BROKER_HOST` および `MODT_BROKER_PORT` を参照してブローカーに接続し、バックグラウンドループを開始します。
* **`disconnect_broker(client)`**: 安全にループを停止し、接続を解除します。

### ペイロード処理
* **`parse_payload(payload_str)`**: 受信した JSON 文字列を辞書形式に変換します。パース失敗時にはエラー情報を返します。
* **`_create_base_payload(extra_data)`**: すべてのメッセージに共通の `timestamp` (ISO 8601形式) を付与します。

## ペイロード生成ヘルパー

各通信プロトコルに準拠した JSON ペイロードを生成します。

### 状態管理 (KVストア) 用
* **`create_state_get_payload(user_id, key)`**: 特定のキーの取得リクエスト。
* **`create_state_set_payload(user_id, key, value)`**: 値の保存リクエスト。`value` には文字列のほか、辞書やリストも指定可能です。
* **`create_state_all_get_payload(user_id)`**: ユーザーに紐付く全データの取得リクエスト。
* **`create_state_all_value_payload(user_id, data_dict)`**: `db-unit` から返信される、全 KV ペアを含む辞書データ用。

## 実装上のメリット



1. **プロトコルのカプセル化**: ペイロードの構造（キー名やデータ型）が変更された場合でも、この SDK を修正するだけで全ユニットに対応が波及します。
2. **接続ロジックの共通化**: Docker Compose 環境下でのホスト名解決やポート設定を意識せずに接続が可能です。
3. **データ型への柔軟性**: `db-unit` への保存時における JSON 変換などを意識せず、Python のネイティブなデータ構造をそのまま扱えます。

## 配置と利用方法

Docker Compose において、ホスト側の `./common` ディレクトリを各コンテナの `/app/common` 等にマウントし、`PYTHONPATH` を通してインポートしてください。

```python
from common import modt

# 接続例
client = modt.get_mqtt_client("my-service")
modt.connect_broker(client)

# メッセージ送信例
payload = modt.create_state_set_payload("user-123", "theme", "dark")
client.publish(modt.TOPIC_STATE_SET, payload)