/**
 * ═══════════════════════════════════════════════════════════════
 * UIMM PÔLE FORMATION — premium.js
 * Three.js Network Field | GSAP ScrollTrigger | Laser Scan
 * Page Transitions (rideau 5 bandes) | RAF optimisé
 * ═══════════════════════════════════════════════════════════════
 */

/* ══════════════════════════════════════════════════════════════
   1. PAGE TRANSITIONS — Rideau noir 5 bandes
   ══════════════════════════════════════════════════════════════ */
(function initPageTransitions() {

    /* Reveal d'entrée systématique à chaque chargement */
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

    /* Sortie sur submit (sauf formulaires inline AJAX) */
    document.addEventListener('submit', e => {
        if (e.target.dataset.noTransition) return;
        document.body.classList.add('pt-leaving');
    });

})();


/* ══════════════════════════════════════════════════════════════
   2. THREE.JS — CHAMP DE PARTICULES RÉSEAU (portail uniquement)
   Injecté directement dans .portail-background existant.
   RAF optimisé avec interpolation couleur douce.
   ══════════════════════════════════════════════════════════════ */
(function initNetworkField() {

    /* Portail uniquement */
    if (!document.body.classList.contains('page-portail')) return;
    if (typeof THREE === 'undefined') return;

    /* Injecter le canvas dans le DOM existant */
    const canvas        = document.createElement('canvas');
    canvas.id           = 'matrix-bg';
    canvas.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none;';
    document.body.insertBefore(canvas, document.body.firstChild);

    /* Setup renderer */
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.6));
    renderer.setClearColor(0x020c18, 1);

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(68, 1, 0.1, 1000);
    camera.position.z = 185;

    /* Brume de profondeur */
    scene.fog = new THREE.FogExp2(0x020c18, 0.0052);

    /* Nœuds (particules) */
    const N   = 280;
    const pos = new Float32Array(N * 3);
    const SPR = 210;
    for (let i = 0; i < N; i++) {
        pos[i*3]   = (Math.random() - .5) * SPR * 2;
        pos[i*3+1] = (Math.random() - .5) * SPR;
        pos[i*3+2] = (Math.random() - .5) * SPR;
    }
    const nodeGeo = new THREE.BufferGeometry();
    nodeGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));

    /* Material — exposé globalement pour contrôle externe */
    const nodeMat = new THREE.PointsMaterial({
        color: 0x00e5ff, size: 1.5, transparent: true,
        opacity: .52, sizeAttenuation: true, depthWrite: false,
    });
    window._pMat = nodeMat;
    const nodes = new THREE.Points(nodeGeo, nodeMat);
    scene.add(nodes);

    /* Connexions réseau */
    const lineMat = new THREE.LineBasicMaterial({
        color: 0x00e5ff, transparent: true, opacity: .08, depthWrite: false,
    });
    window._lMat = lineMat;
    const edgeV = [];
    for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
            const d = Math.sqrt(
                (pos[i*3]-pos[j*3])**2 +
                (pos[i*3+1]-pos[j*3+1])**2 +
                (pos[i*3+2]-pos[j*3+2])**2
            );
            if (d < 58) edgeV.push(pos[i*3],pos[i*3+1],pos[i*3+2], pos[j*3],pos[j*3+1],pos[j*3+2]);
        }
    }
    const lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(edgeV), 3));
    const lines = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lines);

    /* Resize réactif */
    function resize() {
        const w = window.innerWidth, h = window.innerHeight;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }
    resize();
    window.addEventListener('resize', resize, { passive: true });

    /* Parallax souris */
    let mx = 0, my = 0;
    window.addEventListener('mousemove', e => {
        mx = (e.clientX / window.innerWidth  - .5) * 2;
        my = (e.clientY / window.innerHeight - .5) * 2;
    }, { passive: true });

    /* Interpolation couleur douce (lerp 5%/frame ≈ 300ms) */
    const tc = new THREE.Color(0x00e5ff);
    const cc = new THREE.Color(0x00e5ff);

    /* RAF loop — RequestAnimationFrame optimisé */
    let rafId;
    function animate() {
        rafId = requestAnimationFrame(animate);
        const t = Date.now() * 0.00022;

        /* Couleur interpolée */
        cc.lerp(tc, .05);
        nodeMat.color.copy(cc);
        lineMat.color.copy(cc);

        /* Rotation lente + parallax */
        nodes.rotation.y  = t * .16 + mx * .07;
        nodes.rotation.x  = t * .05 + my * .04;
        lines.rotation.y  = nodes.rotation.y;
        lines.rotation.x  = nodes.rotation.x;

        /* Dérive caméra */
        camera.position.x = Math.sin(t * .38) * 9 + mx * 14;
        camera.position.y = Math.cos(t * .27) * 6 + my * 9;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
    }
    animate();

    /* Nettoyage GPU */
    window.addEventListener('pagehide', () => {
        cancelAnimationFrame(rafId);
        renderer.dispose();
        nodeGeo.dispose(); nodeMat.dispose();
        lineGeo.dispose(); lineMat.dispose();
    });

})();


/* ══════════════════════════════════════════════════════════════
   3. LASER SCAN — Bouton .btn-formateur (toutes les 3 secondes)
   Double RAF pour forcer reflow avant l'animation.
   ══════════════════════════════════════════════════════════════ */
(function initLaserScan() {

    function injectLaser() {
        const btn = document.querySelector('.btn-formateur');
        if (!btn || btn.querySelector('.btn-laser')) return;
        const laser = document.createElement('span');
        laser.className = 'btn-laser';
        btn.insertBefore(laser, btn.firstChild);

        /* S'assurer que le texte est dans un span */
        const children = Array.from(btn.childNodes);
        children.forEach(n => {
            if (n.nodeType === 3 && n.textContent.trim()) {
                const sp = document.createElement('span');
                sp.className = 'btn-text';
                sp.textContent = n.textContent;
                btn.replaceChild(sp, n);
            }
        });
    }

    function fireLaser() {
        const laser = document.querySelector('.btn-laser');
        if (!laser) return;
        laser.style.transition = 'none';
        laser.style.transform  = 'translateX(-120%)';
        requestAnimationFrame(() => requestAnimationFrame(() => {
            laser.style.transition = 'transform .72s cubic-bezier(.22,1,.36,1)';
            laser.style.transform  = 'translateX(120%)';
        }));
    }

    if (!document.body.classList.contains('page-portail') &&
        !document.body.classList.contains('page-change-code')) return;

    window.addEventListener('load', () => {
        injectLaser();
        setTimeout(() => {
            fireLaser();
            setInterval(fireLaser, 3000);
        }, 1200);
    });

})();


/* ══════════════════════════════════════════════════════════════
   4. GSAP SCROLLTRIGGER — Dashboard : Apple-style scroll
   Chaque section scale-out en quittant l'écran (scrub: true)
   ══════════════════════════════════════════════════════════════ */
(function initScrollEffects() {

    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;
    if (!document.body.classList.contains('page-dashboard')) return;

    gsap.registerPlugin(ScrollTrigger);

    /* — Mode cards : reveal staggeré à l'entrée — */
    gsap.utils.toArray('.mode-card').forEach((card, i) => {
        gsap.fromTo(card,
            { opacity: 0, y: 44, scale: .95 },
            {
                opacity: 1, y: 0, scale: 1,
                duration: .85,
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

    /* — Grille modes : scale-out + opacity en quittant (scrub fluide) — */
    const modesGrid = document.querySelector('.modes-grid');
    if (modesGrid) {
        /* Titre section : parallax discret */
        const title = document.querySelector('.section-title');
        if (title) {
            gsap.to(title, {
                y: -40, opacity: 0, ease: 'none',
                scrollTrigger: {
                    trigger: modesGrid,
                    start: 'top 20%',
                    end: 'top top',
                    scrub: true,
                }
            });
        }

        /* Grille : scale 0.8 + opacity 0 en sortant */
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

    /* — Bannière : parallax ½ vitesse — */
    const banner = document.querySelector('.mode-banner');
    if (banner) {
        gsap.to(banner, {
            y: '-30%', ease: 'none',
            scrollTrigger: {
                trigger: '.dashboard-main',
                start: 'top top',
                end: 'bottom top',
                scrub: true,
            }
        });
    }

    /* — Section packs : refresh ScrollTrigger quand elle s'affiche — */
    const packsSection = document.getElementById('packsSection');
    if (packsSection) {
        new MutationObserver(() => ScrollTrigger.refresh())
            .observe(packsSection, { attributes: true, attributeFilter: ['style'] });
    }

    /* — Pack cards : stagger reveal — */
    function revealPacks() {
        document.querySelectorAll('.pack-card:not(.revealed)').forEach((c, i) => {
            setTimeout(() => c.classList.add('revealed'), i * 55);
        });
    }
    document.addEventListener('DOMContentLoaded', () => {
        const orig = window.togglePacks;
        if (typeof orig === 'function') {
            window.togglePacks = function() {
                orig();
                setTimeout(() => { ScrollTrigger.refresh(); revealPacks(); }, 80);
            };
        }
        const s = document.getElementById('packsSection');
        if (s && s.style.display !== 'none') setTimeout(revealPacks, 300);
    });

    /* — Footer fade-in — */
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
