import os
import json
import time
import paho.mqtt.client as mqtt

# システム全体で使用する標準トピックの定義
TOPIC_AUTH_SUCCESS = "modt/auth/success"
TOPIC_APP_READY = "modt/app/ready"
TOPIC_SESSION_QUERY = "modt/session/query"
TOPIC_SESSION_INFO = "modt/session/info"

def get_mqtt_client():
    """Paho MQTTのバージョン差異を吸収してクライアントオブジェクトを生成します。"""
    try:
        # Paho MQTT 2.0以降のAPIバージョン指定
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        # 1.x系の古いバージョンを利用している場合
        return mqtt.Client()

def connect_broker(client):
    """
    環境変数からブローカー情報を取得して接続します。
    設定が不足している場合は、不具合を防ぐため明示的に例外を投げます。
    """
    host = os.getenv("MODT_BROKER_HOST")
    port_str = os.getenv("MODT_BROKER_PORT")
    
    if not host or not port_str:
        raise RuntimeError(
            "必須の環境変数が設定されていません。MODT_BROKER_HOST と MODT_BROKER_PORT を .env で定義してください。"
        )
    
    try:
        port = int(port_str)
    except ValueError:
        raise ValueError(f"MODT_BROKER_PORT には数値を指定してください。現在の値: {port_str}")
        
    client.connect(host, port, 60)
    client.loop_start()

def parse_payload(payload_str):
    """受信したJSON文字列を解析し、データとエラー内容を返します。"""
    try:
        return json.loads(payload_str), None
    except Exception as e:
        return None, str(e)

def create_auth_success_payload(user_id, session_id, role="user"):
    """認証成功時のメッセージペイロードを生成します。"""
    return json.dumps({
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    })

def create_app_ready_payload(app_name, redirect_url, session_id):
    """アプリケーションの準備完了を知らせるメッセージペイロードを生成します。"""
    return json.dumps({
        "app_name": app_name,
        "redirect_url": redirect_url,
        "session_id": session_id
    })

def create_session_query_payload(session_id):
    """セッションの身分照会を行うためのリクエストペイロードを生成します。"""
    return json.dumps({
        "session_id": session_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    })

def create_session_info_payload(session_id, user_id=None, role=None, status="invalid"):
    """照会リクエストに対する回答用の詳細ペイロードを生成します。"""
    return json.dumps({
        "session_id": session_id,
        "user_id": user_id,
        "role": role,
        "status": status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    })