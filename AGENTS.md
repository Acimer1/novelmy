# novelmy 项目上下文

这是一个 Windows 多用户小说下载站：Vue 3 页面通过同源 API 访问 Flask，SQLite 记录会话、配额、卡密和用户的下载记录。番茄和七猫共用文件列表，但**下载完成、扣次和落盘的时机不同**。流程图见[项目导读](docs/ONBOARDING.md)。

## 运行、构建与开发

以下 PowerShell 命令均从**仓库根目录**执行。服务机需安装 Python 和带 npm 的 Node.js（推荐 Node 22.12 或更新的 22.x），不依赖 mise。

| 目的 | 命令 | 实际行为 |
|---|---|---|
| 一键启动 | `.\start.bat` | 创建或复用 `.venv`，补齐依赖，每次构建前端并校验首页引用的 JS/CSS，再启动 Flask。默认访问 `http://localhost:5000/`，服务监听 `0.0.0.0`。 |
| 换端口 | `.\start.bat --port 5001` | 将端口参数传递给 [server.py](server.py)。 |
| 只构建 | `.\start.bat --build` | 生成并校验前端，不启动 Flask，也不安装 Python 业务依赖。 |
| Vue 热更新 | `npm --prefix frontend ci --include=dev`，然后 `npm --prefix frontend run dev` | Vite 默认使用演示数据；开发页面加 `?mode=live` 后，`/api` 代理到 `127.0.0.1:5000`，需要单独启动后端。 |
| 只运行后端 | `.\.venv\Scripts\python.exe server.py` | 跳过前端构建，要求依赖已安装；不等于隔离模式。 |

编辑 [frontend/src/](frontend/src/) 和 [frontend/public/](frontend/public/)，不要编辑 `web_static/`：它是 Git 忽略的纯产物，[Vite](frontend/vite.config.js) 每次生产构建都会清空并重建。生产首页 `/` 默认连接真实 API，`/?mode=demo` 使用演示数据；原 `/web_static/preview/index.html?mode=live` 是兼容 URL，不是另一个前端工程。

**不要用正式启动命令做无副作用的检查。** 根入口调用 [backend/server.py](backend/server.py) 的 `main()`：建表和迁移、同步文件，并启动或复用番茄桌面程序；已有进程不可连接时可能被重启。`flask run` 不执行这段初始化。只改页面时优先用 Vite 演示模式；需要真实 API 时用下面的隔离服务。

## 测试与隔离联调

```powershell
# 前端：Node 内置测试运行器；第二条只跑一条具名测试
npm --prefix frontend test
node --test --test-name-pattern="任务接受后只扣一次" frontend/test/preview.test.js

# Python：首次准备隔离环境（已有 .venv 和依赖时跳过这两条）
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 只跑一个 Flask 测试方法；不需要 Chrome 或前端构建
.\.venv\Scripts\python.exe -m unittest -v tests.test_integration.LiveFlows.test_account_download_files_and_admin

# 完整 Python 回归：含浏览器用例，须先有生产构建和 Chrome
.\start.bat --build
$env:CHROME_BIN = Get-ItemPropertyValue 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe' '(default)'
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

- 项目未配置独立的 lint 命令；Vite 构建和测试是不同的检查。
- 手动联调：构建前端后运行 `.\.venv\Scripts\python.exe -m tests.integration_backend`，访问 `http://127.0.0.1:5086/`。注册测试账户，卡密 `LOCAL-TEST` 可兑换 4 次；番茄样书 ID 为 `10001`，七猫为 `20001`、`20002`。
- [隔离后端](tests/integration_backend.py) 在导入 Flask 模块**之前**指定 `NOVELMY_TEST_ROOT`，每次在 `.integration/` 下创建新库和文件目录，只替换外部书源。接口测试验证真实 Cookie、SQLite 扣次和文件字节；[Chrome 测试](tests/test_browser_live.py) 从 `/` 驱动读者和管理员流程。这些测试通过不代表真实桌面程序或七猫线上服务可用。

## 跨文件的业务边界

- **页面与请求。** [App.vue](frontend/src/App.vue) 管理登录态、当前页、主题和配额；已访问的两个书源页切换时只隐藏不销毁，避免丢失正在进行的下载。[SourceShelf.vue](frontend/src/pages/SourceShelf.vue) 管理搜索、格式、确认及逐条批量提交；[library.js](frontend/src/api/library.js) 负责模式选择、书源字段归一化和番茄轮询。改下载协议时同时核对这两处和 Flask 路由。指南文案与跳转在 [GuidePage.vue](frontend/src/pages/GuidePage.vue)。
- **认证与归属。** Flask session 中的 `sid` 关联 SQLite 的 `sessions`、`users`；受保护路由通过 `g.user` 取得当前用户。`init_db()` 同时负责建表和兼容已有库，没有独立的迁移命令。`downloads` 记录文件归属和来源，物理文件共享存放；用户列表和取回接口不能用一次全目录扫描替代。
- **番茄：接受任务不等于可取文件。** `/api/download` 委托根目录 `fanqie-desktop.exe`，普通用户在任务被接受时扣次，并写入 `file_size=0` 占位。前端轮询 `/api/jobs`，完成后调用 `/api/finish_download`；后端另有定时校验、文件同步和占位修复。修改重试时须保留复用占位不重复扣次、管理员不扣次的行为。桌面程序历史背景见[补丁记录](docs/exe参数设置.md)，当前行为以 `start_exe()` 为准。
- **七猫：同一请求生成文件。** `/api/qimao/download` 使用 [QimaoApiClient](backend/qimao_api.py) 获取书籍和章节，由 [QimaoBookDownloader](backend/qimao_downloader.py) 生成 TXT/EPUB。写入文件后才更新配额和下载记录，不走番茄任务队列。
- **取回与分卷。** [FilesPage.vue](frontend/src/pages/FilesPage.vue) 根据记录的 `source` 选择取回接口。TXT 分卷免费，任务状态保存在 Flask 进程内，重启后任务 ID 失效；产物位于 `data/novel_cache/split/`。

## 数据、升级与备份

正式库为 `data/app.db`，小说正文在 `data/novel_cache/`。番茄桌面程序先写用户下载目录 `Downloads/FanqieNovels`，再同步到 Web 文件目录；七猫直接写 Web 文件目录。升级旧部署前先停服，把服务器自己的 `app.db` 和 `web_downloads/` 备份到仓库外，再分别迁移到这两个新位置：只有库没有正文，历史记录仍在但文件可能无法取回。

[定时备份批处理](script/backup/backup_db_daily.bat) 调用[邮件备份脚本](script/backup/backup_db.py)，不经过 Flask。它备份数据库，不备份小说正文；配置优先读取仓库根的 `config_backup.json`，其次读取脚本同目录配置，日志写入 `logs/backup_db.log`。书源链接示例见 [docs/链接url.txt](docs/链接url.txt)。
