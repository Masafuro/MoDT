import sqlite3
import json
import modt
import time

def init_db(db_path="modt_state.db"):
    """データベースの初期化を行い、テーブルを作成します。"""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS states (
            user_id TEXT,
            key TEXT,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, key)
        )
    """)
    conn.commit()
    return conn

def on_message(client, userdata, msg):
    """メッセージを受信した際のメインロジックです。"""
    data, error = modt.parse_payload(msg.payload.decode())
    if error or not data:
        modt.logger.error(f"Payload error: {error}")
        return

    conn = userdata["db_conn"]
    cursor = conn.cursor()
    user_id = data.get("user_id")
    key = data.get("key")

    # 値の保存（SET）処理
    if msg.topic == modt.TOPIC_STATE_SET:
        value = data.get("value")
        db_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        cursor.execute(
            "INSERT OR REPLACE INTO states (user_id, key, value, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, key, db_value)
        )
        conn.commit()
        modt.logger.info(f"Stored value for user: {user_id}, key: {key}")

    # 特定のキーの値を取得（GET）処理
    elif msg.topic == modt.TOPIC_STATE_GET:
        cursor.execute("SELECT value FROM states WHERE user_id = ? AND key = ?", (user_id, key))
        result = cursor.fetchone()
        
        if result:
            status = "valid"
            try:
                val = json.loads(result[0])
            except (json.JSONDecodeError, TypeError, ValueError):
                val = result[0]
        else:
            status = "not_found"
            val = None
        
        response = modt.create_state_value_payload(user_id, key, val, status)
        client.publish(modt.TOPIC_STATE_VAL, response)
        modt.logger.info(f"Answered GET request for: {user_id}/{key}")

    # ユーザーに紐付く全データを取得（ALL GET）処理
    elif msg.topic == modt.TOPIC_STATE_ALL_GET:
        cursor.execute("SELECT key, value FROM states WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        
        all_data = {}
        for row in rows:
            k, v = row[0], row[1]
            try:
                all_data[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError, ValueError):
                all_data[k] = v
        
        # modt.py の新設関数を使用して返信ペイロードを作成
        response = modt.create_state_all_value_payload(user_id, all_data)
        client.publish(modt.TOPIC_STATE_ALL_VAL, response)
        modt.logger.info(f"Published all data for user: {user_id}")

    # キー一覧の照会（KEYS QUERY）処理
    elif msg.topic == modt.TOPIC_STATE_KEYS_QUERY:
        cursor.execute("SELECT key FROM states WHERE user_id = ?", (user_id,))
        keys = [row[0] for row in cursor.fetchall()]
        
        response = modt.create_state_keys_list_payload(user_id, keys)
        client.publish(modt.TOPIC_STATE_KEYS_LIST, response)
        modt.logger.info(f"Published key list for: {user_id}")

def main():
    """データベースユニットのメインループです。"""
    db_conn = init_db()
    client = modt.get_mqtt_client(client_id="database-unit")
    
    client.user_data_set({"db_conn": db_conn})
    client.on_message = on_message
    
    modt.connect_broker(client)
    
    # 購読リストを SDK の定数を使用して定義
    client.subscribe([
        (modt.TOPIC_STATE_GET, 0),
        (modt.TOPIC_STATE_SET, 0),
        (modt.TOPIC_STATE_KEYS_QUERY, 0),
        (modt.TOPIC_STATE_ALL_GET, 0)
    ])
    
    modt.logger.info("Database Unit is running with SDK updates...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        modt.disconnect_broker(client)
        db_conn.close()

if __name__ == "__main__":
    main()