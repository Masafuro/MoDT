from flask import Flask, render_template
from common import modt

app = Flask(__name__)

def on_message(client, userdata, msg):
    if msg.topic == "modt/auth/success":
        data, error = modt.parse_payload(msg.payload.decode())
        if error:
            print(f"Payload error: {error}", flush=True)
            return

        user_id = data.get("user_id")
        session_id = data.get("session_id")
        print(f"Auth success received for user: {user_id}", flush=True)

        payload = modt.create_app_ready_payload(
            app_name="dummy-app",
            redirect_url="http://localhost:5001/",
            session_id=session_id
        )
        client.publish("modt/app/ready", payload)
        print(f"Redirect signal sent via SDK for session: {session_id}", flush=True)

# SDKを利用したMQTTセットアップ
mqtt_client = modt.get_mqtt_client()
mqtt_client.on_message = on_message
modt.connect_broker(mqtt_client)
mqtt_client.subscribe("modt/auth/success")

@app.route("/")
def index():
    # 文字列を直接返す代わりに、templates/index.html を描画して返します
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)