/* ═══════════════════════════════════════════════════
 * effects.js - 全局微动效
 *  - 按钮波纹（自动绑定 .btn 类）
 *  - 卡片 3D 倾斜（自动绑定 .tilt-card）
 *  - 页面切换过渡（hook switchTab）
 *  - 数字 count-up
 *  - 滚动指示器
 * ═══════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  // ── 按钮波纹 ──
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn, .btn-sm, .btn-xs, .btn-go, .btn-cyan, .btn-outline, .btn-ghost, .btn-red, .split-btn, .fmt-opt, .nav-btn, .subtab, .pg-btn, .confirm-btn');
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 1.2;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
    if (getComputedStyle(btn).position === 'static') btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 700);
  });

  // ── 卡片 3D 倾斜 ──
  function attachTilt(el) {
    if (el.dataset.tilt === '1') return;
    el.dataset.tilt = '1';
    const max = 4;
    el.addEventListener('mousemove', (e) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      el.style.transform = `perspective(1000px) rotateX(${-y * max}deg) rotateY(${x * max}deg) translateY(-2px) scale(1.01)`;
    });
    el.addEventListener('mouseleave', () => {
      el.style.transform = '';
    });
  }

  function scanTilt() {
    document.querySelectorAll('.tilt-card').forEach(attachTilt);
  }

  // 定时扫描新增卡片
  setInterval(scanTilt, 800);

  // ── 数字 count-up ──
  function countUp(el, target, duration) {
    duration = duration || 1200;
    const start = parseFloat(el.textContent) || 0;
    const t0 = performance.now();
    function tick(t) {
      const p = Math.min(1, (t - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = start + (target - start) * eased;
      el.textContent = Math.floor(val).toLocaleString();
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = target.toLocaleString();
    }
    requestAnimationFrame(tick);
  }

  global.countUp = countUp;
  global.scanTilt = scanTilt;

  // ── 滚动指示器（首屏提示） ──
  function setupScrollHint() {
    if (document.querySelector('.scroll-hint')) return;
    const hint = document.createElement('div');
    hint.className = 'scroll-hint';
    document.body.appendChild(hint);
    function check() {
      if (window.scrollY > 80) hint.classList.remove('show');
      else if (document.body.scrollHeight > window.innerHeight + 200) hint.classList.add('show');
      else hint.classList.remove('show');
    }
    window.addEventListener('scroll', check, { passive: true });
    window.addEventListener('resize', check);
    setTimeout(check, 500);
  }
  setTimeout(setupScrollHint, 1500);

  // ── 错误抖动辅助 ──
  global.shakeElement = function (el) {
    if (!el) return;
    el.classList.remove('shake-on-error');
    void el.offsetWidth; // 触发 reflow 重启动画
    el.classList.add('shake-on-error');
    setTimeout(() => el.classList.remove('shake-on-error'), 500);
  };

  // ── 成功/错误脉冲 ──
  global.pulseSuccess = function (el) {
    if (!el) return;
    el.classList.remove('pulse-success');
    void el.offsetWidth;
    el.classList.add('pulse-success');
    setTimeout(() => el.classList.remove('pulse-success'), 700);
  };
  global.pulseError = function (el) {
    if (!el) return;
    el.classList.remove('pulse-error');
    void el.offsetWidth;
    el.classList.add('pulse-error');
    setTimeout(() => el.classList.remove('pulse-error'), 700);
  };
})(window);
