# db-unit

データベースユニット
## 単独実行
> docker-compose up --build -d

## テスト
### ユーザー状態の保存（SET）
特定のユーザーに対して設定値を保存する際は、以下のコマンドを実行します。PowerShell上では JSON 内のダブルクォーテーションをバックスラッシュでエスケープする必要がある点に注意してください。 
> docker exec mosquitto mosquitto_pub -t "modt/state/set" -m "{\"user_id\": \"user001\", \"key\": \"theme\", \"value\": \"dark\", \"timestamp\": \"2025-12-31T16:00:00\"}"

### ユーザー状態の取得（GET）
データベースに保存されている値を確認したい場合のリクエストコマンドです。このメッセージを送信すると、データベースユニットが modt/state/value トピックに結果を返します。 
> docker exec mosquitto mosquitto_pub -t "modt/state/get" -m "{\"user_id\": \"user001\", \"key\": \"theme\", \"timestamp\": \"2025-12-31T16:00:00\"}"

### ユーザー保有キーの一覧照会（KEYS QUERY）
対象のユーザーが現在どのような設定項目を持っているかを一括で確認するためのコマンドです。 
> docker exec mosquitto mosquitto_pub -t "modt/state/keys/query" -m "{\"user_id\": \"user001\", \"timestamp\": \"2025-12-31T16:00:00\"}"