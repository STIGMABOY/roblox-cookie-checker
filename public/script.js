// ============================================
// KONFIGURASI OPTIMIZED
// ============================================
const API_BASE_URL = window.location.origin;
const SAMPLE_COOKIE = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_testcookie123";
const MAX_COOKIES_PER_BATCH = 500; // Batasi jumlah cookie per batch

// ============================================
// STATE & VARIABLES
// ============================================
let currentUser = null;
let userToken = null;
let userData = null;
let isChecking = false;
let currentBatchId = null;
let refreshInterval = null;
let apiConnected = false;
let currentTab = 'results';
let checkStartTime = null;
let batchResults = [];

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

// Create batch info element dynamically
const batchInfoHTML = `
<div class="batch-info" id="batchInfo" style="display: none;">
    <div class="batch-header">
        <h4><i class="fas fa-layer-group"></i> Batch Information</h4>
        <div class="batch-actions">
            <button id="pauseResumeBtn" class="btn-pause-resume" style="display: none;">
                <i class="fas fa-pause"></i> Pause
            </button>
            <button id="batchExportBtn" class="btn-batch-export">
                <i class="fas fa-download"></i> Export This Batch
            </button>
        </div>
    </div>
    <div class="batch-stats">
        <div class="batch-stat">
            <span class="batch-stat-label">Batch ID:</span>
            <span class="batch-stat-value" id="batchId">-</span>
        </div>
        <div class="batch-stat">
            <span class="batch-stat-label">Speed:</span>
            <span class="batch-stat-value" id="checkSpeed">0/sec</span>
        </div>
        <div class="batch-stat">
            <span class="batch-stat-label">ETA:</span>
            <span class="batch-stat-value" id="checkETA">-</span>
        </div>
        <div class="batch-stat">
            <span class="batch-stat-label">Concurrent:</span>
            <span class="batch-stat-value" id="concurrentChecks">3</span>
        </div>
    </div>
    <div class="batch-progress-info">
        <div class="progress-detail">
            <span>Processed: </span>
            <span id="processedCount">0</span> / 
            <span id="totalCount">0</span>
        </div>
        <div class="progress-detail">
            <span>Success Rate: </span>
            <span id="successRate">0%</span>
        </div>
    </div>
</div>
`;

// Insert batch info after progress section
const progressSectionElement = document.querySelector('.progress-section');
if (progressSectionElement) {
    progressSectionElement.insertAdjacentHTML('afterend', batchInfoHTML);
}

// Get new batch elements
const batchInfo = document.getElementById('batchInfo');
const batchIdElement = document.getElementById('batchId');
const checkSpeedElement = document.getElementById('checkSpeed');
const checkETAElement = document.getElementById('checkETA');
const concurrentChecksElement = document.getElementById('concurrentChecks');
const processedCountElement = document.getElementById('processedCount');
const totalCountElement = document.getElementById('totalCount');
const successRateElement = document.getElementById('successRate');
const batchExportBtn = document.getElementById('batchExportBtn');
const pauseResumeBtn = document.getElementById('pauseResumeBtn');

// ============================================
// EVENT LISTENERS
// ============================================
loginBtn.addEventListener('click', handleLogin);
logoutBtn.addEventListener('click', handleLogout);
usernameInput.addEventListener('keypress', (e) => e.key === 'Enter' && handleLogin());
passwordInput.addEventListener('keypress', (e) => e.key === 'Enter' && handleLogin());
cookiesInput.addEventListener('input', updateCookieCount);
sampleBtn.addEventListener('click', addSampleCookie);
startBtn.addEventListener('click', startCheckingOptimized);
stopBtn.addEventListener('click', stopChecking);
testBtn.addEventListener('click', testSingleCookie);
clearBtn.addEventListener('click', clearResults);
exportBtn.addEventListener('click', exportValidCookies);
exportValidBtn.addEventListener('click', exportAllValidCookies);
refreshLogs.addEventListener('click', fetchLogs);
toastClose.addEventListener('click', hideToast);
batchExportBtn.addEventListener('click', exportBatchCookies);
pauseResumeBtn.addEventListener('click', togglePauseResume);

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
            initDashboardOptimized();
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
// OPTIMIZED DASHBOARD INITIALIZATION
// ============================================
async function initDashboardOptimized() {
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
        
        // Check for existing batch
        checkExistingBatch();
        
    } catch (error) {
        console.error('Dashboard init error:', error);
        showToast('Error menginisialisasi dashboard', 'error');
    }
}

async function loadUserStats() {
    try {
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
        if (isChecking && currentBatchId) {
            updateBatchStatus();
        } else {
            updateStatus();
        }
        updateCurrentTime();
    }, 3000);
}

// ============================================
// OPTIMIZED CHECKING FUNCTIONS
// ============================================

async function startCheckingOptimized() {
    const cookies = parseCookies(cookiesInput.value);
    
    if (cookies.length === 0) {
        showToast('Masukkan cookies terlebih dahulu!', 'error');
        return;
    }
    
    const { validCookies, invalidCookies } = validateCookies(cookies);
    
    if (invalidCookies.length > 0) {
        showToast(`${invalidCookies.length} cookies format tidak valid. Akan di-skip.`, 'warning');
    }
    
    if (validCookies.length === 0) {
        showToast('Tidak ada cookie yang valid untuk di-check!', 'error');
        return;
    }
    
    if (validCookies.length > MAX_COOKIES_PER_BATCH) {
        if (!confirm(`Anda akan check ${validCookies.length} cookies (max ${MAX_COOKIES_PER_BATCH}). Hanya ${MAX_COOKIES_PER_BATCH} pertama yang akan diproses. Lanjutkan?`)) {
            return;
        }
    }
    
    if (!apiConnected) {
        showToast('API tidak terhubung. Tidak dapat memulai checking.', 'error');
        return;
    }
    
    // Reset batch info
    currentBatchId = null;
    checkStartTime = Date.now();
    batchResults = [];
    
    try {
        showToast(`Memulai checking ${Math.min(validCookies.length, MAX_COOKIES_PER_BATCH)} cookies...`, 'info');
        
        // Limit cookies jika terlalu banyak
        const cookiesToCheck = validCookies.slice(0, MAX_COOKIES_PER_BATCH);
        
        const response = await fetch(`${API_BASE_URL}/api/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'start',
                cookies: cookiesToCheck
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            isChecking = true;
            currentBatchId = data.batch_id;
            
            // Update UI
            startBtn.disabled = true;
            stopBtn.disabled = false;
            progressSection.style.display = 'block';
            batchInfo.style.display = 'block';
            
            // Update batch info
            batchIdElement.textContent = currentBatchId;
            totalCountElement.textContent = data.total;
            processedCountElement.textContent = '0';
            
            // Show pause button
            pauseResumeBtn.style.display = 'flex';
            pauseResumeBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
            
            showToast(`Checking dimulai! Batch ID: ${currentBatchId}`, 'success');
            
            // Start monitoring
            startBatchMonitoring();
            
            // Update user stats
            updateUserStatsAfterStart(cookiesToCheck.length);
            
        } else if (data.batch_id) {
            // Already running, join existing batch
            currentBatchId = data.batch_id;
            showToast(`Bergabung dengan batch yang sedang berjalan: ${currentBatchId}`, 'info');
            startBatchMonitoring();
        } else {
            showToast(data.message || 'Gagal memulai checking', 'error');
        }
    } catch (error) {
        console.error('Start checking error:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

async function startBatchMonitoring() {
    if (!currentBatchId) return;
    
    // Update status every 2 seconds
    if (refreshInterval) clearInterval(refreshInterval);
    
    refreshInterval = setInterval(async () => {
        await updateBatchStatus();
    }, 2000);
}

async function updateBatchStatus() {
    try {
        // Get batch status
        const statusResponse = await fetch(`${API_BASE_URL}/api/check?batch=${currentBatchId}`);
        if (statusResponse.ok) {
            const batchData = await statusResponse.json();
            
            if (batchData.success) {
                // Update progress
                const progress = Math.round((batchData.total_checked / batchData.total) * 100);
                progressFill.style.width = `${progress}%`;
                progressPercent.textContent = `${progress}%`;
                
                // Update counts
                processedCountElement.textContent = batchData.total_checked;
                
                // Update stats
                validCount.textContent = batchData.valid || 0;
                invalidCount.textContent = batchData.invalid || 0;
                
                // Calculate success rate
                if (batchData.total_checked > 0) {
                    const successRate = Math.round((batchData.valid / batchData.total_checked) * 100);
                    successRateElement.textContent = `${successRate}%`;
                }
                
                // Calculate speed and ETA
                if (checkStartTime && batchData.total_checked > 0) {
                    const elapsedSeconds = (Date.now() - checkStartTime) / 1000;
                    const speed = batchData.total_checked / elapsedSeconds;
                    checkSpeedElement.textContent = `${speed.toFixed(1)}/sec`;
                    
                    if (speed > 0 && batchData.total) {
                        const remaining = batchData.total - batchData.total_checked;
                        const etaSeconds = remaining / speed;
                        checkETAElement.textContent = formatTime(etaSeconds);
                    }
                }
                
                // Update progress text
                progressText.textContent = 
                    `Checking ${batchData.total_checked} dari ${batchData.total} cookies`;
                
                // Store batch results
                if (batchData.results) {
                    batchResults = batchData.results;
                    updateResultsTable(batchResults);
                }
                
                // If completed
                if (batchData.completed || !batchData.is_running) {
                    isChecking = false;
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    pauseResumeBtn.style.display = 'none';
                    
                    // Show completion message
                    showToast(`Checking selesai! ${batchData.valid} valid, ${batchData.invalid} invalid`, 'success');
                    
                    // Auto-refresh results
                    fetchResults();
                    fetchLogs();
                    
                    // Clear interval
                    if (refreshInterval) {
                        clearInterval(refreshInterval);
                        refreshInterval = null;
                    }
                }
            }
        }
        
        // Also get general status
        await updateStatus();
        
    } catch (error) {
        console.error('Batch monitoring error:', error);
    }
}

async function stopChecking() {
    if (!isChecking && !currentBatchId) return;
    
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
            progressSection.style.display = 'none';
            pauseResumeBtn.style.display = 'none';
            
            if (refreshInterval) {
                clearInterval(refreshInterval);
                refreshInterval = null;
            }
            
            showToast(`Checking dihentikan! Total checked: ${data.total_checked}`, 'warning');
            
            // Fetch final results
            fetchResults();
            fetchLogs();
        }
    } catch (error) {
        showToast('Error menghentikan checking: ' + error.message, 'error');
    }
}

async function togglePauseResume() {
    if (!currentBatchId) return;
    
    try {
        // First get current status
        const statusResponse = await fetch(`${API_BASE_URL}/api/check?batch=${currentBatchId}`);
        if (statusResponse.ok) {
            const batchData = await statusResponse.json();
            
            if (batchData.success) {
                const action = batchData.status === 'paused' ? 'resume' : 'pause';
                
                const response = await fetch(`${API_BASE_URL}/api/check`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: action })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    if (action === 'pause') {
                        pauseResumeBtn.innerHTML = '<i class="fas fa-play"></i> Resume';
                        showToast('Checking dijeda', 'info');
                    } else {
                        pauseResumeBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
                        showToast('Checking dilanjutkan', 'success');
                    }
                }
            }
        }
    } catch (error) {
        console.error('Pause/resume error:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

// ============================================
// EXPORT FUNCTIONS
// ============================================

async function exportBatchCookies() {
    if (!currentBatchId) {
        showToast('Tidak ada batch aktif untuk diexport', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'export',
                batch_id: currentBatchId
            })
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
            
            showToast(`Exported ${data.valid_count} valid cookies (${data.total_robux} Robux)`, 'success');
        }
    } catch (error) {
        console.error('Export batch error:', error);
        showToast('Error mengexport batch: ' + error.message, 'error');
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
    await exportValidCookies();
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function parseCookies(text) {
    if (!text) return [];
    
    return text.split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
}

function validateCookies(cookies) {
    const validCookies = [];
    const invalidCookies = [];
    
    cookies.forEach((cookie, index) => {
        if (cookie.includes('_|WARNING:-DO-NOT-SHARE-THIS.')) {
            validCookies.push(cookie);
        } else if (cookie.length > 50) {
            // Might be a cookie without warning prefix
            validCookies.push(cookie);
        } else {
            invalidCookies.push({
                index: index + 1,
                cookie: cookie.substring(0, 50) + '...'
            });
        }
    });
    
    return { validCookies, invalidCookies };
}

function updateCookieCount() {
    const cookies = parseCookies(cookiesInput.value);
    const { validCookies, invalidCookies } = validateCookies(cookies);
    const count = validCookies.length;
    
    cookieCount.textContent = `${count} valid cookies ditemukan`;
    if (invalidCookies.length > 0) {
        cookieCount.textContent += `, ${invalidCookies.length} invalid`;
    }
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

function formatTime(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)} detik`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        return `${minutes}m ${secs}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.round((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

function updateUserStatsAfterStart(cookiesCount) {
    const currentChecks = parseInt(userData.total_checks || 0) + 1;
    const currentCookies = parseInt(userData.total_cookies || 0) + cookiesCount;
    userData.total_checks = currentChecks;
    userData.total_cookies = currentCookies;
    localStorage.setItem('user_total_checks', currentChecks);
    localStorage.setItem('user_total_cookies', currentCookies);
    updateUserInfo();
}

// ============================================
// EXISTING FUNCTIONS (updated)
// ============================================

async function testSingleCookie() {
    const cookies = parseCookies(cookiesInput.value);
    const { validCookies } = validateCookies(cookies);
    
    if (validCookies.length === 0) {
        showToast('Masukkan cookie valid terlebih dahulu!', 'error');
        return;
    }
    
    const cookie = validCookies[0];
    
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
        updateUserStatsAfterStart(1);
        
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
            
            // Hide batch info
            batchInfo.style.display = 'none';
            currentBatchId = null;
            
            showToast('Semua hasil dibersihkan!', 'info');
        }
    } catch (error) {
        showToast('Error membersihkan hasil: ' + error.message, 'error');
    }
}

// ============================================
// API CONNECTION & STATUS
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
        
        if (status.status === 'running' && status.stats) {
            // Update concurrent checks display
            concurrentChecksElement.textContent = status.stats.speed ? Math.round(status.stats.speed * 2) : '3';
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
    
    // Add new rows (limit to 100)
    results.slice(0, 100).forEach(result => {
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
    
    // Batch ID if available
    const batchInfo = result.batch_id ? `<br><small class="batch-id">Batch: ${result.batch_id}</small>` : '';
    
    row.innerHTML = `
        <td>${result.cookie_id + 1}</td>
        <td>${statusBadge}</td>
        <td><strong>${result.username}</strong>${batchInfo}</td>
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
    
    // Limit rows to 100
    const rows = resultsBody.querySelectorAll('tr');
    if (rows.length > 100) {
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
                ${log.batch_id ? `<span>Batch: ${log.batch_id}</span>` : ''}
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
                    ${account.batch_id ? `<small>Batch: ${account.batch_id}</small>` : ''}
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
// BATCH MANAGEMENT
// ============================================

async function checkExistingBatch() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/check`);
        
        if (response.ok) {
            const status = await response.json();
            
            if (status.is_checking && status.batch_id) {
                // Join existing batch
                currentBatchId = status.batch_id;
                isChecking = true;
                
                // Update UI
                startBtn.disabled = true;
                stopBtn.disabled = false;
                progressSection.style.display = 'block';
                batchInfo.style.display = 'block';
                pauseResumeBtn.style.display = 'flex';
                
                // Update batch info
                batchIdElement.textContent = currentBatchId;
                pauseResumeBtn.innerHTML = status.status === 'paused' 
                    ? '<i class="fas fa-play"></i> Resume'
                    : '<i class="fas fa-pause"></i> Pause';
                
                // Start monitoring
                startBatchMonitoring();
                
                showToast(`Bergabung dengan batch yang sedang berjalan: ${currentBatchId}`, 'info');
            }
        }
    } catch (error) {
        console.error('Check existing batch error:', error);
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
        await initDashboardOptimized();
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

// ============================================
// ADD CSS FOR BATCH INFO
// ============================================

const batchStyles = `
<style>
.batch-info {
    background: rgba(0, 0, 0, 0.4);
    border-radius: 12px;
    padding: 20px;
    margin-top: 20px;
    border: 1px solid rgba(76, 201, 240, 0.3);
    display: none;
}

.batch-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    flex-wrap: wrap;
    gap: 10px;
}

.batch-header h4 {
    color: #4cc9f0;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 18px;
}

.batch-actions {
    display: flex;
    gap: 10px;
    align-items: center;
}

.btn-batch-export {
    padding: 8px 16px;
    background: rgba(155, 89, 182, 0.2);
    border: 1px solid rgba(155, 89, 182, 0.3);
    border-radius: 8px;
    color: #9b59b6;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
    transition: all 0.3s;
}

.btn-batch-export:hover {
    background: rgba(155, 89, 182, 0.3);
}

.btn-pause-resume {
    padding: 8px 16px;
    background: rgba(243, 156, 18, 0.2);
    border: 1px solid rgba(243, 156, 18, 0.3);
    border-radius: 8px;
    color: #f39c12;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
    transition: all 0.3s;
}

.btn-pause-resume:hover {
    background: rgba(243, 156, 18, 0.3);
}

.batch-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
    margin-bottom: 15px;
}

.batch-stat {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.batch-stat-label {
    color: #b0b0b0;
    font-size: 14px;
}

.batch-stat-value {
    font-weight: 600;
    color: #4cc9f0;
    font-family: 'Consolas', monospace;
    font-size: 14px;
}

.batch-progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    font-size: 14px;
}

.progress-detail {
    color: #b0b0b0;
}

.progress-detail span:last-child {
    color: #4cc9f0;
    font-weight: 600;
    margin-left: 5px;
}

.batch-id {
    color: #9b59b6;
    font-size: 11px;
    display: block;
    margin-top: 2px;
}
</style>
`;

// Inject styles
document.head.insertAdjacentHTML('beforeend', batchStyles);
