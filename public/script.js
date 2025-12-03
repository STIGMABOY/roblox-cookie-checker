// ============================================
// KONFIGURASI
// ============================================
const API_BASE_URL = window.location.origin;
const SAMPLE_COOKIE = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_testcookie123";

// ============================================
// STATE & VARIABLES
// ============================================
let currentUser = null;
let userToken = null;
let userData = null;
let isChecking = false;
let refreshInterval = null;
let apiConnected = false;
let currentTab = 'results';

// ============================================
// DOM ELEMENTS
// ============================================
const loginSection = document.getElementById('loginSection');
const dashboardSection = document.getElementById('dashboardSection');
const loginBtn = document.getElementById('loginBtn');
const logoutBtn = document.getElementById('logoutBtn');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const cookiesInput = document.getElementById('cookiesInput');
const sampleBtn = document.getElementById('sampleBtn');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const testBtn = document.getElementById('testBtn');
const clearBtn = document.getElementById('clearBtn');
const exportBtn = document.getElementById('exportBtn');
const exportValidBtn = document.getElementById('exportValidBtn');
const refreshLogs = document.getElementById('refreshLogs');
const resultsBody = document.getElementById('resultsBody');
const noResults = document.getElementById('noResults');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressPercent = document.getElementById('progressPercent');
const progressText = document.getElementById('progressText');
const apiStatusIcon = document.getElementById('apiStatusIcon');
const apiStatusText = document.getElementById('apiStatusText');
const cookieCount = document.getElementById('cookieCount');
const currentTime = document.getElementById('currentTime');
const logsList = document.getElementById('logsList');
const validList = document.getElementById('validList');

// User info elements
const userName = document.getElementById('userName');
const userExpiry = document.getElementById('userExpiry');
const daysLeft = document.getElementById('daysLeft');
const loginCount = document.getElementById('loginCount');
const totalChecks = document.getElementById('totalChecks');
const totalCookies = document.getElementById('totalCookies');

// Stats elements
const validCount = document.getElementById('validCount');
const invalidCount = document.getElementById('invalidCount');
const totalRobux = document.getElementById('totalRobux');
const premiumCount = document.getElementById('premiumCount');

// Logs stats elements
const totalChecksLog = document.getElementById('totalChecksLog');
const validCookiesLog = document.getElementById('validCookiesLog');
const invalidCookiesLog = document.getElementById('invalidCookiesLog');
const totalRobuxLog = document.getElementById('totalRobuxLog');

// Tab elements
const tabButtons = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

// Toast elements
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toastMessage');
const toastIcon = document.getElementById('toastIcon');
const toastClose = document.getElementById('toastClose');

// ============================================
// EVENT LISTENERS
// ============================================
loginBtn.addEventListener('click', handleLogin);
logoutBtn.addEventListener('click', handleLogout);
usernameInput.addEventListener('keypress', (e) => e.key === 'Enter' && handleLogin());
passwordInput.addEventListener('keypress', (e) => e.key === 'Enter' && handleLogin());
cookiesInput.addEventListener('input', updateCookieCount);
sampleBtn.addEventListener('click', addSampleCookie);
startBtn.addEventListener('click', startChecking);
stopBtn.addEventListener('click', stopChecking);
testBtn.addEventListener('click', testSingleCookie);
clearBtn.addEventListener('click', clearResults);
exportBtn.addEventListener('click', exportValidCookies);
exportValidBtn.addEventListener('click', exportAllValidCookies);
refreshLogs.addEventListener('click', fetchLogs);
toastClose.addEventListener('click', hideToast);

// Tab buttons
tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tabId = button.getAttribute('data-tab');
        switchTab(tabId);
    });
});

// ============================================
// AUTHENTICATION FUNCTIONS
// ============================================
async function handleLogin() {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    
    if (!username || !password) {
        showToast('Username dan password harus diisi!', 'error');
        return;
    }
    
    try {
        showToast('Login...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.data.username;
            userToken = data.data.token;
            userData = data.data;
            
            // Save to localStorage
            localStorage.setItem('cookieCheckerToken', userToken);
            localStorage.setItem('cookieCheckerUser', currentUser);
            
            // Switch to dashboard
            loginSection.style.display = 'none';
            dashboardSection.style.display = 'block';
            
            showToast('Login berhasil! Selamat datang.', 'success');
            
            // Initialize dashboard
            initDashboard();
        } else {
            showToast(data.message || 'Login gagal!', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

async function handleLogout() {
    if (isChecking) {
        if (!confirm('Checking masih berjalan. Yakin ingin logout?')) {
            return;
        }
        stopChecking();
    }
    
    try {
        if (userToken) {
            await fetch(`${API_BASE_URL}/api/auth/logout`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: userToken })
            });
        }
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    // Clear state
    currentUser = null;
    userToken = null;
    userData = null;
    localStorage.removeItem('cookieCheckerToken');
    localStorage.removeItem('cookieCheckerUser');
    
    // Switch to login
    dashboardSection.style.display = 'none';
    loginSection.style.display = 'flex';
    usernameInput.value = '';
    passwordInput.value = '';
    
    // Stop auto-refresh
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    showToast('Logout berhasil!', 'info');
}

async function verifyToken() {
    const token = localStorage.getItem('cookieCheckerToken');
    
    if (!token) return false;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser = localStorage.getItem('cookieCheckerUser');
            userToken = token;
            userData = data.data;
            return true;
        }
    } catch (error) {
        console.error('Token verification error:', error);
    }
    
    return false;
}

// ============================================
// DASHBOARD INITIALIZATION
// ============================================
async function initDashboard() {
    try {
        // Load user stats
        await loadUserStats();
        
        // Update user info
        updateUserInfo();
        
        // Start auto-refresh
        startAutoRefresh();
        
        // Start time updater
        updateCurrentTime();
        setInterval(updateCurrentTime, 1000);
        
        // Check API connection
        checkApiConnection();
        
        // Load existing results
        fetchResults();
        fetchLogs();
        
        // Update cookie count
        updateCookieCount();
        
    } catch (error) {
        console.error('Dashboard init error:', error);
        showToast('Error menginisialisasi dashboard', 'error');
    }
}

async function loadUserStats() {
    try {
        // Simulated user stats - in real app, fetch from API
        const now = new Date();
        const expiry = userData?.expires_at ? new Date(userData.expires_at) : new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
        const days = Math.max(0, Math.ceil((expiry - now) / (1000 * 60 * 60 * 24)));
        
        userData = {
            ...userData,
            days_left: days || 0,
            login_count: userData?.login_count || 1,
            total_checks: localStorage.getItem('user_total_checks') || 0,
            total_cookies: localStorage.getItem('user_total_cookies') || 0
        };
    } catch (error) {
        console.error('Load user stats error:', error);
    }
}

function updateUserInfo() {
    if (!userData) return;
    
    userName.textContent = currentUser;
    
    if (userData.expires_at) {
        const expiry = new Date(userData.expires_at);
        userExpiry.textContent = `Expires: ${expiry.toLocaleDateString()}`;
    }
    
    daysLeft.textContent = userData.days_left || 0;
    loginCount.textContent = userData.login_count || 1;
    totalChecks.textContent = userData.total_checks || 0;
    totalCookies.textContent = userData.total_cookies || 0;
}

function startAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    refreshInterval = setInterval(() => {
        updateStatus();
        if (isChecking) {
            fetchResults();
        }
        updateCurrentTime();
    }, 3000); // Update setiap 3 detik
}

// ============================================
// API CONNECTION
// ============================================
async function checkApiConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/check`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });
        
        if (response.ok) {
            apiConnected = true;
            apiStatusIcon.className = 'fas fa-wifi';
            apiStatusText.textContent = 'API Connected';
            apiStatusIcon.style.color = '#2ecc71';
        } else {
            throw new Error('API not responding');
        }
    } catch (error) {
        apiConnected = false;
        apiStatusIcon.className = 'fas fa-wifi-slash';
        apiStatusText.textContent = 'API Disconnected';
        apiStatusIcon.style.color = '#e74c3c';
        showToast('API tidak terhubung. Periksa koneksi.', 'error');
    }
}

// ============================================
// COOKIE UTILITIES
// ============================================
function parseCookies(text) {
    if (!text) return [];
    
    return text.split('\n')
        .map(line => line.trim())
        .filter(line => {
            return line.length > 0 && 
                   (line.includes('_|WARNING:-DO-NOT-SHARE-THIS.') || 
                    line.length > 50);
        });
}

function updateCookieCount() {
    const cookies = parseCookies(cookiesInput.value);
    const count = cookies.length;
    cookieCount.textContent = `${count} cookies ditemukan`;
    cookieCount.style.color = count > 0 ? '#2ecc71' : '#e74c3c';
    
    // Update button states
    startBtn.disabled = count === 0;
    testBtn.disabled = count === 0;
}

function addSampleCookie() {
    if (!cookiesInput.value.includes(SAMPLE_COOKIE)) {
        if (cookiesInput.value.trim()) {
            cookiesInput.value += '\n' + SAMPLE_COOKIE;
        } else {
            cookiesInput.value = SAMPLE_COOKIE;
        }
        updateCookieCount();
        showToast('Sample cookie ditambahkan', 'info');
    } else {
        showToast('Sample cookie sudah ada', 'warning');
    }
}

// ============================================
// CONTROL FUNCTIONS
// ============================================
async function startChecking() {
    const cookies = parseCookies(cookiesInput.value);
    
    if (cookies.length === 0) {
        showToast('Masukkan cookies terlebih dahulu!', 'error');
        return;
    }
    
    if (cookies.length > 100) {
        if (!confirm(`Anda akan check ${cookies.length} cookies. Ini mungkin butuh waktu lama. Lanjutkan?`)) {
            return;
        }
    }
    
    if (!apiConnected) {
        showToast('API tidak terhubung. Tidak dapat memulai checking.', 'error');
        return;
    }
    
    try {
        showToast(`Memulai checking ${cookies.length} cookies...`, 'info');
        
        const response = await fetch(`${API_BASE_URL}/api/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'start',
                cookies: cookies
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            isChecking = true;
            startBtn.disabled = true;
            stopBtn.disabled = false;
            progressSection.style.display = 'block';
            showToast(`Checking dimulai! ${data.total} cookies`, 'success');
            
            // Update user stats
            const currentChecks = parseInt(userData.total_checks || 0) + 1;
            const currentCookies = parseInt(userData.total_cookies || 0) + cookies.length;
            userData.total_checks = currentChecks;
            userData.total_cookies = currentCookies;
            localStorage.setItem('user_total_checks', currentChecks);
            localStorage.setItem('user_total_cookies', currentCookies);
            updateUserInfo();
        } else {
            showToast(data.error || 'Gagal memulai checking', 'error');
        }
    } catch (error) {
        console.error('Start checking error:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

async function stopChecking() {
    if (!isChecking) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'stop' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            isChecking = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;
            showToast('Checking dihentikan!', 'warning');
        }
    } catch (error) {
        showToast('Error menghentikan checking: ' + error.message, 'error');
    }
}

async function testSingleCookie() {
    const cookies = parseCookies(cookiesInput.value);
    
    if (cookies.length === 0) {
        showToast('Masukkan cookie terlebih dahulu!', 'error');
        return;
    }
    
    const cookie = cookies[0];
    
    try {
        showToast('Testing cookie...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/api/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'test',
                cookie: cookie
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        // Add to table
        addResultToTable(result);
        noResults.style.display = 'none';
        
        // Update stats
        updateStatsFromResult(result);
        
        // Update user stats
        const currentChecks = parseInt(userData.total_checks || 0) + 1;
        const currentCookies = parseInt(userData.total_cookies || 0) + 1;
        userData.total_checks = currentChecks;
        userData.total_cookies = currentCookies;
        localStorage.setItem('user_total_checks', currentChecks);
        localStorage.setItem('user_total_cookies', currentCookies);
        updateUserInfo();
        
        showToast(`Test selesai: ${result.status}`, 
            result.status === 'valid' ? 'success' : 'error');
            
    } catch (error) {
        console.error('Test error:', error);
        showToast('Error testing: ' + error.message, 'error');
    }
}

async function clearResults() {
    if (!confirm('Yakin ingin menghapus semua hasil?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'clear' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Clear UI
            resultsBody.innerHTML = '';
            noResults.style.display = 'flex';
            
            // Reset stats
            validCount.textContent = '0';
            invalidCount.textContent = '0';
            totalRobux.textContent = '0';
            premiumCount.textContent = '0';
            
            // Clear logs
            logsList.innerHTML = '';
            validList.innerHTML = '';
            
            showToast('Semua hasil dibersihkan!', 'info');
        }
    } catch (error) {
        showToast('Error membersihkan hasil: ' + error.message, 'error');
    }
}

async function exportValidCookies() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'export' })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Create download
            const blob = new Blob([data.export_data], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = data.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showToast(`File diexport: ${data.filename}`, 'success');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast('Error mengexport: ' + error.message, 'error');
    }
}

async function exportAllValidCookies() {
    // Similar to exportValidCookies but for all valid accounts
    await exportValidCookies();
}

// ============================================
// STATUS & PROGRESS UPDATES
// ============================================
async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/check`);
        
        if (!response.ok) {
            throw new Error('API not responding');
        }
        
        const status = await response.json();
        
        // Update button states
        isChecking = status.is_checking;
        startBtn.disabled = isChecking;
        stopBtn.disabled = !isChecking;
        
        // Update progress if running
        if (status.status === 'running' && status.stats) {
            progressSection.style.display = 'block';
            progressFill.style.width = `${status.stats.progress}%`;
            progressPercent.textContent = `${status.stats.progress}%`;
            progressText.textContent = 
                `Checking ${status.stats.current} dari ${status.stats.total} cookies`;
            
            // Update stats
            validCount.textContent = status.stats.valid;
            invalidCount.textContent = status.stats.invalid;
            totalRobux.textContent = status.stats.robux.toLocaleString();
            premiumCount.textContent = status.stats.premium;
            
            // Auto-refetch results
            fetchResults();
        } else if (status.status === 'completed' || status.status === 'stopped') {
            progressSection.style.display = 'none';
        }
        
    } catch (error) {
        console.error('Status update error:', error);
    }
}

// ============================================
// RESULTS MANAGEMENT
// ============================================
async function fetchResults() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/check?action=results`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const results = await response.json();
        
        if (results && results.length > 0) {
            // Sort by timestamp (newest first)
            results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            // Update table
            updateResultsTable(results);
            noResults.style.display = 'none';
            
            // Update stats from results
            updateStatsFromResults(results);
        } else if (resultsBody.children.length === 0) {
            noResults.style.display = 'flex';
        }
    } catch (error) {
        console.error('Fetch results error:', error);
    }
}

function updateResultsTable(results) {
    // Clear existing rows
    resultsBody.innerHTML = '';
    
    // Add new rows (limit to 50)
    results.slice(0, 50).forEach(result => {
        addResultToTable(result);
    });
}

function addResultToTable(result) {
    const row = document.createElement('tr');
    
    // Format waktu
    const time = new Date(result.timestamp || new Date());
    const timeStr = time.toLocaleTimeString('id-ID', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    });
    
    // Status badge
    let statusBadge = '';
    switch(result.status) {
        case 'valid':
            statusBadge = '<span class="badge badge-valid">VALID</span>';
            row.style.borderLeft = '4px solid #2ecc71';
            break;
        case 'invalid':
            statusBadge = '<span class="badge badge-invalid">INVALID</span>';
            row.style.borderLeft = '4px solid #e74c3c';
            break;
        case 'rate_limited':
            statusBadge = '<span class="badge badge-rate_limited">RATE LIMITED</span>';
            row.style.borderLeft = '4px solid #9b59b6';
            break;
        default:
            statusBadge = '<span class="badge badge-error">ERROR</span>';
            row.style.borderLeft = '4px solid #f39c12';
    }
    
    row.innerHTML = `
        <td>${result.cookie_id + 1}</td>
        <td>${statusBadge}</td>
        <td><strong>${result.username}</strong></td>
        <td>${result.display_name || result.username}</td>
        <td class="robux-cell">${(result.robux || 0).toLocaleString()}</td>
        <td>${result.premium ? '<i class="fas fa-crown premium-icon"></i>' : '-'}</td>
        <td>${result.friends_count || 0}</td>
        <td class="error-cell" title="${result.error || ''}">${result.error || '-'}</td>
        <td>${timeStr}</td>
    `;
    
    // Add animation for new rows
    row.style.opacity = '0';
    row.style.transform = 'translateY(-10px)';
    resultsBody.prepend(row);
    
    // Animate in
    setTimeout(() => {
        row.style.transition = 'all 0.3s ease';
        row.style.opacity = '1';
        row.style.transform = 'translateY(0)';
    }, 10);
    
    // Limit rows to 50
    const rows = resultsBody.querySelectorAll('tr');
    if (rows.length > 50) {
        rows[rows.length - 1].remove();
    }
}

function updateStatsFromResult(result) {
    if (result.status === 'valid') {
        const currentValid = parseInt(validCount.textContent) || 0;
        validCount.textContent = currentValid + 1;
        
        const currentRobux = parseInt(totalRobux.textContent.replace(/,/g, '')) || 0;
        totalRobux.textContent = (currentRobux + (result.robux || 0)).toLocaleString();
        
        if (result.premium) {
            const currentPremium = parseInt(premiumCount.textContent) || 0;
            premiumCount.textContent = currentPremium + 1;
        }
    } else {
        const currentInvalid = parseInt(invalidCount.textContent) || 0;
        invalidCount.textContent = currentInvalid + 1;
    }
}

function updateStatsFromResults(results) {
    const valid = results.filter(r => r.status === 'valid').length;
    const invalid = results.filter(r => r.status !== 'valid').length;
    const robux = results.reduce((sum, r) => sum + (r.robux || 0), 0);
    const premium = results.filter(r => r.premium).length;
    
    validCount.textContent = valid;
    invalidCount.textContent = invalid;
    totalRobux.textContent = robux.toLocaleString();
    premiumCount.textContent = premium;
}

// ============================================
// LOGS & VALID ACCOUNTS
// ============================================
async function fetchLogs() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/check?action=logs`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update logs stats
        totalChecksLog.textContent = data.total_results;
        validCookiesLog.textContent = data.valid_count;
        invalidCookiesLog.textContent = data.invalid_count;
        totalRobuxLog.textContent = data.total_robux.toLocaleString();
        
        // Update logs list
        updateLogsList(data.all_logs);
        
        // Update valid accounts list
        updateValidAccountsList(data.valid_cookies);
        
    } catch (error) {
        console.error('Fetch logs error:', error);
    }
}

function updateLogsList(logs) {
    logsList.innerHTML = '';
    
    if (!logs || logs.length === 0) {
        logsList.innerHTML = '<div class="log-item">Belum ada logs</div>';
        return;
    }
    
    // Show latest 20 logs
    logs.slice(0, 20).forEach(log => {
        const logItem = document.createElement('div');
        logItem.className = `log-item ${log.status}`;
        
        const time = new Date(log.timestamp);
        const timeStr = time.toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        logItem.innerHTML = `
            <div class="log-header">
                <span class="log-username">${log.username}</span>
                <span class="log-time">${timeStr}</span>
            </div>
            <div class="log-details">
                <span>Status: ${log.status}</span>
                ${log.robux ? `<span>Robux: ${log.robux.toLocaleString()}</span>` : ''}
                ${log.premium ? '<span>Premium: Yes</span>' : ''}
                ${log.error ? `<span>Error: ${log.error}</span>` : ''}
            </div>
        `;
        
        logsList.appendChild(logItem);
    });
}

function updateValidAccountsList(validCookies) {
    validList.innerHTML = '';
    
    if (!validCookies || validCookies.length === 0) {
        validList.innerHTML = '<div class="valid-account-card">Belum ada akun valid</div>';
        return;
    }
    
    validCookies.slice(0, 20).forEach(account => {
        const accountCard = document.createElement('div');
        accountCard.className = 'valid-account-card';
        
        const time = new Date(account.timestamp);
        const timeStr = time.toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        accountCard.innerHTML = `
            <div class="valid-account-header">
                <div class="valid-account-name">
                    <h4>${account.username}</h4>
                    <p>${account.display_name}</p>
                </div>
                <div class="valid-account-robux">
                    ${account.robux.toLocaleString()} Robux
                </div>
            </div>
            <div class="valid-account-details">
                <div class="detail-item">
                    <i class="fas fa-id-card"></i>
                    <span>ID: ${account.user_id}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-crown"></i>
                    <span>Premium: ${account.premium ? 'Yes' : 'No'}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-user-friends"></i>
                    <span>Friends: ${account.friends}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-clock"></i>
                    <span>${timeStr}</span>
                </div>
            </div>
        `;
        
        validList.appendChild(accountCard);
    });
}

// ============================================
// TAB MANAGEMENT
// ============================================
function switchTab(tabId) {
    // Update active tab button
    tabButtons.forEach(button => {
        button.classList.remove('active');
        if (button.getAttribute('data-tab') === tabId) {
            button.classList.add('active');
        }
    });
    
    // Update active tab content
    tabContents.forEach(content => {
        content.classList.remove('active');
        if (content.id === `${tabId}-tab`) {
            content.classList.add('active');
        }
    });
    
    currentTab = tabId;
    
    // Refresh data for the active tab
    if (tabId === 'logs' || tabId === 'valid') {
        fetchLogs();
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function updateCurrentTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('id-ID', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const dateStr = now.toLocaleDateString('id-ID', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    currentTime.textContent = `${dateStr} • ${timeStr}`;
}

function showToast(message, type = 'info') {
    // Set content
    toastMessage.textContent = message;
    
    // Set type styling
    toast.className = 'toast ' + type;
    
    // Set icon based on type
    switch(type) {
        case 'success':
            toastIcon.className = 'fas fa-check-circle';
            break;
        case 'error':
            toastIcon.className = 'fas fa-exclamation-circle';
            break;
        case 'warning':
            toastIcon.className = 'fas fa-exclamation-triangle';
            break;
        default:
            toastIcon.className = 'fas fa-info-circle';
    }
    
    // Show toast
    toast.classList.add('show');
    
    // Auto-hide after 5 seconds
    setTimeout(hideToast, 5000);
}

function hideToast() {
    toast.classList.remove('show');
}

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', async function() {
    // Check if user is already logged in
    const isLoggedIn = await verifyToken();
    
    if (isLoggedIn) {
        // Auto login
        loginSection.style.display = 'none';
        dashboardSection.style.display = 'block';
        await initDashboard();
    } else {
        // Show login
        loginSection.style.display = 'flex';
        dashboardSection.style.display = 'none';
        
        // Focus username field
        setTimeout(() => usernameInput.focus(), 100);
    }
    
    // Initial cookie count
    updateCookieCount();
    
    // Show welcome message
    setTimeout(() => {
        if (!isLoggedIn) {
            showToast('Selamat datang! Login dengan akun yang diberikan admin.', 'info');
        }
    }, 1000);
});