/* ============================================================
   BIRTHDAY SPA — script.js
   ============================================================ */

/* ── CONFETTI ─────────────────────────────────────────────── */
(function spawnConfetti() {
  const container = document.getElementById('confetti-container');
  if (!container) return;

  const shapes  = ['●', '■', '▲', '★', '♥'];
  const colors  = ['#F5C842', '#FDE88A', '#F2708A', '#FAB0C0', '#FFFFFF', '#D4A820'];
  const total   = 55;

  for (let i = 0; i < total; i++) {
    const el = document.createElement('span');
    el.textContent = shapes[Math.floor(Math.random() * shapes.length)];

    const size  = Math.random() * 14 + 8;
    const left  = Math.random() * 100;
    const delay = Math.random() * 6;
    const dur   = Math.random() * 8 + 6;

    el.style.cssText = `
      position: absolute;
      top: 0;
      left: ${left}%;
      font-size: ${size}px;
      color: ${colors[Math.floor(Math.random() * colors.length)]};
      opacity: 0.8;
      animation: confettiFall ${dur}s ${delay}s linear infinite;
      user-select: none;
      pointer-events: none;
    `;
    container.appendChild(el);
  }
})();


/* ── OPEN SECTION → Redirige a página propia ──────────────── */
const sectionRoutes = {
  galeria: '/pages/album.html',
  deseos:  '/pages/carta.html',
  programa: '/pages/video.html'
};

function openSection(key) {
  const route = sectionRoutes[key];
  if (route) {
    // Pequeña animación de salida antes de navegar
    document.body.style.transition = 'opacity .3s ease';
    document.body.style.opacity = '0';
    setTimeout(() => { window.location.href = route; }, 280);
  }
}


/* ── SCROLL REVEAL (IntersectionObserver) ─────────────────── */
(function initReveal() {
  const items = document.querySelectorAll('.card, .sections__header');
  if (!('IntersectionObserver' in window)) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.style.animation = 'fadeUp .6s ease both';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  items.forEach((el) => {
    el.style.opacity = '0';
    observer.observe(el);
  });
})();
