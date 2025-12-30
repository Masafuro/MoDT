import os
import json
import time
import paho.mqtt.client as mqtt

def get_mqtt_client():
    """Paho MQTTのバージョン差異を吸収してクライアントを生成します。"""
    try:
        # Paho MQTT 2.0+ への対応
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        # 旧バージョンへの対応
        return mqtt.Client()

def connect_broker(client):
    """環境変数からホストを取得して接続を開始します。"""
    host = os.getenv("MODT_BROKER_HOST", "broker")
    if not host:
        host = os.getenv("MQTT_BROKER_HOST", "broker")
    client.connect(host, 1883, 60)
    client.loop_start()

def parse_payload(payload_str):
    """JSONのパースとエラーハンドリングを一括で行います。"""
    try:
        return json.loads(payload_str), None
    except Exception as e:
        return None, str(e)

def create_auth_success_payload(user_id, session_id, role="user"):
    """
    認証成功時の標準メッセージを生成します。
    identify-app で使用します。
    """
    return json.dumps({
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    })

def create_app_ready_payload(app_name, redirect_url, session_id):
    """
    アプリ準備完了時の標準メッセージを生成します。
    dummy-app 等のアプリケーションユニットで使用します。
    """
    return json.dumps({
        "app_name": app_name,
        "redirect_url": redirect_url,
        "session_id": session_id
    })