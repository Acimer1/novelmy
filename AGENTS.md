# novelmy 项目上下文

## 运行与验证

在 Windows 仓库根目录执行：

```powershell
python -m pip install -r requirements.txt
python server.py
```

- 默认访问 `http://localhost:5000`；指定端口用 `python server.py --port 5001`。服务实际监听 `0.0.0.0`，不局限于本机。若当前 shell 的 `python` 指向 Microsoft Store，可在上述命令前加 `mise exec --` 使用已配置的解释器。
- [启动.bat](启动.bat) 是同一流程的一键入口，但会隐藏 pip 输出；排查安装错误用上面的分步命令。
- 用脚本入口启动，而不是 `flask run`：建表和迁移、同步已有文件、启动或复用番茄桌面程序都在 [server.py](server.py) 的 `__main__` 中。启动不是只读检查，会接触现有数据库、下载目录和桌面进程。
- 前端由 Flask 直接提供，无需构建。仓库未配置 lint、自动化测试或 CI，也没有可运行的单测目标或单测命令。

## 改动从哪里入手

- **页面与接口一起看。** 实际首页是 [web_static/index.html](web_static/index.html)，交互、请求和不少样式直接写在页内。改接口时用路由字符串定位前端调用，再看 [server.py](server.py) 中对应的处理函数；[backup/](backup/) 和 `.bak` 不是运行入口。
- **认证与持久化。** `current_user()` 用 Flask session 里的 `sid` 查 SQLite 的 `sessions` 和 `users`；`login_required` 将用户放入 `g.user`。表定义及现有库的迁移都在 `init_db()`，无独立迁移工具。`downloads` 按用户记录书籍和来源，实体文件则共享存放在 `web_downloads/`，不能用目录枚举代替用户文件列表。
- **番茄是异步任务。** `/api/download` 经 `invoke_tauri()` 将任务交给 Windows 桌面程序；任务被接受时写 `file_size=0` 占位，对普通用户扣次。前端轮询 `/api/jobs` 并调用 `/api/finish_download`；后端定时校验实际文件是否生成，文件列表也会尝试修复占位。改重试或计费时需保留复用占位不重复扣次、管理员不扣次的语义。
- **七猫（界面称灵猫）是同步请求。** `/api/qimao/download` 调用 [qimao_api.py](qimao_api.py) 获取书籍与章节信息，再由 [qimao_downloader.py](qimao_downloader.py) 生成 TXT/EPUB。写入实体文件后才更新配额及下载记录；不要套用番茄任务轮询流程。
- **分卷与备份独立于下载。** TXT 分割在后台线程中运行，不扣下载次数；任务状态在进程内，产物在 `web_downloads/_split/`。数据库邮件备份由 [backup_db_daily.bat](backup_db_daily.bat) 调用 [backup_db.py](backup_db.py)，不是 Flask 的定时任务。

涉及桌面程序替换时，先看 [exe 参数与补丁记录](exe参数设置.md) 了解仓库内二进制的来历；当前启动行为以 `server.py` 的 `start_exe()` 为准。
