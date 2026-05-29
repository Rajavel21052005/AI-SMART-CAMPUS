/* ============================================================
   Smart Campus AI — Main JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  // ── Sidebar toggle ──────────────────────────────────────────
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar       = document.getElementById('sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      if (window.innerWidth <= 768) {
        sidebar.classList.toggle('mobile-open');
      } else {
        sidebar.classList.toggle('collapsed');
      }
    });
  }

  // ── Dark / Light theme toggle ───────────────────────────────
  const themeToggle = document.getElementById('themeToggle');
  const themeIcon   = document.getElementById('themeIcon');
  const htmlEl      = document.documentElement;

  // Restore saved preference
  const savedTheme = localStorage.getItem('sc-theme') || 'light';
  htmlEl.setAttribute('data-bs-theme', savedTheme);
  _updateThemeIcon(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      const current = htmlEl.getAttribute('data-bs-theme');
      const next    = current === 'dark' ? 'light' : 'dark';
      htmlEl.setAttribute('data-bs-theme', next);
      localStorage.setItem('sc-theme', next);
      _updateThemeIcon(next);
    });
  }

  function _updateThemeIcon(theme) {
    if (!themeIcon) return;
    themeIcon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
  }

  // ── Auto-dismiss flash alerts after 5 s ─────────────────────
  document.querySelectorAll('.alert.alert-dismissible').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // ── Confirm before dangerous actions ────────────────────────
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm || 'Are you sure?')) {
        e.preventDefault();
      }
    });
  });

  // ── AJAX helper with CSRF ────────────────────────────────────
  window.apiPost = function (url, data) {
    const csrfToken = document.cookie.split(';')
      .find(c => c.trim().startsWith('csrf_token='))
      ?.split('=')[1] || '';
    return fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body:    JSON.stringify(data),
    }).then(r => r.json());
  };

  // ── Tooltip init ─────────────────────────────────────────────
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

});
