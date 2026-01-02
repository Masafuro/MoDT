import time
import os
from flask import Flask, request, jsonify, render_template, redirect
from common import modt

app = Flask(__name__)

# リクエストごとの状態を保持する一時的なバッファ
request_context = {}

def on_connect(client, userdata, flags, rc):
    """ブローカー接続成功時に呼ばれるコールバック"""
    if rc == 0:
        modt.logger.info("Viewer Unit connected to broker successfully.")
        # 接続後に必要なトピックを購読する
        client.subscribe([
            (modt.TOPIC_SESSION_INFO, 0),
            (modt.TOPIC_STATE_ALL_VAL, 0)
        ])
    else:
        modt.logger.error(f"Viewer Unit connection failed with code {rc}")

def on_message(client, userdata, msg):
    """MQTTからの返信を待ち受けるコールバック"""
    payload, error = modt.parse_payload(msg.payload.decode())
    if error:
        return

    # 1. セッション照会の結果（identify-unitからの返答）
    if msg.topic == modt.TOPIC_SESSION_INFO:
        sid = payload.get("session_id")
        if sid in request_context:
            request_context[sid]["user_id"] = payload.get("user_id")
            request_context[sid]["auth_status"] = payload.get("status")
            modt.logger.info(f"Identify response received: {sid} -> {payload.get('user_id')}")

    # 2. 全データ取得の結果（db-unitからの返答）
    elif msg.topic == modt.TOPIC_STATE_ALL_VAL:
        uid = payload.get("user_id")
        for sid, ctx in request_context.items():
            if ctx.get("user_id") == uid:
                ctx["all_data"] = payload.get("data", {})
                ctx["completed"] = True
                modt.logger.info(f"All data received for user: {uid}")

# MQTTクライアントのセットアップ
client = modt.get_mqtt_client(client_id="viewer-unit-service")
client.on_connect = on_connect
client.on_message = on_message

# ブローカーに接続
modt.connect_broker(client)

# 重要：Flaskを実行しながらバックグラウンドでMQTT処理を動かすためにloop_startを開始する
client.loop_start()

@app.route('/view-data', methods=['GET'])
def view_data():
    """セッションIDを元にユーザーの全データを取得してテーブル表示する"""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    request_context[session_id] = {
        "user_id": None,
        "auth_status": "pending",
        "all_data": {},
        "completed": False,
        "query_sent": False
    }

    client.publish(modt.TOPIC_SESSION_QUERY, modt.create_session_query_payload(session_id))

    timeout = 5.0
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ctx = request_context[session_id]
        if ctx["user_id"] and ctx["auth_status"] == "valid" and not ctx["query_sent"]:
            client.publish(modt.TOPIC_STATE_ALL_GET, modt.create_state_all_get_payload(ctx["user_id"]))
            ctx["query_sent"] = True

        if ctx["completed"]:
            html_content = render_template(
                "index.html",
                session_id=session_id,
                user_id=ctx["user_id"],
                states=ctx["all_data"]
            )
            del request_context[session_id]
            return html_content
        
        time.sleep(0.1)

    if session_id in request_context:
        del request_context[session_id]
    return "Unauthorized or data fetch timeout", 403

@app.route('/update-data', methods=['POST'])
def update_data():
    """任意のキーと値を登録・更新するエンドポイント"""
    session_id = request.form.get('session_id')
    user_id = request.form.get('user_id')
    new_key = request.form.get('new_key')
    new_value = request.form.get('new_value')

    if not all([session_id, user_id, new_key, new_value]):
        return "必須パラメータが不足しています", 400

    payload = modt.create_state_set_payload(user_id, new_key, new_value)
    client.publish(modt.TOPIC_STATE_SET, payload)
    
    time.sleep(0.5)
    return redirect(f"/view-data?session_id={session_id}")

@app.route('/delete-data', methods=['POST'])
def delete_data():
    """特定のキーを削除するエンドポイント"""
    session_id = request.form.get('session_id')
    user_id = request.form.get('user_id')
    target_key = request.form.get('key')

    if not all([session_id, user_id, target_key]):
        return "削除パラメータが不足しています", 400

    payload = modt.create_state_delete_payload(user_id, target_key)
    client.publish(modt.TOPIC_STATE_DELETE, payload)
    
    modt.logger.info(f"Delete request sent for {user_id}: {target_key}")
    
    time.sleep(0.5)
    return redirect(f"/view-data?session_id={session_id}")

@app.route('/clear-data', methods=['POST'])
def clear_data():
    """ユーザーの全データを一括削除するエンドポイント"""
    session_id = request.form.get('session_id')
    user_id = request.form.get('user_id')

    if not all([session_id, user_id]):
        return "パラメータが不足しています", 400

    payload = modt.create_state_clear_payload(user_id)
    client.publish(modt.TOPIC_STATE_CLEAR, payload)
    
    modt.logger.info(f"Clear all data request sent for {user_id}")
    
    time.sleep(0.5)
    return redirect(f"/view-data?session_id={session_id}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)