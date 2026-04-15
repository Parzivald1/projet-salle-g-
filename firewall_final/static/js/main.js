/**
 * Portail Captif — UIMM Pôle Formation
 * main.js — Tilt supprimé, reste inchangé
 */

// =============================================================================
// 1. TOGGLE PANEL FORMATEUR
// =============================================================================
function toggleFormateurPanel() {
    const tab = document.getElementById('formateurTab');
    if (!tab) return;
    tab.classList.toggle('open');
    if (tab.classList.contains('open')) {
        const firstInput = tab.querySelector('.code-digit');
        if (firstInput) setTimeout(() => firstInput.focus(), 300);
    }
}
document.addEventListener('click', (e) => {
    const tab = document.getElementById('formateurTab');
    if (tab && tab.classList.contains('open') && !tab.contains(e.target)) {
        tab.classList.remove('open');
    }
});
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const tab = document.getElementById('formateurTab');
        if (tab) tab.classList.remove('open');
        closeModal();
    }
});

// =============================================================================
// 2. MODAL DE CONFIRMATION
// =============================================================================
let confirmCallback = null;
function showConfirmModal(title, message, callback) {
    const modal = document.getElementById('confirm-modal');
    if (!modal) return;
    modal.querySelector('.modal-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    confirmCallback = callback;
    modal.style.display = 'flex';
    requestAnimationFrame(() => modal.classList.add('active'));
    const cancelBtn = modal.querySelector('.btn-secondary');
    if (cancelBtn) setTimeout(() => cancelBtn.focus(), 80);
}
function closeModal() {
    const modal = document.getElementById('confirm-modal');
    if (!modal) return;
    modal.classList.remove('active');
    setTimeout(() => { modal.style.display = 'none'; }, 220);
    confirmCallback = null;
}
document.addEventListener('DOMContentLoaded', () => {
    const confirmBtn = document.getElementById('confirm-btn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
            if (confirmCallback) confirmCallback();
            closeModal();
        });
    }
    const modal = document.getElementById('confirm-modal');
    if (modal) {
        const backdrop = modal.querySelector('.modal-backdrop');
        if (backdrop) backdrop.addEventListener('click', closeModal);
    }
});

// =============================================================================
// 3. AUTO-DISMISS FLASH MESSAGES
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.flash-message').forEach((msg, i) => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(40px)';
            setTimeout(() => msg.remove(), 360);
        }, 5000 + i * 600);
    });
});

// =============================================================================
// 4. VALIDATION FORMULAIRE DOMAINE
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
    const addForm = document.querySelector('.add-form');
    if (addForm) {
        addForm.addEventListener('submit', (e) => {
            const domaineInput = document.getElementById('domaine');
            if (!domaineInput) return;
            let d = domaineInput.value.trim().toLowerCase()
                .replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/.*$/, '');
            if (!d || d.length < 3 || !d.includes('.')) {
                e.preventDefault();
                alert('Veuillez entrer un domaine valide (ex: exemple.com)');
                return;
            }
            domaineInput.value = d;
        });
    }
});

// =============================================================================
// 5. SESSION TIMER (15 min)
// =============================================================================
let sessionTimeout = null, warningShown = false;
function initSessionTimer() {
    const resetTimer = () => {
        if (sessionTimeout) clearTimeout(sessionTimeout);
        warningShown = false;
        sessionTimeout = setTimeout(() => {
            if (!warningShown) { warningShown = true; showSessionWarning(); }
        }, 13 * 60 * 1000);
    };
    ['click','keypress','mousemove','scroll'].forEach(ev =>
        document.addEventListener(ev, resetTimer, { passive: true })
    );
    resetTimer();
}
function showSessionWarning() {
    const warning = document.createElement('div');
    warning.className = 'session-warning';
    warning.innerHTML = `<div class="warning-content"><span class="warning-icon">⏱</span><span class="warning-text">Votre session expire dans 2 minutes</span><button class="warning-dismiss" onclick="this.closest('.session-warning').remove()">OK</button></div>`;
    document.body.appendChild(warning);
    setTimeout(() => { if (warning.parentElement) warning.remove(); }, 30000);
}
if (document.body.classList.contains('page-dashboard') ||
    document.body.classList.contains('page-gestion')) {
    document.addEventListener('DOMContentLoaded', initSessionTimer);
}

// =============================================================================
// 6. RIPPLE sur les boutons
// =============================================================================
document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn');
    if (!btn || btn.classList.contains('btn-delete') || btn.disabled) return;
    const ripple = document.createElement('span');
    const rect   = btn.getBoundingClientRect();
    const size   = Math.max(rect.width, rect.height);
    const x      = e.clientX - rect.left - size / 2;
    const y      = e.clientY - rect.top  - size / 2;
    Object.assign(ripple.style, {
        position:'absolute', pointerEvents:'none',
        width:`${size}px`, height:`${size}px`,
        left:`${x}px`, top:`${y}px`,
        borderRadius:'50%',
        background:'rgba(255,255,255,0.25)',
        transform:'scale(0)',
        animation:'rippleEffect 0.6s ease-out forwards'
    });
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 620);
});

// NOTE : Effet 3D TILT supprimé intentionnellement (section 7 retirée)

// =============================================================================
// 8. STAGGERED REVEAL pour les pack-cards
// =============================================================================
function revealPackCards() {
    const cards = document.querySelectorAll('.pack-card');
    if (!cards.length) return;
    cards.forEach((card, i) => {
        setTimeout(() => card.classList.add('revealed'), i * 55);
    });
}
const _origTogglePacks = window.togglePacks;
window.togglePacks = function() {
    if (typeof _origTogglePacks === 'function') _origTogglePacks();
    setTimeout(revealPackCards, 60);
};
document.addEventListener('DOMContentLoaded', () => {
    const section = document.getElementById('packsSection');
    if (section && section.style.display !== 'none') {
        setTimeout(revealPackCards, 200);
    }
});

// =============================================================================
// 9. CODE DIGIT : classe .filled
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.code-digit').forEach(input => {
        const update = () => {
            input.value.trim().length > 0
                ? input.classList.add('filled')
                : input.classList.remove('filled');
        };
        input.addEventListener('input', update);
        input.addEventListener('keydown', () => setTimeout(update, 10));
    });
});

// =============================================================================
// 10. UTILITAIRES
// =============================================================================
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}
function formatRelativeDate(dateString) {
    const diff    = new Date() - new Date(dateString);
    const minutes = Math.floor(diff / 60000);
    const hours   = Math.floor(diff / 3600000);
    const days    = Math.floor(diff / 86400000);
    if (minutes < 1)  return "À l'instant";
    if (minutes < 60) return `Il y a ${minutes} min`;
    if (hours < 24)   return `Il y a ${hours}h`;
    if (days < 7)     return `Il y a ${days}j`;
    return new Date(dateString).toLocaleDateString('fr-FR');
}

// =============================================================================
// 11. KEYFRAMES RUNTIME
// =============================================================================
(function() {
    const s = document.createElement('style');
    s.textContent = `
        @keyframes rippleEffect { to { transform: scale(4); opacity: 0; } }
        @keyframes slideOut { from{opacity:1;transform:translateX(0)} to{opacity:0;transform:translateX(48px)} }
    `;
    document.head.appendChild(s);
})();
