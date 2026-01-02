import os
import paho.mqtt.client as mqtt
from .utils import logger

def get_mqtt_client(client_id=""):
    """
    MQTTクライアントを生成します。
    プロトコルをMQTTv311に固定し、接続の安定性を高めます。
    """
    try:
        # paho-mqtt 2.x 用の記述
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id, protocol=mqtt.MQTTv311)
    except AttributeError:
        # paho-mqtt 1.x 用の記述
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    return client

def connect_broker(client):
    """
    環境変数からブローカー情報を取得して接続します。
    ループの開始（loop_start/loop_forever）は各ユニット側に委ねます。
    """
    host = os.getenv("MODT_BROKER_HOST", "broker")
    port_str = os.getenv("MODT_BROKER_PORT", "1883")
    
    try:
        port = int(port_str)
        client.connect(host, port, 60)
        logger.info(f"MQTTブローカー（{host}:{port}）に接続待機状態になりました。")
    except Exception as e:
        logger.error(f"MQTTブローカーへの接続に失敗しました: {e}")
        raise

def disconnect_broker(client):
    """安全に切断します。"""
    client.disconnect()
    logger.info("MQTTブローカーから切断されました。")