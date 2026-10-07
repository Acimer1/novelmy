/* ═══════════════════════════════════════════════════
 * toast.js - Toast 通知 + 确认弹窗组件
 * 用法：
 *   <link rel="stylesheet" href="/toast.css">
 *   <script src="/toast.js"></script>
 *
 *   toast.success('保存成功')
 *   toast.error('网络错误', { duration: 5000 })
 *   toast.warning('次数不足')
 *   toast.info('正在加载...')
 *   toast.show({ type: 'success', title: '...', message: '...', duration: 3000 })
 *
 *   confirmDialog('确认操作', '真的要删除吗？', () => { ... })
 *   confirmDialog({ title: '...', message: '...', onOk: fn, onCancel: fn, okText: '...', cancelText: '...' })
 * ═══════════════════════════════════════════════════ */

(function (global) {
  'use strict';

  // ── 工具：HTML 转义 ──
  const escapeHtml = (s) => {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  };

  // ── 容器：单例 ──
  let container = null;
  function getContainer() {
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  // ── 变体元数据 ──
  const VARIANTS = {
    success: { icon: '✓', title: '成功' },
    error: { icon: '✕', title: '错误' },
    warning: { icon: '⚠', title: '注意' },
    info: { icon: 'ℹ', title: '提示' },
  };

  // ── 主函数：show ──
  /**
   * @param {object|string} opts - 配置或字符串
   * @param {string} [opts.type='info'] - success/error/warning/info
   * @param {string} [opts.title] - 标题
   * @param {string} [opts.message] - 内容
   * @param {number} [opts.duration=3500] - 自动消失毫秒，0=不自动关
   * @param {boolean} [opts.closable=true] - 是否可手动关闭
   */
  function show(opts) {
    if (typeof opts === 'string') opts = { message: opts };
    const type = VARIANTS[opts.type] ? opts.type : 'info';
    const variant = VARIANTS[type];
    const title = opts.title != null ? opts.title : variant.title;
    const message = opts.message != null ? opts.message : '';
    const duration = opts.duration != null ? opts.duration : type === 'error' ? 4500 : 3500;
    const closable = opts.closable !== false;

    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.setAttribute('role', 'alert');
    el.innerHTML = `
      <div class="toast-icon">${variant.icon}</div>
      <div class="toast-content">
        <div class="toast-title">${escapeHtml(title)}</div>
        ${message ? `<div class="toast-message">${escapeHtml(message)}</div>` : ''}
      </div>
      ${closable ? '<button class="toast-close" aria-label="关闭">×</button>' : ''}
    `;

    let timer = null;
    const close = () => {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      el.classList.add('toast-leaving');
      setTimeout(() => el.remove(), 300);
    };

    if (closable) {
      el.querySelector('.toast-close').addEventListener('click', close);
    }
    if (duration > 0) {
      timer = setTimeout(close, duration);
    }

    // 鼠标悬停暂停进度（可选增强）
    el.addEventListener('mouseenter', () => {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      const bar = el.querySelector(':scope > *');
      // 不复杂化进度条：直接停止关闭即可
    });
    el.addEventListener('mouseleave', () => {
      if (duration > 0 && !timer) {
        timer = setTimeout(close, 1500);
      }
    });

    getContainer().appendChild(el);
    return { close };
  }

  // ── 快捷方法 ──
  function makeShortcut(type) {
    return (msg, opts) => {
      // 兼容两种调用：toast.success('msg') 与 toast.success('msg', { duration: 5000 })
      if (typeof msg === 'string') {
        return show(Object.assign({ type, message: msg }, opts || {}));
      }
      return show(Object.assign({ type }, msg));
    };
  }

  const toast = {
    show,
    success: makeShortcut('success'),
    error: makeShortcut('error'),
    warning: makeShortcut('warning'),
    info: makeShortcut('info'),
  };

  // ── Confirm 弹窗 ──
  /**
   * @param {string|object} titleOrOpts
   * @param {string} [message]
   * @param {function} [onOk]
   * @param {function} [onCancel]
   */
  function confirmDialog(titleOrOpts, message, onOk, onCancel) {
    let opts;
    if (typeof titleOrOpts === 'string') {
      opts = { title: titleOrOpts, message, onOk, onCancel };
    } else {
      opts = Object.assign({}, titleOrOpts);
    }

    const title = opts.title || '确认';
    const msg = opts.message || '';
    const okText = opts.okText || '确定';
    const cancelText = opts.cancelText || '取消';
    const danger = opts.danger === true;
    const handleOk = opts.onOk;
    const handleCancel = opts.onCancel;

    return new Promise((resolve) => {
      const mask = document.createElement('div');
      mask.className = 'confirm-mask';
      mask.innerHTML = `
        <div class="confirm-box" role="dialog" aria-modal="true">
          <h3 class="confirm-title"><span class="confirm-icon">?</span>${escapeHtml(title)}</h3>
          <div class="confirm-message">${escapeHtml(msg)}</div>
          <div class="confirm-actions">
            <button class="confirm-btn" data-act="cancel">${escapeHtml(cancelText)}</button>
            <button class="confirm-btn ${danger ? '' : 'confirm-btn-primary'}" data-act="ok" ${
        danger ? 'style="background:linear-gradient(135deg,#ef4444,#dc2626);border-color:rgba(239,68,68,.4);box-shadow:0 4px 16px rgba(239,68,68,.3),inset 0 1px 0 rgba(255,255,255,.2);color:#fff;"' : ''
      }>${escapeHtml(okText)}</button>
          </div>
        </div>
      `;

      const close = (result) => {
        mask.style.animation = 'confirm-fade 0.18s ease forwards';
        const box = mask.querySelector('.confirm-box');
        box.style.animation = 'confirm-pop 0.18s cubic-bezier(0.4,0,0.6,1) reverse forwards';
        setTimeout(() => {
          mask.remove();
          resolve(result);
          if (result && handleOk) {
            try {
              handleOk();
            } catch (e) {
              console.error('confirmDialog onOk error:', e);
            }
          } else if (!result && handleCancel) {
            try {
              handleCancel();
            } catch (e) {
              console.error('confirmDialog onCancel error:', e);
            }
          }
        }, 180);
      };

      mask.addEventListener('click', (e) => {
        if (e.target === mask) close(false);
      });
      mask.querySelector('[data-act="ok"]').addEventListener('click', () => close(true));
      mask.querySelector('[data-act="cancel"]').addEventListener('click', () => close(false));
      document.addEventListener('keydown', function escHandler(e) {
        if (e.key === 'Escape') {
          document.removeEventListener('keydown', escHandler);
          close(false);
        }
        if (e.key === 'Enter') {
          document.removeEventListener('keydown', escHandler);
          close(true);
        }
      });

      document.body.appendChild(mask);
      // 焦点放到确定按钮
      setTimeout(() => {
        const okBtn = mask.querySelector('[data-act="ok"]');
        if (okBtn) okBtn.focus();
      }, 50);
    });
  }

  // ── 暴露到全局 ──
  global.toast = toast;
  global.confirmDialog = confirmDialog;
})(window);
