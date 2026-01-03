# MoDT-Network Hub Unit Specification

## 開発進捗
- commonにhub.pyを作成
- 以下のサンプルコードはまだ検討中

### unit sample code
```python
import time
from common.utils import HubClient

def main():
    # 同期型のクライアントを初期化
    hub = HubClient(unit_name="unitA")
    # 接続の安定を待つための僅かな待機
    time.sleep(1)

    print("--- データの取得 (GET) ---")
    res = hub.get("endpoint_unitB")
    print(f"Response: {res}")

    print("\n--- データの更新 (POST) ---")
    res = hub.post("status_unitA", "active")
    print(f"Response: {res}")

if __name__ == "__main__":
    main()
```

### hub sample code
```python
import json
import paho.mqtt.client as mqtt

# 簡易的なデータストア
STORE = {"endpoint_unitB": "http://localhost:8080"}

def on_message(client, userdata, msg):
    try:
        parts = msg.topic.split('/')
        from_unit = parts[1]
        method = parts[2]
        payload = json.loads(msg.payload.decode())
        
        req_id = payload.get("id")
        key = payload.get("key")
        
        # データの引き当てロジック
        value = STORE.get(key)
        status = 200 if value else 404
        
        if method == "POST":
            STORE[key] = payload.get("value")
            value = STORE[key]
            status = 200

        # 送信元ユニットへ、IDとキーを維持してレスポンス
        res_topic = f"modt/{from_unit}/response"
        res_payload = {
            "id": req_id,
            "key": key,
            "status": status,
            "value": value
        }
        client.publish(res_topic, json.dumps(res_payload))
        print(f"Hub: {from_unit} {method} {key} -> {status}")
    except Exception as e:
        print(f"Hub Error: {e}")

hub = mqtt.Client()
hub.on_message = on_message
hub.connect("localhost", 1883)
hub.subscribe("modt/+/GET")
hub.subscribe("modt/+/POST")
hub.loop_forever()

```



## システムの設計思想
ハブユニット（hub-unit）は、modt-networkにおける情報の中心的な調停者であり、各ユニット間の疎結合な連携を実現するためのメッセージ交換基盤です。本設計では、MQTTトピックを「配送経路とアクションの宣言」として定義し、JSONペイロードを「情報の具体的な内容」として明確に分離しました。ハブは、Redisが保持するリアルタイムな動的データと、YAMLやJSONファイルに記述された静的な設計データを透過的に扱うことで、開発環境から本番環境まで一貫したデバッガビリティを提供します。

## 通信プロトコルの定義
本システムでは、情報の宛先と実行すべきメソッドをトピック名によって決定します。これにより、ハブ側でのルーティング処理が簡素化され、ネットワーク層での可視性が向上します。

### リクエスト・トピック
各ユニットからハブへ送られるリクエストは、以下の形式で発行されます。
modt/{送信元ユニット名}/{メソッド}
ここで使用されるメソッドには、GET、POST、PUTなどが割り当てられます。例えば、ユニットAが情報を取得したい場合、トピック名は modt/unitA/GET となります。このようにトピックを「送信元と動作」に限定することで、キー名に特殊文字が含まれる場合でも、トピック階層の破壊を防ぎ、安全な通信が可能になります。

### レスポンス・トピック
ハブからの応答は、リクエストの文脈を維持したまま、以下の単一のレスポンス用トピックに配信されます。
modt/{送信元ユニット名}/response
各ユニットは自身の名前を冠したこのトピックを購読することで、ハブからのあらゆる回答を一括して受け取ることができます。



## メッセージデータ構造
メッセージのペイロードには、情報の識別子であるキーと、対話の同期を保つためのID、そして実データである値が含まれます。従来の body という呼称を排し、トピック（キー）と対になる存在として **value** という名称を採用しています。

### リクエスト・ペイロード
リクエスト時のJSONには、ユニット側で生成した ID と、操作対象の KEY を含めます。
{"id": "req_001", "key": "target_resource"}
POSTやPUTのように値を書き込む必要がある場合は、さらに value フィールドを付加します。
例：{"id": "req_001", "key": "target_resource", "value": "new_data"}

### レスポンス・ペイロード
ハブからのレスポンスには、リクエストから継承した ID と KEY に加え、ハブが判定したステータスコードと取得された値を格納します。
例：{"id": "req_001", "key": "target_resource", "status": 200, "value": "current_data"}
ハブは受け取ったIDをそのまま送り返す「エコー」を行い、ユニット側でのリクエストとレスポンスの照合を保証します。



## データの優先順位とステータスコード
ハブはリクエストされたキーに対して以下の順序で検索を行い、情報の性質をステータスコードで通知します。

まずRedisを検索し、実在するユニットから報告された生きたデータが存在すれば **200 OK** を返却します。Redisにデータがない場合、ハブはローカルのYAMLまたはJSON設定ファイルを確認します。ファイル内に該当するキーの定義があれば、それを初期値として採用し、**203 Non-Authoritative Information** を付与して返却します。いずれのソースにもデータが存在しない場合は **404 Not Found** となります。この仕組みにより、開発者は設定ファイルを編集するだけで、特定のユニットが未完成の状態でもシステム全体の動作をシミュレートできます。

## 自律的なID管理
IDの発行権限は各ユニットが完全に保持します。トピックの最前段にユニット名が含まれているため、異なるユニット間でIDが重複しても通信が衝突することはありません。各ユニットは自身の内部ロジックに応じて、連番、タイムスタンプ、あるいはUUIDなど、最適なID体系を自由に選択してハブとの対話を開始できます。