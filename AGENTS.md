# novelmy 项目上下文

## 运行与验证

在 Windows 仓库根目录执行：

```powershell
python -m pip install -r requirements.txt
python server.py
```

- 默认访问 `http://localhost:5000`；可用 `python server.py --port 5001` 指定端口。服务实际监听 `0.0.0.0`。若 `python` 指向 Microsoft Store，可在命令前加 `mise exec --`。
- [启动.bat](启动.bat) 是同一流程的一键入口，但会隐藏 pip 输出。根入口调用 [backend/server.py](backend/server.py) 的 `main()` 建表、迁移、同步文件、启动或复用桌面程序；`flask run` 不执行这些步骤。生产启动不是只读检查。
- 旧首页由 Flask 直接提供。新版 Vue 工程在 [frontend/](frontend/)：首次运行 `npm ci`，`npm run dev` 启动本地演示，`npm test` 运行前端测试，`node --test test/preview.test.js` 运行单个测试文件。`npm run build` 只写 `web_static/preview/`，不替换首页。

### 新版连接哪个后端

- **演示模式**：新版页面不带 `?mode=live` 时使用模拟数据；即使从正式 Flask 端口打开，也不会访问账户和下载 API。
- **本地正式后端**：先构建前端，在仓库根运行 `.\.venv\Scripts\python.exe server.py`，打开 `http://127.0.0.1:5000/web_static/preview/index.html?mode=live`。请求发往同源 Flask，读写 `data/app.db` 和 `data/novel_cache/`，使用真实书源与配额。`/` 仍是旧首页。
- **升级旧部署**：在拉取此重构提交前停服，先将服务器原有 `app.db` 和 `web_downloads/` 备份到仓库外。部署后分别恢复到 `data/app.db` 和 `data/novel_cache/`，再启动服务。旧路径曾被 Git 跟踪，新路径不随提交分发。

### 用隔离数据库验收新版

在仓库根目录执行（项目虚拟环境需已安装 `requirements.txt`）：

```powershell
mise exec -- npm --prefix frontend run build
$env:CHROME_BIN = Get-ItemPropertyValue 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe' '(default)'
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

只运行接口测试：`.\.venv\Scripts\python.exe -m unittest -v tests.test_integration`。手动验收：运行 `.\.venv\Scripts\python.exe -m tests.integration_backend`，打开 `http://127.0.0.1:5086/web_static/preview/index.html?mode=live`。注册测试账户，用 `LOCAL-TEST` 兑换 4 次；番茄样书 ID 是 `10001`，七猫批量可逐行输入 `20001`、`20002`。每次启动在 `.integration/` 新建数据库和文件目录；会话、扣次和文件接口是真实的，外部书源使用本地夹具。

## 改动从哪里入手

- **界面与接口。** 新版页面在 [frontend/src/pages/](frontend/src/pages/)，请求在 [frontend/src/api/](frontend/src/api/)；旧首页是 [web_static/index.html](web_static/index.html)。按路由字符串到 [backend/server.py](backend/server.py) 找处理函数；仓库导读和链接示例分别在 [docs/ONBOARDING.md](docs/ONBOARDING.md) 和 [docs/链接url.txt](docs/链接url.txt)；`logs/` 存放本地日志，不作为源码提交。
- **认证与持久化。** `current_user()` 用 Flask session 里的 `sid` 查 SQLite 的 `sessions` 和 `users`；`login_required` 将用户放入 `g.user`。表定义及迁移在 `init_db()`，无独立迁移工具。`downloads` 按用户记录书籍和来源；实体文件共享存放，不能用目录枚举代替用户文件列表。
- **番茄是异步任务。** `/api/download` 经 `invoke_tauri()` 将任务交给桌面程序；接受任务时写 `file_size=0` 占位，普通用户扣次。前端轮询 `/api/jobs` 并调用 `/api/finish_download`；后端定时校验实际文件。复用占位不重复扣次，管理员不扣次。
- **七猫是同步请求。** `/api/qimao/download` 调用 [qimao_api.py](backend/qimao_api.py) 获取书籍与章节信息，[qimao_downloader.py](backend/qimao_downloader.py) 生成 TXT/EPUB。写入文件后才更新配额及下载记录。
- **分卷与备份。** TXT 分割在后台线程运行，不扣次数；任务状态在进程内，小说正文保存在 `data/novel_cache/`，分卷产物在 `data/novel_cache/split/`。邮件备份脚本在 [script/backup/](script/backup/)，不经过 Flask。服务和[备份脚本](script/backup/backup_db.py) 均使用 `data/app.db`；备份配置优先读仓库根目录的 `config_backup.json`，其次读脚本同目录的配置，日志写入 `logs/backup_db.log`。[定时任务批处理](script/backup/backup_db_daily.bat) 按脚本位置定位项目。升级已有部署时，先停服并备份服务器自己的数据库，再将其迁移到 `data/app.db`，不要用开发机的库覆盖。

涉及桌面程序替换时，先看 [exe 参数与补丁记录](docs/exe参数设置.md)；当前启动行为以 [backend/server.py](backend/server.py) 的 `start_exe()` 为准。
