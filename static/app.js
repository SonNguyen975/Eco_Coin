/**
 * ECO COIN – app.js
 * Global JavaScript: animations, number counters, utilities
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── ANIMATE BALANCE COUNT-UP ──
    const balanceEl = document.getElementById('balanceDisplay');
    if (balanceEl) {
        const target = parseInt(balanceEl.dataset.value || '0', 10);
        animateCounter(balanceEl, 0, target, 1200, v =>
            v.toLocaleString('vi-VN') + 'đ'
        );
    }

    // ── FADE-IN CARDS ON SCROLL ──
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.tx-card').forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(16px)';
        card.style.transition = `opacity 0.4s ease ${i * 0.05}s, transform 0.4s ease ${i * 0.05}s`;
        observer.observe(card);
    });

    // ── AUTO-DISMISS ALERTS ──
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease, max-height 0.5s ease';
            alert.style.opacity = '0';
            alert.style.maxHeight = '0';
            alert.style.padding = '0';
            alert.style.margin = '0';
        }, 5000);
    });

    // ── RIPPLE EFFECT ON BUTTONS ──
    document.querySelectorAll('.btn-primary').forEach(btn => {
        btn.addEventListener('click', function (e) {
            const ripple = document.createElement('span');
            const rect = btn.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            ripple.style.cssText = `
                position:absolute;
                border-radius:50%;
                background:rgba(255,255,255,0.25);
                width:${size}px; height:${size}px;
                left:${e.clientX - rect.left - size/2}px;
                top:${e.clientY - rect.top - size/2}px;
                animation: ripple 0.6s ease-out forwards;
                pointer-events:none;
            `;
            btn.style.position = 'relative';
            btn.style.overflow = 'hidden';
            btn.appendChild(ripple);
            setTimeout(() => ripple.remove(), 700);
        });
    });

    // Inject ripple keyframe
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            from { transform: scale(0); opacity: 1; }
            to   { transform: scale(2); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
});

/**
 * Animate a number counter from start to end.
 * @param {Element} el - Target element
 * @param {number} start - Start value
 * @param {number} end - End value
 * @param {number} duration - Duration in ms
 * @param {Function} formatter - Format function (value => string)
 */
function animateCounter(el, start, end, duration, formatter) {
    if (start === end) { el.textContent = formatter(end); return; }
    const startTime = performance.now();
    const diff = end - start;

    function update(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Ease-out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + diff * eased);
        el.textContent = formatter(current);
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}
