# -*- coding: utf-8 -*-
"""程序配置：读写 ~/.sks/sks-win-explorer-tab/config.json。

跟 data.json 放在同一个用户目录下，方便统一备份、清理和迁移。
"""
import json
import os

from store import DATA_DIR

DEFAULT_ETU_PATH = r"D:\usr\ExplorerTabUtility\ExplorerTabUtility.exe"

CLOSE_ACTIONS = ("tray", "exit")

DEFAULTS = {
    "etu_path": DEFAULT_ETU_PATH,
    "show_full_path": False,
    "close_action": "tray",
}


def config_file():
    return os.path.join(DATA_DIR, "config.json")


def load():
    data = dict(DEFAULTS)
    try:
        with open(config_file(), "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            data.update(raw)
    except (OSError, ValueError):
        pass
    path = data.get("etu_path")
    if not isinstance(path, str) or not path.strip():
        data["etu_path"] = DEFAULT_ETU_PATH
    data["show_full_path"] = bool(data.get("show_full_path", False))
    if data.get("close_action") not in CLOSE_ACTIONS:
        data["close_action"] = "tray"
    return data


def save(data):
    """写入 config.json，失败返回 False。"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = config_file() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, config_file())
        return True
    except OSError:
        return False