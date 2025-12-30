import os
import json
import paho.mqtt.client as mqtt
from flask import Flask

app = Flask(__name__)
MQTT_HOST = os.getenv("MODT_BROKER_HOST", "broker")

def on_message(client, userdata, msg):
    try:
        # identify-appからの認証成功イベントを受信
        if msg.topic == "modt/auth/success":
            data = json.loads(msg.payload.decode())
            user_id = data.get("user_id")
            session_id = data.get("session_id")
            
            print(f"Received auth success for user: {user_id}, session: {session_id}", flush=True)

            # 規格に基づいた返信メッセージの作成
            response_payload = {
                "app_name": "dummy-app",
                "redirect_url": "http://localhost:5001/",
                "session_id": session_id
            }

            # 準備完了を通知
            client.publish("modt/app/ready", json.dumps(response_payload))
            print(f"Published standard redirect info for session: {session_id}", flush=True)

    except Exception as e:
        print(f"Error in dummy-app MQTT process: {e}", flush=True)

# MQTTクライアントの設定
try:
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except AttributeError:
    mqtt_client = mqtt.Client()

mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_HOST, 1883, 60)
mqtt_client.subscribe("modt/auth/success")
mqtt_client.loop_start()

@app.route("/")
def index():
    return "<h1>Welcome to Dummy App Unit</h1><p>これはダミーアプリケーションの画面です。</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)