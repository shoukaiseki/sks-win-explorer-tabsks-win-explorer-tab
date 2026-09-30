# -*- coding: utf-8 -*-
"""枚举 Windows 资源管理器窗口/标签页，以及打开路径、检测 ExplorerTabUtility。"""
import os
import subprocess
import time

import win32com.client

DEFAULT_ETU_EXE = r"D:\usr\ExplorerTabUtility\ExplorerTabUtility.exe"


def list_windows():
    """返回 [(hwnd, [路径, ...]), ...]，按窗口分组，顺序与标签栏一致。

    Win11 的 Shell.Application.Windows() 会把每个标签页也当成一个条目返回，
    同一窗口下的所有标签页共享同一个 HWND，所以按 HWND 分组就得到
    「窗口 -> 标签页列表」的结构，无需依赖 UI Automation。
    """
    shell = win32com.client.Dispatch("Shell.Application")
    items = shell.Windows()
    grouped = {}
    for i in range(items.Count):
        try:
            item = items.Item(i)
            full = str(item.FullName)
            if full and not full.lower().endswith("explorer.exe"):
                continue
            hwnd = int(item.HWND)
            path = _item_path(item)
        except Exception:
            continue
        if path:
            grouped.setdefault(hwnd, []).append(path)
    return list(grouped.items())


def _item_path(item):
    try:
        return item.Document.Folder.Self.Path
    except Exception:
        pass
    url = item.LocationURL or ""
    if url.lower().startswith("file:///"):
        return url[8:].replace("/", "\\")
    return url


def open_paths(paths, delay=0.5):
    """逐个打开路径。ETU 常驻时会被并入已有窗口，成为它的标签页。"""
    for path in paths:
        subprocess.Popen(["explorer.exe", path])
        time.sleep(delay)


def etu_exe_name(exe_path=None):
    """ETU 的进程名，按它判断是否在运行。"""
    return os.path.basename(exe_path or DEFAULT_ETU_EXE) or "ExplorerTabUtility.exe"


def etu_running(exe_path=None):
    name = etu_exe_name(exe_path)
    try:
        wmi = win32com.client.GetObject("winmgmts:")
        query = ("SELECT ProcessId FROM Win32_Process WHERE Name = '%s'"
                 % name.replace("'", "''"))
        for _ in wmi.ExecQuery(query):
            return True
    except Exception:
        pass
    return False


def start_etu(exe_path=None):
    exe_path = exe_path or DEFAULT_ETU_EXE
    if not os.path.exists(exe_path):
        return False
    subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
    return True