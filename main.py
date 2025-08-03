from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import jwt
import bcrypt
import sqlite3
import os
from datetime import datetime, timedelta

app = FastAPI(title="Notes App API", description="A secure RESTful API for personal note management")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"

# Database setup
DATABASE = "notes.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Notes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class NoteCreate(BaseModel):
    title: str
    content: str

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class Note(BaseModel):
    id: int
    title: str
    content: str
    user_id: int
    created_at: str
    updated_at: str

class User(BaseModel):
    id: int
    username: str
    email: str
    created_at: str

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# API Routes
@app.get("/")
async def root():
    return {"message": "Notes App API", "version": "1.0.0"}

@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (user.username, user.email))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Create new user
    hashed_password = hash_password(user.password)
    cursor.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (user.username, user.email, hashed_password)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/login")
async def login_user(user: UserLogin):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (user.username,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or not verify_password(user.password, result[1]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": result[0]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/notes", response_model=List[Note])
async def get_notes(current_user: int = Depends(get_current_user)):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, title, content, user_id, created_at, updated_at FROM notes WHERE user_id = ? ORDER BY updated_at DESC",
        (current_user,)
    )
    notes = cursor.fetchall()
    conn.close()
    
    return [
        Note(
            id=note[0],
            title=note[1],
            content=note[2],
            user_id=note[3],
            created_at=note[4],
            updated_at=note[5]
        ) for note in notes
    ]

@app.post("/notes", response_model=Note, status_code=status.HTTP_201_CREATED)
async def create_note(note: NoteCreate, current_user: int = Depends(get_current_user)):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO notes (title, content, user_id) VALUES (?, ?, ?)",
        (note.title, note.content, current_user)
    )
    conn.commit()
    note_id = cursor.lastrowid
    
    cursor.execute(
        "SELECT id, title, content, user_id, created_at, updated_at FROM notes WHERE id = ?",
        (note_id,)
    )
    created_note = cursor.fetchone()
    conn.close()
    
    return Note(
        id=created_note[0],
        title=created_note[1],
        content=created_note[2],
        user_id=created_note[3],
        created_at=created_note[4],
        updated_at=created_note[5]
    )

@app.get("/notes/{note_id}", response_model=Note)
async def get_note(note_id: int, current_user: int = Depends(get_current_user)):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, title, content, user_id, created_at, updated_at FROM notes WHERE id = ? AND user_id = ?",
        (note_id, current_user)
    )
    note = cursor.fetchone()
    conn.close()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return Note(
        id=note[0],
        title=note[1],
        content=note[2],
        user_id=note[3],
        created_at=note[4],
        updated_at=note[5]
    )

@app.put("/notes/{note_id}", response_model=Note)
async def update_note(note_id: int, note_update: NoteUpdate, current_user: int = Depends(get_current_user)):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if note exists and belongs to user
    cursor.execute("SELECT id FROM notes WHERE id = ? AND user_id = ?", (note_id, current_user))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Update note
    update_fields = []
    update_values = []
    
    if note_update.title is not None:
        update_fields.append("title = ?")
        update_values.append(note_update.title)
    
    if note_update.content is not None:
        update_fields.append("content = ?")
        update_values.append(note_update.content)
    
    if update_fields:
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.append(note_id)
        update_values.append(current_user)
        
        cursor.execute(
            f"UPDATE notes SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?",
            update_values
        )
        conn.commit()
    
    # Get updated note
    cursor.execute(
        "SELECT id, title, content, user_id, created_at, updated_at FROM notes WHERE id = ?",
        (note_id,)
    )
    updated_note = cursor.fetchone()
    conn.close()
    
    return Note(
        id=updated_note[0],
        title=updated_note[1],
        content=updated_note[2],
        user_id=updated_note[3],
        created_at=updated_note[4],
        updated_at=updated_note[5]
    )

@app.delete("/notes/{note_id}")
async def delete_note(note_id: int, current_user: int = Depends(get_current_user)):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, current_user))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Note deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

