from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import json

app = FastAPI(title="AlgoCards Cloud Sync API")

# Cấu hình CORS cho phép client web gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            wins INT DEFAULT 0,
            unlocked_cards TEXT DEFAULT '["STK-01", "QUE-01", "GRA-01"]'
        )
    """)
    conn.commit()
    conn.close()

init_db()

class UserAuthSchema(BaseModel):
    username: str
    password: str

class ProgressSchema(BaseModel):
    username: str
    wins: int
    unlocked_cards: list

@app.post("/api/register")
def register(user: UserAuthSchema):
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    try:
        default_cards = json.dumps(["STK-01", "QUE-01", "GRA-01"])
        cursor.execute("INSERT INTO users (username, password, unlocked_cards) VALUES (?, ?, ?)", 
                       (user.username, user.password, default_cards))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Tài khoản đã tồn tại!")
    finally:
        conn.close()
    return {"status": "success", "message": "Đăng ký tài khoản thành công!"}

@app.post("/api/login")
def login(user: UserAuthSchema):
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute("SELECT wins, unlocked_cards FROM users WHERE username = ? AND password = ?", 
                   (user.username, user.password))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu!")
    
    return {
        "status": "success",
        "username": user.username,
        "wins": row[0],
        "unlocked_cards": json.loads(row[1])
    }

@app.post("/api/progress/save")
def save_progress(prog: ProgressSchema):
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET wins = ?, unlocked_cards = ? WHERE username = ?",
                   (prog.wins, json.dumps(prog.unlocked_cards), prog.username))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã lưu tiến độ thành công lên Cloud!"}
@app.get("/")
def read_root():
    return {"message": "Welcome to AlgoCards API Server is running!"}