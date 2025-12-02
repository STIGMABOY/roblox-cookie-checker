// Main JavaScript for Roblox Cookie Checker

// Global variables
let currentUser = null;
let isChecking = false;
let currentCheckId = null;

// Utility functions
function showLoading(message = 'Memproses...') {
    document.getElementById('loadingText').textContent = message;
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-message">${message}</div>
        <button class="toast-close">&times;</button>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
    
    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    });
}

// Cookie checker functions
async function checkSingleCookie(cookie) {
    try {
        const response = await fetch('/api/check/single', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ cookie: cookie })
        });
        
        return await response.json();
    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}

async function checkMultipleCookies(cookies) {
    try {
        const response = await fetch('/api/check-cookies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                cookies: cookies,
                user_id: currentUser.id 
            })
        });
        
        return await response.json();
    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}

// User authentication functions
async function login(username, password) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            showToast('Login berhasil!', 'success');
            return data;
        } else {
            showToast(data.detail || 'Login gagal', 'error');
            return null;
        }
    } catch (error) {
        showToast('Koneksi error: ' + error.message, 'error');
        return null;
    }
}

async function logout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST'
        });
        
        currentUser = null;
        showToast('Logout berhasil', 'success');
        window.location.href = '/';
    } catch (error) {
        window.location.href = '/';
    }
}

async function checkAuth() {
    try {
        const response = await fetch('/api/auth/me');
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            return true;
        }
    } catch (error) {
        // Not authenticated
    }
    
    window.location.href = '/';
    return false;
}

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseenter', function() {
            const tooltipText = this.getAttribute('data-tooltip');
            const tooltipEl = document.createElement('div');
            tooltipEl.className = 'tooltip';
            tooltipEl.textContent = tooltipText;
            document.body.appendChild(tooltipEl);
            
            const rect = this.getBoundingClientRect();
            tooltipEl.style.left = rect.left + 'px';
            tooltipEl.style.top = (rect.top - tooltipEl.offsetHeight - 10) + 'px';
            
            this._tooltip = tooltipEl;
        });
        
        tooltip.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                document.body.removeChild(this._tooltip);
                this._tooltip = null;
            }
        });
    });
    
    // Check if user is logged in on dashboard pages
    if (window.location.pathname.includes('dashboard')) {
        checkAuth();
    }
});

// Export functions for use in HTML files
window.CookieChecker = {
    login,
    logout,
    checkAuth,
    checkSingleCookie,
    checkMultipleCookies,
    showLoading,
    hideLoading,
    showToast
};