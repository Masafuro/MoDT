import json
import time

def _create_base_payload(extra_data):
    """共通のタイムスタンプを含むペイロードの基礎を生成します。"""
    payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    payload.update(extra_data)
    return json.dumps(payload)

def create_auth_success_payload(user_id, session_id, role="user"):
    return _create_base_payload({"user_id": user_id, "session_id": session_id, "role": role})

def create_app_ready_payload(app_name, redirect_url, session_id):
    return _create_base_payload({"app_name": app_name, "redirect_url": redirect_url, "session_id": session_id})

def create_session_query_payload(session_id):
    return _create_base_payload({"session_id": session_id})

def create_session_info_payload(session_id, user_id=None, role=None, status="invalid"):
    return _create_base_payload({"session_id": session_id, "user_id": user_id, "role": role, "status": status})

def create_state_get_payload(user_id, key):
    return _create_base_payload({"user_id": user_id, "key": key, "action": "get"})

def create_state_set_payload(user_id, key, value):
    return _create_base_payload({"user_id": user_id, "key": key, "value": value, "action": "set"})

def create_state_keys_query_payload(user_id):
    return _create_base_payload({"user_id": user_id, "action": "list_keys"})

def create_state_keys_list_payload(user_id, keys):
    return _create_base_payload({"user_id": user_id, "keys": keys})

def create_state_value_payload(user_id, key, value, status="valid"):
    return _create_base_payload({"user_id": user_id, "key": key, "value": value, "status": status})

def create_state_all_get_payload(user_id):
    return _create_base_payload({"user_id": user_id, "action": "get_all"})

def create_state_all_value_payload(user_id, data_dict):
    return _create_base_payload({"user_id": user_id, "data": data_dict})

# 新設された削除用ペイロード生成関数
def create_state_delete_payload(user_id, key):
    """特定のキーを削除するためのリクエストを生成します。"""
    return _create_base_payload({"user_id": user_id, "key": key, "action": "delete"})

def create_state_clear_payload(user_id):
    """ユーザーの全データを一括削除するためのリクエストを生成します。"""
    return _create_base_payload({"user_id": user_id, "action": "clear_all"})