@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem ============================================================
rem  sks-win-explorer-tab 打包脚本
rem
rem  python.exe 直接写 conda 环境的绝对路径来调用，
rem  保证用的是该环境里的包（pywin32 就装在这里）。
rem
rem  产物：target\sks-win-explorer-tab.exe
rem  中间产物（target\build、target\*.spec）也在 target 下，
rem  想清理直接删掉整个 target 目录。
rem ============================================================

set "NAME=sks-win-explorer-tab"
set "OUT=%~dp0target"

rem 依赖自检：pywin32 是程序运行必需，PyInstaller 是打包必需
D:\usr\miniconda3\python.exe -c "import win32com.client" 2>nul
if errorlevel 1 (
    echo [提示] 该 conda 环境缺少 pywin32，正在安装...
    D:\usr\miniconda3\python.exe -m pip install pywin32 -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo.
        echo [错误] pywin32 安装失败，请检查网络后重试。
        pause
        exit /b 1
    )
)

D:\usr\miniconda3\python.exe -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 该 conda 环境缺少 PyInstaller，正在安装...
    D:\usr\miniconda3\python.exe -m pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo.
        echo [错误] PyInstaller 安装失败，请检查网络后重试。
        pause
        exit /b 1
    )
)

if not exist "%OUT%" mkdir "%OUT%"

rem 清理上次的中间产物，已生成的 exe 会被 --noconfirm 覆盖
if exist "%OUT%\build" rmdir /s /q "%OUT%\build"

echo [信息] 开始打包，请稍候...
echo.
D:\usr\miniconda3\python.exe -m PyInstaller --noconfirm --onefile --windowed --name "%NAME%" --distpath "%OUT%" --workpath "%OUT%\build" --specpath "%OUT%" main.py
if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请查看上面的输出。
    pause
    exit /b 1
)

echo.
echo ========================================
echo [完成] exe 已生成：
echo        %OUT%\%NAME%.exe
echo ========================================
echo [提示] 该 exe 可单独复制到任意位置使用，运行时无需 Python 环境。
echo [提示] 修改 ETU 路径：编辑 %USERPROFILE%\.sks\sks-win-explorer-tab\config.json
echo.
pause