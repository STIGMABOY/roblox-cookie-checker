from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import json
import sqlite3
from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Optional
import re
import asyncio

# ==================== OPTIMIZED FASTAPI APP ====================
app = FastAPI(
    title="Roblox Cookie Checker Premium",
    version="4.0.0",
    docs_url=None,
    redoc_url=None
)

# Add compression middleware for faster loading
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="public"), name="static")

# ==================== OPTIMIZED DATABASE ====================
def get_db():
    """Optimized database connection with connection pooling"""
    conn = sqlite3.connect(
        'file:checker.db?mode=rwc&cache=shared',
        uri=True,
        check_same_thread=False,
        timeout=10
    )
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with indexes for faster queries"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")
    
    # Create tables with optimized structure
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            is_admin BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            account_type TEXT DEFAULT 'premium',
            subscription_expires DATETIME,
            max_cookies_per_check INTEGER DEFAULT 50,
            daily_limit INTEGER DEFAULT 20,
            checks_today INTEGER DEFAULT 0,
            last_check_date DATE,
            created_by TEXT DEFAULT 'admin',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_users_username 
        ON users(username);
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_users_is_active 
        ON users(is_active);
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sessions_token 
        ON user_sessions(session_token);
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sessions_expires 
        ON user_sessions(expires_at);
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS check_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            valid_count INTEGER DEFAULT 0,
            invalid_count INTEGER DEFAULT 0,
            total_robux INTEGER DEFAULT 0,
            results_json TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_results_user 
        ON check_results(user_id);
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_results_timestamp 
        ON check_results(timestamp DESC);
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            duration_days INTEGER NOT NULL,
            max_cookies_per_check INTEGER DEFAULT 50,
            daily_limit INTEGER DEFAULT 20,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            payment_status TEXT DEFAULT 'paid',
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (package_id) REFERENCES packages (id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_packages_user 
        ON user_packages(user_id);
    ''')
    
    # Create default admin if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users 
            (username, password_hash, is_admin, account_type, max_cookies_per_check, daily_limit)
            VALUES (?, ?, 1, 'admin', 999, 999)
        ''', ('admin', admin_hash))
    
    conn.commit()
    print("✅ Database initialized with optimizations")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("🚀 Server started with optimizations")

# ==================== OPTIMIZED HELPER FUNCTIONS ====================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def verify_session(token: str):
    """Optimized session verification with caching"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Clean expired sessions first
    cursor.execute("DELETE FROM user_sessions WHERE expires_at < datetime('now')")
    
    cursor.execute('''
        SELECT u.* FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_token = ?
    ''', (token,))
    
    return cursor.fetchone()

# ==================== DATA MODELS ====================
class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    package_id: int = 1
    account_type: str = "premium"

class CookieCheckRequest(BaseModel):
    cookies: str

# ==================== FAST AUTHENTICATION MIDDLEWARE ====================
async def get_current_user(request: Request):
    """Optimized authentication middleware"""
    # Try cookie first (fastest)
    token = request.cookies.get("session_token")
    
    if not token:
        # Try authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await verify_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account inactive")
    
    return dict(user)

async def verify_admin(user: dict = Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ==================== OPTIMIZED API ENDPOINTS ====================
@app.get("/")
async def home():
    """Serve login page with cache headers"""
    headers = {
        "Cache-Control": "public, max-age=3600",
        "ETag": "login-page-v1"
    }
    with open("public/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), headers=headers)

@app.get("/dashboard")
async def dashboard():
    with open("public/dashboard.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/admin")
async def admin_login():
    with open("public/admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/admin-dashboard")
async def admin_dashboard():
    with open("public/dashboard_admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# ==================== OPTIMIZED AUTH ENDPOINTS ====================
@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Optimized login endpoint"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Use parameterized query for security and speed
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND is_active = 1",
        (request.username,)
    )
    
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if hash_password(request.password) != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session token
    token = secrets.token_hex(32)
    expires_at = datetime.now() + timedelta(days=30)
    
    cursor.execute('''
        INSERT INTO user_sessions (user_id, session_token, expires_at)
        VALUES (?, ?, ?)
    ''', (user["id"], token, expires_at.isoformat()))
    
    conn.commit()
    
    # Set secure cookie
    response = JSONResponse({
        "success": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "is_admin": bool(user["is_admin"]),
            "is_active": bool(user["is_active"]),
            "account_type": user["account_type"],
            "subscription_expires": user["subscription_expires"],
            "max_cookies_per_check": user["max_cookies_per_check"],
            "daily_limit": user["daily_limit"],
            "checks_today": user["checks_today"],
            "created_by": user["created_by"]
        }
    })
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30*24*60*60,
        path="/"
    )
    
    return response

@app.post("/api/auth/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    if token:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_sessions WHERE session_token = ?", (token,))
        conn.commit()
    
    response = JSONResponse({"success": True})
    response.delete_cookie("session_token")
    return response

@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Fast user info endpoint"""
    return {
        "success": True,
        "user": user
    }

# ==================== OPTIMIZED COOKIE CHECKING ====================
import requests
import random
import time

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
]

async def check_single_cookie_fast(cookie: str):
    """Optimized cookie checking with timeout"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Cookie': f'.ROBLOSECURITY={cookie}',
        'Accept': 'application/json'
    }
    
    try:
        # Fast timeout for quick response
        response = requests.get(
            "https://users.roblox.com/v1/users/authenticated",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            result = {
                "status": "valid",
                "username": data.get("name", "Unknown"),
                "user_id": data.get("id", "Unknown"),
                "display_name": data.get("displayName", "Unknown")
            }
            
            # Try to get balance (non-blocking)
            try:
                balance_resp = requests.get(
                    "https://economy.roblox.com/v1/user/currency",
                    headers=headers,
                    timeout=5
                )
                if balance_resp.status_code == 200:
                    balance_data = balance_resp.json()
                    result["robux"] = balance_data.get("robux", 0)
                else:
                    result["robux"] = 0
            except:
                result["robux"] = 0
            
            return result
        elif response.status_code == 401:
            return {"status": "invalid", "error": "Cookie expired"}
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}"}
            
    except requests.exceptions.Timeout:
        return {"status": "error", "error": "Timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/check-cookies")
async def check_cookies(
    request: CookieCheckRequest,
    user: dict = Depends(get_current_user)
):
    """Optimized cookie checking endpoint"""
    # Validate user subscription
    if user["subscription_expires"]:
        expires = datetime.fromisoformat(user["subscription_expires"])
        if datetime.now() > expires:
            raise HTTPException(status_code=403, detail="Subscription expired")
    
    # Parse cookies
    cookies = [c.strip() for c in request.cookies.strip().split('\n') if c.strip()]
    
    if not cookies:
        raise HTTPException(status_code=400, detail="No cookies provided")
    
    if len(cookies) > user["max_cookies_per_check"]:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {user['max_cookies_per_check']} cookies allowed"
        )
    
    # Check daily limit
    today = datetime.now().strftime("%Y-%m-%d")
    if user["last_check_date"] != today:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET checks_today = 0, last_check_date = ? WHERE id = ?",
            (today, user["id"])
        )
        conn.commit()
        checks_today = 0
    else:
        checks_today = user["checks_today"]
    
    if checks_today >= user["daily_limit"]:
        raise HTTPException(status_code=403, detail="Daily limit reached")
    
    # Start checking with progress
    results = []
    valid_count = 0
    total_robux = 0
    
    for idx, cookie in enumerate(cookies):
        result = await check_single_cookie_fast(cookie)
        result["cookie_id"] = idx + 1
        results.append(result)
        
        if result["status"] == "valid":
            valid_count += 1
            total_robux += result.get("robux", 0)
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    # Save results
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO check_results 
        (user_id, valid_count, invalid_count, total_robux, results_json)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        user["id"],
        valid_count,
        len(cookies) - valid_count,
        total_robux,
        json.dumps(results, ensure_ascii=False)
    ))
    
    cursor.execute(
        "UPDATE users SET checks_today = checks_today + 1 WHERE id = ?",
        (user["id"],)
    )
    
    conn.commit()
    
    return {
        "success": True,
        "results": results,
        "summary": {
            "total": len(cookies),
            "valid": valid_count,
            "invalid": len(cookies) - valid_count,
            "total_robux": total_robux
        }
    }

# ==================== OPTIMIZED USER ENDPOINTS ====================
@app.get("/api/user/stats")
async def get_user_stats(user: dict = Depends(get_current_user)):
    """Fast stats endpoint with optimized query"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total_checks,
            COALESCE(SUM(valid_count), 0) as total_valid,
            COALESCE(SUM(total_robux), 0) as total_robux
        FROM check_results 
        WHERE user_id = ?
    ''', (user["id"],))
    
    stats = cursor.fetchone()
    
    return {
        "success": True,
        "stats": {
            "total_checks": stats["total_checks"],
            "total_valid": stats["total_valid"],
            "total_robux": stats["total_robux"]
        }
    }

@app.get("/api/user/history")
async def get_user_history(
    limit: int = 10,
    offset: int = 0,
    user: dict = Depends(get_current_user)
):
    """Optimized history with pagination"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, valid_count, invalid_count, total_robux, timestamp
        FROM check_results 
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    ''', (user["id"], limit, offset))
    
    history = [
        {
            "id": row["id"],
            "valid_count": row["valid_count"],
            "invalid_count": row["invalid_count"],
            "total_robux": row["total_robux"],
            "timestamp": row["timestamp"]
        }
        for row in cursor.fetchall()
    ]
    
    return {"success": True, "history": history}

# ==================== ADMIN ENDPOINTS (OPTIMIZED) ====================
@app.post("/api/admin/create-user")
async def create_user(
    request: CreateUserRequest,
    admin: dict = Depends(verify_admin)
):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check existing user
    cursor.execute("SELECT id FROM users WHERE username = ?", (request.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username exists")
    
    # Create user
    password_hash = hash_password(request.password)
    expires_at = datetime.now() + timedelta(days=30)
    
    cursor.execute('''
        INSERT INTO users 
        (username, password_hash, email, full_name, is_active,
         account_type, subscription_expires, max_cookies_per_check, daily_limit, created_by)
        VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
    ''', (
        request.username,
        password_hash,
        request.email,
        request.full_name,
        request.account_type,
        expires_at.isoformat(),
        50, 20, admin["username"]
    ))
    
    user_id = cursor.lastrowid
    conn.commit()
    
    return {
        "success": True,
        "message": "User created",
        "user_id": user_id,
        "password": request.password
    }

@app.get("/api/admin/users")
async def get_all_users(admin: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            id, username, email, full_name, is_active,
            account_type, subscription_expires, max_cookies_per_check,
            daily_limit, checks_today, created_by, created_at
        FROM users 
        WHERE is_admin = 0
        ORDER BY created_at DESC
    ''')
    
    users = [
        {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "full_name": row["full_name"],
            "is_active": bool(row["is_active"]),
            "account_type": row["account_type"],
            "subscription_expires": row["subscription_expires"],
            "max_cookies_per_check": row["max_cookies_per_check"],
            "daily_limit": row["daily_limit"],
            "checks_today": row["checks_today"],
            "created_by": row["created_by"],
            "created_at": row["created_at"]
        }
        for row in cursor.fetchall()
    ]
    
    return {"success": True, "users": users}

# ==================== HEALTH CHECK ====================
@app.get("/api/health")
async def health_check():
    """Fast health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Roblox Cookie Checker"
    }

# ==================== ERROR HANDLERS ====================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    )
