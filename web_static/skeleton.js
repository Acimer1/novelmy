/* ═══════════════════════════════════════════════════
 * skeleton.js - 骨架屏加载占位组件
 * 用法：
 *   <link rel="stylesheet" href="/skeleton.css">
 *   <script src="/skeleton.js"></script>
 *
 *   skeleton.bookGrid('container-id', 6)  // 渲染 6 个书籍卡片骨架
 *   skeleton.fileList('container-id', 5)  // 渲染 5 个文件行骨架
 *   skeleton.detail('container-id')       // 渲染详情页骨架
 *   skeleton.text('container-id', 3)      // 渲染 3 行文字骨架
 *   skeleton.hide('container-id')         // 清除
 * ═══════════════════════════════════════════════════ */

(function (global) {
  'use strict';

  function el(html) {
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstChild;
  }

  function $(id) {
    return typeof id === 'string' ? document.getElementById(id) : id;
  }

  function clear(container) {
    if (!container) return;
    container.innerHTML = '';
  }

  // ── 书籍网格骨架 ──
  function bookGrid(containerId, count) {
    count = count || 6;
    const c = $(containerId);
    if (!c) return;
    clear(c);
    const grid = el('<div class="skeleton-book"></div>');
    for (let i = 0; i < count; i++) {
      const card = el(`
        <div class="skeleton-book-card">
          <div class="skeleton-book-cover"></div>
          <div class="skeleton-book-info">
            <div class="skeleton-book-title"></div>
            <div class="skeleton-book-meta"></div>
          </div>
        </div>
      `);
      grid.appendChild(card);
    }
    c.appendChild(grid);
  }

  // ── 文件列表骨架 ──
  function fileList(containerId, count) {
    count = count || 5;
    const c = $(containerId);
    if (!c) return;
    clear(c);
    for (let i = 0; i < count; i++) {
      const row = el(`
        <div class="skeleton-file-row">
          <div class="skeleton-file-icon"></div>
          <div class="skeleton-file-info">
            <div class="skeleton-file-name"></div>
            <div class="skeleton-file-meta"></div>
          </div>
          <div class="skeleton-file-action"></div>
        </div>
      `);
      c.appendChild(row);
    }
  }

  // ── 详情页骨架 ──
  function detail(containerId) {
    const c = $(containerId);
    if (!c) return;
    clear(c);
    c.appendChild(el(`
      <div class="skeleton-detail">
        <div class="skeleton-cover"></div>
        <div class="skeleton-detail-info">
          <div class="skeleton-detail-title"></div>
          <div class="skeleton-detail-line short"></div>
          <div class="skeleton-detail-line medium"></div>
          <div class="skeleton-detail-line long"></div>
        </div>
      </div>
    `));
  }

  // ── 文字骨架 ──
  function text(containerId, lines) {
    lines = lines || 3;
    const c = $(containerId);
    if (!c) return;
    clear(c);
    for (let i = 0; i < lines; i++) {
      c.appendChild(el('<div class="skeleton-block"></div>'));
    }
  }

  // ── 表格行骨架 ──
  function tableRow(containerId, rows, cols) {
    rows = rows || 5;
    cols = cols || 4;
    const c = $(containerId);
    if (!c) return;
    clear(c);
    for (let i = 0; i < rows; i++) {
      const row = el('<div class="skeleton-table-row"></div>');
      for (let j = 0; j < cols; j++) {
        const cell = el('<div class="skeleton-table-cell"></div>');
        cell.style.flex = '1';
        cell.style.width = (60 + Math.random() * 30) + '%';
        row.appendChild(cell);
      }
      c.appendChild(row);
    }
  }

  // ── 清除骨架 ──
  function hide(containerId) {
    const c = $(containerId);
    if (!c) return;
    clear(c);
  }

  global.skeleton = {
    bookGrid,
    fileList,
    detail,
    text,
    tableRow,
    hide,
  };
})(window);
