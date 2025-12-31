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

# 新設：全件取得用のトピック
TOPIC_STATE_ALL_GET = "modt/state/all/get"
TOPIC_STATE_ALL_VAL = "modt/state/all/value"

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

# 既存のペイロード生成関数（省略せずに維持してください）
def create_auth_success_payload(user_id, session_id, role="user"):
    return _create_base_payload({"user_id": user_id, "session_id": session_id, "role": role})

def create_app_ready_payload(app_name, redirect_url, session_id):
    return _create_base_payload({"app_name": app_name, "redirect_url": redirect_url, "session_id": session_id})

def create_session_query_payload(session_id):
    return _create_base_payload({"session_id": session_id})

def create_session_info_payload(session_id, user_id=None, role=None, status="invalid"):
    return _create_base_payload({"session_id": session_id, "user_id": user_id, "role": role, "status": status})

def create_state_get_payload(user_id, key):
    return _create_base_payload({"user_id": user_id, "key": key, "action": "get"})

def create_state_set_payload(user_id, key, value):
    return _create_base_payload({"user_id": user_id, "key": key, "value": value, "action": "set"})

def create_state_keys_query_payload(user_id):
    return _create_base_payload({"user_id": user_id, "action": "list_keys"})

def create_state_keys_list_payload(user_id, keys):
    return _create_base_payload({"user_id": user_id, "keys": keys})

def create_state_value_payload(user_id, key, value, status="valid"):
    return _create_base_payload({"user_id": user_id, "key": key, "value": value, "status": status})

# 新設：全件取得・返信用ペイロード生成関数
def create_state_all_get_payload(user_id):
    """特定のユーザーに関連付けられた全てのキーと値の取得リクエストを生成します。"""
    return _create_base_payload({"user_id": user_id, "action": "get_all"})

def create_state_all_value_payload(user_id, data_dict):
    """取得した全KVデータを返信するための専用ペイロードを生成します。"""
    return _create_base_payload({"user_id": user_id, "data": data_dict})