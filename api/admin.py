from http.server import BaseHTTPRequestHandler
import json, time
from datetime import datetime, timedelta, timezone

# Import dari auth.py
from api.auth import (
    verify_token, get_all_users, update_admin_password, 
    get_user_stats, load_users, save_users, load_sessions,
    save_sessions, hash_password, deactivate_user, activate_user
)

class handler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        try:
            admin_token = self.headers.get('Authorization', '').replace('Bearer ', '')
            
            if not admin_token:
                raise ValueError("Authorization required")
            
            admin_payload = verify_token(admin_token)
            if not admin_payload or admin_payload.get('role') != 'admin':
                raise ValueError("Admin access required")
            
            path = self.path
            
            if path == '/api/admin/stats':
                users = get_all_users()
                sessions_data = load_sessions()

                total_users = len(users)
                active_users = len([u for u in users if u['is_active']])
                expired_users = total_users - active_users

                # Real-time expired users tracking
                now = datetime.now(timezone.utc)
                recently_expired = []
                for user in users:
                    if not user['is_active']:
                        expires_at = datetime.fromisoformat(user['expires_at'])
                        if (now - expires_at).days <= 1:  # Expired within last 24 hours
                            recently_expired.append({
                                'username': user['username'],
                                'expired_at': user['expires_at'],
                                'hours_since_expired': int((now - expires_at).total_seconds() / 3600)
                            })

                # Active sessions with real-time data
                active_sessions = []
                for session in sessions_data['sessions']:
                    expires_at = datetime.fromisoformat(session['expires_at'])
                    if now < expires_at:
                        last_activity = session.get('last_activity')
                        if last_activity:
                            last_activity_dt = datetime.fromisoformat(last_activity)
                            minutes_since_activity = int((now - last_activity_dt).total_seconds() / 60)
                        else:
                            minutes_since_activity = None

                        active_sessions.append({
                            'username': session['username'],
                            'created_at': session['created_at'],
                            'last_activity': last_activity,
                            'minutes_since_activity': minutes_since_activity,
                            'expires_at': session['expires_at']
                        })

                total_logins = sum([u.get('login_count', 0) for u in users])
                total_checks = sum([u.get('total_checks', 0) for u in users])
                total_cookies = sum([u.get('total_cookies', 0) for u in users])

                today = now.date()
                today_logins = 0
                for user in users:
                    if user.get('last_login'):
                        last_login = datetime.fromisoformat(user['last_login']).date()
                        if last_login == today:
                            today_logins += 1

                response = {
                    'success': True,
                    'stats': {
                        'total_users': total_users,
                        'active_users': active_users,
                        'expired_users': expired_users,
                        'recently_expired': recently_expired,
                        'total_logins': total_logins,
                        'today_logins': today_logins,
                        'total_checks': total_checks,
                        'total_cookies': total_cookies,
                        'active_sessions': len(active_sessions),
                        'active_sessions_detail': active_sessions,
                        'server_time': now.isoformat()
                    }
                }
                
            elif path == '/api/admin/dashboard':
                users = get_all_users()
                
                active_users_list = []
                expired_users_list = []
                
                for user in users:
                    user_info = {
                        'username': user['username'],
                        'created_at': user['created_at'],
                        'expires_at': user['expires_at'],
                        'days_valid': user['days_valid'],
                        'is_active': user['is_active'],
                        'last_login': user.get('last_login'),
                        'login_count': user.get('login_count', 0),
                        'total_checks': user.get('total_checks', 0),
                        'total_cookies': user.get('total_cookies', 0),
                        'created_by': user.get('created_by', 'admin')
                    }
                    
                    if user['is_active']:
                        active_users_list.append(user_info)
                    else:
                        expired_users_list.append(user_info)
                
                response = {
                    'success': True,
                    'active_users': active_users_list,
                    'expired_users': expired_users_list
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
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            admin_token = self.headers.get('Authorization', '').replace('Bearer ', '')
            
            if not admin_token:
                raise ValueError("Authorization required")
            
            admin_payload = verify_token(admin_token)
            if not admin_payload or admin_payload.get('role') != 'admin':
                raise ValueError("Admin access required")
            
            path = self.path
            
            if path == '/api/admin/update_password':
                new_password = data.get('new_password', '').strip()
                current_password = data.get('current_password', '').strip()
                
                if not new_password or len(new_password) < 8:
                    raise ValueError("Password must be at least 8 characters")
                
                # Verify current password
                users_data = load_users()
                if not hash_password(current_password) == users_data.get('admin_password'):
                    raise ValueError("Current password is incorrect")
                
                success = update_admin_password(new_password)
                
                response = {
                    'success': success,
                    'message': 'Admin password updated successfully'
                }
                
            elif path == '/api/admin/bulk_create':
                users_data = data.get('users', [])
                
                if not users_data:
                    raise ValueError("No users provided")
                
                from api.auth import create_user_account
                
                created_users = []
                failed_users = []
                
                for user_data in users_data:
                    username = user_data.get('username', '').strip()
                    password = user_data.get('password', '').strip()
                    days_valid = int(user_data.get('days_valid', 30))
                    
                    if username and password:
                        success, result = create_user_account(username, password, days_valid, "admin")
                        if success:
                            created_users.append({
                                'username': username,
                                'days_valid': days_valid,
                                'expires_at': result['expires_at']
                            })
                        else:
                            failed_users.append({
                                'username': username,
                                'error': result
                            })
                
                response = {
                    'success': True,
                    'message': f'Created {len(created_users)} users, failed {len(failed_users)}',
                    'created_users': created_users,
                    'failed_users': failed_users
                }
                
            elif path == '/api/admin/deactivate_user':
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
                    
            elif path == '/api/admin/activate_user':
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
                    

                
            elif path == '/api/admin/clear_sessions':
                sessions_data = load_sessions()
                old_count = len(sessions_data['sessions'])
                
                # Remove sessions older than 7 days
                seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
                sessions_data['sessions'] = [
                    s for s in sessions_data['sessions'] 
                    if datetime.fromisoformat(s['created_at']) > seven_days_ago
                ]
                
                removed_count = old_count - len(sessions_data['sessions'])
                save_sessions(sessions_data)
                
                response = {
                    'success': True,
                    'message': f'Removed {removed_count} old sessions'
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