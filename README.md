# sks-win-explorer-tab

Windows 资源管理器窗口 / 标签页的快照与恢复工具，基于 Python + tkinter。

把当前打开的多个资源管理器窗口（含各自的标签页）存成一组，之后一键恢复；
配合 ExplorerTabUtility 还能让恢复出来的窗口自动并入已有窗口成为标签页。

## 功能

**左侧 —— 当前打开的窗口**

- 以卡片形式列出所有已打开的资源管理器窗口，卡片下方逐行列出该窗口每个标签页的完整路径
- 卡片按钮：
  - `保存标签页组`：把该窗口的全部标签页存成一组
  - `添加到收藏夹`：把该窗口的全部路径加入收藏夹
- 每行路径右侧也有 `添加到收藏夹` 按钮，添加时弹出目录选择对话框，可指定存到哪个收藏夹目录

**右侧 —— 已保存的标签页组**

OneTab 风格列表，每组支持：

- `打开`：整组路径一次性恢复
- `打开单个`：逐条选择打开
- `复制路径`：把整组路径复制到剪贴板
- 重命名 / 删除

**顶部 —— 收藏夹栏**

- 支持多层文件夹嵌套
- `＋ 添加收藏夹`：手动添加任意目录全路径
- `＋ 文件夹`：新建收藏夹文件夹
- `整理…`：打开收藏夹整理窗口（类似 Chrome 书签管理器）
- 路径型收藏是直接打开按钮，文件夹型收藏是下拉菜单
- 记录上次选择的目标目录，下次打开对话框默认选中

**收藏夹整理窗口**

- 树形展示全部收藏夹与路径，文件夹默认展开
- `上移` / `下移`：在同一层级内调整顺序
- `移动到…`：把选中条目移动到其他文件夹（会排除自身及其子文件夹，避免移进自己；同目录重复路径会拦截）
- `新建文件夹` / `重命名…` / `删除`
- 双击路径条目可直接打开该目录
- 任意改动会同时刷新顶部收藏夹栏和整理窗口，即时可见

**ExplorerTabUtility（ETU）集成**

- `使用 ExplorerTabUtility` 勾选框：关闭后不检测 ETU 进程、不显示相关按钮，恢复标签页组时只开独立窗口
- `刷新状态`：手动检测 ETU 是否运行（不做自动轮询，避免空耗 CPU）
- `路径…`：选择 ETU 可执行文件位置，写入 `config.json`
- `启动 ETU`：直接拉起 ETU

**关闭行为 / 系统托盘**

- 顶部 `关闭时最小化到托盘` 勾选框：
  - 勾选：点窗口关闭按钮只隐藏窗口，托盘区保留图标，程序继续在后台运行
  - 取消：点关闭按钮直接退出程序
- 托盘图标左键（或双击）触发 `显示主界面`，右键菜单有 `显示主界面` / `退出`
- 该设置持久化到 `config.json` 的 `close_action`（`tray` / `exit`）
- 未安装 `pystray` / `pillow` 时会弹提示并回退为直接关闭

界面默认最大化启动，`F5` 刷新窗口列表。

## 环境要求

- Windows 11（依赖 `Shell.Application` 枚举资源管理器窗口 / 标签页）
- Python 3.13，使用独立 conda 环境 `sks-win-explorer-tab`
- 依赖见 `requirements.txt`：`pip install -r requirements.txt`
  - `pywin32`：枚举资源管理器窗口 / 标签页
  - `pystray` + `pillow`：关闭时最小化到系统托盘
- 可选：ExplorerTabUtility —— 想要「新窗口并入已有窗口成为标签页」的效果时需要

`run.bat` / `build.bat` 里是**直接写 conda 环境 `python.exe` 的绝对路径**来调用的：

```bat
E:\devwork\miniconda_tmp\envs\sks-win-explorer-tab\python.exe "%~dp0main.py"
```

这样保证用的是该环境里装的包。
环境建在别的位置时，把两个脚本里的 `PY` / `python.exe` 路径一起改掉。

## 目录结构

```
sks-win-explorer-tab/
├─ main.py        界面与交互逻辑
├─ explorer.py    枚举资源管理器窗口/标签页、打开路径、ETU 进程检测与启动
├─ store.py       数据持久化（标签页组、收藏夹、设置）
├─ config.py      程序配置读写（config.json）
├─ tray.py        系统托盘图标（pystray 封装）
├─ requirements.txt 运行依赖清单
├─ run.bat        源码方式启动（带控制台，方便看报错）
├─ build.bat      打包脚本，产物输出到 target/
├─ target/        打包输出目录（内容已被 git 忽略）
└─ README.md
```

配置和数据都在用户目录 `~/.sks/sks-win-explorer-tab/` 下，不放在程序目录里，
所以 exe 可以随便挪位置，配置不会跟着丢。

## 运行

双击 `run.bat`，或：

```bat
E:\devwork\miniconda_tmp\envs\sks-win-explorer-tab\python.exe main.py
```

`run.bat` 默认带控制台启动（能看到报错）。确认无误后想去掉黑窗，
把命令里的 `python.exe` 改成 `pythonw.exe` 即可。

## 打包

双击 `build.bat`。脚本会：

1. 用 conda 环境的 `python.exe` 检查 `pywin32` 和 `PyInstaller`，缺哪个就 `pip install` 哪个
2. 在 `target/` 下生成单文件、无控制台的 exe

产物：

```
target/sks-win-explorer-tab.exe
```

- 可单独复制到任意位置运行，运行时不需要 Python 环境
- 打包中间产物（`target/build/`、`target/*.spec`）也在 `target/` 下，删掉整个 `target` 目录即可清理

## 配置

`~/.sks/sks-win-explorer-tab/config.json`，即 `C:\Users\<用户名>\.sks\sks-win-explorer-tab\config.json`：

```json
{
  "etu_path": "D:\\usr\\ExplorerTabUtility\\ExplorerTabUtility.exe",
  "show_full_path": false,
  "close_action": "tray"
}
```

| 字段 | 说明 |
| --- | --- |
| `etu_path` | ExplorerTabUtility 可执行文件路径 |
| `show_full_path` | 收藏夹是否显示全路径（对应界面上「显示全路径」勾选框） |
| `close_action` | 关闭窗口时的行为：`tray` 最小化到托盘，`exit` 直接退出 |

- 文件不存在或内容损坏时，自动使用默认值
- 也可以在界面上操作（`路径…` 选 ETU、勾选 `显示全路径`），改动立即写入该文件

## 数据存储

用户目录 `~/.sks/sks-win-explorer-tab/`（即 `C:\Users\<用户名>\.sks\sks-win-explorer-tab\`）下有两个文件：

| 文件 | 内容 |
| --- | --- |
| `data.json` | 标签页组、收藏夹、界面状态 |
| `config.json` | 程序配置（ETU 路径、显示全路径开关） |

`data.json` 字段：

| 字段 | 说明 |
| --- | --- |
| `use_etu` | 是否启用 ExplorerTabUtility |
| `groups` | 已保存的标签页组 |
| `favorites` | 收藏夹（支持多层文件夹） |
| `last_fav_dir` | 上次在收藏夹对话框中选中的目录 id |

`config.json` 字段见上面的「配置」一节。

## 关于 ExplorerTabUtility

Windows 11 原生不支持通过命令行把新窗口变成已有窗口的标签页。本工具借助 ETU 实现：
ETU 常驻后会监听新打开的资源管理器窗口，把它们并入已有窗口。因此：

- ETU 需要保持运行，效果才生效
- 关掉顶部勾选框后，本工具只做「打开独立窗口」

## 常见问题

- **`刷新状态` 显示未运行，但 ETU 确实开着**：确认 `~/.sks/sks-win-explorer-tab/config.json` 里的 `etu_path` 指向正在运行的那个 exe —— 进程名是按该路径的文件名匹配的。
- **恢复标签页组时全开成了独立窗口**：ETU 没在运行，或者顶部勾选框没勾上。
- **关闭窗口后程序没退出**：`config.json` 里 `close_action` 是 `tray`，属于预期行为。点托盘图标右键 `退出`，或取消顶部 `关闭时最小化到托盘` 勾选。
- **勾了「关闭时最小化到托盘」却直接退出了**：环境里缺 `pystray` / `pillow`，会弹提示并回退为直接关闭，装上即可。
- **`run.bat` / `build.bat` 报「is not recognized」之类的乱码错误**：脚本必须是 UTF-8 无 BOM + CRLF 换行，改动时注意别存成 LF。