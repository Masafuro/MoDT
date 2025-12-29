import os
import json
import time
import paho.mqtt.client as mqtt
import redis

BROKER_HOST = os.getenv("MODT_BROKER_HOST", "broker")
r = redis.Redis(host='localhost', port=6379, db=0)

def on_message(client, userdata, msg):
    try:
        log_entry = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "topic": msg.topic,
            "payload": msg.payload.decode('utf-8')
        }
        r.lpush("modt:logs", json.dumps(log_entry))
        r.ltrim("modt:logs", 0, 999)
    except Exception as e:
        print(f"Error logging message: {e}")

client = mqtt.Client()
client.on_message = on_message
client.connect(BROKER_HOST, 1883, 60)
client.subscribe("#")
client.loop_forever()