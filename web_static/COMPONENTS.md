# 前端组件使用文档

> 适用版本：2026-09-01 新增的独立 UI 组件模块
> 设计原则：融入「深空玻璃拟态」风格，开箱即用

---

## 一、目录

- [Toast 通知](#toast-通知)
- [确认弹窗 confirmDialog](#确认弹窗-confirmdialog)
- [骨架屏 skeleton](#骨架屏-skeleton)
- [错误页 error.html](#错误页-errorhtml)

---

## Toast 通知

### 引入

```html
<link rel="stylesheet" href="/toast.css">
<script src="/toast.js"></script>
```

### 基础用法

```js
// 成功
toast.success('保存成功');

// 错误
toast.error('网络异常');

// 警告
toast.warning('次数不足');

// 信息
toast.info('正在加载...');
```

### 高级用法（带选项）

```js
toast.show({
  type: 'success',           // 'success' | 'error' | 'warning' | 'info'
  title: '保存成功',
  message: '你的修改已保存',
  duration: 3000,             // 自动消失毫秒，0=不自动关，默认按 type 自动
  closable: true,             // 是否可手动关闭
});

// 返回 { close } 句柄
const t = toast.error('hello');
setTimeout(t.close, 1000);  // 手动关闭
```

### 替换 alert

```js
// 旧
if (!name) { alert('请输入姓名'); return; }

// 新
if (!name) { toast.warning('请输入姓名'); return; }
```

---

## 确认弹窗 confirmDialog

### 引入

> 已包含在 `toast.js` 中，无需额外引入。

### 用法（Promise 风格）

```js
const ok = await confirmDialog({
  title: '删除确认',
  message: '确定要删除这本书吗？此操作不可恢复。',
  okText: '删除',
  cancelText: '再想想',
  danger: true,               // 红色按钮
  onOk: () => { /* 点确定 */ },
  onCancel: () => { /* 点取消 */ },
});
if (ok) {
  // 用户点了确定
}
```

### 用法（兼容老式回调）

```js
confirmDialog('下载确认', `下载《${name}》将消耗 1 次下载次数，是否继续？`, () => {
  // 用户点确定
});
```

### 替换 confirm

```js
// 旧
if (!confirm('确认删除？')) return;

// 新
const ok = await confirmDialog({ title: '确认', message: '确认删除？', danger: true });
if (!ok) return;
```

### 快捷键

- `Enter` = 确认
- `Esc` = 取消
- 点击遮罩 = 取消

---

## 骨架屏 skeleton

### 引入

```html
<link rel="stylesheet" href="/skeleton.css">
<script src="/skeleton.js"></script>
```

### 书籍网格骨架

```js
skeleton.bookGrid('fResults', 6);  // 6 个书籍卡片
```

### 文件列表骨架

```js
skeleton.fileList('fFiles', 5);
```

### 详情页骨架

```js
skeleton.detail('fDetail');
```

### 文字骨架

```js
skeleton.text('myDiv', 3);  // 3 行文字
```

### 表格行骨架

```js
skeleton.tableRow('aUsers', 5, 4);  // 5 行 4 列
```

### 清除骨架

```js
skeleton.hide('fResults');
```

### 实战示例：搜索时显示骨架

```js
async function fSearch() {
  const c = document.getElementById('fResults');
  skeleton.bookGrid('fResults', 6);  // 显示骨架
  try {
    const r = await api('/api/search?q=...');
    const d = await r.json();
    // 渲染真实结果
    c.innerHTML = ...;
  } catch (e) {
    skeleton.hide('fResults');
    toast.error('搜索失败');
  }
}
```

---

## 错误页 error.html

### 访问

| URL                            | 含义            |
| ------------------------------ | --------------- |
| `/error.html?code=404`         | 页面不存在      |
| `/error.html?code=500`         | 服务器内部错误  |
| `/error.html?code=403`         | 无权访问        |
| `/error.html?code=401`         | 未登录          |

### 跳转用法

```js
// 前端
if (response.status === 404) {
  location.href = '/error.html?code=404';
}
```

### 后端返回友好错误

```python
@app.errorhandler(404)
def not_found(e):
    return send_file('web_static/error.html?code=404')  # 或重定向
```

---

## 风格规范

所有组件均：
- 玻璃拟态（半透明 + 模糊 + 顶部高光线）
- 橙色 / 青色 / 红色 / 绿色 主题色与项目一致
- 入场出场动画（cubic-bezier 缓动）
- 移动端适配（@media max-width: 640px）
- GPU 友好（仅 transform / opacity）

---

## 浏览器兼容

- Chrome / Edge 90+
- Firefox 88+
- Safari 14+（含 backdrop-filter 支持）

不支持的环境会自动回退为不透明背景，仍可使用。
