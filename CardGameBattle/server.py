from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import json

app = FastAPI(title="AlgoCards API Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect("game_progress.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            deck_data TEXT DEFAULT '[]',
            unlocked_cards TEXT DEFAULT '["46986414", "89631139", "STK-01", "GRA-01", "QUE-01", "DP-01"]'
        )
    """)
    conn.commit()
    conn.close()

init_db()

class UserAuth(BaseModel):
    username: str
    password: str

class ProgressSync(BaseModel):
    username: str
    deck_data: str
    unlocked_cards: str

@app.post("/api/register")
def register(data: UserAuth):
    conn = sqlite3.connect("game_progress.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (data.username,))
    if cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "Tai khoan da ton tai!"}

    cursor.execute(
        "INSERT INTO users (username, password, deck_data, unlocked_cards) VALUES (?, ?, ?, ?)",
        (data.username, data.password, "[]", "[]")
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Dang ky thanh cong! Hay dang nhap."}

@app.post("/api/login")
def login(data: UserAuth):
    conn = sqlite3.connect("game_progress.db")
    cursor = conn.cursor()
    cursor.execute("SELECT deck_data, unlocked_cards FROM users WHERE username = ? AND password = ?", (data.username, data.password))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"status": "error", "message": "Sai tài khoản hoặc mật khẩu!"}
    
    try:
        saved_deck = json.loads(row[0]) if row[0].startswith('[') else eval(row[0])
        saved_cards = json.loads(row[1]) if row[1].startswith('[') else eval(row[1])
    except Exception:
        saved_deck, saved_cards = [], []

    return {
        "status": "success", 
        "message": "Đăng nhập thành công!", 
        "deck_data": saved_deck, 
        "unlocked_cards": saved_cards
    }

@app.post("/api/sync")
def sync_progress(data: ProgressSync):
    conn = sqlite3.connect("game_progress.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET deck_data = ?, unlocked_cards = ? WHERE username = ?",
                   (data.deck_data, data.unlocked_cards, data.username))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã đồng bộ bộ bài lên Server thành công!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)