import time
import os
from flask import Flask, request, jsonify, render_template
import modt

app = Flask(__name__)

# リクエストごとの状態を保持する一時的なバッファ
# キーはsession_id、値は取得した情報を格納する辞書
request_context = {}

def on_message(client, userdata, msg):
    """MQTTからの返信を待ち受けるコールバック"""
    payload, error = modt.parse_payload(msg.payload.decode())
    if error:
        return

    # セッション照会の結果（identify-unitからの返答）
    if msg.topic == modt.TOPIC_SESSION_INFO:
        sid = payload.get("session_id")
        if sid in request_context:
            request_context[sid]["user_id"] = payload.get("user_id")
            request_context[sid]["auth_status"] = payload.get("status")
            modt.logger.info(f"Identify response received: {sid} -> {payload.get('user_id')}")

    # データ取得の結果（db-unitからの返答）
    elif msg.topic == modt.TOPIC_STATE_VAL:
        uid = payload.get("user_id")
        # 該当するuser_idを持つリクエストコンテキストを探す
        for sid, ctx in request_context.items():
            if ctx.get("user_id") == uid:
                ctx["db_data"] = payload.get("value")
                ctx["completed"] = True
                modt.logger.info(f"Data value received for user: {uid}")

# MQTTクライアントのセットアップ
client = modt.get_mqtt_client(client_id="viewer-unit-service")
client.on_message = on_message
modt.connect_broker(client)
client.subscribe([(modt.TOPIC_SESSION_INFO, 0), (modt.TOPIC_STATE_VAL, 0)])

@app.route('/view-data', methods=['GET'])
def view_data():
    """セッションIDを元にユーザーデータを取得して表示するエンドポイント"""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    # このリクエストの状態を初期化
    request_context[session_id] = {
        "user_id": None,
        "auth_status": "pending",
        "db_data": None,
        "completed": False,
        "query_sent": False  # 重複送信を防ぐためのフラグ
    }

    # 手順1: セッションIDを投げてユーザーIDを問い合わせる
    client.publish(modt.TOPIC_SESSION_QUERY, modt.create_session_query_payload(session_id))

    # 手順2: 内部通信の完了を待機（最大5秒）
    timeout = 5.0
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ctx = request_context[session_id]
        
        # ユーザーIDが判明し、まだデータベースに問い合わせていない場合
        if ctx["user_id"] and ctx["auth_status"] == "valid" and not ctx["query_sent"]:
            # 手順3: 判明したユーザーIDを使ってデータを要求
            client.publish(modt.TOPIC_STATE_GET, modt.create_state_get_payload(ctx["user_id"], "theme"))
            ctx["query_sent"] = True
            modt.logger.info(f"State GET published for user: {ctx['user_id']}")

        # 全てのデータが揃った場合、テンプレートをレンダリングして返す
        if ctx["completed"]:
            html_content = render_template(
                "index.html",
                session_id=session_id,
                user_id=ctx["user_id"],
                theme=ctx["db_data"]
            )
            del request_context[session_id]
            return html_content
        
        time.sleep(0.1)

    # タイムアウトまたは認証失敗
    if session_id in request_context:
        del request_context[session_id]
    return "Unauthorized or data fetch timeout", 403

if __name__ == '__main__':
    # 内部ポート5000でWebサーバーを起動
    app.run(host='0.0.0.0', port=5000)