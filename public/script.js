// ==================== GLOBAL CONFIG ====================
const CONFIG = {
    API_URL: window.location.origin + '/api',
    SESSION_TIMEOUT: 30 * 60 * 1000, // 30 minutes
    CHECK_INTERVAL: 1000, // 1 second per cookie
    TOAST_DURATION: 3000
};

// ==================== GLOBAL STATE ====================
let appState = {
    user: null,
    isChecking: false,
    currentResults: null,
    lastActivity: Date.now(),
    sessionTimer: null
};

// ==================== LOADING OPTIMIZATIONS ====================
class LoadingManager {
    constructor() {
        this.loadingQueue = [];
        this.isLoading = false;
    }

    show(message = 'Loading...', progress = 0) {
        if (!document.getElementById('loadingOverlay')) {
            this.createLoadingOverlay();
        }
        
        const overlay = document.getElementById('loadingOverlay');
        const text = document.getElementById('loadingText');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        if (text) text.textContent = message;
        if (progressBar) progressBar.style.width = `${progress}%`;
        if (progressText) progressText.textContent = `${progress}%`;
        
        overlay.style.display = 'flex';
        this.isLoading = true;
    }

    hide() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'none';
            this.isLoading = false;
        }
    }

    updateProgress(progress, message = null) {
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        const text = document.getElementById('loadingText');
        
        if (progressBar) progressBar.style.width = `${progress}%`;
        if (progressText) progressText.textContent = `${progress}%`;
        if (message && text) text.textContent = message;
    }

    createLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <i class="fas fa-spinner"></i>
                <h3 id="loadingText">Loading...</h3>
                <div class="loading-progress">
                    <div class="progress-bar" id="progressBar"></div>
                </div>
                <div class="progress-text" id="progressText">0%</div>
            </div>
        `;
        document.body.appendChild(overlay);
    }
}

class ToastManager {
    constructor() {
        this.container = null;
        this.queue = [];
        this.isShowing = false;
        this.createContainer();
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = CONFIG.TOAST_DURATION) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-message">${message}</div>
            <button class="toast-close">&times;</button>
        `;

        this.container.appendChild(toast);

        // Animate in
        setTimeout(() => toast.classList.add('show'), 10);

        // Auto remove
        const removeToast = () => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode === this.container) {
                    this.container.removeChild(toast);
                }
            }, 300);
        };

        // Close button
        toast.querySelector('.toast-close').addEventListener('click', removeToast);

        // Auto remove after duration
        setTimeout(removeToast, duration);
    }

    success(message) {
        this.show(message, 'success');
    }

    error(message) {
        this.show(message, 'error');
    }

    warning(message) {
        this.show(message, 'warning');
    }

    info(message) {
        this.show(message, 'info');
    }
}

// ==================== CACHE MANAGER ====================
class CacheManager {
    constructor() {
        this.cache = new Map();
        this.MAX_ITEMS = 100;
        this.TTL = 5 * 60 * 1000; // 5 minutes
    }

    set(key, data, ttl = this.TTL) {
        if (this.cache.size >= this.MAX_ITEMS) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }

        this.cache.set(key, {
            data,
            expiry: Date.now() + ttl
        });
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;

        if (Date.now() > item.expiry) {
            this.cache.delete(key);
            return null;
        }

        return item.data;
    }

    clear() {
        this.cache.clear();
    }

    remove(key) {
        this.cache.delete(key);
    }
}

// ==================== API CLIENT ====================
class ApiClient {
    constructor() {
        this.baseURL = CONFIG.API_URL;
        this.cache = new CacheManager();
        this.loadingManager = new LoadingManager();
        this.toastManager = new ToastManager();
    }

    async request(endpoint, options = {}) {
        const cacheKey = `${endpoint}:${JSON.stringify(options.body || {})}`;
        
        // Check cache for GET requests
        if (!options.method || options.method === 'GET') {
            const cached = this.cache.get(cacheKey);
            if (cached) return cached;
        }

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...options,
                headers
            });

            if (response.status === 401) {
                this.handleUnauthorized();
                throw new Error('Session expired');
            }

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            // Cache successful GET responses
            if (!options.method || options.method === 'GET') {
                this.cache.set(cacheKey, data);
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            this.toastManager.error(error.message || 'Request failed');
            throw error;
        }
    }

    async get(endpoint) {
        return this.request(endpoint);
    }

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    handleUnauthorized() {
        appState.user = null;
        localStorage.removeItem('session_token');
        window.location.href = '/';
    }
}

// ==================== SESSION MANAGER ====================
class SessionManager {
    constructor() {
        this.api = new ApiClient();
        this.timeout = CONFIG.SESSION_TIMEOUT;
        this.timer = null;
    }

    startSession() {
        this.resetTimer();
        document.addEventListener('mousemove', () => this.resetTimer());
        document.addEventListener('keypress', () => this.resetTimer());
        document.addEventListener('click', () => this.resetTimer());
    }

    resetTimer() {
        if (this.timer) clearTimeout(this.timer);
        this.timer = setTimeout(() => {
            this.api.toastManager.warning('Session will expire soon');
        }, this.timeout - 60000); // Warn 1 minute before

        setTimeout(() => {
            if (appState.user) {
                this.api.handleUnauthorized();
            }
        }, this.timeout);
    }

    clearSession() {
        if (this.timer) clearTimeout(this.timer);
        document.removeEventListener('mousemove', () => this.resetTimer());
        document.removeEventListener('keypress', () => this.resetTimer());
        document.removeEventListener('click', () => this.resetTimer());
    }
}

// ==================== COOKIE CHECKER ====================
class CookieChecker {
    constructor() {
        this.api = new ApiClient();
        this.currentCheck = null;
    }

    async checkCookies(cookiesText, onProgress = null) {
        if (appState.isChecking) {
            this.api.toastManager.warning('Already checking cookies');
            return;
        }

        const cookies = cookiesText.split('\n')
            .map(c => c.trim())
            .filter(c => c.length > 0);

        if (cookies.length === 0) {
            this.api.toastManager.error('No cookies to check');
            return;
        }

        if (cookies.length > (appState.user?.max_cookies_per_check || 50)) {
            this.api.toastManager.error(`Maximum ${appState.user.max_cookies_per_check} cookies allowed`);
            return;
        }

        appState.isChecking = true;
        this.api.loadingManager.show(`Checking ${cookies.length} cookies...`, 0);

        try {
            const response = await this.api.post('/check-cookies', {
                cookies: cookiesText
            });

            if (response.success) {
                appState.currentResults = response;
                this.displayResults(response);
                this.api.toastManager.success(`Check complete! ${response.summary.valid} valid found`);
            } else {
                this.api.toastManager.error(response.detail || 'Check failed');
            }
        } catch (error) {
            console.error('Check error:', error);
        } finally {
            appState.isChecking = false;
            this.api.loadingManager.hide();
        }
    }

    displayResults(data) {
        const resultsSection = document.getElementById('resultsSection');
        if (!resultsSection) return;

        // Update summary
        const summary = data.summary;
        const summaryHTML = `
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="summary-value">${summary.total}</div>
                    <div class="summary-label">Total Cookies</div>
                </div>
                <div class="summary-card success">
                    <div class="summary-value">${summary.valid}</div>
                    <div class="summary-label">Valid</div>
                </div>
                <div class="summary-card danger">
                    <div class="summary-value">${summary.invalid}</div>
                    <div class="summary-label">Invalid</div>
                </div>
                <div class="summary-card warning">
                    <div class="summary-value">${summary.total_robux.toLocaleString()}</div>
                    <div class="summary-label">Total Robux</div>
                </div>
            </div>
        `;

        const summaryElement = document.getElementById('resultsSummary');
        if (summaryElement) {
            summaryElement.innerHTML = summaryHTML;
            animateElements(summaryElement.querySelectorAll('.summary-card'));
        }

        // Update results table
        const tableBody = document.getElementById('resultsBody');
        if (tableBody) {
            let tableHTML = '';
            data.results.forEach((result, index) => {
                const statusClass = result.status === 'valid' ? 'success' : 
                                  result.status === 'error' ? 'warning' : 'danger';
                const statusIcon = result.status === 'valid' ? 'check' : 
                                 result.status === 'error' ? 'exclamation-triangle' : 'times';
                
                tableHTML += `
                    <tr style="animation-delay: ${index * 0.05}s">
                        <td>${index + 1}</td>
                        <td>
                            <span class="badge badge-${statusClass}">
                                <i class="fas fa-${statusIcon}"></i> ${result.status.toUpperCase()}
                            </span>
                        </td>
                        <td>${result.username || '-'}</td>
                        <td>${result.user_id || '-'}</td>
                        <td><strong>${result.robux ? result.robux.toLocaleString() : '0'}</strong></td>
                        <td>
                            ${result.premium ? 
                                '<span class="badge badge-premium"><i class="fas fa-crown"></i> Premium</span>' : 
                                '<span class="badge badge-secondary">Standard</span>'
                            }
                        </td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="showResultDetail(${index})">
                                <i class="fas fa-info-circle"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });
            
            tableBody.innerHTML = tableHTML;
            animateElements(tableBody.querySelectorAll('tr'));
        }

        // Show results section
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    cancelCheck() {
        if (this.currentCheck) {
            this.currentCheck.cancel();
            this.currentCheck = null;
        }
        appState.isChecking = false;
        this.api.loadingManager.hide();
        this.api.toastManager.info('Check cancelled');
    }
}

// ==================== UI ANIMATIONS ====================
function animateElements(elements) {
    elements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            el.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, index * 50);
    });
}

function createRipple(event) {
    const button = event.currentTarget;
    const circle = document.createElement("span");
    const diameter = Math.max(button.clientWidth, button.clientHeight);
    const radius = diameter / 2;

    circle.style.width = circle.style.height = `${diameter}px`;
    circle.style.left = `${event.clientX - button.getBoundingClientRect().left - radius}px`;
    circle.style.top = `${event.clientY - button.getBoundingClientRect().top - radius}px`;
    circle.classList.add("ripple");

    const ripple = button.getElementsByClassName("ripple")[0];
    if (ripple) ripple.remove();

    button.appendChild(circle);
}

// ==================== INITIALIZATION ====================
async function initializeApp() {
    // Initialize managers
    window.loadingManager = new LoadingManager();
    window.toastManager = new ToastManager();
    window.apiClient = new ApiClient();
    window.cookieChecker = new CookieChecker();
    window.sessionManager = new SessionManager();

    // Check authentication
    await checkAuth();
    
    // Add ripple effect to buttons
    document.addEventListener('click', function(e) {
        if (e.target.matches('.btn:not(:disabled)')) {
            createRipple(e);
        }
    });

    // Initialize sidebar toggle for mobile
    initSidebarToggle();

    // Start session timer
    if (appState.user) {
        sessionManager.startSession();
    }

    console.log('App initialized successfully');
}

async function checkAuth() {
    try {
        const response = await apiClient.get('/auth/me');
        if (response.success) {
            appState.user = response.user;
            
            // Update UI based on user type
            if (window.location.pathname === '/' && !response.user.is_admin) {
                window.location.href = '/dashboard';
            } else if (window.location.pathname.includes('admin') && !response.user.is_admin) {
                window.location.href = '/dashboard';
            }
            
            updateUserUI(response.user);
            return true;
        }
    } catch (error) {
        // Not authenticated
        if (window.location.pathname.includes('dashboard') || 
            window.location.pathname.includes('admin-dashboard')) {
            window.location.href = '/';
        }
    }
    return false;
}

function updateUserUI(user) {
    // Update user info in sidebar
    const userInfo = document.getElementById('userInfo');
    if (userInfo) {
        userInfo.innerHTML = `
            <div class="user-avatar">
                <i class="fas fa-user-${user.is_admin ? 'shield' : 'circle'}"></i>
            </div>
            <div class="user-details">
                <h3>${user.username}</h3>
                <p class="user-email">${user.email || 'No email'}</p>
                <p class="user-created">${user.account_type.toUpperCase()} Account</p>
            </div>
        `;
    }

    // Update stats in header
    updateHeaderStats(user);
}

function updateHeaderStats(user) {
    const todayChecks = document.getElementById('todayChecks');
    const dailyLimit = document.getElementById('dailyLimit');
    const maxCookies = document.getElementById('maxCookies');
    const accountStatus = document.getElementById('accountStatus');
    const remainingDays = document.getElementById('remainingDays');

    if (todayChecks) todayChecks.textContent = user.checks_today || 0;
    if (dailyLimit) dailyLimit.textContent = user.daily_limit || 0;
    if (maxCookies) maxCookies.textContent = user.max_cookies_per_check || 0;

    if (accountStatus && remainingDays && user.subscription_expires) {
        const expires = new Date(user.subscription_expires);
        const now = new Date();
        const diffDays = Math.ceil((expires - now) / (1000 * 60 * 60 * 24));
        
        if (diffDays > 0) {
            accountStatus.textContent = 'Active';
            accountStatus.className = 'text-success';
            remainingDays.textContent = diffDays;
        } else {
            accountStatus.textContent = 'Expired';
            accountStatus.className = 'text-danger';
            remainingDays.textContent = '0';
        }
    }
}

function initSidebarToggle() {
    const menuToggle = document.createElement('button');
    menuToggle.className = 'menu-toggle';
    menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
    menuToggle.onclick = () => {
        document.querySelector('.sidebar').classList.toggle('active');
        document.querySelector('.main-content').classList.toggle('expanded');
    };
    
    if (window.innerWidth <= 1024) {
        document.body.appendChild(menuToggle);
    }

    window.addEventListener('resize', () => {
        if (window.innerWidth <= 1024 && !document.querySelector('.menu-toggle')) {
            document.body.appendChild(menuToggle);
        } else if (window.innerWidth > 1024 && document.querySelector('.menu-toggle')) {
            document.querySelector('.menu-toggle').remove();
        }
    });
}

// ==================== PAGE SPECIFIC FUNCTIONS ====================
// Login page functions
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username')?.value;
    const password = document.getElementById('password')?.value;
    
    if (!username || !password) {
        toastManager.error('Please enter username and password');
        return;
    }

    loadingManager.show('Logging in...');
    
    try {
        const response = await apiClient.post('/auth/login', { username, password });
        
        if (response.success) {
            toastManager.success('Login successful!');
            
            // Redirect based on user type
            setTimeout(() => {
                if (response.user.is_admin) {
                    window.location.href = '/admin-dashboard';
                } else {
                    window.location.href = '/dashboard';
                }
            }, 1000);
        }
    } catch (error) {
        console.error('Login error:', error);
    } finally {
        loadingManager.hide();
    }
}

// Dashboard functions
async function loadDashboardData() {
    loadingManager.show('Loading dashboard...');
    
    try {
        const [stats, history] = await Promise.all([
            apiClient.get('/user/stats'),
            apiClient.get('/user/history')
        ]);
        
        updateDashboardUI(stats, history);
    } catch (error) {
        console.error('Dashboard load error:', error);
    } finally {
        loadingManager.hide();
    }
}

function updateDashboardUI(stats, history) {
    // Update stats
    const statsContainer = document.getElementById('statsContainer');
    if (statsContainer && stats.stats) {
        statsContainer.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-search"></i>
                    </div>
                    <div class="stat-value">${stats.stats.total_checks || 0}</div>
                    <div class="stat-label">Total Checks</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <div class="stat-value">${stats.stats.total_valid || 0}</div>
                    <div class="stat-label">Valid Cookies</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-coins"></i>
                    </div>
                    <div class="stat-value">${(stats.stats.total_robux || 0).toLocaleString()}</div>
                    <div class="stat-label">Total Robux</div>
                </div>
            </div>
        `;
        animateElements(statsContainer.querySelectorAll('.stat-card'));
    }

    // Update history
    const historyTable = document.getElementById('historyTable');
    if (historyTable && history.history) {
        let tableHTML = '';
        
        if (history.history.length > 0) {
            history.history.forEach((item, index) => {
                const date = new Date(item.timestamp);
                tableHTML += `
                    <tr style="animation-delay: ${index * 0.05}s">
                        <td>${date.toLocaleString()}</td>
                        <td><span class="badge badge-success">${item.valid_count}</span></td>
                        <td><span class="badge badge-danger">${item.invalid_count}</span></td>
                        <td><strong>${item.total_robux.toLocaleString()}</strong></td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="viewHistoryDetail(${item.id})">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });
        } else {
            tableHTML = `
                <tr>
                    <td colspan="5" class="text-center">
                        <div class="no-data">
                            <i class="fas fa-history"></i>
                            <p>No check history yet</p>
                        </div>
                    </td>
                </tr>
            `;
        }
        
        historyTable.innerHTML = tableHTML;
        animateElements(historyTable.querySelectorAll('tr'));
    }
}

// ==================== GLOBAL FUNCTIONS ====================
window.showResultDetail = function(index) {
    if (!appState.currentResults || !appState.currentResults.results[index]) return;
    
    const result = appState.currentResults.results[index];
    const modalBody = document.getElementById('detailModalBody');
    
    let detailHTML = `
        <div class="modal-header">
            <h4><i class="fas fa-cookie-bite"></i> Cookie #${result.cookie_id} Details</h4>
        </div>
        <div class="modal-body">
            <div class="detail-grid">
    `;
    
    if (result.status === 'valid') {
        detailHTML += `
                <div class="detail-item">
                    <label>Status:</label>
                    <span class="text-success"><strong>VALID</strong></span>
                </div>
                <div class="detail-item">
                    <label>Username:</label>
                    <span>${result.username}</span>
                </div>
                <div class="detail-item">
                    <label>User ID:</label>
                    <span>${result.user_id}</span>
                </div>
                <div class="detail-item">
                    <label>Display Name:</label>
                    <span>${result.display_name || result.username}</span>
                </div>
                <div class="detail-item">
                    <label>Robux Balance:</label>
                    <span class="robux-big">${result.robux ? result.robux.toLocaleString() : '0'}</span>
                </div>
                <div class="detail-item">
                    <label>Premium Status:</label>
                    <span class="${result.premium ? 'text-premium' : 'text-secondary'}">
                        ${result.premium ? 
                            '<i class="fas fa-crown"></i> Premium Account' : 
                            'Standard Account'}
                    </span>
                </div>
        `;
    } else {
        detailHTML += `
                <div class="detail-item">
                    <label>Status:</label>
                    <span class="text-danger"><strong>${result.status.toUpperCase()}</strong></span>
                </div>
                <div class="detail-item">
                    <label>Error:</label>
                    <span class="text-danger">${result.error || 'Unknown error'}</span>
                </div>
        `;
    }
    
    detailHTML += `
            </div>
            <div class="detail-actions">
                <button class="btn btn-secondary" onclick="closeModal()">
                    <i class="fas fa-times"></i> Close
                </button>
            </div>
        </div>
    `;
    
    modalBody.innerHTML = detailHTML;
    openModal('detailModal');
};

window.openModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
};

window.closeModal = function() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('active');
    });
    document.body.style.overflow = 'auto';
};

window.logout = async function() {
    if (confirm('Are you sure you want to logout?')) {
        loadingManager.show('Logging out...');
        
        try {
            await apiClient.post('/auth/logout');
            appState.user = null;
            sessionManager.clearSession();
            window.location.href = '/';
        } catch (error) {
            console.error('Logout error:', error);
            window.location.href = '/';
        }
    }
};

// ==================== INITIALIZE ON LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    // Add loading animation to page
    document.body.style.opacity = '0';
    document.body.style.transition = 'opacity 0.5s ease';
    
    setTimeout(() => {
        document.body.style.opacity = '1';
        initializeApp();
    }, 100);
    
    // Close modal on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeModal();
    });
    
    // Close modal on outside click
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            closeModal();
        }
    });
});

// ==================== EXPORT FOR HTML USE ====================
window.App = {
    loadingManager: window.loadingManager,
    toastManager: window.toastManager,
    apiClient: window.apiClient,
    cookieChecker: window.cookieChecker,
    sessionManager: window.sessionManager,
    checkAuth,
    handleLogin,
    loadDashboardData,
    showResultDetail,
    openModal,
    closeModal,
    logout
};
