import os
import json
import threading
from flask import Flask, render_template_string
import paho.mqtt.client as mqtt

app = Flask(__name__)

# 認証済みユーザー情報を保持するメモリ領域
last_authorized_user = None

# 接続成功時のコールバック
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT Broker successfully.")
        client.subscribe("modt/auth/success")
    else:
        print(f"Failed to connect, return code {rc}")

# MQTTメッセージ受信時のコールバック
def on_message(client, userdata, msg):
    global last_authorized_user
    print(f"Received message on topic: {msg.topic}")
    try:
        payload = msg.payload.decode('utf-8')
        print(f"Raw payload: {payload}")
        data = json.loads(payload)
        last_authorized_user = data
        print(f"User {data.get('user_id')} recognized and welcomed.")
    except Exception as e:
        print(f"Error processing message: {e}")

# MQTTクライアントの設定と実行（スレッド用）
def run_mqtt():
    broker_host = os.getenv("MODT_BROKER_HOST", "broker")
    # Paho MQTT v2.x に対応した記述（APIバージョンを明示）
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"Attempting to connect to broker at {broker_host}...")
    try:
        client.connect(broker_host, 1883, 60)
        client.loop_forever()
    except Exception as e:
        print(f"MQTT Connection Error: {e}")

@app.route('/')
def home():
    if last_authorized_user:
        return render_template_string("""
            <h1>Welcome to MoDT Ecosystem</h1>
            <p>Status: <strong>Active (Authenticated)</strong></p>
            <ul>
                <li>User ID: {{ user.user_id }}</li>
                <li>Role: {{ user.role }}</li>
                <li>Session: {{ user.session_id }}</li>
            </ul>
        """, user=last_authorized_user)
    else:
        return "<h1>MoDT App Waiting...</h1><p>Status: Waiting for authentication signal.</p>"

if __name__ == '__main__':
    mqtt_thread = threading.Thread(target=run_mqtt, daemon=True)
    mqtt_thread.start()
    app.run(host='0.0.0.0', port=5000)