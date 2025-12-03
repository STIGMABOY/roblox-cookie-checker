// ============================================
// KONFIGURASI
// ============================================
const API_BASE_URL = window.location.origin;

// ============================================
// STATE & VARIABLES
// ============================================
let adminToken = null;
let currentAdmin = null;
let allUsers = [];
let selectedUser = null;
let refreshInterval = null;

// ============================================
// DOM ELEMENTS
// ============================================
const adminLogin = document.getElementById('adminLogin');
const adminDashboard = document.getElementById('adminDashboard');
const adminLoginBtn = document.getElementById('adminLoginBtn');
const adminLogoutBtn = document.getElementById('adminLogoutBtn');
const adminUsername = document.getElementById('adminUsername');
const adminPassword = document.getElementById('adminPassword');
const adminToast = document.getElementById('adminToast');
const adminToastMessage = document.getElementById('adminToastMessage');
const adminToastIcon = document.getElementById('adminToastIcon');
const adminToastClose = document.getElementById('adminToastClose');

// Stats elements
const totalUsers = document.getElementById('totalUsers');
const activeUsers = document.getElementById('activeUsers');
const totalLogins = document.getElementById('totalLogins');
const todayLogins = document.getElementById('todayLogins');
const totalChecks = document.getElementById('totalChecks');
const totalCookies = document.getElementById('totalCookies');
const expiredUsers = document.getElementById('expiredUsers');

// Tab elements
const adminTabButtons = document.querySelectorAll('.admin-tab-btn');
const adminTabContents = document.querySelectorAll('.admin-tab-content');

// Users table
const usersTableBody = document.getElementById('usersTableBody');
const searchUsers = document.getElementById('searchUsers');
const refreshUsers = document.getElementById('refreshUsers');

// Create user form
const newUsername = document.getElementById('newUsername');
const newPassword = document.getElementById('newPassword');
const customDays = document.getElementById('customDays');
const userNotes = document.getElementById('userNotes');
const createUserBtn = document.getElementById('createUserBtn');
const durationButtons = document.querySelectorAll('.duration-btn');
const previewUsername = document.getElementById('previewUsername');
const previewDuration = document.getElementById('previewDuration');
const previewExpiry = document.getElementById('previewExpiry');

// Bulk create form
const bulkUsers = document.getElementById('bulkUsers');
const bulkDays = document.getElementById('bulkDays');
const bulkCreateBtn = document.getElementById('bulkCreateBtn');
const bulkResults = document.getElementById('bulkResults');
const successCount = document.getElementById('successCount');
const failedCount = document.getElementById('failedCount');
const successList = document.getElementById('successList');
const failedList = document.getElementById('failedList');

// Settings
const currentPassword = document.getElementById('currentPassword');
const newAdminPassword = document.getElementById('newAdminPassword');
const confirmAdminPassword = document.getElementById('confirmAdminPassword');
const updateAdminPasswordBtn = document.getElementById('updateAdminPasswordBtn');
const serverTime = document.getElementById('serverTime');
const systemTotalUsers = document.getElementById('systemTotalUsers');
const activeSessions = document.getElementById('activeSessions');
const clearExpiredBtn = document.getElementById('clearExpiredBtn');
const clearSessionsBtn = document.getElementById('clearSessionsBtn');
const refreshStatsBtn = document.getElementById('refreshStatsBtn');

// Modal
const userActionsModal = document.getElementById('userActionsModal');
const modalClose = document.querySelector('.modal-close');
const userInfoModal = document.getElementById('userInfoModal');
const extendForm = document.getElementById('extendForm');
const extendDays = document.getElementById('extendDays');
const confirmExtendBtn = document.getElementById('confirmExtendBtn');

// Time
const adminCurrentTime = document.getElementById('adminCurrentTime');

// ============================================
// EVENT LISTENERS
// ============================================
adminLoginBtn.addEventListener('click', handleAdminLogin);
adminLogoutBtn.addEventListener('click', handleAdminLogout);
adminPassword.addEventListener('keypress', (e) => e.key === 'Enter' && handleAdminLogin());
adminToastClose.addEventListener('click', hideAdminToast);

// Tab switching
adminTabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tabId = button.getAttribute('data-tab');
        switchAdminTab(tabId);
    });
});

// Create user form
durationButtons.forEach(button => {
    button.addEventListener('click', () => {
        durationButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        customDays.value = button.getAttribute('data-days');
        updateUserPreview();
    });
});

customDays.addEventListener('input', updateUserPreview);
newUsername.addEventListener('input', updateUserPreview);
createUserBtn.addEventListener('click', createUser);

// Bulk create
bulkCreateBtn.addEventListener('click', bulkCreateUsers);

// Users table
searchUsers.addEventListener('input', filterUsers);
refreshUsers.addEventListener('click', loadUsers);

// Settings
updateAdminPasswordBtn.addEventListener('click', updateAdminPassword);
clearExpiredBtn.addEventListener('click', clearExpiredUsers);
clearSessionsBtn.addEventListener('click', clearOldSessions);
refreshStatsBtn.addEventListener('click', refreshStatistics);

// Modal
modalClose.addEventListener('click', hideModal);
document.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', hideModal);
});

// Action buttons in modal
document.querySelectorAll('.btn-action').forEach(button => {
    button.addEventListener('click', (e) => {
        const action = e.currentTarget.getAttribute('data-action');
        handleUserAction(action);
    });
});

confirmExtendBtn.addEventListener('click', confirmExtension);

// ============================================
// AUTHENTICATION FUNCTIONS
// ============================================
async function handleAdminLogin() {
    const password = adminPassword.value.trim();
    
    if (!password) {
        showAdminToast('Masukkan password admin!', 'error');
        return;
    }
    
    try {
        showAdminToast('Login admin...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                username: 'admin', 
                password: password 
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.data.role === 'admin') {
            adminToken = data.data.token;
            currentAdmin = 'admin';
            
            // Save to localStorage
            localStorage.setItem('adminToken', adminToken);
            
            // Switch to dashboard
            adminLogin.style.display = 'none';
            adminDashboard.style.display = 'block';
            
            showAdminToast('Login admin berhasil!', 'success');
            
            // Initialize admin dashboard
            initAdminDashboard();
        } else {
            showAdminToast(data.message || 'Password admin salah!', 'error');
        }
    } catch (error) {
        console.error('Admin login error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

async function handleAdminLogout() {
    try {
        if (adminToken) {
            await fetch(`${API_BASE_URL}/api/auth/logout`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: adminToken })
            });
        }
    } catch (error) {
        console.error('Admin logout error:', error);
    }
    
    // Clear state
    adminToken = null;
    currentAdmin = null;
    localStorage.removeItem('adminToken');
    
    // Switch to login
    adminDashboard.style.display = 'none';
    adminLogin.style.display = 'flex';
    adminPassword.value = '';
    
    // Stop auto-refresh
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    showAdminToast('Logout admin berhasil!', 'info');
}

async function verifyAdminToken() {
    const token = localStorage.getItem('adminToken');
    
    if (!token) return false;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token })
        });
        
        const data = await response.json();
        
        if (data.success && data.data.role === 'admin') {
            adminToken = token;
            currentAdmin = data.data.username;
            return true;
        }
    } catch (error) {
        console.error('Admin token verification error:', error);
    }
    
    return false;
}

// ============================================
// ADMIN DASHBOARD INITIALIZATION
// ============================================
async function initAdminDashboard() {
    try {
        // Load dashboard stats
        await loadDashboardStats();
        
        // Load users
        await loadUsers();
        
        // Start auto-refresh
        startAdminAutoRefresh();
        
        // Start time updater
        updateAdminCurrentTime();
        setInterval(updateAdminCurrentTime, 1000);
        
        // Update system info
        updateSystemInfo();
        
        // Update user preview
        updateUserPreview();
        
    } catch (error) {
        console.error('Admin dashboard init error:', error);
        showAdminToast('Error menginisialisasi dashboard admin', 'error');
    }
}

async function loadDashboardStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/stats`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            
            totalUsers.textContent = stats.total_users;
            activeUsers.textContent = `${stats.active_users} Active`;
            totalLogins.textContent = stats.total_logins;
            todayLogins.textContent = `${stats.today_logins} Today`;
            totalChecks.textContent = stats.total_checks;
            totalCookies.textContent = `${stats.total_cookies} Cookies`;
            expiredUsers.textContent = stats.expired_users;
            
            // Update system info
            systemTotalUsers.textContent = stats.total_users;
            activeSessions.textContent = stats.active_sessions;
            
            if (stats.server_time) {
                const serverTimeDate = new Date(stats.server_time);
                serverTime.textContent = serverTimeDate.toLocaleString('id-ID');
            }
        }
    } catch (error) {
        console.error('Load dashboard stats error:', error);
    }
}

function startAdminAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    refreshInterval = setInterval(() => {
        loadDashboardStats();
        updateAdminCurrentTime();
    }, 10000); // Update setiap 10 detik
}

function updateSystemInfo() {
    // Update server time periodically
    setInterval(() => {
        const now = new Date();
        serverTime.textContent = now.toLocaleString('id-ID');
    }, 1000);
}

// ============================================
// USER MANAGEMENT
// ============================================
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/users`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            allUsers = data.users;
            renderUsersTable(allUsers);
        }
    } catch (error) {
        console.error('Load users error:', error);
        showAdminToast('Error memuat daftar user', 'error');
    }
}

function renderUsersTable(users) {
    usersTableBody.innerHTML = '';
    
    if (!users || users.length === 0) {
        usersTableBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px;">
                    <i class="fas fa-users" style="font-size: 48px; opacity: 0.3; margin-bottom: 15px;"></i>
                    <p>Belum ada user yang dibuat</p>
                </td>
            </tr>
        `;
        return;
    }
    
    users.forEach(user => {
        const row = document.createElement('tr');
        
        // Calculate days left
        const expiresAt = new Date(user.expires_at);
        const now = new Date();
        const daysLeft = Math.max(0, Math.ceil((expiresAt - now) / (1000 * 60 * 60 * 24)));
        
        // Format dates
        const createdDate = new Date(user.created_at).toLocaleDateString('id-ID');
        const expiryDate = expiresAt.toLocaleDateString('id-ID');
        
        // Status badge
        let statusBadge = '';
        if (!user.is_active) {
            statusBadge = '<span class="status-badge status-inactive">INACTIVE</span>';
        } else if (daysLeft <= 0) {
            statusBadge = '<span class="status-badge status-expired">EXPIRED</span>';
        } else {
            statusBadge = '<span class="status-badge status-active">ACTIVE</span>';
        }
        
        row.innerHTML = `
            <td><strong>${user.username}</strong></td>
            <td>${statusBadge}</td>
            <td>${createdDate}</td>
            <td>${expiryDate}</td>
            <td>${daysLeft} hari</td>
            <td>${user.login_count || 0}</td>
            <td>${user.total_checks || 0}</td>
            <td>
                <div class="admin-actions">
                    <button class="btn-action-small btn-edit" data-username="${user.username}">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn-action-small btn-extend" data-username="${user.username}">
                        <i class="fas fa-calendar-plus"></i> Extend
                    </button>
                    <button class="btn-action-small btn-delete" data-username="${user.username}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </td>
        `;
        
        usersTableBody.appendChild(row);
    });
    
    // Add event listeners to action buttons
    document.querySelectorAll('.btn-edit').forEach(button => {
        button.addEventListener('click', (e) => {
            const username = e.currentTarget.getAttribute('data-username');
            showUserActions(username);
        });
    });
    
    document.querySelectorAll('.btn-extend').forEach(button => {
        button.addEventListener('click', (e) => {
            const username = e.currentTarget.getAttribute('data-username');
            showUserActions(username);
            handleUserAction('extend');
        });
    });
    
    document.querySelectorAll('.btn-delete').forEach(button => {
        button.addEventListener('click', (e) => {
            const username = e.currentTarget.getAttribute('data-username');
            if (confirm(`Yakin ingin menghapus user ${username}?`)) {
                deleteUser(username);
            }
        });
    });
}

function filterUsers() {
    const searchTerm = searchUsers.value.toLowerCase();
    
    if (!searchTerm) {
        renderUsersTable(allUsers);
        return;
    }
    
    const filteredUsers = allUsers.filter(user => 
        user.username.toLowerCase().includes(searchTerm)
    );
    
    renderUsersTable(filteredUsers);
}

function showUserActions(username) {
    const user = allUsers.find(u => u.username === username);
    
    if (!user) {
        showAdminToast('User tidak ditemukan', 'error');
        return;
    }
    
    selectedUser = user;
    
    // Update modal info
    const expiresAt = new Date(user.expires_at);
    const now = new Date();
    const daysLeft = Math.max(0, Math.ceil((expiresAt - now) / (1000 * 60 * 60 * 24)));
    
    userInfoModal.innerHTML = `
        <p><strong>Username:</strong> ${user.username}</p>
        <p><strong>Dibuat:</strong> ${new Date(user.created_at).toLocaleString('id-ID')}</p>
        <p><strong>Kadaluarsa:</strong> ${expiresAt.toLocaleString('id-ID')}</p>
        <p><strong>Sisa hari:</strong> ${daysLeft} hari</p>
        <p><strong>Total login:</strong> ${user.login_count || 0}</p>
        <p><strong>Total checks:</strong> ${user.total_checks || 0}</p>
        <p><strong>Total cookies:</strong> ${user.total_cookies || 0}</p>
        <p><strong>Status:</strong> ${user.is_active ? 'Aktif' : 'Tidak aktif'}</p>
    `;
    
    // Show modal
    userActionsModal.classList.add('show');
}

function hideModal() {
    userActionsModal.classList.remove('show');
    selectedUser = null;
    extendForm.style.display = 'none';
}

function handleUserAction(action) {
    if (!selectedUser) return;
    
    switch(action) {
        case 'extend':
            extendForm.style.display = 'block';
            break;
            
        case 'deactivate':
            if (confirm(`Yakin ingin menonaktifkan user ${selectedUser.username}?`)) {
                deactivateUser(selectedUser.username);
            }
            break;
            
        case 'activate':
            if (confirm(`Yakin ingin mengaktifkan user ${selectedUser.username}?`)) {
                activateUser(selectedUser.username);
            }
            break;
            
        case 'delete':
            if (confirm(`Yakin ingin menghapus user ${selectedUser.username}?`)) {
                deleteUser(selectedUser.username);
            }
            break;
    }
}

async function confirmExtension() {
    if (!selectedUser) return;
    
    const additionalDays = parseInt(extendDays.value);
    
    if (!additionalDays || additionalDays < 1) {
        showAdminToast('Masukkan jumlah hari yang valid', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/extend`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: selectedUser.username,
                additional_days: additionalDays
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAdminToast(`Berhasil memperpanjang ${additionalDays} hari untuk ${selectedUser.username}`, 'success');
            hideModal();
            loadUsers();
            loadDashboardStats();
        } else {
            showAdminToast(data.message || 'Gagal memperpanjang', 'error');
        }
    } catch (error) {
        console.error('Extend user error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

async function deactivateUser(username) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/deactivate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAdminToast(`User ${username} dinonaktifkan`, 'success');
            hideModal();
            loadUsers();
            loadDashboardStats();
        } else {
            showAdminToast(data.message || 'Gagal menonaktifkan user', 'error');
        }
    } catch (error) {
        console.error('Deactivate user error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

async function activateUser(username) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/activate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAdminToast(`User ${username} diaktifkan`, 'success');
            hideModal();
            loadUsers();
            loadDashboardStats();
        } else {
            showAdminToast(data.message || 'Gagal mengaktifkan user', 'error');
        }
    } catch (error) {
        console.error('Activate user error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

async function deleteUser(username) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/user/${username}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Accept': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAdminToast(`User ${username} dihapus`, 'success');
            hideModal();
            loadUsers();
            loadDashboardStats();
        } else {
            showAdminToast(data.message || 'Gagal menghapus user', 'error');
        }
    } catch (error) {
        console.error('Delete user error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

// ============================================
// CREATE USER FUNCTIONS
// ============================================
function updateUserPreview() {
    const username = newUsername.value.trim() || '[username]';
    const days = parseInt(customDays.value) || 30;
    
    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + days);
    
    previewUsername.textContent = username;
    previewDuration.textContent = `${days} hari`;
    previewExpiry.textContent = expiryDate.toLocaleDateString('id-ID');
}

async function createUser() {
    const username = newUsername.value.trim();
    const password = newPassword.value.trim();
    const days = parseInt(customDays.value) || 30;
    const notes = userNotes.value.trim();
    
    if (!username || !password) {
        showAdminToast('Username dan password harus diisi!', 'error');
        return;
    }
    
    if (password.length < 6) {
        showAdminToast('Password minimal 6 karakter', 'error');
        return;
    }
    
    try {
        showAdminToast('Membuat user...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/api/auth/create_user`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                password,
                days_valid: days
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAdminToast(`User ${username} berhasil dibuat untuk ${days} hari`, 'success');
            
            // Reset form
            newUsername.value = '';
            newPassword.value = '';
            userNotes.value = '';
            
            // Switch to users tab
            switchAdminTab('users');
            
            // Reload users
            loadUsers();
            loadDashboardStats();
            
            // Update preview
            updateUserPreview();
        } else {
            showAdminToast(data.message || 'Gagal membuat user', 'error');
        }
    } catch (error) {
        console.error('Create user error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

// ============================================
// BULK CREATE FUNCTIONS
// ============================================
async function bulkCreateUsers() {
    const usersText = bulkUsers.value.trim();
    const days = parseInt(bulkDays.value) || 30;
    
    if (!usersText) {
        showAdminToast('Masukkan daftar user!', 'error');
        return;
    }
    
    // Parse users
    const userLines = usersText.split('\n')
        .map(line => line.trim())
        .filter(line => line.includes(':'));
    
    if (userLines.length === 0) {
        showAdminToast('Format tidak valid. Gunakan format: username:password', 'error');
        return;
    }
    
    const users = [];
    for (const line of userLines) {
        const [username, password] = line.split(':').map(s => s.trim());
        if (username && password) {
            users.push({ username, password });
        }
    }
    
    if (users.length === 0) {
        showAdminToast('Tidak ada user yang valid ditemukan', 'error');
        return;
    }
    
    try {
        showAdminToast(`Membuat ${users.length} user...`, 'info');
        
        const response = await fetch(`${API_BASE_URL}/api/admin/bulk_create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                users: users.map(u => ({
                    username: u.username,
                    password: u.password,
                    days_valid: days
                }))
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show results
            bulkResults.style.display = 'block';
            successCount.textContent = data.created_users.length;
            failedCount.textContent = data.failed_users.length;
            
            // Update success list
            successList.innerHTML = '';
            data.created_users.forEach(user => {
                const div = document.createElement('div');
                div.textContent = `${user.username} - ${user.days_valid} hari`;
                successList.appendChild(div);
            });
            
            // Update failed list
            failedList.innerHTML = '';
            data.failed_users.forEach(user => {
                const div = document.createElement('div');
                div.textContent = `${user.username}: ${user.error}`;
                failedList.appendChild(div);
            });
            
            showAdminToast(`Berhasil membuat ${data.created_users.length} user`, 'success');
            
            // Reload users
            loadUsers();
            loadDashboardStats();
        } else {
            showAdminToast(data.message || 'Gagal membuat user', 'error');
        }
    } catch (error) {
        console.error('Bulk create error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

// ============================================
// SETTINGS FUNCTIONS
// ============================================
async function updateAdminPassword() {
    const currentPass = currentPassword.value.trim();
    const newPass = newAdminPassword.value.trim();
    const confirmPass = confirmAdminPassword.value.trim();
    
    if (!currentPass || !newPass || !confirmPass) {
        showAdminToast('Semua field harus diisi!', 'error');
        return;
    }
    
    if (newPass.length < 8) {
        showAdminToast('Password baru minimal 8 karakter', 'error');
        return;
    }
    
    if (newPass !== confirmPass) {
        showAdminToast('Password baru tidak cocok', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/update_password`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_password: currentPass,
                new_password: newPass
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAdminToast('Password admin berhasil diupdate', 'success');
            
            // Clear form
            currentPassword.value = '';
            newAdminPassword.value = '';
            confirmAdminPassword.value = '';
        } else {
            showAdminToast(data.message || 'Gagal update password', 'error');
        }
    } catch (error) {
        console.error('Update admin password error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

async function clearExpiredUsers() {
    if (!confirm('Yakin ingin menonaktifkan semua user yang sudah expired?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/clear_expired`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAdminToast(data.message, 'success');
            loadUsers();
            loadDashboardStats();
        } else {
            showAdminToast(data.message || 'Gagal membersihkan user expired', 'error');
        }
    } catch (error) {
        console.error('Clear expired users error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

async function clearOldSessions() {
    if (!confirm('Yakin ingin membersihkan session lama?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/clear_sessions`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAdminToast(data.message, 'success');
            loadDashboardStats();
        } else {
            showAdminToast(data.message || 'Gagal membersihkan session', 'error');
        }
    } catch (error) {
        console.error('Clear sessions error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

async function refreshStatistics() {
    try {
        await loadDashboardStats();
        showAdminToast('Statistics refreshed', 'success');
    } catch (error) {
        console.error('Refresh statistics error:', error);
        showAdminToast('Error: ' + error.message, 'error');
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function switchAdminTab(tabId) {
    // Update active tab button
    adminTabButtons.forEach(button => {
        button.classList.remove('active');
        if (button.getAttribute('data-tab') === tabId) {
            button.classList.add('active');
        }
    });
    
    // Update active tab content
    adminTabContents.forEach(content => {
        content.classList.remove('active');
        if (content.id === `${tabId}-tab`) {
            content.classList.add('active');
        }
    });
}

function updateAdminCurrentTime() {
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
    
    adminCurrentTime.textContent = `${dateStr} • ${timeStr}`;
}

function showAdminToast(message, type = 'info') {
    // Set content
    adminToastMessage.textContent = message;
    
    // Set type styling
    adminToast.className = 'toast ' + type;
    
    // Set icon based on type
    switch(type) {
        case 'success':
            adminToastIcon.className = 'fas fa-check-circle';
            break;
        case 'error':
            adminToastIcon.className = 'fas fa-exclamation-circle';
            break;
        case 'warning':
            adminToastIcon.className = 'fas fa-exclamation-triangle';
            break;
        default:
            adminToastIcon.className = 'fas fa-info-circle';
    }
    
    // Show toast
    adminToast.classList.add('show');
    
    // Auto-hide after 5 seconds
    setTimeout(hideAdminToast, 5000);
}

function hideAdminToast() {
    adminToast.classList.remove('show');
}

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', async function() {
    // Check if admin is already logged in
    const isAdminLoggedIn = await verifyAdminToken();
    
    if (isAdminLoggedIn) {
        // Auto login
        adminLogin.style.display = 'none';
        adminDashboard.style.display = 'block';
        await initAdminDashboard();
    } else {
        // Show login
        adminLogin.style.display = 'flex';
        adminDashboard.style.display = 'none';
        
        // Focus password field
        setTimeout(() => adminPassword.focus(), 100);
    }
    
    // Show welcome message
    setTimeout(() => {
        if (!isAdminLoggedIn) {
            showAdminToast('Selamat datang di Admin Panel. Login dengan password admin.', 'info');
        }
    }, 1000);
    
    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === userActionsModal) {
            hideModal();
        }
    });
});