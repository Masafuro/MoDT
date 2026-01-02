import time
import os
from flask import Flask, request, jsonify, render_template, redirect
from common import modt

app = Flask(__name__)

# リクエストごとの状態を保持する一時的なバッファ
request_context = {}

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
    # modt.py で新設した TOPIC_STATE_ALL_VAL を使用します
    elif msg.topic == modt.TOPIC_STATE_ALL_VAL:
        uid = payload.get("user_id")
        # 該当するuser_idを持つ全てのリクエストコンテキストにデータを流し込む
        for sid, ctx in request_context.items():
            if ctx.get("user_id") == uid:
                ctx["all_data"] = payload.get("data", {})
                ctx["completed"] = True
                modt.logger.info(f"All data received for user: {uid} ({len(ctx['all_data'])} keys)")

# MQTTクライアントのセットアップ
client = modt.get_mqtt_client(client_id="viewer-unit-service")
client.on_message = on_message
modt.connect_broker(client)

# 新設された全件取得用トピックを購読リストに追加
client.subscribe([
    (modt.TOPIC_SESSION_INFO, 0),
    (modt.TOPIC_STATE_ALL_VAL, 0)
])

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

    # 手順1: 身元照会
    client.publish(modt.TOPIC_SESSION_QUERY, modt.create_session_query_payload(session_id))

    timeout = 5.0
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ctx = request_context[session_id]
        
        # 手順2: ユーザーID判明後、全データを一括リクエスト
        if ctx["user_id"] and ctx["auth_status"] == "valid" and not ctx["query_sent"]:
            # modt.py の新設関数を利用
            client.publish(modt.TOPIC_STATE_ALL_GET, modt.create_state_all_get_payload(ctx["user_id"]))
            ctx["query_sent"] = True
            modt.logger.info(f"State ALL_GET published for user: {ctx['user_id']}")

        # 手順3: データの受信完了を確認してレンダリング
        if ctx["completed"]:
            html_content = render_template(
                "index.html",
                session_id=session_id,
                user_id=ctx["user_id"],
                states=ctx["all_data"] # 辞書形式でテンプレートに渡す
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
    new_key = request.form.get('new_key')   # キー名をフォームから取得
    new_value = request.form.get('new_value') # 値をフォームから取得

    if not all([session_id, user_id, new_key, new_value]):
        return "必須パラメータが不足しています", 400

    # 任意のキー名で保存リクエストをパブリッシュ
    payload = modt.create_state_set_payload(user_id, new_key, new_value)
    client.publish(modt.TOPIC_STATE_SET, payload)
    
    modt.logger.info(f"Update request sent for {user_id}: {new_key} -> {new_value}")

    # 非同期処理の完了を待ってリダイレクト
    time.sleep(0.5)
    return redirect(f"/view-data?session_id={session_id}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)