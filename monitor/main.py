import time
import json
from common import modt

def on_message(client, userdata, msg):
    """
    MQTTメッセージ受信時の処理。
    MoDTプロトコルに準拠した全通信を、人間が読みやすい形式でログ出力します。
    """
    try:
        topic = msg.topic
        payload_raw = msg.payload.decode('utf-8')
        
        # 受信時刻を取得
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # JSONとして解析を試み、成功すれば整形して表示
        payload_data, error = modt.parse_payload(payload_raw)
        
        print("\n" + "="*70, flush=True)
        print(f"[{timestamp}] Topic: {topic}", flush=True)
        print("-" * 70, flush=True)
        
        if error:
            # JSONでない、あるいは破損している場合はそのまま表示
            print(f"Raw Payload: {payload_raw}", flush=True)
            print(f"Parse Error: {error}", flush=True)
        else:
            # 整形されたJSONを出力
            pretty_payload = json.dumps(payload_data, indent=4, ensure_ascii=False)
            print(pretty_payload, flush=True)
            
        print("="*70 + "\n", flush=True)
        
    except Exception as e:
        print(f"Error logging message: {e}", flush=True)

# SDKを使用してMQTTクライアントを生成
mqtt_client = modt.get_mqtt_client()
mqtt_client.on_message = on_message

print("Monitor Unit starting via MoDT SDK...", flush=True)

try:
    # SDKの厳格な接続関数を利用
    # MODT_BROKER_HOST と MODT_BROKER_PORT が未設定ならここで例外が発生します
    modt.connect_broker(mqtt_client)
    
    # MoDTシステム内のすべてのトピックをワイルドカードで購読
    mqtt_client.subscribe("#")
    print("Subscribed to all topics. Waiting for messages...", flush=True)
    
    # メインスレッドを維持して待機状態を継続
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\nMonitor Unit stopping...", flush=True)
except Exception as e:
    print(f"Monitor failed to start: {e}", flush=True)