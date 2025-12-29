# MoDT
MQTTを基盤とした、Dockerコンテナによるポン付け可能な疎結合アプリケーションフレームワーク

## 開発方針
- 各モジュールはdockerイメージになること
- 各モジュールはmqttによる通信によって連携すること
- VPSを想定し、mosquittoを内部のみに開くこと

## 開発概要
- broker
  - mosquittoの設定ファイル等
  - docker-compose.ymlによってmosquittoが組み込まれる。
- monitor
  - redisに流れてきたデータを格納する。