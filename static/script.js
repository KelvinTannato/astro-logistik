// --- KONFIGURASI API ---
const API_URL = "http://127.0.0.1:8000";
const TOKEN_KEY = 'astro_access_token';
const ROLE_KEY = 'astro_user_role';

let currentUserRole = null;
let currentEditId = null; 
let allShipments = []; // <--- PENAMPUNG DATA GLOBAL (Supaya tombol edit aman)

// --- INISIALISASI ---
document.addEventListener('DOMContentLoaded', () => {
    const isLoginPage = document.getElementById('login-form');
    const isDashboardPage = document.getElementById('smu-table');
    const token = localStorage.getItem(TOKEN_KEY);
    currentUserRole = localStorage.getItem(ROLE_KEY);

    if (isLoginPage) {
        if (token) { window.location.href = '/index.html'; return; }
        setupAuthListeners();
    } 
    else if (isDashboardPage) {
        if (!token) { window.location.href = '/login.html'; return; }
        setupDashboard();
    }
});

// ==========================================
// BAGIAN 1: OTENTIKASI
// ==========================================
function setupAuthListeners() {
    document.getElementById('login-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const u = document.getElementById('login-username').value;
        const p = document.getElementById('login-password').value;
        const formData = new URLSearchParams();
        formData.append('username', u);
        formData.append('password', p);

        try {
            const res = await fetch(`${API_URL}/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });
            if (!res.ok) throw new Error("Login Gagal! Cek username/password.");
            const data = await res.json();
            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(ROLE_KEY, data.role);
            showToast('Login Berhasil!', 'success');
            setTimeout(() => window.location.href = '/index.html', 1000);
        } catch (err) { showToast(err.message, 'error'); }
    });

    document.getElementById('register-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const u = document.getElementById('reg-username').value;
        const p = document.getElementById('reg-password').value;
        try {
            const res = await fetch(`${API_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });
            if (!res.ok) throw new Error("Registrasi Gagal");
            showToast('Registrasi Berhasil! Silakan Login.', 'success');
            toggleAuthDisplay();
        } catch (err) { showToast(err.message, 'error'); }
    });

    document.getElementById('toggle-auth')?.addEventListener('click', (e) => {
        e.preventDefault();
        toggleAuthDisplay();
    });
}

function toggleAuthDisplay() {
    const loginForm = document.getElementById('login-form');
    const regForm = document.getElementById('register-form');
    loginForm.style.display = loginForm.style.display === 'none' ? 'block' : 'none';
    regForm.style.display = regForm.style.display === 'none' ? 'block' : 'none';
}

// ==========================================
// BAGIAN 2: DASHBOARD
// ==========================================
function setupDashboard() {
    const isAdmin = (currentUserRole === 'admin');
    document.body.classList.toggle('admin-mode', isAdmin);
    document.getElementById('user-display').innerHTML = `<i class="fas fa-user-circle"></i> ${isAdmin ? 'ADMIN MODE' : 'User Mode'}`;

    loadShipments();

    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(ROLE_KEY);
        window.location.href = '/login.html';
    });

    document.getElementById('smu-input-form')?.addEventListener('submit', handleSmuInput);
    
    // Listener Tombol Simpan di Modal Edit
    document.getElementById('save-modal-btn')?.addEventListener('click', saveEditData);
    
    // Listener Tutup Modal
    document.querySelectorAll('.close-modal, .close-modal-btn').forEach(el => {
        el.addEventListener('click', () => document.getElementById('edit-modal').classList.remove('show'));
    });
}

async function loadShipments() {
    const token = localStorage.getItem(TOKEN_KEY);
    try {
        const res = await fetch(`${API_URL}/shipments/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.status === 401) {
            alert("Sesi habis, silakan login ulang.");
            document.getElementById('logout-btn').click();
            return;
        }
        allShipments = await res.json(); // Simpan ke variabel global
        renderTable(allShipments);
        updateStatistics(allShipments);
    } catch (err) { console.error(err); }
}

// --- FUNGSI INPUT DATA BARU (AUTO TRACKING) ---
async function handleSmuInput(e) {
    e.preventDefault();
    const token = localStorage.getItem(TOKEN_KEY);
    
    // Ambil nilai form
    const smuVal = document.getElementById('smu-nomor').value.toUpperCase();
    const originVal = document.getElementById('smu-asal').value.toUpperCase();
    const destVal = document.getElementById('smu-tujuan').value.toUpperCase();
    
    const payload = {
        customer_name: document.getElementById('smu-customer').value,
        smu: smuVal,
        origin: originVal,
        transit: document.getElementById('smu-transit').value.toUpperCase() || null,
        destination: destVal,
        koli: 0, // Default 0, nanti robot yang isi
        notes: document.getElementById('smu-notes').value
    };

    try {
        // 1. SIMPAN DATA KE DATABASE DULU
        const res = await fetch(`${API_URL}/shipments/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error("Gagal input data");

        // 2. JIKA SUKSES, TAMPILKAN DI TABEL
        showToast('Data Tersimpan! Robot mulai bekerja...', 'success');
        document.getElementById('smu-input-form').reset();
        
        // Refresh tabel dulu biar data muncul (status awal: Manifested)
        await loadShipments(); 

        // 3. TRIGGER ROBOT OTOMATIS (AUTO-PILOT)
        // Panggil fungsi tracking yang sama dengan tombol manual
        // Panel Loading di kanan atas akan otomatis muncul
        triggerSingleUpdate(smuVal);

    } catch (err) { 
        showToast(err.message, 'error'); 
    }
}

// --- FUNGSI RENDER TABEL (UPDATE WARNA LOGIC) ---
function renderTable(data) {
    const tbody = document.querySelector('#smu-table tbody');
    tbody.innerHTML = '';
    data.sort((a, b) => b.id - a.id);

    if (data.length === 0) {
        document.getElementById('no-data-message').style.display = 'block';
        return;
    }
    document.getElementById('no-data-message').style.display = 'none';

    data.forEach(item => {
        const tr = document.createElement('tr');
        const rute = item.transit ? `${item.origin} > ${item.transit} > ${item.destination}` : `${item.origin} > ${item.destination}`;
        
        // --- LOGIKA PEWARNAAN DISPLAY ---
        let statusClass = 'pending'; // Default Merah
        const s = item.status.toUpperCase();
        const origin = item.origin.toUpperCase();
        const transit = item.transit ? item.transit.toUpperCase() : 'XXX';
        const dest = item.destination.toUpperCase();

        // 4. HIJAU: SUDAH DITERIMA
        if (s.includes("SUDAH DITERIMA")) {
            statusClass = 'done';
        }
        // 3. BIRU TERANG: SAMPAI DI {TUJUAN}
        else if (s.includes(`SAMPAI DI ${dest}`)) {
            statusClass = 'info';
        }
        // 2. ABU-ABU TERANG:
        // - {ASAL} > {TRANSIT}
        // - {ASAL} > {TUJUAN} (Jika direct)
        // - MASIH DI {TRANSIT}
        // - {TRANSIT} > {TUJUAN}
        else if (s.includes(">") || s.includes(`MASIH DI ${transit}`)) {
            statusClass = 'transit'; // Pastikan class .transit ada di CSS
        }
        // 1. MERAH: MASIH DI {ASAL}
        else if (s.includes(`MASIH DI ${origin}`)) {
            statusClass = 'pending';
        }

        // Tombol Admin & Aksi
        const adminBtn = currentUserRole === 'admin' ? 
            `<button class="btn info-btn small-btn" title="Cek Status Robot" onclick="triggerSingleUpdate('${item.smu}')"><i class="fas fa-robot"></i></button>` : '';

        const actionButtons = `
            <div style="display:flex; gap:5px;">
                ${adminBtn}
                <button class="btn warning-btn small-btn" onclick="openEditModal(${item.id})"><i class="fas fa-edit"></i></button>
                <button class="btn danger-outline-btn small-btn" onclick="deleteShipment(${item.id})"><i class="fas fa-trash"></i></button>
            </div>
        `;

        tr.innerHTML = `
            <td data-label="Tanggal">${new Date(item.created_at).toLocaleDateString()}</td>
            <td data-label="Customer"><strong>${item.customer_name}</strong></td>
            <td data-label="Nomor SMU">${item.smu}</td>
            <td data-label="Rute">${rute}</td>
            <td data-label="Koli">${item.koli}</td>
            <td data-label="Status"><span class="status-badge ${statusClass}">${item.status}</span></td>
            <td data-label="Est. Bandara">${item.eta_bandara || '-'}</td>
            <td data-label="Aksi">${actionButtons}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ==========================================
// BAGIAN 3: EDIT & HAPUS
// ==========================================

// Buka Modal Edit (Mencari data berdasarkan ID)
window.openEditModal = function(id) {
    const item = allShipments.find(i => i.id === id);
    if (!item) return;

    currentEditId = id;
    // Isi form dengan data
    document.getElementById('modal-smu').value = item.smu;
    document.getElementById('modal-customer').value = item.customer_name;
    document.getElementById('modal-asal').value = item.origin;
    document.getElementById('modal-transit').value = item.transit || '';
    document.getElementById('modal-tujuan').value = item.destination;
    document.getElementById('modal-koli').value = item.koli;
    document.getElementById('modal-notes').value = item.notes || '';
    
    // Tampilkan Modal
    document.getElementById('edit-modal').classList.add('show');
}

// Simpan Perubahan (PUT)
async function saveEditData() {
    if (!currentEditId) return;
    const token = localStorage.getItem(TOKEN_KEY);
    
    const payload = {
        smu: document.getElementById('modal-smu').value,
        customer_name: document.getElementById('modal-customer').value,
        origin: document.getElementById('modal-asal').value,
        transit: document.getElementById('modal-transit').value || null,
        destination: document.getElementById('modal-tujuan').value,
        koli: parseInt(document.getElementById('modal-koli').value),
        notes: document.getElementById('modal-notes').value
    };

    try {
        const res = await fetch(`${API_URL}/shipments/${currentEditId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error("Gagal mengupdate data");
        
        showToast('Data berhasil diperbarui!', 'success');
        document.getElementById('edit-modal').classList.remove('show');
        loadShipments(); // Refresh tabel
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Hapus Data (DELETE)
window.deleteShipment = async function(id) {
    if (!confirm('Yakin ingin menghapus data ini?')) return;
    const token = localStorage.getItem(TOKEN_KEY);

    try {
        const res = await fetch(`${API_URL}/shipments/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) throw new Error("Gagal menghapus data (Mungkin bukan milik Anda)");
        
        showToast('Data dihapus.', 'success');
        loadShipments();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// // ==========================================
// BAGIAN 4: ROBOT TRIGGER (FLOATING PANEL)
// ==========================================
window.triggerSingleUpdate = async function(smu) {
    const token = localStorage.getItem(TOKEN_KEY);
    
    // Ambil elemen panel baru
    const loadingPanel = document.getElementById('loading-panel');
    const loadingText = document.getElementById('loading-text');
    const loadingSub = document.getElementById('loading-subtext');
    const progressBar = document.getElementById('progress-bar-fill');
    const progressPerc = document.getElementById('progress-percentage');

    // 1. TAMPILKAN PANEL (Geser dari kanan ke layar)
    loadingPanel.style.right = '20px'; // Muncul di pojok kanan
    
    // Reset Data
    loadingText.textContent = `Melacak ${smu}`;
    loadingSub.textContent = "Menghubungkan ke Robot AI...";
    progressBar.style.width = '0%';
    progressPerc.textContent = '0%';

    // 2. SIMULASI PROGRESS
    let progress = 0;
    const interval = setInterval(() => {
        if (progress < 30) progress += 5;
        else if (progress < 70) progress += 2;
        else if (progress < 90) progress += 0.5;
        
        progressBar.style.width = `${progress}%`;
        progressPerc.textContent = `${Math.round(progress)}%`;
        
        if (progress > 20 && progress < 50) loadingSub.textContent = "Membuka Website Maskapai...";
        if (progress > 50 && progress < 80) loadingSub.textContent = "Menganalisis Data Status...";
        if (progress > 80) loadingSub.textContent = "Cek Jadwal via Google Flight...";

    }, 300);

    try {
        // 3. REQUEST KE BACKEND
        const res = await fetch(`${API_URL}/update-tracking/${smu}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        clearInterval(interval);

        if (!res.ok) throw new Error("Gagal update tracking");
        
        // 4. SUKSES
        progressBar.style.width = '100%';
        progressPerc.textContent = '100%';
        loadingText.textContent = "Berhasil!";
        loadingSub.textContent = "Data telah diperbarui.";
        
        const result = await res.json();
        
        // Sembunyikan panel setelah 2 detik
        setTimeout(() => {
            loadingPanel.style.right = '-400px'; // Geser keluar layar
            showToast(`Update Sukses: ${result.data.status}`, 'success');
            loadShipments();
        }, 2000);

    } catch (err) {
        clearInterval(interval);
        // Tampilkan error di panel sebentar sebelum tutup
        loadingText.textContent = "Gagal!";
        loadingSub.textContent = "Terjadi kesalahan sistem.";
        progressBar.style.backgroundColor = "#ef4444"; // Merah
        
        setTimeout(() => {
            loadingPanel.style.right = '-400px';
            showToast(err.message, 'error');
            // Reset warna bar
            setTimeout(() => progressBar.style.backgroundColor = "", 500);
        }, 3000);
    }
}

function showToast(msg, type) {
    const c = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast ${type} show`;
    t.innerHTML = `<i class="fas fa-info-circle"></i> ${msg}`;
    c.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

function updateStatistics(data) {
    document.getElementById('stat-total-today').textContent = data.length;
    const arrived = data.filter(i => i.status.includes('Selesai') || i.status.includes('Sampai') || i.status.includes('Delivered')).length;
    document.getElementById('stat-arrived').textContent = arrived;
    document.getElementById('stat-on-process').textContent = data.length - arrived;
}