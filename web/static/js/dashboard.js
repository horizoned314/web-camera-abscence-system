/**
 * dashboard.js
 * Realtime attendance dashboard — vanilla JS
 * Polling /api/attendance setiap 3 detik
 * Polling /api/notifications setiap 2 detik
 */

'use strict';

// ══════════════════════════════════════════════════════════════
// State
// ══════════════════════════════════════════════════════════════
const state = {
  page        : 1,
  perPage     : 10,
  totalPages  : 1,
  search      : '',
  filter      : 'semua',
  previousHadir: new Set(),  // npm yang sudah hadir — untuk deteksi baru
  initialized : false,
  loading     : false,
};

// ══════════════════════════════════════════════════════════════
// API helpers
// ══════════════════════════════════════════════════════════════

async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Fetch & render attendance ─────────────────────────────────
async function fetchData(silent = false) {
  if (state.loading && !silent) return;
  state.loading = true;

  try {
    const params = new URLSearchParams({
      search  : state.search,
      status  : state.filter === 'semua' ? '' : state.filter,
      page    : state.page,
      per_page: state.perPage,
    });

    const json = await apiFetch(`/api/attendance?${params}`);

    // Detect students newly marked hadir
    if (state.initialized) {
      detectNewHadir(json.data);
    }

    renderStats(json.stats);
    renderTable(json.data, json.total, json.total_pages);
    renderPagination(json.page, json.total_pages, json.total);

    state.totalPages  = json.total_pages;
    state.initialized = true;

  } catch (err) {
    if (!silent) showTableError();
  } finally {
    state.loading = false;
  }
}

// ── Fetch server-side notifications ──────────────────────────
async function fetchNotifications() {
  try {
    const notifs = await apiFetch('/api/notifications');
    notifs.forEach(n => showToast(n.message, n.type));
  } catch { /* silent */ }
}

// ── Reset all attendance ──────────────────────────────────────
async function confirmReset() {
  const btn = document.getElementById('btn-confirm-reset');
  btn.disabled = true;
  btn.innerHTML = `
    <svg class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
    </svg>
    <span>Mereset…</span>`;

  try {
    await apiFetch('/api/reset', { method: 'POST' });
    state.previousHadir.clear();
    state.page = 1;
    await fetchData();
    showToast('Absensi berhasil direset', 'info');
  } catch {
    showToast('Gagal mereset absensi', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Ya, Reset</span>';
    closeResetModal();
  }
}

// ── Sync users → attendance ───────────────────────────────────
async function syncData() {
  try {
    showToast('Menyinkronkan data mahasiswa…', 'info');
    const res = await apiFetch('/api/sync', { method: 'POST' });
    await fetchData();
    showToast(res.pesan, res.added > 0 ? 'success' : 'info');
  } catch {
    showToast('Gagal melakukan sinkronisasi', 'error');
  }
}

// ══════════════════════════════════════════════════════════════
// Renderers
// ══════════════════════════════════════════════════════════════

function renderStats(stats) {
  setStatNumber('stat-total',       stats.total);
  setStatNumber('stat-hadir',       stats.hadir);
  setStatNumber('stat-tidak-hadir', stats.tidak_hadir);

  const pct = stats.total > 0
    ? Math.round((stats.hadir / stats.total) * 100)
    : 0;
  const el = document.getElementById('stat-pct');
  if (el) el.textContent = `${pct}% kehadiran`;
}

function setStatNumber(id, value) {
  const el = document.getElementById(id);
  if (!el || el.textContent === String(value)) return;
  el.textContent = value;
  el.classList.remove('animate-count-up');
  void el.offsetWidth; // reflow
  el.classList.add('animate-count-up');
}

// ── Table ─────────────────────────────────────────────────────
function renderTable(data, total, totalPages) {
  const tbody = document.getElementById('table-body');
  const badge = document.getElementById('total-badge');
  if (badge) badge.textContent = total;

  if (!data || data.length === 0) {
    tbody.innerHTML = renderEmptyState();
    return;
  }

  const offset = (state.page - 1) * state.perPage;
  tbody.innerHTML = data
    .map((row, i) => renderRow(row, offset + i + 1))
    .join('');
}

function renderRow(row, no) {
  const statusBadge = buildStatusBadge(row.status);
  const waktu       = formatTime(row.waktu_hadir);
  const initials    = getInitials(row.nama);

  return `
    <tr class="hover:bg-surface-hover transition-colors duration-150" data-npm="${esc(row.npm)}">
      <td class="px-5 py-3.5 text-xs text-gray-500 tabular-nums">${no}</td>

      <td class="px-5 py-3.5">
        <span class="font-npm text-gray-400">${esc(row.npm)}</span>
      </td>

      <td class="px-5 py-3.5">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-indigo-600/15 border border-indigo-500/10
                      flex items-center justify-center text-indigo-400
                      text-xs font-semibold shrink-0 select-none">
            ${initials}
          </div>
          <span class="text-sm font-medium text-gray-200 truncate max-w-[200px]">${esc(row.nama)}</span>
        </div>
      </td>

      <td class="px-5 py-3.5">${statusBadge}</td>

      <td class="px-5 py-3.5 text-sm text-gray-500 font-mono tabular-nums">${waktu}</td>
    </tr>`;
}

function buildStatusBadge(status) {
  const map = {
    hadir: `
      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
                   bg-green-500/10 text-green-400 border border-green-500/20">
        <span class="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0"></span>Hadir
      </span>`,
    tidak_hadir: `
      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
                   bg-red-500/10 text-red-400 border border-red-500/20">
        <span class="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0"></span>Tidak Hadir
      </span>`,
  };
  return map[status] ?? `
    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
                 bg-gray-500/10 text-gray-400 border border-gray-500/20">
      <span class="w-1.5 h-1.5 rounded-full bg-gray-500 shrink-0"></span>Tidak Dikenal
    </span>`;
}

function renderEmptyState() {
  const isFiltered = state.search || state.filter !== 'semua';
  return `
    <tr>
      <td colspan="5" class="px-5 py-16 text-center">
        <div class="flex flex-col items-center gap-3">
          <div class="w-16 h-16 rounded-2xl bg-surface border border-surface-border
                      flex items-center justify-center">
            <svg class="w-7 h-7 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </div>
          <div class="space-y-1">
            <p class="text-sm font-medium text-gray-400">
              ${isFiltered ? 'Tidak ada data yang cocok' : 'Belum ada data mahasiswa'}
            </p>
            <p class="text-xs text-gray-600">
              ${isFiltered
                ? 'Coba ubah filter atau kata kunci pencarian'
                : 'Jalankan register.py lalu klik Sinkron Mahasiswa'}
            </p>
          </div>
        </div>
      </td>
    </tr>`;
}

function showTableError() {
  const tbody = document.getElementById('table-body');
  tbody.innerHTML = `
    <tr>
      <td colspan="5" class="px-5 py-12 text-center">
        <p class="text-sm text-red-400">Gagal memuat data. Periksa koneksi server.</p>
      </td>
    </tr>`;
}

// ── Pagination ────────────────────────────────────────────────
function renderPagination(page, totalPages, total) {
  const info    = document.getElementById('pagination-info');
  const buttons = document.getElementById('pagination-buttons');

  const from = total === 0 ? 0 : (page - 1) * state.perPage + 1;
  const to   = Math.min(page * state.perPage, total);

  if (info) {
    info.textContent = total > 0
      ? `Menampilkan ${from}–${to} dari ${total} mahasiswa`
      : 'Tidak ada data';
  }

  if (!buttons) return;

  if (totalPages <= 1) {
    buttons.innerHTML = '';
    return;
  }

  const pages = buildPageNumbers(page, totalPages);
  let html = '';

  // Prev
  html += `<button onclick="goToPage(${page - 1})" ${page === 1 ? 'disabled' : ''}
    class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
           ${page === 1
              ? 'text-gray-700 cursor-not-allowed'
              : 'text-gray-400 hover:bg-surface hover:text-white border border-transparent hover:border-surface-border'}">
    ← Prev
  </button>`;

  pages.forEach(p => {
    if (p === '…') {
      html += `<span class="w-8 h-8 flex items-center justify-center text-xs text-gray-600">…</span>`;
    } else {
      html += `<button onclick="goToPage(${p})"
        class="w-8 h-8 rounded-lg text-xs font-medium transition-colors
               ${p === page
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/30'
                  : 'text-gray-400 hover:bg-surface hover:text-white border border-transparent hover:border-surface-border'}">
        ${p}
      </button>`;
    }
  });

  // Next
  html += `<button onclick="goToPage(${page + 1})" ${page === totalPages ? 'disabled' : ''}
    class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
           ${page === totalPages
              ? 'text-gray-700 cursor-not-allowed'
              : 'text-gray-400 hover:bg-surface hover:text-white border border-transparent hover:border-surface-border'}">
    Next →
  </button>`;

  buttons.innerHTML = html;
}

function buildPageNumbers(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, '…', total];
  if (current >= total - 3) return [1, '…', total-4, total-3, total-2, total-1, total];
  return [1, '…', current - 1, current, current + 1, '…', total];
}

// ══════════════════════════════════════════════════════════════
// Realtime: detect newly hadir
// ══════════════════════════════════════════════════════════════
function detectNewHadir(data) {
  data.forEach(row => {
    if (row.status === 'hadir' && !state.previousHadir.has(row.npm)) {
      // Highlight the row
      requestAnimationFrame(() => {
        const tr = document.querySelector(`tr[data-npm="${CSS.escape(row.npm)}"]`);
        if (tr) {
          tr.classList.add('row-new-hadir');
          setTimeout(() => tr.classList.remove('row-new-hadir'), 2500);
        }
      });
    }
  });

  // Update tracker
  state.previousHadir = new Set(
    data.filter(r => r.status === 'hadir').map(r => r.npm)
  );
}

// ══════════════════════════════════════════════════════════════
// Toast notifications
// ══════════════════════════════════════════════════════════════
const TOAST_STYLES = {
  success : 'bg-green-500/10 border-green-500/25 text-green-300',
  error   : 'bg-red-500/10   border-red-500/25   text-red-300',
  warning : 'bg-amber-500/10 border-amber-500/25 text-amber-300',
  info    : 'bg-blue-500/10  border-blue-500/25  text-blue-300',
};

const TOAST_ICONS = {
  success : `<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`,
  error   : `<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>`,
  warning : `<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>`,
  info    : `<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
};

function showToast(message, type = 'info', duration = 4500) {
  const container = document.getElementById('toast-container');
  const id        = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const style     = TOAST_STYLES[type] || TOAST_STYLES.info;
  const icon      = TOAST_ICONS[type]  || TOAST_ICONS.info;

  const div = document.createElement('div');
  div.id        = id;
  div.className = `pointer-events-auto toast-enter flex items-start gap-3 px-4 py-3
                   rounded-xl border backdrop-blur-md shadow-2xl ${style}`;
  div.innerHTML = `
    ${icon}
    <p class="text-xs font-medium leading-relaxed flex-1">${esc(message)}</p>
    <button onclick="removeToast('${id}')"
            class="shrink-0 opacity-50 hover:opacity-100 transition-opacity text-base leading-none mt-0.5">
      ×
    </button>`;

  container.appendChild(div);

  const timer = setTimeout(() => removeToast(id), duration);
  div.dataset.timer = timer;
}

function removeToast(id) {
  const el = document.getElementById(id);
  if (!el) return;
  clearTimeout(el.dataset.timer);
  el.classList.replace('toast-enter', 'toast-exit');
  setTimeout(() => el.remove(), 280);
}

// ══════════════════════════════════════════════════════════════
// Modal
// ══════════════════════════════════════════════════════════════
function openResetModal() {
  const modal = document.getElementById('reset-modal');
  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

function closeResetModal() {
  const modal = document.getElementById('reset-modal');
  modal.classList.add('hidden');
  modal.classList.remove('flex');
}

// Close modal on Escape key
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeResetModal();
});

// ══════════════════════════════════════════════════════════════
// Sidebar (mobile)
// ══════════════════════════════════════════════════════════════
function openSidebar() {
  document.getElementById('sidebar').classList.remove('-translate-x-full');
  document.getElementById('sidebar-overlay').classList.remove('hidden');
}

function closeSidebar() {
  document.getElementById('sidebar').classList.add('-translate-x-full');
  document.getElementById('sidebar-overlay').classList.add('hidden');
}

// ══════════════════════════════════════════════════════════════
// Filter & search & pagination handlers
// ══════════════════════════════════════════════════════════════
function setFilter(filter) {
  state.filter = filter;
  state.page   = 1;

  document.querySelectorAll('.filter-btn').forEach(btn => {
    const active = btn.dataset.filter === filter;
    btn.classList.toggle('active-filter', active);
    btn.classList.toggle('text-gray-400', !active);
    btn.classList.toggle('hover:text-gray-200', !active);
  });

  fetchData();
}

function goToPage(page) {
  if (page < 1 || page > state.totalPages) return;
  state.page = page;
  fetchData();
}

// Search with debounce
let _searchTimer = null;
document.getElementById('search-input').addEventListener('input', e => {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(() => {
    state.search = e.target.value.trim();
    state.page   = 1;
    fetchData();
  }, 380);
});

// ══════════════════════════════════════════════════════════════
// Live clock
// ══════════════════════════════════════════════════════════════
function updateClock() {
  const now = new Date();
  const opts = {
    weekday: 'long', year: 'numeric',
    month: 'long',   day: 'numeric',
  };
  const dateStr = now.toLocaleDateString('id-ID', opts);
  const timeStr = now.toLocaleTimeString('id-ID');
  const full    = `${dateStr} · ${timeStr}`;

  ['live-time', 'footer-time'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = full;
  });
}

// ══════════════════════════════════════════════════════════════
// Utilities
// ══════════════════════════════════════════════════════════════
function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getInitials(nama) {
  return String(nama)
    .split(' ')
    .slice(0, 2)
    .map(w => w[0] || '')
    .join('')
    .toUpperCase();
}

function formatTime(timeStr) {
  if (!timeStr) return '—';
  try {
    const d = new Date(timeStr.replace(' ', 'T'));
    return d.toLocaleTimeString('id-ID', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch {
    return timeStr;
  }
}

// ══════════════════════════════════════════════════════════════
// Bootstrap
// ══════════════════════════════════════════════════════════════
(async function init() {
  // Initial clock
  updateClock();
  setInterval(updateClock, 1000);

  // Initial data load
  await fetchData();

  // Poll data every 3 seconds
  setInterval(() => fetchData(true), 3000);

  // Poll notifications every 2 seconds
  setInterval(fetchNotifications, 2000);
})();
