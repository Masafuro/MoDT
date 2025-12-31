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

# 自作SDK（common/modt.py）のインポート
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

def on_message(client, userdata, msg):
    """MQTTメッセージ受信時の処理。"""
    data, error = modt.parse_payload(msg.payload.decode())
    if error:
        print(f"Payload Error: {error}", flush=True)
        return

    # 1. アプリ準備完了通知の処理 (リダイレクトフロー)
    if msg.topic == "modt/app/ready":
        s_id = data.get("session_id")
        redirect_url = data.get("redirect_url")
        if s_id and redirect_url:
            ready_apps[s_id] = redirect_url
            print(f"Session {s_id} registered for redirection to {redirect_url}.", flush=True)

    # 2. セッション照会リクエストの処理 (他ユニットからの身分確認)
    elif msg.topic == "modt/session/query":
        query_sid = data.get("session_id")
        print(f"Session query received for: {query_sid}", flush=True)
        
        session_info = active_sessions.get(query_sid)
        if session_info:
            # 有効なセッション情報を返信
            res_payload = modt.create_session_info_payload(
                session_id=query_sid,
                user_id=session_info["user_id"],
                role=session_info["role"],
                status="valid"
            )
        else:
            # 無効または存在しないセッションとして返信
            res_payload = modt.create_session_info_payload(
                session_id=query_sid,
                status="invalid"
            )
        
        client.publish("modt/session/info", res_payload)

# SDKを利用したMQTTクライアントの初期化
mqtt_client = modt.get_mqtt_client()
mqtt_client.on_message = on_message

@app.on_event("startup")
def startup_event():
    """起動時にブローカーへ接続し、必要なトピックを購読します。"""
    try:
        modt.connect_broker(mqtt_client)
        mqtt_client.subscribe("modt/app/ready")
        mqtt_client.subscribe("modt/session/query")
        print("MQTT Connection and subscriptions successful.")
    except Exception as e:
        print(f"MQTT Startup Error: {e}")

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
        
        # セッション情報をメモリ上に保持
        active_sessions[session_id] = {
            "user_id": user_id_str,
            "role": user.role
        }
        
        # 認証成功イベントを発行 (SDKを利用)
        payload = modt.create_auth_success_payload(user_id_str, session_id, user.role)
        mqtt_client.publish("modt/auth/success", payload)
        
        # クッキーをセットして待機画面へリダイレクト
        # 外部公開URL設定に基づき、セキュアなクッキーを発行します
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
    print(f"WebSocket connected: session_id = {session_id}")
    try:
        while True:
            if session_id in ready_apps:
                redirect_url = ready_apps.pop(session_id)
                print(f"Match found for session {session_id}. Sending URL: {redirect_url}")
                await websocket.send_json({"ready": True, "url": redirect_url})
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session: {session_id}")