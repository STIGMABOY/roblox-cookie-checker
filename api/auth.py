from http.server import BaseHTTPRequestHandler
import json, os, hashlib, time, uuid
from datetime import datetime, timedelta, timezone
import threading
import jwt
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os

SECRET_KEY = "robin_cookie_pro_2024_secret_key_change_this"
ADMIN_PASSWORD = "admin123456"

# MongoDB connection
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://default:default@cluster0.mongodb.net/?retryWrites=true&w=majority')
DB_NAME = os.environ.get('DB_NAME', 'robin_cookie_checker')

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    # Test connection
    client.admin.command('ping')
    print("MongoDB connected successfully")
except (ConnectionFailure, Exception):
    print("MongoDB connection failed, falling back to file storage")
    client = None
    db = None

file_lock = threading.Lock()
_sessions_cache = None
_users_cache = None
_cache_timestamp = 0
CACHE_DURATION = 30  # seconds

# Fallback file storage if MongoDB fails
DATA_DIR = "/tmp/data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")

def init_fallback_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if not os.path.exists(USERS_FILE):
        with file_lock:
            with open(USERS_FILE, 'w') as f:
                json.dump({"users": [], "admin_password": hash_password(ADMIN_PASSWORD)}, f)

    if not os.path.exists(SESSIONS_FILE):
        with file_lock:
            with open(SESSIONS_FILE, 'w') as f:
                json.dump({"sessions": []}, f)

if not db:
    init_fallback_data()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def create_token(username, role, expires_at=None):
    if expires_at is None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    payload = {
        'username': username,
        'role': role,
        'exp': expires_at.timestamp()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except:
        return None

def load_users():
    global _users_cache, _cache_timestamp
    current_time = time.time()

    # Return cached data if still valid
    if _users_cache is not None and (current_time - _cache_timestamp) < CACHE_DURATION:
        return _users_cache

    # Load from MongoDB or fallback to file
    if db:
        try:
            users_collection = db.users
            admin_doc = users_collection.find_one({"type": "admin"})
            users_list = list(users_collection.find({"type": "user"}))

            _users_cache = {
                "users": users_list,
                "admin_password": admin_doc.get("password_hash", hash_password(ADMIN_PASSWORD)) if admin_doc else hash_password(ADMIN_PASSWORD)
            }
        except Exception as e:
            print(f"MongoDB load error: {e}, falling back to file")
            # Fallback to file
            with file_lock:
                try:
                    with open(USERS_FILE, 'r') as f:
                        _users_cache = json.load(f)
                except:
                    _users_cache = {"users": [], "admin_password": hash_password(ADMIN_PASSWORD)}
    else:
        # Fallback to file
        with file_lock:
            try:
                with open(USERS_FILE, 'r') as f:
                    _users_cache = json.load(f)
            except:
                _users_cache = {"users": [], "admin_password": hash_password(ADMIN_PASSWORD)}

    _cache_timestamp = current_time
    return _users_cache

def save_users(data):
    global _users_cache, _cache_timestamp

    # Save to MongoDB or fallback to file
    if db:
        try:
            users_collection = db.users

            # Save admin password
            users_collection.replace_one(
                {"type": "admin"},
                {"type": "admin", "password_hash": data["admin_password"]},
                upsert=True
            )

            # Save users
            for user in data["users"]:
                users_collection.replace_one(
                    {"username": user["username"]},
                    {**user, "type": "user"},
                    upsert=True
                )

            # Remove users not in the list
            existing_usernames = {user["username"] for user in data["users"]}
            users_collection.delete_many({"type": "user", "username": {"$nin": list(existing_usernames)}})

        except Exception as e:
            print(f"MongoDB save error: {e}, falling back to file")
            # Fallback to file
            with file_lock:
                with open(USERS_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
    else:
        # Fallback to file
        with file_lock:
            with open(USERS_FILE, 'w') as f:
                json.dump(data, f, indent=2)

    # Update cache
    _users_cache = data
    _cache_timestamp = time.time()

def load_sessions():
    global _sessions_cache, _cache_timestamp
    current_time = time.time()

    # Return cached data if still valid
    if _sessions_cache is not None and (current_time - _cache_timestamp) < CACHE_DURATION:
        return _sessions_cache

    # Load from MongoDB or fallback to file
    if db:
        try:
            sessions_collection = db.sessions
            sessions_list = list(sessions_collection.find({}))
            _sessions_cache = {"sessions": sessions_list}
        except Exception as e:
            print(f"MongoDB sessions load error: {e}, falling back to file")
            # Fallback to file
            with file_lock:
                try:
                    with open(SESSIONS_FILE, 'r') as f:
                        _sessions_cache = json.load(f)
                except:
                    _sessions_cache = {"sessions": []}
    else:
        # Fallback to file
        with file_lock:
            try:
                with open(SESSIONS_FILE, 'r') as f:
                    _sessions_cache = json.load(f)
            except:
                _sessions_cache = {"sessions": []}

    _cache_timestamp = current_time
    return _sessions_cache

def save_sessions(data):
    global _sessions_cache, _cache_timestamp

    # Save to MongoDB or fallback to file
    if db:
        try:
            sessions_collection = db.sessions

            # Clear existing sessions
            sessions_collection.delete_many({})

            # Insert new sessions
            if data["sessions"]:
                sessions_collection.insert_many(data["sessions"])

        except Exception as e:
            print(f"MongoDB sessions save error: {e}, falling back to file")
            # Fallback to file
            with file_lock:
                with open(SESSIONS_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
    else:
        # Fallback to file
        with file_lock:
            with open(SESSIONS_FILE, 'w') as f:
                json.dump(data, f, indent=2)

    # Update cache
    _sessions_cache = data
    _cache_timestamp = time.time()

def create_user_account(username, password, days_valid=30, created_by="admin"):
    users_data = load_users()
    
    for user in users_data['users']:
        if user['username'] == username:
            return False, "Username already exists"
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)

    new_user = {
        'id': str(uuid.uuid4()),
        'username': username,
        'password_hash': hash_password(password),
        'role': 'user',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'created_by': created_by,
        'expires_at': expires_at.isoformat(),
        'days_valid': days_valid,
        'is_active': True,
        'last_login': None,
        'login_count': 0,
        'total_checks': 0,
        'total_cookies': 0
    }

    users_data['users'].append(new_user)
    save_users(users_data)

    token = create_token(username, 'user', expires_at)
    sessions_data = load_sessions()
    sessions_data['sessions'].append({
        'username': username,
        'token': token,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'last_activity': datetime.now(timezone.utc).isoformat(),
        'expires_at': expires_at.isoformat()
    })
    save_sessions(sessions_data)
    
    return True, {
        'username': username,
        'token': token,
        'expires_at': expires_at.isoformat(),
        'days_valid': days_valid
    }

def authenticate_user(username, password):
    users_data = load_users()
    
    if username == 'admin':
        if verify_password(password, users_data.get('admin_password', hash_password(ADMIN_PASSWORD))):
            expires_at = datetime.now(timezone.utc) + timedelta(days=1)
            token = create_token('admin', 'admin', expires_at)
            return True, {
                'username': 'admin',
                'role': 'admin',
                'token': token
            }
        return False, "Invalid admin credentials"

    for user in users_data['users']:
        if user['username'] == username:
            if not user['is_active']:
                return False, "Account is deactivated"

            if verify_password(password, user['password_hash']):
                expires_at = datetime.fromisoformat(user['expires_at'])
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                current_time = datetime.now(timezone.utc)

                # Check if account has expired but don't auto-deactivate
                if current_time > expires_at:
                    return False, "Account expired. Please contact admin."

                user['last_login'] = datetime.now(timezone.utc).isoformat()
                user['login_count'] = user.get('login_count', 0) + 1
                save_users(users_data)

                token = create_token(username, 'user', expires_at)

                sessions_data = load_sessions()
                sessions_data['sessions'].append({
                    'username': username,
                    'token': token,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'last_activity': datetime.now(timezone.utc).isoformat(),
                    'expires_at': user['expires_at']
                })
                save_sessions(sessions_data)

                days_left = (expires_at - current_time).days
                return True, {
                    'username': username,
                    'role': 'user',
                    'token': token,
                    'expires_at': user['expires_at'],
                    'days_left': max(0, days_left)
                }
            else:
                return False, "Invalid password"
    
    return False, "User not found"

def verify_user_token(token):
    payload = verify_token(token)
    if not payload:
        return False, "Invalid token"

    username = payload.get('username')

    # For admin, just verify the token is valid
    if username == 'admin':
        return True, payload

    # Check if user exists and is active first
    users_data = load_users()
    user_found = False
    for user in users_data['users']:
        if user['username'] == username:
            user_found = True
            if not user['is_active']:
                return False, "Account deactivated"
            # Check if user account has expired
            expires_at = datetime.fromisoformat(user['expires_at'])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            current_time = datetime.now(timezone.utc)
            if current_time > expires_at:
                user['is_active'] = False
                save_users(users_data)
                return False, "Account expired"
            break

    if not user_found:
        return False, "User not found"

    # Check session validity - very lenient approach
    sessions_data = load_sessions()
    session_found = False
    for session in sessions_data['sessions']:
        if session['token'] == token:
            session_found = True
            # Only check if session is extremely old (>30 days inactive)
            last_activity = session.get('last_activity')
            if last_activity:
                last_activity_dt = datetime.fromisoformat(last_activity)
                if last_activity_dt.tzinfo is None:
                    last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)
                if (current_time - last_activity_dt).days > 30:
                    # Remove very old inactive session
                    sessions_data['sessions'] = [s for s in sessions_data['sessions'] if s['token'] != token]
                    save_sessions(sessions_data)
                    return False, "Session expired due to inactivity"

            # Update last activity less frequently to reduce I/O
            if not last_activity or (current_time - last_activity_dt).seconds > 300:  # Update every 5 minutes
                session['last_activity'] = datetime.now(timezone.utc).isoformat()
                save_sessions(sessions_data)
            break

    # If no session found, create one (lenient approach)
    if not session_found:
        sessions_data['sessions'].append({
            'username': username,
            'token': token,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_activity': datetime.now(timezone.utc).isoformat(),
            'expires_at': payload.get('exp', (datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        })
        save_sessions(sessions_data)

    return True, payload

def get_all_users():
    users_data = load_users()
    return users_data['users']

def delete_user(username):
    users_data = load_users()
    initial_count = len(users_data['users'])
    users_data['users'] = [u for u in users_data['users'] if u['username'] != username]
    
    if len(users_data['users']) < initial_count:
        save_users(users_data)
        
        sessions_data = load_sessions()
        sessions_data['sessions'] = [s for s in sessions_data['sessions'] if s['username'] != username]
        save_sessions(sessions_data)
        
        return True, f"User {username} deleted successfully"
    
    return False, "User not found"

def extend_user_subscription(username, additional_days):
    users_data = load_users()

    for user in users_data['users']:
        if user['username'] == username:
            expires_at = datetime.fromisoformat(user['expires_at'])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            new_expires_at = expires_at + timedelta(days=additional_days)
            user['expires_at'] = new_expires_at.isoformat()
            user['days_valid'] += additional_days
            user['is_active'] = True
            save_users(users_data)

            # Update sessions
            sessions_data = load_sessions()
            for session in sessions_data['sessions']:
                if session['username'] == username:
                    session['expires_at'] = new_expires_at.isoformat()
            save_sessions(sessions_data)

            return True, {
                'new_expires_at': new_expires_at.isoformat(),
                'days_valid': user['days_valid']
            }

    return False, "User not found"

def update_admin_password(new_password):
    users_data = load_users()
    users_data['admin_password'] = hash_password(new_password)
    save_users(users_data)
    return True

def get_user_stats(username):
    users_data = load_users()
    for user in users_data['users']:
        if user['username'] == username:
            return user
    return None

def update_user_stats(username, cookies_checked=0):
    users_data = load_users()
    for user in users_data['users']:
        if user['username'] == username:
            user['total_checks'] = user.get('total_checks', 0) + 1
            user['total_cookies'] = user.get('total_cookies', 0) + cookies_checked
            save_users(users_data)
            return True
    return False

def deactivate_user(username):
    users_data = load_users()
    for user in users_data['users']:
        if user['username'] == username:
            user['is_active'] = False
            save_users(users_data)
            return True
    return False

def activate_user(username):
    users_data = load_users()
    for user in users_data['users']:
        if user['username'] == username:
            user['is_active'] = True
            save_users(users_data)
            return True
    return False

class handler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            path = self.path
            
            if path == '/api/auth/login':
                username = data.get('username', '').strip()
                password = data.get('password', '').strip()
                
                if not username or not password:
                    raise ValueError("Username and password required")
                
                success, result = authenticate_user(username, password)
                
                if success:
                    response = {
                        'success': True,
                        'message': 'Login successful',
                        'data': result
                    }
                else:
                    response = {
                        'success': False,
                        'message': result
                    }
                    
            elif path == '/api/auth/verify':
                token = data.get('token', '')
                
                if not token:
                    raise ValueError("Token required")
                
                success, result = verify_user_token(token)
                
                if success:
                    response = {
                        'success': True,
                        'message': 'Token valid',
                        'data': result
                    }
                else:
                    response = {
                        'success': False,
                        'message': result
                    }
                    
            elif path == '/api/auth/logout':
                token = data.get('token', '')
                
                if token:
                    sessions_data = load_sessions()
                    sessions_data['sessions'] = [s for s in sessions_data['sessions'] if s['token'] != token]
                    save_sessions(sessions_data)
                
                response = {
                    'success': True,
                    'message': 'Logged out successfully'
                }
                
            elif path == '/api/auth/create_user':
                admin_token = self.headers.get('Authorization', '').replace('Bearer ', '')
                
                if not admin_token:
                    raise ValueError("Authorization required")
                
                admin_payload = verify_token(admin_token)
                if not admin_payload or admin_payload.get('role') != 'admin':
                    raise ValueError("Admin access required")
                
                username = data.get('username', '').strip()
                password = data.get('password', '').strip()
                days_valid = int(data.get('days_valid', 30))
                
                if not username or not password:
                    raise ValueError("Username and password required")
                
                success, result = create_user_account(username, password, days_valid, "admin")
                
                if success:
                    response = {
                        'success': True,
                        'message': f'User {username} created successfully for {days_valid} days',
                        'data': result
                    }
                else:
                    response = {
                        'success': False,
                        'message': result
                    }
                    
            elif path == '/api/auth/extend':
                admin_token = self.headers.get('Authorization', '').replace('Bearer ', '')
                
                if not admin_token:
                    raise ValueError("Authorization required")
                
                admin_payload = verify_token(admin_token)
                if not admin_payload or admin_payload.get('role') != 'admin':
                    raise ValueError("Admin access required")
                
                username = data.get('username', '').strip()
                additional_days = int(data.get('additional_days', 30))
                
                if not username:
                    raise ValueError("Username required")
                
                success, result = extend_user_subscription(username, additional_days)
                
                if success:
                    response = {
                        'success': True,
                        'message': f'Subscription extended by {additional_days} days',
                        'data': result
                    }
                else:
                    response = {
                        'success': False,
                        'message': result
                    }
                    
            elif path == '/api/auth/deactivate':
                admin_token = self.headers.get('Authorization', '').replace('Bearer ', '')
                
                if not admin_token:
                    raise ValueError("Authorization required")
                
                admin_payload = verify_token(admin_token)
                if not admin_payload or admin_payload.get('role') != 'admin':
                    raise ValueError("Admin access required")
                
                username = data.get('username', '').strip()
                
                if not username:
                    raise ValueError("Username required")
                
                success = deactivate_user(username)
                
                if success:
                    response = {
                        'success': True,
                        'message': f'User {username} deactivated'
                    }
                else:
                    response = {
                        'success': False,
                        'message': 'User not found'
                    }
                    
            elif path == '/api/auth/activate':
                admin_token = self.headers.get('Authorization', '').replace('Bearer ', '')
                
                if not admin_token:
                    raise ValueError("Authorization required")
                
                admin_payload = verify_token(admin_token)
                if not admin_payload or admin_payload.get('role') != 'admin':
                    raise ValueError("Admin access required")
                
                username = data.get('username', '').strip()
                
                if not username:
                    raise ValueError("Username required")
                
                success = activate_user(username)
                
                if success:
                    response = {
                        'success': True,
                        'message': f'User {username} activated'
                    }
                else:
                    response = {
                        'success': False,
                        'message': 'User not found'
                    }
                    
            else:
                raise ValueError("Invalid endpoint")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': str(e)
            }).encode())
    
    def do_GET(self):
        try:
            path = self.path
            
            if path == '/api/auth/users':
                admin_token = self.headers.get('Authorization', '').replace('Bearer ', '')
                
                if not admin_token:
                    raise ValueError("Authorization required")
                
                admin_payload = verify_token(admin_token)
                if not admin_payload or admin_payload.get('role') != 'admin':
                    raise ValueError("Admin access required")
                
                users = get_all_users()
                
                response = {
                    'success': True,
                    'users': users
                }
                
            elif path.startswith('/api/auth/user/'):
                username = path.split('/')[-1]
                admin_token = self.headers.get('Authorization', '').replace('Bearer ', '')
                
                if not admin_token:
                    raise ValueError("Authorization required")
                
                admin_payload = verify_token(admin_token)
                if not admin_payload or admin_payload.get('role') != 'admin':
                    raise ValueError("Admin access required")
                
                user_stats = get_user_stats(username)
                
                if user_stats:
                    response = {
                        'success': True,
                        'user': user_stats
                    }
                else:
                    response = {
                        'success': False,
                        'message': 'User not found'
                    }
                    
            else:
                raise ValueError("Invalid endpoint")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': str(e)
            }).encode())
    
    def do_DELETE(self):
        try:
            path = self.path
            
            if path.startswith('/api/auth/user/'):
                username = path.split('/')[-1]
                admin_token = self.headers.get('Authorization', '').replace('Bearer ', '')
                
                if not admin_token:
                    raise ValueError("Authorization required")
                
                admin_payload = verify_token(admin_token)
                if not admin_payload or admin_payload.get('role') != 'admin':
                    raise ValueError("Admin access required")
                
                success, message = delete_user(username)
                
                response = {
                    'success': success,
                    'message': message
                }
                
            else:
                raise ValueError("Invalid endpoint")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': str(e)
            }).encode())