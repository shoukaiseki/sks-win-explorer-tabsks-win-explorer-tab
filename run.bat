@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem ============================================================
rem  sks-win-explorer-tab 启动脚本
rem
rem  python.exe 直接写 conda 环境的绝对路径来调用，
rem  保证运行时用的是该环境里的包（pywin32）。
rem
rem  默认带控制台运行，方便看到报错信息。
rem  确认一切正常后，想去掉黑窗，把下面的 python.exe 改成 pythonw.exe。
rem ============================================================

echo 正在启动 资源管理器标签页快照 ...
D:\usr\miniconda3\python.exe "%~dp0main.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo [退出码 %RC%] 程序异常退出，错误信息见上方。
    echo.
    pause
)
exit /b %RC%