# fanqie-desktop.exe — 当前 CDP 参数设置

> 记录下载器当前实际使用的 exe 启动参数，供排查 CDP 连接问题对照使用。
> 文件位置：`C:\Users\acimer\AppData\Local\Fanqie Novel Downloader\`

## 一、exe 基本信息

| 项目 | 值 |
|------|-----|
| exe 文件名 | `fanqie-desktop.exe` |
| 完整路径 | `C:\Users\acimer\AppData\Local\Fanqie Novel Downloader\fanqie-desktop.exe` |
| 文件大小 | 16,734,208 字节（约 16MB） |
| 文件修改时间 | **2026-07-30 02:01:05** |
| 框架 | Tauri 2（内置 wry） |
| 端口常量 | `CDP_PORT = 9222` |

## 二、server.py 中设置的启动参数

`server.py` 第 225–236 行的启动逻辑：

```python
# 带CDP参数启动
if EXE_PATH.exists():
    env = os.environ.copy()
    env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = f'--remote-debugging-port={CDP_PORT} --remote-allow-origins=*'
    subprocess.Popen(str(EXE_PATH), env=env)
    time.sleep(5)
    try:
        r = requests.get(f'http://127.0.0.1:{CDP_PORT}/json/list', timeout=3)
        return r.status_code == 200 and bool(r.json())
    except:
        pass
return False
```

### 关键参数

| 参数名 | 值 | 作用 |
|--------|-----|------|
| 环境变量 `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` | `--remote-debugging-port=9222 --remote-allow-origins=*` | 让 WebView2 打开 9222 调试端口，并允许任意来源连接 |
| 子进程启动方式 | `subprocess.Popen(str(EXE_PATH), env=env)` | 用带参环境变量拉起 exe |
| 健康检查 | `GET http://127.0.0.1:9222/json/list` | 启动后等待 5 秒，探测 CDP 端口是否响应 |

## 三、CDP 连接逻辑

### 获取 WebSocket 地址（第 239–248 行）

```python
def get_cdp_ws_url():
    """获取CDP WebSocket URL"""
    try:
        r = requests.get(f'http://127.0.0.1:{CDP_PORT}/json/list', timeout=3)
        targets = r.json()
        if targets:
            return targets[0]['webSocketDebuggerUrl']
    except:
        pass
    return None
```

### 调用 Tauri 命令（第 251 行起）

```python
def invoke_tauri(action, payload=None):
    ws_url = get_cdp_ws_url()
    if not ws_url:
        return {'error': '无法连接到exe'}
    ws = websocket.create_connection(ws_url, timeout=30)
    cmd = {
        'id': 1,
        # ...注入 JS / 调用 dispatch 命令，触发番茄下载
    }
```

## 四、整个调用链

```
浏览器 → Flask(server.py, localhost:5000)
        → 设置 WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS
        → subprocess.Popen(fanqie-desktop.exe)
        → WebView2 打开 9222 调试端口
        → GET http://127.0.0.1:9222/json/list 取 WebSocket URL
        → WebSocket 注入 JS / 调 Tauri dispatch → 番茄 API 下载
```

## 五、注意事项（来自排查总结）

- 以上参数是 `server.py` **写入环境变量**的方式，但当前 2026-07-30 版 exe 的 wry **强制传参**，导致外部环境变量里的 `--remote-debugging-port` 实际不生效 → CDP 打不开。
- 修复方向：在 `tauri.conf.json` 的窗口配置加 `"additionalBrowserArgs": "--remote-debugging-port=9222 --remote-allow-origins=*"` 后重新构建 exe；或换旧版 exe；或换到 CDP 曾经成功的机器。
- 本机（宿主机）Web 服务可正常启动，灵猫（七猫）下载可用。

## 六、2026-08-30 已修复：二进制 Patch 方案

### 问题根因（已确认）

exe 内硬编码了 wry 0.55.1 的默认附加浏览器参数：

```
--disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection --autoplay-policy=no-user-gesture-required --proxy-server=http:// --proxy-server=socks5://
```

wry 总是把这个**非空**字符串传给 `CreateCoreWebView2EnvironmentWithOptions`，因此
优先级更高的 `additionalBrowserArguments` 覆盖了：
- 环境变量 `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` ❌
- 注册表键 `HKCU\Software\Microsoft\Edge\WebView2\WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` ❌

（微软文档优先级：additionalBrowserArguments > 注册表键 > 环境变量）

### 修复操作（无需重新构建 exe）

直接**二进制 Patch** exe 中的硬编码参数字符串：

| 项 | 值 |
|----|-----|
| 字符串偏移 | `11930880`（ASCII，UTF-8 存储） |
| 原始长度 | `153` 字节 |
| 替换为 | `--remote-debugging-port=9222 --remote-allow-origins=*`（53 字节 + 100 字节 0x00 填充） |

替换后 WebView2 实际收到的附加参数即调试参数，CDP 9222 端口正常打开。

### 验证结果（2026-08-30）

- ✅ `GET http://127.0.0.1:9222/json/list` → 200，返回 target（title=番茄小说下载器）
- ✅ `/api/info` → `cdp_connected: true`
- ✅ `/api/search?q=仙逆` → 正常返回书籍列表（Tauri 命令调用成功）
- ✅ `/api/book_detail` → 106ms 返回书籍详情

### 备份与还原

- 修改前备份：`fanqie-desktop.exe.orig`（16734208 字节，与项目目录同位置）
- 还原方法：停止 exe → 用 `fanqie-desktop.exe.orig` 覆盖回 `fanqie-desktop.exe`

### 注意事项

- exe 无数字签名（NotSigned），Patch 不影响运行。
- 若以后更换/更新 exe，需重新执行 Patch（偏移可能变化，需重新定位字符串）。
- 该 Patch 使 exe 自身携带调试参数，即使被 `server.py` 杀进程后以任意方式重启，CDP 依然会打开（比环境变量方式更健壮）。
