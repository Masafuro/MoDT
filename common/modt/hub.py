import json
import uuid
import threading
import paho.mqtt.client as mqtt

class HubClient:
    def __init__(self, unit_name, broker_host="localhost", broker_port=1883):
        self.unit_name = unit_name
        self.pending_requests = {}
        self.lock = threading.Lock()
        
        self.client = mqtt.Client()
        self.client.on_message = self._on_message
        self.client.connect(broker_host, broker_port)
        self.client.subscribe(f"modt/{self.unit_name}/response")
        # バックグラウンドでMQTTの通信ループを開始
        self.client.loop_start()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            req_id = payload.get("id")
            with self.lock:
                if req_id in self.pending_requests:
                    # 待機中のスレッドに応答を渡し、Eventを解除する
                    entry = self.pending_requests[req_id]
                    entry["result"] = payload
                    entry["event"].set()
        except Exception as e:
            print(f"SDK Error: {e}")

    def request(self, method, key, value=None, timeout=5.0):
        req_id = str(uuid.uuid4())[:8]
        event = threading.Event()
        
        with self.lock:
            self.pending_requests[req_id] = {"event": event, "result": None}

        topic = f"modt/{self.unit_name}/{method}"
        payload = {"id": req_id, "key": key}
        if value is not None:
            payload["value"] = value

        self.client.publish(topic, json.dumps(payload))

        # 応答が届くまで、あるいはタイムアウトまでここでスレッドを停止
        completed = event.wait(timeout=timeout)
        
        with self.lock:
            entry = self.pending_requests.pop(req_id)
            if completed:
                return entry["result"]
            else:
                return {"id": req_id, "key": key, "status": 408, "value": None}

    def get(self, key, timeout=5.0):
        return self.request("GET", key, timeout=timeout)

    def post(self, key, value, timeout=5.0):
        return self.request("POST", key, value=value, timeout=timeout)