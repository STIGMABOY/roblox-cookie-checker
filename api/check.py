from http.server import BaseHTTPRequestHandler
import json, requests, time, threading, random, queue
from datetime import datetime, timezone
import os

# Konfigurasi
MAX_CONCURRENT_CHECKS = 3  # Maksimal 3 request bersamaan
DELAY_BETWEEN_CHECKS = 0.5  # 0.5 detik delay antar cookie
REQUEST_TIMEOUT = 15  # Timeout 15 detik per request

checker_state = {
    'is_checking': False,
    'current_thread': None,
    'results': [],
    'batch_id': None,
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
        'start_time': None,
        'estimated_time': None,
        'speed': 0
    }
}

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
                'batch_id': checker_state['batch_id'],
                'time': datetime.now(timezone.utc).isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode())
            return
        
        elif self.path == '/api/check?action=results':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(checker_state['results'][-200:]).encode())
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
                'all_logs': checker_state['results'][-100:]
            }
            
            self.wfile.write(json.dumps(response).encode())
            return
        
        elif self.path.startswith('/api/check?batch='):
            batch_id = self.path.split('=')[1]
            if checker_state['batch_id'] == batch_id:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                # Return batch results
                batch_results = [r for r in checker_state['results'] if r.get('batch_id') == batch_id]
                
                response = {
                    'success': True,
                    'batch_id': batch_id,
                    'total': len(batch_results),
                    'valid': len([r for r in batch_results if r['status'] == 'valid']),
                    'invalid': len([r for r in batch_results if r['status'] != 'valid']),
                    'results': batch_results[-100:],
                    'completed': not checker_state['is_checking']
                }
                
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(404)
                self.end_headers()
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
                    # Return current batch info instead of error
                    response = {
                        'success': False,
                        'message': 'Checker is already running',
                        'batch_id': checker_state['batch_id']
                    }
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Generate batch ID
                import uuid
                batch_id = str(uuid.uuid4())[:8]
                
                checker_state['is_checking'] = True
                checker_state['batch_id'] = batch_id
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
                    'start_time': time.time(),
                    'estimated_time': len(cookies) * 2,  # Estimasi kasar
                    'speed': 0
                }
                
                # Start background thread dengan queue system
                thread = threading.Thread(
                    target=check_cookies_batch_optimized, 
                    args=(cookies, batch_id)
                )
                thread.daemon = True
                thread.start()
                checker_state['current_thread'] = thread
                
                response = {
                    'success': True,
                    'message': f'Started checking {len(cookies)} cookies',
                    'total': len(cookies),
                    'batch_id': batch_id,
                    'estimated_time': len(cookies) * 2  # 2 detik per cookie
                }
                
            elif action == 'stop':
                checker_state['is_checking'] = False
                checker_state['live_data']['status'] = 'stopped'
                
                response = {
                    'success': True,
                    'message': 'Checker stopped',
                    'batch_id': checker_state['batch_id'],
                    'total_checked': checker_state['live_data']['total_checked']
                }
                
            elif action == 'pause':
                checker_state['live_data']['status'] = 'paused'
                
                response = {
                    'success': True,
                    'message': 'Checker paused',
                    'batch_id': checker_state['batch_id']
                }
                
            elif action == 'resume':
                checker_state['live_data']['status'] = 'running'
                
                response = {
                    'success': True,
                    'message': 'Checker resumed',
                    'batch_id': checker_state['batch_id']
                }
                
            elif action == 'test':
                cookie = data.get('cookie', '')
                if not cookie:
                    raise ValueError("No cookie provided")
                
                result = check_single_cookie_optimized(cookie, 0)
                response = result
                
                # Add batch ID
                result['batch_id'] = 'test_' + str(int(time.time()))
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
                    'start_time': None,
                    'estimated_time': None,
                    'speed': 0
                }
                checker_state['batch_id'] = None
                
                response = {
                    'success': True,
                    'message': 'Results cleared'
                }
                
            elif action == 'export':
                batch_id = data.get('batch_id', checker_state['batch_id'])
                
                if batch_id:
                    batch_results = [r for r in checker_state['results'] if r.get('batch_id') == batch_id]
                else:
                    batch_results = checker_state['results']
                
                valid_cookies = [r for r in batch_results if r['status'] == 'valid']
                
                export_data = "# VALID ROBLOX COOKIES EXPORT\n"
                export_data += f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                export_data += f"# Batch ID: {batch_id}\n"
                export_data += f"# Total Valid: {len(valid_cookies)}\n"
                export_data += f"# Total Robux: {sum([r.get('robux', 0) for r in valid_cookies])}\n"
                export_data += f"# Total Premium: {len([r for r in valid_cookies if r.get('premium', False)])}\n\n"
                
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
                    'filename': f'valid_cookies_{batch_id}_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.txt',
                    'valid_count': len(valid_cookies),
                    'total_robux': sum([r.get('robux', 0) for r in valid_cookies])
                }
                
            elif action == 'batch_status':
                batch_id = data.get('batch_id', '')
                
                if batch_id and checker_state['batch_id'] == batch_id:
                    batch_results = [r for r in checker_state['results'] if r.get('batch_id') == batch_id]
                    
                    response = {
                        'success': True,
                        'batch_id': batch_id,
                        'is_running': checker_state['is_checking'],
                        'status': checker_state['live_data']['status'],
                        'progress': checker_state['live_data']['progress'],
                        'total_checked': len(batch_results),
                        'valid': len([r for r in batch_results if r['status'] == 'valid']),
                        'invalid': len([r for r in batch_results if r['status'] != 'valid']),
                        'estimated_time_left': checker_state['live_data'].get('estimated_time_left', 0)
                    }
                else:
                    response = {
                        'success': False,
                        'message': 'Batch not found or completed'
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

# ============================================
# FUNGSI OPTIMIZED CHECKING
# ============================================

def check_cookies_batch_optimized(cookies, batch_id):
    """Optimized batch checking with concurrent processing"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import math
    
    start_time = time.time()
    total_cookies = len(cookies)
    
    # Setup untuk concurrent processing
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CHECKS) as executor:
        # Submit semua tasks
        future_to_cookie = {}
        for i, cookie in enumerate(cookies):
            future = executor.submit(check_single_cookie_optimized, cookie, i)
            future_to_cookie[future] = (i, cookie)
        
        # Process results as they complete
        completed = 0
        for future in as_completed(future_to_cookie):
            if not checker_state['is_checking']:
                break
                
            i, cookie = future_to_cookie[future]
            try:
                result = future.result(timeout=REQUEST_TIMEOUT)
                result['batch_id'] = batch_id
                
                # Add to results
                checker_state['results'].append(result)
                
                # Update live data
                completed += 1
                checker_state['live_data']['current'] = completed
                checker_state['live_data']['total_checked'] = completed
                checker_state['live_data']['progress'] = int((completed / total_cookies) * 100)
                
                if result['status'] == 'valid':
                    checker_state['live_data']['valid'] += 1
                    checker_state['live_data']['robux'] += result.get('robux', 0)
                    if result.get('premium', False):
                        checker_state['live_data']['premium'] += 1
                    if result.get('friends_count', 0):
                        checker_state['live_data']['friends'] += result.get('friends_count', 0)
                else:
                    checker_state['live_data']['invalid'] += 1
                
                # Calculate speed and ETA
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    speed = completed / elapsed_time  # cookies per second
                    checker_state['live_data']['speed'] = round(speed, 2)
                    
                    if speed > 0:
                        remaining = total_cookies - completed
                        eta = remaining / speed
                        checker_state['live_data']['estimated_time'] = round(eta)
                
                # Small delay to prevent rate limiting
                time.sleep(DELAY_BETWEEN_CHECKS)
                
            except Exception as e:
                # Handle error for this cookie
                error_result = {
                    'cookie_id': i,
                    'batch_id': batch_id,
                    'status': 'error',
                    'username': 'Unknown',
                    'user_id': 'Unknown',
                    'display_name': 'Unknown',
                    'premium': False,
                    'robux': 0,
                    'friends_count': 0,
                    'error': f'Processing error: {str(e)}',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                checker_state['results'].append(error_result)
                checker_state['live_data']['invalid'] += 1
                completed += 1
                checker_state['live_data']['current'] = completed
                checker_state['live_data']['total_checked'] = completed
                checker_state['live_data']['progress'] = int((completed / total_cookies) * 100)
    
    # Selesai
    if checker_state['is_checking']:
        checker_state['is_checking'] = False
        checker_state['live_data']['status'] = 'completed'
        
        # Final stats
        total_time = time.time() - start_time
        checker_state['live_data']['speed'] = round(total_cookies / total_time, 2) if total_time > 0 else 0

def check_single_cookie_optimized(cookie, cookie_id=0):
    """Optimized single cookie check with better error handling"""
    headers = {
        'User-Agent': get_random_user_agent(),
        'Cookie': f'.ROBLOSECURITY={cookie}',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Referer': 'https://www.roblox.com/',
        'Origin': 'https://www.roblox.com',
        'X-CSRF-TOKEN': ''  # Will be fetched if needed
    }
    
    result = {
        'cookie_id': cookie_id,
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
    
    try:
        # Step 1: Get X-CSRF token first
        csrf_url = "https://auth.roblox.com/v2/logout"
        csrf_response = requests.post(csrf_url, headers=headers, timeout=10)
        
        if 'x-csrf-token' in csrf_response.headers:
            headers['X-CSRF-TOKEN'] = csrf_response.headers['x-csrf-token']
        
        # Step 2: Check authentication with retry
        auth_url = "https://users.roblox.com/v1/users/authenticated"
        
        for attempt in range(2):  # Retry once if rate limited
            try:
                response = requests.get(auth_url, headers=headers, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    user_data = response.json()
                    result['username'] = user_data.get('name', 'Unknown')
                    result['user_id'] = str(user_data.get('id', 'Unknown'))
                    result['display_name'] = user_data.get('displayName', 'Unknown')
                    result['status'] = 'valid'
                    result['error'] = None
                    
                    # Get additional info (non-blocking, if fails continue)
                    get_additional_info(result['user_id'], headers, result)
                    break
                    
                elif response.status_code == 401:
                    result['status'] = 'invalid'
                    result['error'] = 'Unauthorized (Cookie expired/invalid)'
                    break
                elif response.status_code == 403:
                    result['status'] = 'invalid'
                    result['error'] = 'Forbidden (Security restriction)'
                    break
                elif response.status_code == 429:
                    result['status'] = 'rate_limited'
                    result['error'] = 'Rate limited by Roblox'
                    if attempt == 0:
                        time.sleep(2)  # Wait 2 seconds and retry
                        continue
                    break
                else:
                    result['status'] = 'error'
                    result['error'] = f'HTTP {response.status_code}: {response.text[:100]}'
                    break
                    
            except requests.exceptions.Timeout:
                result['status'] = 'error'
                result['error'] = 'Request timeout'
                break
            except requests.exceptions.ConnectionError:
                result['status'] = 'error'
                result['error'] = 'Connection error'
                break
                
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def get_additional_info(user_id, headers, result):
    """Get additional user info (optimized with timeout)"""
    import concurrent.futures
    
    def get_premium():
        try:
            premium_url = "https://premiumfeatures.roblox.com/v1/users/premium/membership"
            premium_resp = requests.get(premium_url, headers=headers, timeout=5)
            if premium_resp.status_code == 200:
                return premium_resp.json().get('isPremium', False)
        except:
            pass
        return False
    
    def get_robux():
        try:
            economy_url = "https://economy.roblox.com/v1/user/currency"
            economy_resp = requests.get(economy_url, headers=headers, timeout=5)
            if economy_resp.status_code == 200:
                return economy_resp.json().get('robux', 0)
        except:
            pass
        return 0
    
    def get_friends():
        try:
            friends_url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
            friends_resp = requests.get(friends_url, headers=headers, timeout=5)
            if friends_resp.status_code == 200:
                return friends_resp.json().get('count', 0)
        except:
            pass
        return 0
    
    def get_user_info():
        try:
            user_info_url = f"https://users.roblox.com/v1/users/{user_id}"
            user_info_resp = requests.get(user_info_url, headers=headers, timeout=5)
            if user_info_resp.status_code == 200:
                info = user_info_resp.json()
                result['created_date'] = info.get('created', '')
        except:
            pass
    
    # Run all requests concurrently with timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        futures.append(executor.submit(get_premium))
        futures.append(executor.submit(get_robux))
        futures.append(executor.submit(get_friends))
        futures.append(executor.submit(get_user_info))
        
        try:
            # Wait for all with timeout
            done, not_done = concurrent.futures.wait(futures, timeout=10)
            
            # Get results
            for future in done:
                try:
                    if future == futures[0]:
                        result['premium'] = future.result()
                    elif future == futures[1]:
                        result['robux'] = future.result()
                    elif future == futures[2]:
                        result['friends_count'] = future.result()
                except:
                    pass
                    
        except concurrent.futures.TimeoutError:
            pass

def get_random_user_agent():
    """Get random user agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)
