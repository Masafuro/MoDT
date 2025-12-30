import time
from common import modt

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        # SDKのバリデーション機能を活用して内容を確認することも可能ですが、
        # モニターは全メッセージを記録するため、ここでは生データを出力します。
        print("\n" + "="*60, flush=True)
        print(f"Time   : {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(f"Topic  : {topic}", flush=True)
        print(f"Payload: {payload}", flush=True)
        print("="*60 + "\n", flush=True)
        
    except Exception as e:
        print(f"Error logging message: {e}", flush=True)

# SDKの関数を使用してMQTTクライアントを生成
mqtt_client = modt.get_mqtt_client()
mqtt_client.on_message = on_message

print("Monitor Unit starting via MoDT SDK...", flush=True)

try:
    # SDKの関数を使用してブローカーへ接続
    modt.connect_broker(mqtt_client)
    
    # すべてのトピックをワイルドカードで購読
    mqtt_client.subscribe("#")
    print("Subscribed to all topics. Waiting for messages...", flush=True)
    
    # Flaskのような常駐プロセスを持たないため、メインスレッドを維持します
    while True:
        time.sleep(1)
        
except Exception as e:
    print(f"Monitor failed to start: {e}", flush=True)