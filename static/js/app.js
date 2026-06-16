/* ── Utilities ──────────────────────────────────────────────────────────── */

/** Format number with commas */
function fmt(n) {
  const num = parseFloat(n) || 0;
  return num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Get trimmed value of an input/select/textarea by id */
function v(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}

/** Generic fetch wrapper */
async function api(url, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin'
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(url, opts);
    if (res.status === 401) { window.location.href = '/login'; return {}; }
    const data = await res.json();
    if (!res.ok && data.error) { toast(data.error, 'error'); }
    return data;
  } catch (err) {
    toast('Network error. Please try again.', 'error');
    return {};
  }
}

/* ── Toast ──────────────────────────────────────────────────────────────── */
let _toastTimer;
function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = `toast ${type} show`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove('show'), 3000);
}

/* ── Modal ──────────────────────────────────────────────────────────────── */
function openModal(id) {
  document.getElementById(id)?.classList.remove('hidden');
  document.getElementById('modal-overlay')?.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal(id) {
  document.getElementById(id)?.classList.add('hidden');
  // hide overlay only if no other modals open
  const open = document.querySelectorAll('.modal:not(.hidden)');
  if (!open.length) {
    document.getElementById('modal-overlay')?.classList.add('hidden');
    document.body.style.overflow = '';
  }
}

// Close modal on overlay click
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modal-overlay')?.addEventListener('click', () => {
    document.querySelectorAll('.modal:not(.hidden)').forEach(m => m.classList.add('hidden'));
    document.getElementById('modal-overlay')?.classList.add('hidden');
    document.body.style.overflow = '';
  });
});

// Escape key closes modals
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal:not(.hidden)').forEach(m => m.classList.add('hidden'));
    document.getElementById('modal-overlay')?.classList.add('hidden');
    document.body.style.overflow = '';
  }
});
