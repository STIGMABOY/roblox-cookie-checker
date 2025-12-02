from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import sqlite3
from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Optional, List
import re

app = FastAPI(
    title="Roblox Cookie Checker Premium",
    description="Sistem premium dengan admin control penuh",
    version="3.0.0"
)

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

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect('premium_checker.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table - Hanya admin yang bisa membuat akun
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            is_admin BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            account_type TEXT DEFAULT 'premium',  -- premium, trial, basic
            subscription_expires DATETIME,
            max_cookies_per_check INTEGER DEFAULT 50,
            daily_limit INTEGER DEFAULT 20,
            checks_today INTEGER DEFAULT 0,
            last_check_date DATE,
            created_by TEXT DEFAULT 'admin',  -- Admin yang membuat akun ini
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # User sessions
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
    
    # Check results
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
    
    # Payments/packages table
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
    
    # User packages/payments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            payment_status TEXT DEFAULT 'paid',  -- paid, pending, expired
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (package_id) REFERENCES packages (id)
        )
    ''')
    
    # Usage logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Insert default admin jika belum ada
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_hash = hash_password("admin123")
        cursor.execute('''
            INSERT INTO users 
            (username, password_hash, is_admin, account_type, max_cookies_per_check, daily_limit)
            VALUES (?, ?, 1, 'admin', 999, 999)
        ''', ('admin', admin_hash))
        print("✅ Default admin created: admin / admin123")
    
    # Insert default packages
    cursor.execute("SELECT COUNT(*) FROM packages")
    if cursor.fetchone()[0] == 0:
        packages = [
            ('Trial 3 Hari', 0, 3, 10, 3),
            ('Paket Basic (1 Bulan)', 100000, 30, 100, 50),
            ('Paket Premium (3 Bulan)', 250000, 90, 500, 200),
            ('Paket Enterprise (1 Tahun)', 800000, 365, 1000, 500)
        ]
        
        for pkg in packages:
            cursor.execute('''
                INSERT INTO packages (name, price, duration_days, max_cookies_per_check, daily_limit)
                VALUES (?, ?, ?, ?, ?)
            ''', pkg)
        print("✅ Default packages created")
    
    conn.commit()
    print("✅ Database initialized successfully")

@app.on_event("startup")
async def startup_event():
    init_db()

# Data models
class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    package_id: int = 1  # Default: Trial package
    account_type: str = "premium"

class UpdateUserRequest(BaseModel):
    user_id: int
    is_active: Optional[bool] = None
    account_type: Optional[str] = None
    subscription_days: Optional[int] = None
    max_cookies_per_check: Optional[int] = None
    daily_limit: Optional[int] = None

class CookieCheckRequest(BaseModel):
    cookies: str

# Dependency untuk authentication
async def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Belum login")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.* FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_token = ? AND s.expires_at > datetime('now')
    ''', (token,))
    
    session = cursor.fetchone()
    if not session:
        raise HTTPException(status_code=401, detail="Sesi telah berakhir")
    
    # Check if account is active
    if not session["is_active"]:
        raise HTTPException(status_code=403, detail="Akun tidak aktif")
    
    return dict(session)

# Dependency untuk admin only
async def verify_admin(user: dict = Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Hanya admin yang bisa mengakses")
    return user

# ==================== AUTHENTICATION ENDPOINTS ====================
@app.post("/api/auth/login")
async def login(request: LoginRequest, response: JSONResponse):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM users WHERE username = ?
    ''', (request.username,))
    
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Akun tidak aktif. Hubungi admin.")
    
    if hash_password(request.password) != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    # Create session token
    token = secrets.token_hex(32)
    expires_at = datetime.now() + timedelta(days=30)
    
    cursor.execute('''
        INSERT INTO user_sessions (user_id, session_token, expires_at)
        VALUES (?, ?, ?)
    ''', (user["id"], token, expires_at.isoformat()))
    
    # Log login
    cursor.execute('''
        INSERT INTO usage_logs (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (user["id"], "login", "User logged in"))
    
    conn.commit()
    
    # Set cookie
    response = JSONResponse({
        "success": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "is_admin": bool(user["is_admin"]),
            "account_type": user["account_type"]
        }
    })
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=30*24*60*60,
        samesite="lax",
        secure=False  # Set True jika menggunakan HTTPS
    )
    
    return response

@app.post("/api/auth/logout")
async def logout(request: Request, response: JSONResponse):
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
async def get_current_user_info(user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "is_admin": bool(user["is_admin"]),
            "is_active": bool(user["is_active"]),
            "account_type": user["account_type"],
            "subscription_expires": user["subscription_expires"],
            "max_cookies_per_check": user["max_cookies_per_check"],
            "daily_limit": user["daily_limit"],
            "checks_today": user["checks_today"],
            "created_by": user["created_by"]
        }
    }

# ==================== ADMIN ENDPOINTS ====================
@app.post("/api/admin/create-user")
async def create_user(
    request: CreateUserRequest,
    admin: dict = Depends(verify_admin)
):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if username exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (request.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username sudah terdaftar")
    
    # Get package info
    cursor.execute("SELECT * FROM packages WHERE id = ?", (request.package_id,))
    package = cursor.fetchone()
    if not package:
        raise HTTPException(status_code=400, detail="Package tidak ditemukan")
    
    # Calculate expiration
    expires_at = datetime.now() + timedelta(days=package["duration_days"])
    
    # Create user
    password_hash = hash_password(request.password)
    
    cursor.execute('''
        INSERT INTO users 
        (username, password_hash, email, full_name, is_admin, is_active,
         account_type, subscription_expires, max_cookies_per_check, daily_limit, created_by)
        VALUES (?, ?, ?, ?, 0, 1, ?, ?, ?, ?, ?)
    ''', (
        request.username,
        password_hash,
        request.email,
        request.full_name,
        request.account_type,
        expires_at.isoformat(),
        package["max_cookies_per_check"],
        package["daily_limit"],
        admin["username"]
    ))
    
    user_id = cursor.lastrowid
    
    # Record user package
    cursor.execute('''
        INSERT INTO user_packages (user_id, package_id, expires_at)
        VALUES (?, ?, ?)
    ''', (user_id, request.package_id, expires_at.isoformat()))
    
    # Log action
    cursor.execute('''
        INSERT INTO usage_logs (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (admin["id"], "create_user", json.dumps({
        "created_user": request.username,
        "package": package["name"],
        "expires_at": expires_at.isoformat()
    })))
    
    conn.commit()
    
    return {
        "success": True,
        "message": f"User {request.username} berhasil dibuat",
        "user": {
            "id": user_id,
            "username": request.username,
            "email": request.email,
            "package": package["name"],
            "expires_at": expires_at.isoformat(),
            "max_cookies": package["max_cookies_per_check"],
            "daily_limit": package["daily_limit"]
        }
    }

@app.get("/api/admin/users")
async def get_all_users(admin: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.id, u.username, u.email, u.full_name, u.is_active,
            u.account_type, u.subscription_expires, u.max_cookies_per_check,
            u.daily_limit, u.checks_today, u.created_by, u.created_at,
            p.name as package_name
        FROM users u
        LEFT JOIN user_packages up ON u.id = up.user_id
        LEFT JOIN packages p ON up.package_id = p.id
        WHERE u.is_admin = 0
        ORDER BY u.created_at DESC
    ''')
    
    users = []
    for row in cursor.fetchall():
        # Check subscription status
        is_expired = False
        if row["subscription_expires"]:
            expires = datetime.fromisoformat(row["subscription_expires"])
            is_expired = datetime.now() > expires
        
        users.append({
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "full_name": row["full_name"],
            "is_active": bool(row["is_active"]),
            "account_type": row["account_type"],
            "subscription_expires": row["subscription_expires"],
            "subscription_status": "active" if not is_expired else "expired",
            "max_cookies_per_check": row["max_cookies_per_check"],
            "daily_limit": row["daily_limit"],
            "checks_today": row["checks_today"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "package_name": row["package_name"]
        })
    
    return {"users": users}

@app.post("/api/admin/update-user")
async def update_user(
    request: UpdateUserRequest,
    admin: dict = Depends(verify_admin)
):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE id = ?", (request.user_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    # Build update query
    updates = []
    params = []
    
    if request.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if request.is_active else 0)
    
    if request.account_type:
        updates.append("account_type = ?")
        params.append(request.account_type)
    
    if request.subscription_days is not None:
        new_expiry = datetime.now() + timedelta(days=request.subscription_days)
        updates.append("subscription_expires = ?")
        params.append(new_expiry.isoformat())
    
    if request.max_cookies_per_check is not None:
        updates.append("max_cookies_per_check = ?")
        params.append(request.max_cookies_per_check)
    
    if request.daily_limit is not None:
        updates.append("daily_limit = ?")
        params.append(request.daily_limit)
    
    if updates:
        updates.append("updated_at = datetime('now')")
        params.append(request.user_id)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        
        # Log action
        cursor.execute('''
            INSERT INTO usage_logs (user_id, action, details)
            VALUES (?, ?, ?)
        ''', (admin["id"], "update_user", json.dumps({
            "user_id": request.user_id,
            "updates": updates
        })))
        
        conn.commit()
    
    return {"success": True, "message": "User berhasil diupdate"}

@app.post("/api/admin/reset-password/{user_id}")
async def reset_user_password(
    user_id: int,
    new_password: str = "123456",  # Default password
    admin: dict = Depends(verify_admin)
):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    new_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    
    # Log action
    cursor.execute('''
        INSERT INTO usage_logs (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (admin["id"], "reset_password", json.dumps({
        "target_user_id": user_id,
        "username": user["username"]
    })))
    
    conn.commit()
    
    return {
        "success": True,
        "message": f"Password untuk {user['username']} telah direset",
        "new_password": new_password
    }

@app.get("/api/admin/stats")
async def get_admin_stats(admin: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    # Total users
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
    total_users = cursor.fetchone()[0]
    
    # Active users
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0 AND is_active = 1")
    active_users = cursor.fetchone()[0]
    
    # Total checks
    cursor.execute("SELECT COUNT(*) FROM check_results")
    total_checks = cursor.fetchone()[0]
    
    # Total valid cookies
    cursor.execute("SELECT SUM(valid_count) FROM check_results")
    total_valid = cursor.fetchone()[0] or 0
    
    # Total robux
    cursor.execute("SELECT SUM(total_robux) FROM check_results")
    total_robux = cursor.fetchone()[0] or 0
    
    # Recent activity
    cursor.execute('''
        SELECT u.username, r.timestamp, r.valid_count, r.total_robux
        FROM check_results r
        JOIN users u ON r.user_id = u.id
        ORDER BY r.timestamp DESC
        LIMIT 10
    ''')
    
    recent_activity = []
    for row in cursor.fetchall():
        recent_activity.append({
            "username": row["username"],
            "timestamp": row["timestamp"],
            "valid_count": row["valid_count"],
            "total_robux": row["total_robux"]
        })
    
    # Package statistics
    cursor.execute('''
        SELECT p.name, COUNT(up.id) as user_count
        FROM packages p
        LEFT JOIN user_packages up ON p.id = up.package_id
        GROUP BY p.id
        ORDER BY p.price
    ''')
    
    package_stats = []
    for row in cursor.fetchall():
        package_stats.append({
            "name": row["name"],
            "user_count": row["user_count"]
        })
    
    return {
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "total_checks": total_checks,
            "total_valid_cookies": total_valid,
            "total_robux": total_robux
        },
        "recent_activity": recent_activity,
        "package_stats": package_stats
    }

# ==================== USER ENDPOINTS ====================
@app.get("/api/user/stats")
async def get_user_stats(user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    # User's check statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total_checks,
            SUM(valid_count) as total_valid,
            SUM(total_robux) as total_robux
        FROM check_results 
        WHERE user_id = ?
    ''', (user["id"],))
    
    stats = cursor.fetchone()
    
    # Check subscription status
    subscription_status = "active"
    if user["subscription_expires"]:
        expires = datetime.fromisoformat(user["subscription_expires"])
        if datetime.now() > expires:
            subscription_status = "expired"
    
    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")
    if user["last_check_date"] != today:
        # Reset daily count
        cursor.execute("UPDATE users SET checks_today = 0, last_check_date = ? WHERE id = ?", 
                      (today, user["id"]))
        conn.commit()
        checks_today = 0
    else:
        checks_today = user["checks_today"]
    
    # Get user's package info
    cursor.execute('''
        SELECT p.name FROM user_packages up
        JOIN packages p ON up.package_id = p.id
        WHERE up.user_id = ?
        ORDER BY up.created_at DESC
        LIMIT 1
    ''', (user["id"],))
    
    package = cursor.fetchone()
    
    return {
        "stats": {
            "total_checks": stats["total_checks"] or 0,
            "total_valid": stats["total_valid"] or 0,
            "total_robux": stats["total_robux"] or 0
        },
        "account": {
            "username": user["username"],
            "account_type": user["account_type"],
            "subscription_status": subscription_status,
            "subscription_expires": user["subscription_expires"],
            "max_cookies_per_check": user["max_cookies_per_check"],
            "daily_limit": user["daily_limit"],
            "checks_today": checks_today,
            "package": package["name"] if package else "Unknown"
        }
    }

@app.get("/api/user/history")
async def get_user_history(
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(get_current_user)
):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, valid_count, invalid_count, total_robux, timestamp
        FROM check_results 
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    ''', (user["id"], limit, offset))
    
    results = cursor.fetchall()
    
    history = []
    for row in results:
        history.append({
            "id": row["id"],
            "valid_count": row["valid_count"],
            "invalid_count": row["invalid_count"],
            "total_robux": row["total_robux"],
            "timestamp": row["timestamp"]
        })
    
    return {"history": history}

# ==================== COOKIE CHECKING ENDPOINT ====================
def check_single_cookie_api(cookie: str):
    """Check single cookie using API calls"""
    import requests
    import random
    import time
    
    # Clean cookie
    cookie = cookie.strip()
    if not cookie:
        return {"status": "invalid", "error": "Empty cookie"}
    
    if not cookie.startswith('_|WARNING:'):
        cookie = f"_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_{cookie}"
    
    headers = {
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        ]),
        'Cookie': f'.ROBLOSECURITY={cookie}',
        'Accept': 'application/json'
    }
    
    try:
        # Get user info
        response = requests.get(
            "https://users.roblox.com/v1/users/authenticated",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            user_data = response.json()
            result = {
                "status": "valid",
                "username": user_data.get("name", "Unknown"),
                "user_id": user_data.get("id", "Unknown"),
                "display_name": user_data.get("displayName", "Unknown")
            }
            
            # Get Robux balance
            try:
                balance_resp = requests.get(
                    "https://economy.roblox.com/v1/user/currency",
                    headers=headers,
                    timeout=10
                )
                if balance_resp.status_code == 200:
                    balance_data = balance_resp.json()
                    result["robux"] = balance_data.get("robux", 0)
                else:
                    result["robux"] = 0
            except:
                result["robux"] = 0
            
            # Get premium status
            try:
                premium_resp = requests.get(
                    "https://premiumfeatures.roblox.com/v1/users/premium/membership",
                    headers=headers,
                    timeout=10
                )
                if premium_resp.status_code == 200:
                    premium_data = premium_resp.json()
                    result["premium"] = premium_data.get("isPremium", False)
                else:
                    result["premium"] = False
            except:
                result["premium"] = False
            
            return result
            
        elif response.status_code == 401:
            return {"status": "invalid", "error": "Cookie expired/invalid"}
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/check-cookies")
async def check_cookies(
    request: CookieCheckRequest,
    user: dict = Depends(get_current_user)
):
    # Check subscription
    if user["subscription_expires"]:
        expires = datetime.fromisoformat(user["subscription_expires"])
        if datetime.now() > expires:
            raise HTTPException(status_code=403, detail="Subscription telah berakhir")
    
    # Check if account is active
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Akun tidak aktif")
    
    # Parse cookies
    cookies = [c.strip() for c in request.cookies.strip().split('\n') if c.strip()]
    
    if not cookies:
        raise HTTPException(status_code=400, detail="Tidak ada cookie yang dimasukkan")
    
    if len(cookies) > user["max_cookies_per_check"]:
        raise HTTPException(
            status_code=400,
            detail=f"Maksimal {user['max_cookies_per_check']} cookie per pengecekan"
        )
    
    # Check daily limit
    today = datetime.now().strftime("%Y-%m-%d")
    if user["last_check_date"] != today:
        # Reset counter
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
        raise HTTPException(status_code=403, detail="Limit harian telah habis")
    
    # Start checking
    results = []
    valid_count = 0
    total_robux = 0
    
    for idx, cookie in enumerate(cookies):
        result = check_single_cookie_api(cookie)
        result["cookie_id"] = idx + 1
        results.append(result)
        
        if result["status"] == "valid":
            valid_count += 1
            total_robux += result.get("robux", 0)
        
        # Delay to avoid rate limiting
        time.sleep(1)
    
    # Save results to database
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
    
    # Update user's check count
    cursor.execute(
        "UPDATE users SET checks_today = checks_today + 1 WHERE id = ?",
        (user["id"],)
    )
    
    # Log usage
    cursor.execute('''
        INSERT INTO usage_logs (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (
        user["id"],
        "cookie_check",
        json.dumps({
            "total_cookies": len(cookies),
            "valid_count": valid_count,
            "total_robux": total_robux
        })
    ))
    
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

# ==================== PUBLIC PAGES ====================
@app.get("/")
async def home():
    with open("public/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard")
async def dashboard():
    with open("public/dashboard.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/admin")
async def admin_page():
    with open("public/admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/admin-dashboard")
async def admin_dashboard():
    with open("public/dashboard_admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# Health check
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Roblox Cookie Checker Premium",
        "timestamp": datetime.now().isoformat()
    }