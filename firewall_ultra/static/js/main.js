/**
 * UIMM — main.js  (tilt supprimé, ripple + session + modal conservés)
 */

/* ─── Modal ─── */
let confirmCallback = null;

function showConfirmModal(title, message, callback) {
    const modal = document.getElementById('confirm-modal');
    if (!modal) return;
    modal.querySelector('.modal-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    confirmCallback = callback;
    modal.style.display = 'flex';
    requestAnimationFrame(() => modal.classList.add('active'));
    setTimeout(() => { const b = modal.querySelector('.btn-secondary'); if (b) b.focus(); }, 80);
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
    const backdrop = document.querySelector('#confirm-modal .modal-backdrop');
    if (backdrop) backdrop.addEventListener('click', closeModal);
});

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
});

/* ─── Flash auto-dismiss ─── */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.flash-message').forEach((msg, i) => {
        setTimeout(() => {
            msg.style.transition = 'opacity .35s ease, transform .35s ease';
            msg.style.opacity    = '0';
            msg.style.transform  = 'translateX(40px)';
            setTimeout(() => msg.remove(), 380);
        }, 5000 + i * 600);
    });
});

/* ─── Validation domaine ─── */
document.addEventListener('DOMContentLoaded', () => {
    const addForm = document.querySelector('.add-form');
    if (!addForm) return;
    addForm.addEventListener('submit', e => {
        const inp = document.getElementById('domaine');
        if (!inp) return;
        let d = inp.value.trim().toLowerCase()
            .replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/.*$/, '');
        if (!d || d.length < 3 || !d.includes('.')) {
            e.preventDefault();
            alert('Veuillez entrer un domaine valide (ex: exemple.com)');
            return;
        }
        inp.value = d;
    });
});

/* ─── Session timer ─── */
let sessionTimeout = null, warningShown = false;
function initSessionTimer() {
    const reset = () => {
        if (sessionTimeout) clearTimeout(sessionTimeout);
        warningShown = false;
        sessionTimeout = setTimeout(() => {
            if (!warningShown) { warningShown = true; showSessionWarning(); }
        }, 13 * 60 * 1000);
    };
    ['click','keypress','mousemove','scroll'].forEach(ev =>
        document.addEventListener(ev, reset, { passive: true })
    );
    reset();
}
function showSessionWarning() {
    const w = document.createElement('div');
    w.className = 'session-warning';
    w.innerHTML = `<div class="warning-content"><span class="warning-icon">⏱</span><span class="warning-text">Votre session expire dans 2 minutes</span><button class="warning-dismiss" onclick="this.closest('.session-warning').remove()">OK</button></div>`;
    document.body.appendChild(w);
    setTimeout(() => { if (w.parentElement) w.remove(); }, 30000);
}
if (document.body.classList.contains('page-dashboard') || document.body.classList.contains('page-gestion')) {
    document.addEventListener('DOMContentLoaded', initSessionTimer);
}

/* ─── Ripple sur boutons ─── */
document.addEventListener('click', e => {
    const btn = e.target.closest('.btn');
    if (!btn || btn.classList.contains('btn-delete') || btn.disabled) return;
    const r    = document.createElement('span');
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    Object.assign(r.style, {
        position:'absolute', pointerEvents:'none', borderRadius:'50%',
        width:`${size}px`, height:`${size}px`,
        left:`${e.clientX - rect.left - size/2}px`,
        top:`${e.clientY - rect.top  - size/2}px`,
        background:'rgba(255,255,255,.22)',
        transform:'scale(0)',
        animation:'rippleEff .6s ease-out forwards'
    });
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(r);
    setTimeout(() => r.remove(), 620);
});

/* ─── Keyframes runtime ─── */
const _s = document.createElement('style');
_s.textContent = `
@keyframes rippleEff { to { transform: scale(4); opacity: 0; } }
@keyframes slideOut  { from{opacity:1;transform:translateX(0)} to{opacity:0;transform:translateX(48px)} }
`;
document.head.appendChild(_s);
