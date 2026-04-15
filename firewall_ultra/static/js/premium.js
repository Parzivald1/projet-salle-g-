/**
 * ═══════════════════════════════════════════════════════════════════════
 * CFAI PORTAL — premium.js
 * Three.js Network Field | GSAP ScrollTrigger | Laser Scan
 * Page Transitions | Dynamic Accent Color API
 * ═══════════════════════════════════════════════════════════════════════
 */

/* ═══════════════════════════════════════════════════════════════
   1. PAGE TRANSITION — Rideau noir à 5 bandes
   ═══════════════════════════════════════════════════════════════ */
(function initPageTransitions() {

    /* Reveal d'entrée systématique */
    document.body.classList.add('pt-entering');
    window.addEventListener('load', () => {
        setTimeout(() => document.body.classList.remove('pt-entering'), 860);
    });

    /* Sortie au clic sur liens internes */
    document.addEventListener('click', e => {
        const link = e.target.closest('a[href]');
        if (!link) return;
        const href = link.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('http') ||
            href.startsWith('javascript') || link.target === '_blank') return;
        e.preventDefault();
        document.body.classList.add('pt-leaving');
        setTimeout(() => { window.location.href = href; }, 590);
    });

    /* Sortie au submit de formulaire (sauf data-no-transition) */
    document.addEventListener('submit', e => {
        if (e.target.dataset.noTransition) return;
        document.body.classList.add('pt-leaving');
    });

})();


/* ═══════════════════════════════════════════════════════════════
   2. THREE.JS — CHAMP DE PARTICULES RÉSEAU
   Exposé via window._particleMat et window._lineMat pour
   le switch dynamique de couleur (cyan ↔ orange).
   ═══════════════════════════════════════════════════════════════ */
(function initNetworkField() {

    /* Seulement sur la page portail */
    if (!document.body.classList.contains('page-portail')) return;
    if (typeof THREE === 'undefined') return;

    /* ── Setup renderer ── */
    const canvas        = document.createElement('canvas');
    canvas.id           = 'matrix-canvas';
    canvas.style.cssText = 'position:fixed;inset:0;z-index:0;pointer-events:none;';
    document.body.insertBefore(canvas, document.body.firstChild);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.6));
    renderer.setClearColor(0x020c18, 1);

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(68, 1, 0.1, 1000);
    camera.position.z = 185;

    /* ── Brume de profondeur ── */
    scene.fog = new THREE.FogExp2(0x020c18, 0.0052);

    /* ── Nœuds (particules) ── */
    const NODE_COUNT = 300;
    const nodePos    = new Float32Array(NODE_COUNT * 3);
    const SPREAD     = 210;

    for (let i = 0; i < NODE_COUNT; i++) {
        nodePos[i * 3]     = (Math.random() - .5) * SPREAD * 2;
        nodePos[i * 3 + 1] = (Math.random() - .5) * SPREAD;
        nodePos[i * 3 + 2] = (Math.random() - .5) * SPREAD;
    }

    const nodeGeo = new THREE.BufferGeometry();
    nodeGeo.setAttribute('position', new THREE.BufferAttribute(nodePos, 3));

    /* ── Material nœuds (couleur exposée globalement) ── */
    const nodeMat = new THREE.PointsMaterial({
        color:        0x00e5ff,
        size:         1.5,
        transparent:  true,
        opacity:      .55,
        sizeAttenuation: true,
        depthWrite:   false,
    });

    /* Exposer pour le switch de couleur */
    window._particleMat = nodeMat;

    const nodes = new THREE.Points(nodeGeo, nodeMat);
    scene.add(nodes);

    /* ── Connexions (lignes réseau) ── */
    const lineMat = new THREE.LineBasicMaterial({
        color:       0x00e5ff,
        transparent: true,
        opacity:     .09,
        depthWrite:  false,
    });
    window._lineMat = lineMat;

    const MAX_EDGE_DIST = 58;
    const edgeVerts     = [];
    for (let i = 0; i < NODE_COUNT; i++) {
        for (let j = i + 1; j < NODE_COUNT; j++) {
            const ax = nodePos[i*3],   ay = nodePos[i*3+1], az = nodePos[i*3+2];
            const bx = nodePos[j*3],   by = nodePos[j*3+1], bz = nodePos[j*3+2];
            const d  = Math.sqrt((ax-bx)**2 + (ay-by)**2 + (az-bz)**2);
            if (d < MAX_EDGE_DIST) edgeVerts.push(ax,ay,az, bx,by,bz);
        }
    }
    const lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(edgeVerts), 3));
    const lines = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lines);

    /* ── Resize réactif ── */
    function onResize() {
        const w = window.innerWidth, h = window.innerHeight;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }
    onResize();
    window.addEventListener('resize', onResize, { passive: true });

    /* ── Parallax souris ── */
    let mx = 0, my = 0;
    window.addEventListener('mousemove', e => {
        mx = (e.clientX / window.innerWidth  - .5) * 2;
        my = (e.clientY / window.innerHeight - .5) * 2;
    }, { passive: true });

    /* ── Transition de couleur fluide (non-bloquante) ── */
    let targetColor   = new THREE.Color(0x00e5ff);
    let currentColor  = new THREE.Color(0x00e5ff);

    /**
     * updateParticleAccent(hex)
     * Appelé par portail.html lors du switch Formateur/Élève
     */
    window.updateParticleAccent = function(hexColor) {
        targetColor.setHex(hexColor);
    };

    /* ── RAF loop principal (RequestAnimationFrame) ── */
    let rafId;
    function animate() {
        rafId = requestAnimationFrame(animate);

        const t = Date.now() * 0.00022;

        /* Interpolation couleur douce (lerp 5% par frame ≈ 300ms) */
        currentColor.lerp(targetColor, .05);
        nodeMat.color.copy(currentColor);
        lineMat.color.copy(currentColor);

        /* Rotation lente du champ */
        nodes.rotation.y  = t * 0.16 + mx * 0.07;
        nodes.rotation.x  = t * 0.05 + my * 0.04;
        lines.rotation.y  = nodes.rotation.y;
        lines.rotation.x  = nodes.rotation.x;

        /* Légère dérive de caméra */
        camera.position.x = Math.sin(t * .38) * 9  + mx * 14;
        camera.position.y = Math.cos(t * .27) * 6  + my * 9;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
    }
    animate();

    /* Nettoyage mémoire GPU */
    window.addEventListener('pagehide', () => {
        cancelAnimationFrame(rafId);
        renderer.dispose();
        nodeGeo.dispose(); nodeMat.dispose();
        lineGeo.dispose(); lineMat.dispose();
    });

})();


/* ═══════════════════════════════════════════════════════════════
   3. LASER SCAN — animation sur les boutons .login__submit
   Se déclenche au chargement + toutes les 3 secondes
   ═══════════════════════════════════════════════════════════════ */
(function initLaserScan() {

    /**
     * Lance une passe laser sur un élément .login__submit-laser donné.
     * Utilise double rAF pour forcer le reflow avant l'animation CSS.
     */
    function fireLaser(laserEl) {
        if (!laserEl) return;
        /* Reset instantané */
        laserEl.style.transition = 'none';
        laserEl.style.transform  = 'translateX(-120%)';

        requestAnimationFrame(() => requestAnimationFrame(() => {
            laserEl.style.transition = 'transform .72s cubic-bezier(.22,1,.36,1)';
            laserEl.style.transform  = 'translateX(120%)';
        }));
    }

    /* Cycle laser sur tous les boutons submit actifs */
    function laserCycle() {
        document.querySelectorAll('.login__submit-laser').forEach(el => {
            /* Ne scanner que si le bouton parent n'est pas disabled */
            const btn = el.closest('.login__submit');
            if (btn && !btn.disabled) fireLaser(el);
        });
    }

    /* Premier scan après 1.2s, puis toutes les 3s */
    setTimeout(() => {
        laserCycle();
        setInterval(laserCycle, 3000);
    }, 1200);

})();


/* ═══════════════════════════════════════════════════════════════
   4. GSAP SCROLLTRIGGER — Dashboard scroll cinématique
   Apple-style : sections scale-out en quittant l'écran
   ═══════════════════════════════════════════════════════════════ */
(function initScrollEffects() {

    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;
    if (!document.body.classList.contains('page-dashboard')) return;

    gsap.registerPlugin(ScrollTrigger);

    /* — Mode cards : reveal staggeré à l'entrée ── */
    gsap.utils.toArray('.mode-card').forEach((card, i) => {
        gsap.fromTo(card,
            { opacity: 0, y: 44, scale: .95 },
            {
                opacity: 1, y: 0, scale: 1,
                duration: .8,
                delay: i * .13,
                ease: 'power3.out',
                scrollTrigger: {
                    trigger: card,
                    start: 'top 90%',
                    toggleActions: 'play none none reverse',
                }
            }
        );
    });

    /* — Grille des modes : scale-out en quittant (scrub fluide) ── */
    const modesGrid = document.querySelector('.modes-grid');
    if (modesGrid) {
        gsap.to(modesGrid, {
            scale: .80,
            opacity: 0,
            ease: 'none',
            scrollTrigger: {
                trigger: modesGrid,
                start: 'top top',
                end: 'bottom top',
                scrub: 1.8,
            }
        });
    }

    /* — Bannière : parallax ½ vitesse ── */
    const banner = document.querySelector('.mode-banner');
    if (banner) {
        gsap.to(banner, {
            y: '-28%',
            ease: 'none',
            scrollTrigger: {
                trigger: '.dashboard-main',
                start: 'top top',
                end: 'bottom top',
                scrub: true,
            }
        });
    }

    /* — Section packs : fade-in reveal ── */
    const packsSection = document.getElementById('packsSection');
    if (packsSection) {
        const obs = new MutationObserver(() => ScrollTrigger.refresh());
        obs.observe(packsSection, { attributes: true, attributeFilter: ['style'] });
    }

    /* — Footer ── */
    const footer = document.querySelector('.dashboard-footer');
    if (footer) {
        gsap.fromTo(footer,
            { opacity: 0, y: 18 },
            {
                opacity: 1, y: 0, duration: .6, ease: 'power2.out',
                scrollTrigger: { trigger: footer, start: 'top 95%' }
            }
        );
    }

})();


/* ═══════════════════════════════════════════════════════════════
   5. STAGGERED REVEAL — Pack cards (dashboard)
   ═══════════════════════════════════════════════════════════════ */
function revealPackCards() {
    document.querySelectorAll('.pack-card:not(.revealed)').forEach((card, i) => {
        setTimeout(() => card.classList.add('revealed'), i * 55);
    });
}

/* Patch togglePacks pour déclencher le stagger reveal */
document.addEventListener('DOMContentLoaded', () => {
    const orig = window.togglePacks;
    if (typeof orig === 'function') {
        window.togglePacks = function () {
            orig();
            setTimeout(revealPackCards, 80);
        };
    }
    /* Cas mode partiel déjà actif au chargement */
    const section = document.getElementById('packsSection');
    if (section && section.style.display !== 'none') {
        setTimeout(revealPackCards, 300);
    }
});

