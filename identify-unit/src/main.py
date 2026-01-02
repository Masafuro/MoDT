import os
import uuid
import asyncio
from datetime import datetime
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# 分割された新SDKパッケージのインポート
from common import modt

app = FastAPI()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# .env から設定を読み込み
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
IDENTIFY_PUBLIC_URL = os.getenv("IDENTIFY_PUBLIC_URL", "http://localhost:5000")

# データベース接続設定
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 状態管理用の辞書
ready_apps = {}      # リダイレクト待ちのセッション (session_id -> redirect_url)
active_sessions = {} # ログイン済みの有効なセッション情報 (session_id -> {user_id, role})

def on_connect(client, userdata, flags, rc):
    """
    ブローカー接続成功時に呼ばれるコールバック。
    SDKの定数を使用して、必要なトピックを一括購読します。
    """
    if rc == 0:
        modt.logger.info("Identify Unit connected to MQTT broker.")
        client.subscribe([
            (modt.TOPIC_APP_READY, 0),
            (modt.TOPIC_SESSION_QUERY, 0)
        ])
    else:
        modt.logger.error(f"Identify Unit connection failed with code {rc}")

def on_message(client, userdata, msg):
    """MQTTメッセージ受信時の処理。"""
    data, error = modt.parse_payload(msg.payload.decode())
    if error:
        modt.logger.error(f"Payload Error: {error}")
        return

    # 1. アプリ準備完了通知の処理 (リダイレクトフロー)
    if msg.topic == modt.TOPIC_APP_READY:
        s_id = data.get("session_id")
        redirect_url = data.get("redirect_url")
        if s_id and redirect_url:
            ready_apps[s_id] = redirect_url
            modt.logger.info(f"Session {s_id} ready to redirect to {redirect_url}")

    # 2. セッション照会リクエストの処理 (他ユニットからの身分確認)
    elif msg.topic == modt.TOPIC_SESSION_QUERY:
        query_sid = data.get("session_id")
        modt.logger.info(f"Session query received for: {query_sid}")
        
        session_info = active_sessions.get(query_sid)
        if session_info:
            res_payload = modt.create_session_info_payload(
                session_id=query_sid,
                user_id=session_info["user_id"],
                role=session_info["role"],
                status="valid"
            )
        else:
            res_payload = modt.create_session_info_payload(
                session_id=query_sid,
                status="invalid"
            )
        
        client.publish(modt.TOPIC_SESSION_INFO, res_payload)

# MQTTクライアントの初期化
mqtt_client = modt.get_mqtt_client(client_id="identify-unit-service")
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

@app.on_event("startup")
def startup_event():
    """FastAPI起動時にMQTT接続を開始し、バックグラウンドループを起動します。"""
    try:
        modt.connect_broker(mqtt_client)
        # Webサーバーの裏でMQTTパケット処理を継続させるために必須
        mqtt_client.loop_start()
        modt.logger.info("MQTT background loop started in Identify Unit.")
    except Exception as e:
        modt.logger.error(f"MQTT Startup Error: {e}")

@app.on_event("shutdown")
def shutdown_event():
    """シャットダウン時にMQTT接続を安全に終了します。"""
    mqtt_client.loop_stop()
    modt.disconnect_broker(mqtt_client)

@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "username": "", "error": None})

@app.get("/register", response_class=HTMLResponse)
def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "username": "", "error": None})

@app.post("/register")
def post_register(request: Request, username: str = Form(...), password: str = Form(...)):
    if len(password) < 8:
        return templates.TemplateResponse("register.html", {"request": request, "username": username, "error": "パスワードは8文字以上で入力してください"})
    
    db = SessionLocal()
    hashed_password = pwd_context.hash(password)
    try:
        db.execute(text("INSERT INTO users (username, password_hash) VALUES (:u, :p)"), {"u": username, "p": hashed_password})
        db.commit()
        return RedirectResponse(url="/login", status_code=303)
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("register.html", {"request": request, "username": username, "error": "そのユーザー名は使用できません"})
    finally:
        db.close()

@app.post("/login")
def post_login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.execute(text("SELECT id, username, password_hash, role FROM users WHERE username = :u"), {"u": username}).fetchone()
    db.close()
    
    if user and pwd_context.verify(password, user.password_hash):
        session_id = str(uuid.uuid4())
        user_id_str = str(user.id)
        
        active_sessions[session_id] = {
            "user_id": user_id_str,
            "role": user.role
        }
        
        # 認証成功イベントを発行 (SDKの定数を利用)
        payload = modt.create_auth_success_payload(user_id_str, session_id, user.role)
        mqtt_client.publish(modt.TOPIC_AUTH_SUCCESS, payload)
        
        response = RedirectResponse(url=f"/waiting?session_id={session_id}", status_code=303)
        response.set_cookie(
            key="modt_session_id", 
            value=session_id, 
            httponly=True, 
            samesite="lax",
            path="/"
        )
        return response
    
    return templates.TemplateResponse("login.html", {"request": request, "username": username, "error": "認証に失敗しました"})

@app.get("/waiting", response_class=HTMLResponse)
def get_waiting(request: Request, session_id: str):
    return templates.TemplateResponse("waiting.html", {"request": request, "session_id": session_id})

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    modt.logger.info(f"WebSocket connected: session_id = {session_id}")
    try:
        while True:
            if session_id in ready_apps:
                redirect_url = ready_apps.pop(session_id)
                modt.logger.info(f"Match found for session {session_id}. Sending URL: {redirect_url}")
                await websocket.send_json({"ready": True, "url": redirect_url})
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        modt.logger.info(f"WebSocket disconnected for session: {session_id}")