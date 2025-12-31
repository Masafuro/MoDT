import os
import time
from flask import Flask, render_template, request, make_response, redirect
from common import modt

app = Flask(__name__)

def get_env_or_raise(key):
    """環境変数を取得し、存在しない場合はRuntimeErrorを発生させます。"""
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"必須の環境変数 '{key}' が設定されていません。.envファイルを確認してください。")
    return value

# 起動時に必須設定をチェック（viewer-unitのURLを追加）
IDENTIFY_PUBLIC_URL = get_env_or_raise("IDENTIFY_PUBLIC_URL")
DUMMY_APP_PUBLIC_URL = get_env_or_raise("DUMMY_APP_PUBLIC_URL")
VIEWER_PUBLIC_URL = get_env_or_raise("VIEWER_PUBLIC_URL")

# セッション照会の結果を一時的に保持する辞書
session_responses = {}

def on_message(client, userdata, msg):
    """MQTTメッセージ受信時の処理。"""
    data, error = modt.parse_payload(msg.payload.decode())
    if error:
        return

    # 1. ログイン直後のリダイレクト準備処理
    if msg.topic == modt.TOPIC_AUTH_SUCCESS:
        session_id = data.get("session_id")
        payload = modt.create_app_ready_payload(
            app_name="dummy-app",
            redirect_url=DUMMY_APP_PUBLIC_URL,
            session_id=session_id
        )
        client.publish(modt.TOPIC_APP_READY, payload)

    # 2. セッション照会結果の受信処理
    elif msg.topic == modt.TOPIC_SESSION_INFO:
        s_id = data.get("session_id")
        if s_id:
            session_responses[s_id] = data

# SDKを利用したMQTTセットアップ
mqtt_client = modt.get_mqtt_client()
mqtt_client.on_message = on_message

# ブローカー接続
modt.connect_broker(mqtt_client)

# トピックの購読
mqtt_client.subscribe(modt.TOPIC_AUTH_SUCCESS)
mqtt_client.subscribe(modt.TOPIC_SESSION_INFO)

def verify_session_via_mqtt(session_id):
    """identify-unitにセッションの妥当性を問い合わせます。"""
    query_payload = modt.create_session_query_payload(session_id)
    mqtt_client.publish(modt.TOPIC_SESSION_QUERY, query_payload)
    
    start_time = time.time()
    while time.time() - start_time < 2.0:
        if session_id in session_responses:
            return session_responses.pop(session_id)
        time.sleep(0.1)
    return None

@app.route("/")
def index():
    # クッキーからセッションIDを取得
    session_id = request.cookies.get("modt_session_id")
    user_info = None
    
    if session_id:
        result = verify_session_via_mqtt(session_id)
        if result and result.get("status") == "valid":
            user_info = {
                "user_id": result.get("user_id"),
                "role": result.get("role")
            }
    
    # テンプレートに user_info に加え、session_id と viewer_url を渡すように修正
    return render_template(
        "index.html", 
        user_info=user_info, 
        session_id=session_id, 
        viewer_url=VIEWER_PUBLIC_URL
    )

@app.route("/logout")
def logout():
    """クッキーを削除し、ログイン画面へ戻ります。"""
    login_url = f"{IDENTIFY_PUBLIC_URL}/login"
    response = make_response(redirect(login_url))
    response.set_cookie("modt_session_id", "", expires=0)
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)