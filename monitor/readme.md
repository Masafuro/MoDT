# MoDT 監視ユニット（monitor）動作確認手順書

## 1. コンテナの稼働状態の確認
まず、システム全体のコンテナが正常に起動しているかを確認する必要があります。ターミナルで以下のコマンドを実行し、modt-brokerとmodt-monitorの両方のサービスにおいて、STATUSが「Up」と表示されていることを確かめてください。これが全てのテストの前提条件となります。

docker-compose ps

## 2. 検証用メッセージの発行
次に、MQTTブローカーを介してテスト用の信号を送信します。この操作によって、監視ユニットがメッセージを正常に捕捉できるかどうかを検証します。以下のコマンドを実行して、任意のトピックにテスト用の文字列をパブリッシュしてください。

docker exec -it modt-broker mosquitto_pub -t "modt/system/check" -m "First connection successful"

## 3. 蓄積されたログの参照
メッセージの送信が完了したら、監視ユニット内部のRedisにデータが正しく保存されているかを直接確認します。redis-cliを用いて、modt:logsというキーに格納されたリスト形式のデータを取得してください。正常に動作していれば、受信時刻、トピック、およびペイロードが含まれたJSON形式のログが出力されます。

docker exec -it modt-monitor redis-cli lrange modt:logs 0 -1

## 4. ログデータの初期化（任意）
開発の過程で蓄積されたログを一度リセットし、まっさらな状態からテストをやり直したい場合は、以下のコマンドを実行してRedis内の該当するキーを削除してください。これにより、古いデータに惑わされることなく新しい検証を行うことができます。

docker exec -it modt-monitor redis-cli del modt:logs


# MoDT システム開発用 SDK コマンドリスト (PowerShell版)

このドキュメントは、Dockerコンテナ内で動作するMQTTブローカー（modt-broker）を通じて、システムの各ユニットに対して手動でメッセージを送信・監視するためのリファレンスです。PowerShell環境においてJSONのダブルクォーテーションを正しく解釈させるため、バックティック（`）によるエスケープを施しています。

---

## 1. システム全体のリアルタイム監視 (MONITOR)

デバッグ時には、まず新しいターミナルを開き、以下のコマンドを実行して全てのメッセージの流れを可視化してください。トピック名と内容がリアルタイムで表示されます。

docker exec -it modt-broker mosquitto_sub -t "modt/#" -v

---

## 2. ユーザー状態の保存 (SET)

特定のユーザー（例: user001）に対して、キーと値のペアを保存するコマンドです。データベースユニット（db-unit）はこのメッセージを受け取り、SQLiteへ内容を書き込みます。

docker exec -it modt-broker mosquitto_pub -t "modt/state/set" -m "{\`"user_id\`": \`"user001\`", \`"key\`": \`"theme\`", \`"value\`": \`"dark\`", \`"timestamp\`": \`"2025-12-31T16:00:00\`"}"

---

## 3. ユーザー状態の取得 (GET)

保存されている値を呼び出すためのリクエストコマンドです。このメッセージを送信した後、監視用ターミナルで返信用トピック（modt/state/value）に結果が流れるのを確認してください。

docker exec -it modt-broker mosquitto_pub -t "modt/state/get" -m "{\`"user_id\`": \`"user001\`", \`"key\`": \`"theme\`", \`"timestamp\`": \`"2025-12-31T16:00:00\`"}"

---

## 4. ユーザー保有キーの一覧照会 (KEYS QUERY)

対象のユーザーが現在どのような設定項目を持っているかを一括で確認したい場合に使用します。

docker exec -it modt-broker mosquitto_pub -t "modt/state/keys/query" -m "{\`"user_id\`": \`"user001\`", \`"timestamp\`": \`"2025-12-31T16:00:00\`"}"