# 小说下载器（番茄 + 七猫/灵猫）项目完整说明

> **本说明写给接手该项目的 AI 或开发者**，帮助快速理解代码结构、运行方式、数据库与敏感凭据。
> 生成时间：2026-10-07

---

## 一、项目是什么

一个**本地多用户 Web 小说下载器**，运行在 Windows 服务器（挂机宝）上：

- **番茄小说**：通过 CDP（Chrome DevTools Protocol）调用 `fanqie-desktop.exe`（Tauri 桌面应用）实现下载
- **七猫小说（灵猫）**：直接调用**逆向移植的 API**（`qimao_api.py` + `qimao_downloader.py`，从 Flutter 客户端源码移植，含签名、请求头伪装、AES 解密）
- Web 前端 + Flask 后端，支持**用户注册/登录、下载配额、用户文件隔离**
- 附带**数据库每日自动备份到邮箱**（SMTP）的功能

---

## 二、技术栈

| 类别 | 技术 |
|---|---|
| 语言 | Python 3.12（Windows Server 2022） |
| Web 后端 | Flask + flask-cors |
| 数据库 | SQLite（`app.db`） |
| 前端 | 纯静态页（原生 HTML/CSS/JS，无框架） |
| 依赖库 | requests、websocket-client、pycryptodome、psutil（见 `requirements.txt`） |

---

## 三、目录结构

```
novelmy_full_backup/
├── server.py               # 主后端（Flask），用户系统 + 番茄/七猫下载接口（核心）
├── qimao_api.py            # 七猫小说 API 客户端（签名/AES 解密/请求伪装）
├── qimao_downloader.py     # 七猫下载器（ZIP→解压→AES 解密→TXT/EPUB）
├── backup_db.py            # 数据库每日备份 → SMTP 邮件推送
├── backup_db_daily.bat     # 定时任务调用的批处理（每天 08:00）
├── config_backup.json      # ⚠️ SMTP 备份配置（含真实授权码，勿上传 git）
├── token.txt               # ⚠️ GitHub Personal Access Token（用完请撤销）
├── requirements.txt        # Python 依赖清单
├── 启动.bat                # 一键启动（pip install + python server.py）
├── git地址.txt             # GitHub 远程仓库地址
├── .gitignore              # 已排除敏感/大文件
├── app.db                  # SQLite 用户数据库
├── web_static/             # 前端页面（index.html + css/js）
├── web_downloads/          # 下载的小说文件（约 230MB，体积大不入 git）
├── _split/                 # （web_downloads 内）分卷下载缓存
├── backup/                 # 旧版本备份（不入 git）
├── _jstest/                # JS 调试临时文件（不入 git）
├── .spec-workflow/         # 规范工作流模板文档
└── 实现文档.md             # 早期实现说明
```

---

## 四、如何运行

**一键启动：** 双击 `启动.bat`（会自动 `pip install -r requirements.txt` 后启动）

或手动：

```bash
cd 项目目录
pip install -r requirements.txt
python server.py
```

- 访问地址：**http://localhost:5000**
- 番茄下载依赖 `fanqie-desktop.exe`（项目根目录，16MB）与 CDP 端口 `9222`，需保持 exe 可用
- 前端登录后即可搜索/下载，管理员可管理用户与配额

---

## 五、核心模块说明

### 5.1 `server.py`（主后端，约 1200 行，57 个函数）

- **用户系统**：注册、登录（SHA-256 + salt 加盐哈希）、会话（session 表）、`@login_required` / `@admin_required` 装饰器
- **数据库**：`get_db()` / `init_db()`，SQLite 惰性创建表
- **番茄下载流程**：`start_exe()` → 通过 CDP 获取 WebSocket → `invoke_tauri()` 调 exe 的 Tauri 命令 → 下载完成后 `api_finish_download` 登记下载记录
- **主要路由：**

| 方法 | 路由 | 功能 |
|---|---|---|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 当前用户信息 |
| GET/POST | `/api/admin/users` | 管理员：用户列表 / 新建用户 |
| DELETE | `/api/admin/users/<uid>` | 删除用户 |
| POST | `/api/admin/users/<uid>/disable` / `enable` | 禁用 / 启用 |
| POST | `/api/admin/users/<uid>/quota` | 增减下载配额 |
| GET | `/api/search` | 番茄搜索 |
| GET | `/api/book_detail` | 番茄书籍详情 |
| POST | `/api/download` | 发起番茄下载 |
| GET | `/api/jobs` | 下载任务列表 |
| GET | `/api/files` | 当前用户文件列表 |
| POST | `/api/sync` | 同步文件到 web_downloads |
| GET | `/api/file/<book_name>` | 下载小说文件 |
| GET | `/api/qimao/search` | 七猫搜索 |
| GET | `/api/qimao/book_detail` | 七猫书籍详情 |
| GET | `/api/qimao/chapters` | 七猫章节列表 |
| POST | `/api/qimao/download` | 发起七猫下载 |
| GET | `/api/qimao/file/<book_name>` | 下载七猫文件 |

### 5.2 `qimao_api.py`（七猫 API 客户端）

- 从 Flutter `lib/core/api_client.dart` 移植
- 含签名密钥 `SIGN_KEY`、AES-128 解密密钥、版本号伪装池、API 节点 `api-bc.wtzw.com` / `api-ks.wtzw.com`

### 5.3 `qimao_downloader.py`（七猫下载器）

- 从 Flutter `book_downloader.dart` + `epub_builder.dart` 移植
- 流程：ZIP 下载 → 解压 → AES 解密 → 生成 TXT/EPUB
- `download_book(book_info, chapters, fmt='txt'|'epub', progress_callback)` 返回文件字节

### 5.4 `backup_db.py`（数据库邮件备份）

- 把 `app.db` 作为附件通过 SMTP 发送到邮箱，防止数据丢失
- 配置读取 `config_backup.json`（smtp_host / smtp_port / smtp_ssl / sender / auth_code / receiver）
- 用法：`python backup_db.py --test`（测试发送）；`python backup_db.py`（正常发送）
- 日志写入 `backup_db.log`

### 5.5 `backup_db_daily.bat`（定时任务脚本）

- 由 Windows 任务计划程序每天 **08:00** 调用，执行 `python backup_db.py`

---

## 六、数据库结构（`app.db`，SQLite）

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,      -- SHA-256(salt + password)
    salt TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    is_disabled INTEGER DEFAULT 0,
    download_quota INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 下载记录表
CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    book_name TEXT NOT NULL,
    author TEXT DEFAULT '',
    book_id TEXT,
    file_name TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    download_time TEXT DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT "fanqie",     -- fanqie=番茄 / qimao=七猫
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 会话表
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## 七、⚠️ 敏感凭据清单（务必注意！）

| 文件 | 内容 | 处理建议 |
|---|---|---|
| `config_backup.json` | QQ 邮箱 **SMTP 授权码** | `.gitignore` 已排除，**严禁上传 git / 分享** |
| `token.txt` | **GitHub Personal Access Token**（`github_pat_` 开头） | 用完即**撤销**；**严禁上传 git** |
| `app.db` | 用户账号（密码为哈希+盐，相对安全） | 含用户数据，勿上传公开仓库 |
| `qimao_api.py` | 七猫签名/AES 密钥 | 逆向产物，谨慎传播 |

> **给 AI 的操作准则**：遇到上述文件时，不要把它们写入 git、不要粘贴到公开对话/日志。若需在 git 中保留模板，只提交占位符版本。

---

## 八、Git 推送指引（在主电脑执行）

项目已在本机 `git init` 并完成首个提交（`bb539ba`），`.gitignore` 已排除敏感/大文件。

1. **确认 `.gitignore` 已挡住敏感文件**（本地已验证：`config_backup.json`、`app.db`、日志、`web_downloads`、exe 均不入库）
2. **删除或忽略 `token.txt`**（.gitignore 中未包含它，push 前务必处理）
3. 配置身份并推送：
   ```bash
   git config user.name "Acimer1"
   git config user.email "Acimer1@users.noreply.github.com"
   git remote add origin https://github.com/Acimer1/novelmy.git
   git push -u origin main
   ```
4. 认证方式：GitHub Personal Access Token（勾选 `repo` 权限）或用 `gh auth login`
5. 远程仓库：`https://github.com/Acimer1/novelmy.git`

> 本机（挂机宝）网络访问 github.com 不稳定，故推到主电脑完成。

---

## 九、定时备份任务

- 任务名：**NovelmyDBBackup**（Windows 任务计划程序）
- 频率：每天 08:00，运行 `backup_db_daily.bat`
- 效果：每天自动把最新 `app.db` 发到 `config_backup.json` 指定的邮箱
- 停用：`schtasks /Delete /TN "NovelmyDBBackup" /F`

---

## 十、常见问题

1. **启动报缺少依赖** → 先 `pip install -r requirements.txt`
2. **番茄下载失败** → 检查 `fanqie-desktop.exe` 是否在项目根目录、CDP 端口 9222 是否被占用
3. **端口 5000 被占用** → 修改 `server.py` 中 `app.run()` 的端口
4. **备份邮件发不出** → 先 `python backup_db.py --test`，检查 `config_backup.json` 的授权码是否失效（QQ 邮箱授权码可能被重置）
5. **前端页面修改** → 直接改 `web_static/index.html`（单文件）或 css/js
