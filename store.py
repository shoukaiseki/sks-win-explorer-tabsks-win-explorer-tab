# -*- coding: utf-8 -*-
"""本地持久化：标签页组、收藏夹、设置，统一放在 data.json。"""
import json
import os
import time
import uuid

DATA_DIR = os.path.join(os.path.expanduser("~"), ".sks", "sks-win-explorer-tab")
DATA_FILE = os.path.join(DATA_DIR, "data.json")

DEFAULTS = {"use_etu": True, "groups": [], "favorites": [], "last_fav_dir": ""}


def load():
    data = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            data.update(raw)
    except (OSError, ValueError):
        pass
    if not isinstance(data.get("groups"), list):
        data["groups"] = []
    if not isinstance(data.get("favorites"), list):
        data["favorites"] = []
    data["use_etu"] = bool(data.get("use_etu", True))
    if not isinstance(data.get("last_fav_dir"), str):
        data["last_fav_dir"] = ""
    return data


def save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def new_group(name, paths):
    return {
        "id": uuid.uuid4().hex,
        "name": name,
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "paths": list(paths),
    }


def new_folder(name):
    return {"id": uuid.uuid4().hex, "type": "folder", "name": name, "children": []}


def new_favorite(path, name=None):
    path = path.rstrip("\\/") or path
    return {
        "id": uuid.uuid4().hex,
        "type": "path",
        "name": name or os.path.basename(path) or path,
        "path": path,
    }