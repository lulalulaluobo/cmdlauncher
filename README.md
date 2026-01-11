# CmdLauncher

Windows 桌面工具（Python + Qt6），把常用的命令行操作收进按钮里执行，输出实时展示并记录日志。

## 功能概览

- 分组命令列表（浅色底 + 分割线），左侧命令 / 说明，右侧输出
- 托盘驻留（Show / Restart / Exit），双击托盘图标恢复窗口
- 输出编码切换：自动 / UTF-8（适配中文输出）
- 管理员命令提示，可一键重启为管理员再执行
- WiFi 密码查询：先选 WiFi，再解析明文密码
- 超时控制与日志落盘

当前内置命令分组：

- 网络相关：ipconfig、ping、WiFi 列表 / 密码、清理 DNS、网络连接、获取 MAC
- 系统设置：进入 BIOS、控制面板、远程桌面、程序和功能、休眠设置
- 系统维护：磁盘清理、清理临时文件、停止 / 恢复 Windows Update

## 运行（开发）

```powershell
cd cmd_launcher
python -m pip install -r requirements.txt
python app.py
```

## 配置命令

命令白名单在 `config/commands.json` 中定义，每条命令支持：

- `id`：唯一标识
- `label`：按钮显示文本
- `description`：命令说明（左侧说明栏）
- `template`：命令模板（支持 `{param}` 占位符）
- `params`：参数定义（类型、默认值、必填、范围）
- `timeout`：超时秒数（`0` 表示不超时）
- `admin`：是否需要管理员权限
- `kind`：分组项使用 `group`

参数扩展：

- `choices`：可选值列表
- `labels`：选项显示文案（映射到 `choices`）
- `ui`：当值为 `"buttons"` 时使用按钮选择

示例：

- `ping` 会弹出参数窗口，`target` 默认值为 `www.baidu.com`，`count` 默认 4。
- `powercfg -h` 使用按钮选择“开/关”。
- `WiFi 密码查询` 先弹出 WiFi 列表，再输出 WiFi 名称与密码。

## 日志

- 右侧为运行日志展示；底部“清空输出”只清 UI。
- 日志写入 `logs/app.log`，若无权限则回退到 `%LOCALAPPDATA%\CmdLauncher\logs\app.log`。

## 打包（one-folder）

使用当前图标与命名（cmd.exe）：

```powershell
pyinstaller --noconfirm --onedir --windowed --name cmd --icon "assets\command.ico" --hidden-import ctypes --hidden-import _ctypes --add-data "core;core" --add-data "ui;ui" --add-data "config;config" app.py
```

产物在 `dist\cmd\cmd.exe`（可将文件夹重命名为 `CmdLauncher` 后分发）。