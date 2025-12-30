import os
import uuid
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import paho.mqtt.client as mqtt

app = FastAPI()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# データベース接続設定
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# MQTT接続設定
MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "broker")

# Paho MQTT 2.0以降の仕様変更に対応するための初期化
try:
    # バージョン2.0以上の場合はCallback APIの指定が必要
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except AttributeError:
    # バージョン1.x系の場合は従来通りの初期化
    mqtt_client = mqtt.Client()

# 準備完了したアプリの情報を保持する辞書
ready_apps = {}

def on_message(client, userdata, msg):
    print(f"--- MQTT Message Received on topic: {msg.topic} ---", flush=True)
    try:
        payload_str = msg.payload.decode()
        print(f"Payload Content: {payload_str}", flush=True)
        data = json.loads(payload_str)
        
        if msg.topic == "modt/app/ready":
            # 規格に基づき、特定のキーのみを抽出します
            s_id = data.get("session_id")
            redirect_url = data.get("redirect_url")
            
            if s_id and redirect_url:
                ready_apps[s_id] = redirect_url
                print(f"Strict Match: Session {s_id} will be redirected to {redirect_url}", flush=True)
            else:
                print("Ignored: Missing required keys (session_id or redirect_url)", flush=True)
    except Exception as e:
        print(f"JSON Parse Error: {e}", flush=True)

@app.on_event("startup")
def startup_event():
    print(f"Connecting to MQTT Broker at {MQTT_HOST}...")
    try:
        mqtt_client.on_message = on_message
        mqtt_client.connect(MQTT_HOST, 1883, 60)
        mqtt_client.subscribe("modt/app/ready")
        mqtt_client.loop_start()
        print("MQTT Connection and subscription successful.")
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
        print(f"New user registered: {username}")
        return RedirectResponse(url="/login", status_code=303)
    except Exception as e:
        db.rollback()
        print(f"Registration DB error: {e}")
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
        payload = {"user_id": str(user.id), "role": user.role, "session_id": session_id, "timestamp": datetime.utcnow().isoformat()}
        print(f"Login successful for {username}. Publishing auth success event.")
        try:
            mqtt_client.publish("modt/auth/success", json.dumps(payload))
        except Exception as e:
            print(f"Failed to publish auth success: {e}")
        return RedirectResponse(url=f"/waiting?session_id={session_id}", status_code=303)
    
    print(f"Login failed for {username}")
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
            # メモリ上の ready_apps にリダイレクト先が登録されたか監視
            if session_id in ready_apps:
                redirect_url = ready_apps.pop(session_id)
                print(f"Match found for session {session_id}. Sending URL: {redirect_url}")
                await websocket.send_json({"ready": True, "url": redirect_url})
                break
            # サーバーに負荷をかけないよう小休止
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session: {session_id}")