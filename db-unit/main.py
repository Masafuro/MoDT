import sqlite3
import json
import os
import time
from common import modt

def init_db(db_path="/app/data/modt_state.db"):
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
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

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        modt.logger.info("Successfully connected to MQTT Broker.")
        client.subscribe([
            (modt.TOPIC_STATE_GET, 0),
            (modt.TOPIC_STATE_SET, 0),
            (modt.TOPIC_STATE_KEYS_QUERY, 0),
            (modt.TOPIC_STATE_ALL_GET, 0),
            (modt.TOPIC_STATE_DELETE, 0), # 追加
            (modt.TOPIC_STATE_CLEAR, 0)   # 追加
        ])
    else:
        modt.logger.error(f"Connection failed with return code {rc}")

def on_message(client, userdata, msg):
    data, error = modt.parse_payload(msg.payload.decode())
    if error or not data:
        return

    conn = userdata["db_conn"]
    cursor = conn.cursor()
    user_id = data.get("user_id")
    key = data.get("key")

    if msg.topic == modt.TOPIC_STATE_SET:
        value = data.get("value")
        db_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        cursor.execute(
            "INSERT OR REPLACE INTO states (user_id, key, value, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, key, db_value)
        )
        conn.commit()
        modt.logger.info(f"SET: {user_id}/{key}")

    elif msg.topic == modt.TOPIC_STATE_GET:
        cursor.execute("SELECT value FROM states WHERE user_id = ? AND key = ?", (user_id, key))
        result = cursor.fetchone()
        status = "valid" if result else "not_found"
        val = None
        if result:
            try:
                val = json.loads(result[0])
            except:
                val = result[0]
        client.publish(modt.TOPIC_STATE_VAL, modt.create_state_value_payload(user_id, key, val, status))

    elif msg.topic == modt.TOPIC_STATE_ALL_GET:
        cursor.execute("SELECT key, value FROM states WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        all_data = {}
        for row in rows:
            try:
                all_data[row[0]] = json.loads(row[1])
            except:
                all_data[row[0]] = row[1]
        client.publish(modt.TOPIC_STATE_ALL_VAL, modt.create_state_all_value_payload(user_id, all_data))

    # --- 新設：削除ロジック ---
    elif msg.topic == modt.TOPIC_STATE_DELETE:
        cursor.execute("DELETE FROM states WHERE user_id = ? AND key = ?", (user_id, key))
        conn.commit()
        modt.logger.info(f"DELETE: {user_id}/{key}")

    elif msg.topic == modt.TOPIC_STATE_CLEAR:
        cursor.execute("DELETE FROM states WHERE user_id = ?", (user_id,))
        conn.commit()
        modt.logger.info(f"CLEAR: All data for user {user_id}")

def main():
    db_conn = init_db()
    client = modt.get_mqtt_client(client_id="database-unit")
    client.user_data_set({"db_conn": db_conn})
    client.on_connect = on_connect
    client.on_message = on_message
    
    modt.connect_broker(client)
    
    try:
        # loop_start()を重複させず、ここでメインスレッドをブロックして待機する
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        modt.disconnect_broker(client)
        db_conn.close()

if __name__ == "__main__":
    main()