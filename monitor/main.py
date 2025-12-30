import os
import json
import time
import paho.mqtt.client as mqtt
import sys

BROKER_HOST = os.getenv("MODT_BROKER_HOST", "broker")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        # 区切り線を入れて視認性を高め、即座に出力します
        print("\n" + "="*60, flush=True)
        print(f"Time   : {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(f"Topic  : {topic}", flush=True)
        print(f"Payload: {payload}", flush=True)
        print("="*60 + "\n", flush=True)
        
    except Exception as e:
        print(f"Error logging message: {e}", flush=True)

# Paho MQTT 2.0+ への対応
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except AttributeError:
    client = mqtt.Client()

client.on_message = on_message

print(f"Monitor Unit starting... (Host: {BROKER_HOST})", flush=True)

try:
    client.connect(BROKER_HOST, 1883, 60)
    client.subscribe("#")
    print("Subscribed to all topics. Waiting for messages...", flush=True)
    client.loop_forever()
except Exception as e:
    print(f"Monitor failed to start: {e}", flush=True)