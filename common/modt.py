import os
import json
import time
import logging
import paho.mqtt.client as mqtt

# ログの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("modt_lib")

# システム全体で使用する標準トピックの定義
TOPIC_AUTH_SUCCESS = "modt/auth/success"
TOPIC_APP_READY = "modt/app/ready"
TOPIC_SESSION_QUERY = "modt/session/query"
TOPIC_SESSION_INFO = "modt/session/info"

# 状態管理（KVストア操作）用のトピック
TOPIC_STATE_GET = "modt/state/get"
TOPIC_STATE_SET = "modt/state/set"
TOPIC_STATE_VAL = "modt/state/value"
TOPIC_STATE_KEYS_QUERY = "modt/state/keys/query"
TOPIC_STATE_KEYS_LIST = "modt/state/keys/list"

def get_mqtt_client(client_id=""):
    """Paho MQTTのバージョン差異を吸収してクライアントオブジェクトを生成します。"""
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
    except AttributeError:
        return mqtt.Client(client_id=client_id)

def connect_broker(client):
    """環境変数からブローカー情報を取得して接続し、ループを開始します。"""
    host = os.getenv("MODT_BROKER_HOST", "broker")
    port_str = os.getenv("MODT_BROKER_PORT", "1883")
    
    try:
        port = int(port_str)
        client.connect(host, port, 60)
        client.loop_start()
        logger.info(f"MQTTブローカー（{host}:{port}）に接続しました。")
    except Exception as e:
        logger.error(f"MQTTブローカーへの接続に失敗しました: {e}")
        raise

def disconnect_broker(client):
    """ブローカーから安全に切断します。"""
    client.loop_stop()
    client.disconnect()
    logger.info("MQTTブローカーから切断されました。")

def parse_payload(payload_str):
    """受信したJSON文字列を解析します。"""
    try:
        return json.loads(payload_str), None
    except Exception as e:
        logger.warning(f"ペイロードの解析に失敗しました: {e}")
        return None, str(e)

def _create_base_payload(extra_data):
    """共通のタイムスタンプを含むペイロードの基礎を生成します。"""
    payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    payload.update(extra_data)
    return json.dumps(payload)

# 認証・セッション関連のペイロード生成関数
def create_auth_success_payload(user_id, session_id, role="user"):
    """認証成功時のメッセージペイロードを生成します。"""
    return _create_base_payload({
        "user_id": user_id,
        "session_id": session_id,
        "role": role
    })

def create_app_ready_payload(app_name, redirect_url, session_id):
    """アプリケーションの準備完了を知らせるメッセージペイロードを生成します。"""
    return _create_base_payload({
        "app_name": app_name,
        "redirect_url": redirect_url,
        "session_id": session_id
    })

def create_session_query_payload(session_id):
    """セッションの身分照会を行うためのリクエストペイロードを生成します。"""
    return _create_base_payload({
        "session_id": session_id
    })

def create_session_info_payload(session_id, user_id=None, role=None, status="invalid"):
    """照会リクエストに対する回答用の詳細ペイロードを生成します。"""
    return _create_base_payload({
        "session_id": session_id,
        "user_id": user_id,
        "role": role,
        "status": status
    })

# 状態管理（KVストア）関連のペイロード生成関数
def create_state_get_payload(user_id, key):
    """特定のユーザーIDとキーに関連付けられた値の取得リクエストを生成します。"""
    return _create_base_payload({
        "user_id": user_id,
        "key": key,
        "action": "get"
    })

def create_state_set_payload(user_id, key, value):
    """特定のユーザーIDとキーに対して値を保存するためのリクエストを生成します。"""
    return _create_base_payload({
        "user_id": user_id,
        "key": key,
        "value": value,
        "action": "set"
    })

def create_state_keys_query_payload(user_id):
    """特定のユーザーが保持している全てのキー一覧を取得するためのリクエストを生成します。"""
    return _create_base_payload({
        "user_id": user_id,
        "action": "list_keys"
    })

def create_state_keys_list_payload(user_id, keys):
    """取得したキーの一覧を返信するためのペイロードを生成します。"""
    return _create_base_payload({
        "user_id": user_id,
        "keys": keys
    })

def create_state_value_payload(user_id, key, value, status="valid"):
    """取得した値を返信するための専用ペイロードを生成します。"""
    return _create_base_payload({
        "user_id": user_id,
        "key": key,
        "value": value,
        "status": status
    })