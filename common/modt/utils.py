import logging
import json

# ログの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("modt_lib")

def parse_payload(payload_str):
    """受信したJSON文字列を解析します。"""
    try:
        return json.loads(payload_str), None
    except Exception as e:
        logger.warning(f"ペイロードの解析に失敗しました: {e}")
        return None, str(e)