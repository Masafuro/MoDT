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