# -*- coding: utf-8 -*-
"""sks-win-explorer-tab —— 资源管理器窗口/标签页快照与恢复。

顶部：收藏夹栏（支持多层文件夹）
左侧：当前打开的资源管理器窗口（卡片），列出该窗口全部标签页全路径
右侧：已保存的标签页组（OneTab 风格），支持重命名、一键恢复、删除
"""
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import config
import explorer
import store

BG = "#f4f5f7"
BAR_BG = "#ffffff"
CARD_BG = "#ffffff"
BORDER = "#d8dbe0"
TEXT = "#1f2328"
MUTED = "#6b7280"
ACCENT = "#2f6fed"
ACCENT_DARK = "#2457c4"
OK = "#2e7d32"
DANGER = "#c0392b"
FONT = "Microsoft YaHei UI"
MONO = "Consolas"


def flat_button(master, text, command, fg=TEXT, bg=CARD_BG, active=None, bold=False):
    return tk.Button(
        master, text=text, command=command,
        font=(FONT, 9, "bold" if bold else "normal"),
        fg=fg, bg=bg, activebackground=active or bg, activeforeground=fg,
        relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
    )


class VScroll(ttk.Frame):
    """带垂直滚动条的容器，内容放进 self.inner。"""

    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self._wid = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_inner(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self._wid, width=event.width)

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()


class HScroll(ttk.Frame):
    """横向滚动容器，内容放进 self.inner（收藏夹栏用）。"""

    def __init__(self, master, bg=BAR_BG):
        super().__init__(master)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, height=30)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._wid = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.pack(fill="both", expand=True)
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_inner(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self._wid, height=event.height)

    def _wheel(self, event):
        self.canvas.xview_scroll(int(-event.delta / 120), "units")

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()


class App:
    def __init__(self, root):
        self.root = root
        self.data = store.load()
        self.cfg = config.load()
        self.etu_state = None          # None=未检测 / True=运行中 / False=未运行
        self._etu_checking = False
        self._etu_result = None
        self.org_win = None            # 收藏夹整理窗口
        self.org_tree = None
        self.org_nodes = {}            # treeview iid -> 节点，根目录的 iid 对应 None

        root.title("资源管理器标签页快照")
        root.configure(bg=BG)
        root.minsize(980, 600)
        root.update_idletasks()
        root.state("zoomed")
        root.bind("<F5>", lambda _e: self.refresh_windows())

        self._build()
        self.refresh_windows()
        self.render_groups()
        self.render_favorites()
        self.apply_etu_visibility()

    # ---------- 布局 ----------

    def _build(self):
        self.root.rowconfigure(2, weight=1)
        self.root.columnconfigure(0, weight=1)

        self._build_top_bar()
        self._build_favorites_bar()
        self._build_body()

    def _build_top_bar(self):
        bar = tk.Frame(self.root, bg=BAR_BG, height=54)
        bar.grid(row=0, column=0, sticky="ew")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=BORDER, height=1).pack(side="bottom", fill="x")

        tk.Label(bar, text="资源管理器标签页快照", bg=BAR_BG, fg=TEXT,
                 font=(FONT, 13, "bold")).pack(side="left", padx=(16, 12))
        flat_button(bar, "刷新窗口列表 (F5)", self.refresh_windows).pack(side="left")

        self.etu_box = tk.Frame(bar, bg=BAR_BG)
        self.etu_box.pack(side="right", padx=(4, 16))
        self.etu_btn = flat_button(self.etu_box, "启动 ETU", self.start_etu, fg=ACCENT)
        self.etu_btn.pack(side="right")
        self.etu_refresh = flat_button(self.etu_box, "刷新状态", self.refresh_etu_status)
        self.etu_refresh.pack(side="right", padx=(0, 6))
        self.etu_path_btn = flat_button(self.etu_box, "路径…", self.set_etu_path)
        self.etu_path_btn.pack(side="right", padx=(0, 6))
        self.etu_label = tk.Label(self.etu_box, text="", bg=BAR_BG, font=(FONT, 9))
        self.etu_label.pack(side="right", padx=(0, 10))

        self.use_etu = tk.BooleanVar(value=bool(self.data.get("use_etu", True)))
        tk.Checkbutton(bar, text="使用 ExplorerTabUtility", variable=self.use_etu,
                       command=self.on_toggle_etu, bg=BAR_BG, fg=TEXT, font=(FONT, 9),
                       activebackground=BAR_BG, activeforeground=TEXT,
                       selectcolor=BAR_BG, bd=0, highlightthickness=0,
                       cursor="hand2").pack(side="right", padx=(0, 20))

    def _build_favorites_bar(self):
        bar = tk.Frame(self.root, bg=BAR_BG, height=46)
        bar.grid(row=1, column=0, sticky="ew")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=BORDER, height=1).pack(side="bottom", fill="x")

        tk.Label(bar, text="收藏夹", bg=BAR_BG, fg=MUTED,
                 font=(FONT, 9, "bold")).pack(side="left", padx=(16, 8))

        self.show_full_path = tk.BooleanVar(value=bool(self.cfg.get("show_full_path", False)))
        tk.Checkbutton(bar, text="显示全路径", variable=self.show_full_path,
                       command=self.on_toggle_full_path, bg=BAR_BG, fg=TEXT, font=(FONT, 9),
                       activebackground=BAR_BG, activeforeground=TEXT,
                       selectcolor=BAR_BG, bd=0, highlightthickness=0,
                       cursor="hand2").pack(side="left")

        actions = tk.Frame(bar, bg=BAR_BG)
        actions.pack(side="right", padx=(8, 16))
        flat_button(actions, "＋ 文件夹", lambda: self.add_folder_dialog(None)).pack(side="right")
        flat_button(actions, "＋ 添加收藏夹", lambda: self.add_favorite_dialog(None),
                    fg=ACCENT, bold=True).pack(side="right", padx=(0, 6))
        flat_button(actions, "整理…", self.open_favorites_manager).pack(
            side="right", padx=(0, 6))

        self.fav_scroll = HScroll(bar, bg=BAR_BG)
        self.fav_scroll.pack(side="left", fill="both", expand=True)

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.grid(row=2, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=11)
        body.columnconfigure(1, weight=9)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        tk.Label(left, text="当前打开的窗口", bg=BG, fg=TEXT,
                 font=(FONT, 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.win_scroll = VScroll(left)
        self.win_scroll.grid(row=1, column=0, sticky="nsew")

        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        tk.Label(right, text="已保存的标签页组", bg=BG, fg=TEXT,
                 font=(FONT, 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.grp_scroll = VScroll(right)
        self.grp_scroll.grid(row=1, column=0, sticky="nsew")

    # ---------- 左侧：窗口卡片 ----------

    def refresh_windows(self):
        self.win_scroll.clear()
        try:
            windows = explorer.list_windows()
        except Exception as exc:
            self._hint(self.win_scroll.inner, "枚举失败：%s" % exc, DANGER)
            return
        if not windows:
            self._hint(self.win_scroll.inner, "没有检测到资源管理器窗口。")
            return
        for index, (_hwnd, paths) in enumerate(windows, 1):
            self._render_window_card(index, paths)

    def _render_window_card(self, index, paths):
        card = tk.Frame(self.win_scroll.inner, bg=CARD_BG,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=2, pady=6)

        head = tk.Frame(card, bg=CARD_BG)
        head.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(head, text="窗口 %d" % index, bg=CARD_BG, fg=TEXT,
                 font=(FONT, 11, "bold")).pack(side="left")
        tk.Label(head, text="%d 个标签页" % len(paths), bg=CARD_BG, fg=MUTED,
                 font=(FONT, 9)).pack(side="right")

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=12, pady=(2, 6))
        for path in paths:
            row = tk.Frame(card, bg=CARD_BG)
            row.pack(fill="x", padx=12, pady=1)
            flat_button(row, "添加到收藏夹",
                        lambda p=path: self.add_paths_to_favorites([p])).pack(side="right")
            tk.Label(row, text=path, bg=CARD_BG, fg=TEXT, font=(MONO, 9),
                     anchor="w", justify="left").pack(side="left", fill="x",
                                                     expand=True, padx=(4, 8))

        foot = tk.Frame(card, bg=CARD_BG)
        foot.pack(fill="x", padx=12, pady=(8, 10))
        tk.Button(foot, text="保存标签页组", font=(FONT, 9), fg="white", bg=ACCENT,
                  activebackground=ACCENT_DARK, activeforeground="white",
                  relief="flat", bd=0, padx=14, pady=4, cursor="hand2",
                  command=lambda ps=paths: self.save_group(ps)).pack(side="right")
        flat_button(foot, text="添加到收藏夹",
                    command=lambda ps=paths: self.add_paths_to_favorites(ps)).pack(
            side="right", padx=(0, 6))

    # ---------- 顶部：收藏夹 ----------

    def render_favorites(self):
        self.fav_scroll.clear()
        nodes = self.data["favorites"]
        if not nodes:
            tk.Label(self.fav_scroll.inner, text="（还没有收藏，点右侧「＋ 添加收藏夹」）",
                     bg=BAR_BG, fg=MUTED, font=(FONT, 9)).pack(side="left", padx=4, pady=10)
        else:
            for node in nodes:
                self._render_favorite(node, self.fav_scroll.inner)
        if self.org_win is not None and self.org_win.winfo_exists():
            self._org_refresh()

    def _fav_label(self, node):
        """路径型收藏的显示文字：开了「显示全路径」就用全路径，否则用名称。"""
        if self.show_full_path.get():
            return node.get("path") or node["name"]
        return node["name"]

    def _render_favorite(self, node, master):
        if node["type"] == "folder":
            btn = flat_button(master, node["name"] + "  ▾", None)
            btn.configure(command=lambda n=node, b=btn: self._popup_folder_menu(n, b))
        else:
            btn = flat_button(master, self._fav_label(node),
                              lambda p=node["path"]: self.open_paths([p]))
        btn.bind("<Button-3>", lambda e, n=node: self._popup_favorite_menu(n, e))
        btn.pack(side="left", padx=2)

    def _popup_folder_menu(self, node, btn):
        """左键菜单：只列出该文件夹下收藏的路径，不含任何操作项。"""
        menu = tk.Menu(self.root, tearoff=0, font=(FONT, 9))
        self._fill_folder_menu(menu, node)
        menu.tk_popup(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height())
        menu.grab_release()

    def _popup_favorite_menu(self, node, event):
        """右键菜单：只放操作项。"""
        self._favorite_menu(node).tk_popup(event.x_root, event.y_root)
        return "break"

    def _fill_folder_menu(self, menu, node):
        children = node.get("children", [])
        if not children:
            menu.add_command(label="（暂无收藏路径）", state="disabled")
            return
        for child in children:
            if child["type"] == "folder":
                sub = tk.Menu(menu, tearoff=0, font=(FONT, 9))
                menu.add_cascade(label=child["name"], menu=sub)
                self._fill_folder_menu(sub, child)
            else:
                menu.add_command(
                    label=self._fav_label(child),
                    command=lambda p=child["path"]: self.open_paths([p]))

    def _favorite_menu(self, node):
        menu = tk.Menu(self.root, tearoff=0, font=(FONT, 9))
        if node["type"] == "path":
            menu.add_command(label="打开", command=lambda: self.open_paths([node["path"]]))
            menu.add_command(label="添加到收藏夹",
                             command=lambda: self.add_paths_to_favorites([node["path"]]))
            menu.add_separator()
        else:
            menu.add_command(label="添加路径…", command=lambda: self.add_favorite_dialog(node))
            menu.add_command(label="添加子文件夹…", command=lambda: self.add_folder_dialog(node))
            menu.add_separator()
        menu.add_command(label="重命名…", command=lambda: self.rename_favorite(node))
        menu.add_command(label="删除", command=lambda: self.delete_favorite(node))
        return menu

    def add_favorite_dialog(self, parent_node=None):
        path = simpledialog.askstring("添加收藏夹", "请输入目录全路径：", parent=self.root)
        if not path:
            return
        path = path.strip().strip('"')
        if not path:
            return
        if not os.path.isdir(path):
            if not messagebox.askyesno("添加收藏夹",
                                       "路径不存在或不是目录：\n%s\n\n仍要添加吗？" % path):
                return
        self._append_node(parent_node, store.new_favorite(path))
        store.save(self.data)
        self.render_favorites()
        self._org_sync()

    def add_folder_dialog(self, parent_node=None):
        name = simpledialog.askstring("新建收藏夹文件夹", "文件夹名称：", parent=self.root)
        if not name or not name.strip():
            return
        self._append_node(parent_node, store.new_folder(name.strip()))
        store.save(self.data)
        self.render_favorites()
        self._org_sync()

    def rename_favorite(self, node, parent=None):
        name = simpledialog.askstring("重命名", "新名称：", initialvalue=node["name"],
                                      parent=parent or self.root)
        if not name or not name.strip() or name.strip() == node["name"]:
            return
        node["name"] = name.strip()
        store.save(self.data)
        self.render_favorites()
        self._org_sync(select_id=node["id"])

    def delete_favorite(self, node, parent=None):
        if not messagebox.askyesno("删除收藏夹", "确定删除「%s」吗？" % node["name"],
                                   parent=parent or self.root):
            return
        found = self._find_parent(node)
        if not found:
            return
        parent_list, index = found
        parent_list.pop(index)
        store.save(self.data)
        self.render_favorites()
        self._org_sync()

    def _append_node(self, parent_node, node):
        if parent_node is None:
            self.data["favorites"].append(node)
        else:
            parent_node.setdefault("children", []).append(node)

    def _iter_path_nodes(self, nodes=None):
        if nodes is None:
            nodes = self.data["favorites"]
        for node in nodes:
            if node["type"] == "path":
                yield node
            else:
                for sub in self._iter_path_nodes(node.get("children", [])):
                    yield sub

    def _iter_folders(self, nodes=None, depth=0):
        """产出 (folder_node, depth)，根目录以 (None, 0) 表示。"""
        if nodes is None:
            nodes = self.data["favorites"]
            yield None, 0
            depth = 1
        for node in nodes:
            if node["type"] == "folder":
                yield node, depth
                yield from self._iter_folders(node.get("children", []), depth + 1)

    def _find_parent(self, node, nodes=None):
        if nodes is None:
            nodes = self.data["favorites"]
        for index, item in enumerate(nodes):
            if item["id"] == node["id"]:
                return nodes, index
            if item["type"] == "folder":
                found = self._find_parent(node, item.get("children", []))
                if found:
                    return found
        return None

    def _folder_of_list(self, lst):
        """返回 children 就是 lst 的那个文件夹节点；根目录返回 None。"""
        for node, _depth in self._iter_folders():
            if node is not None and node.get("children") is lst:
                return node
        return None

    def _contains(self, ancestor, node):
        """node 是否位于 ancestor 文件夹内部（用于防止把文件夹移进自己）。"""
        for child in ancestor.get("children", []):
            if child["id"] == node["id"]:
                return True
            if child["type"] == "folder" and self._contains(child, node):
                return True
        return False

    # ---------- 收藏夹整理 ----------

    def open_favorites_manager(self):
        if self.org_win is not None and self.org_win.winfo_exists():
            self.org_win.deiconify()
            self.org_win.lift()
            self.org_win.focus_set()
            self._org_refresh()
            return

        win = tk.Toplevel(self.root)
        self.org_win = win
        win.title("收藏夹整理")
        win.configure(bg=BG)
        win.transient(self.root)
        win.geometry("660x520")
        win.minsize(540, 360)

        tk.Label(win, text="选中条目后，用下方按钮调整顺序或移动到别的文件夹；双击路径可直接打开。",
                 bg=BG, fg=MUTED, font=(FONT, 9)).pack(anchor="w", padx=16, pady=(12, 6))

        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=16)
        tree = ttk.Treeview(body, columns=("detail",), show="tree headings",
                            selectmode="browse")
        tree.heading("#0", text="名称", anchor="w")
        tree.heading("detail", text="路径", anchor="w")
        tree.column("#0", width=200, anchor="w", stretch=False)
        tree.column("detail", width=400, anchor="w", stretch=True)
        vsb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.org_tree = tree
        tree.bind("<Double-Button-1>", self._org_activate)

        row = tk.Frame(win, bg=BG)
        row.pack(fill="x", padx=16, pady=(10, 14))
        flat_button(row, "上移", lambda: self._org_move(-1)).pack(side="left")
        flat_button(row, "下移", lambda: self._org_move(1)).pack(side="left", padx=(6, 0))
        flat_button(row, "移动到…", self._org_move_to, fg=ACCENT, bold=True).pack(
            side="left", padx=(6, 0))
        flat_button(row, "新建文件夹", self._org_new_folder).pack(side="left", padx=(18, 0))
        flat_button(row, "重命名…", self._org_rename).pack(side="left", padx=(6, 0))
        flat_button(row, "删除", self._org_delete, fg=DANGER).pack(side="left", padx=(6, 0))
        tk.Button(row, text="关闭", command=self._org_close, font=(FONT, 9), fg="white",
                  bg=ACCENT, activebackground=ACCENT_DARK, activeforeground="white",
                  relief="flat", bd=0, padx=18, pady=4, cursor="hand2").pack(side="right")

        win.bind("<Escape>", lambda _e: self._org_close())
        win.protocol("WM_DELETE_WINDOW", self._org_close)
        self._org_refresh()

    def _org_close(self):
        if self.org_win is not None and self.org_win.winfo_exists():
            self.org_win.destroy()
        self.org_win = None
        self.org_tree = None
        self.org_nodes = {}

    def _org_sync(self, select_id=None):
        """整理窗口开着时重建树，没开则什么都不做。"""
        if self.org_win is not None and self.org_win.winfo_exists():
            self._org_refresh(select_id=select_id)

    def _org_refresh(self, select_id=None):
        """按当前数据重建树，尽量保持原来的选中项。"""
        tree = self.org_tree
        if select_id is None:
            current = tree.selection()
            select_id = current[0] if current else None
        tree.delete(*tree.get_children())
        self.org_nodes = {"__root__": None}
        tree.insert("", "end", iid="__root__", text="收藏夹（根目录）", open=True)
        self._org_fill("__root__", self.data["favorites"])
        if select_id and select_id in self.org_nodes:
            tree.selection_set(select_id)
            tree.see(select_id)

    def _org_fill(self, parent_iid, nodes):
        for node in nodes:
            self.org_nodes[node["id"]] = node
            if node["type"] == "folder":
                self.org_tree.insert(parent_iid, "end", iid=node["id"],
                                     text=node["name"], values=("文件夹",), open=True)
                self._org_fill(node["id"], node.get("children", []))
            else:
                self.org_tree.insert(parent_iid, "end", iid=node["id"],
                                     text=node["name"], values=(node.get("path", ""),))

    def _org_selected_node(self):
        """选中的节点；根目录和未选中都返回 None。"""
        picked = self.org_tree.selection()
        if not picked:
            return None
        return self.org_nodes.get(picked[0])

    def _org_activate(self, _event):
        node = self._org_selected_node()
        if node is None or node["type"] == "folder":
            return
        self.open_paths([node["path"]])

    def _org_move(self, delta):
        node = self._org_selected_node()
        if node is None:
            return
        found = self._find_parent(node)
        if not found:
            return
        siblings, index = found
        target = index + delta
        if target < 0 or target >= len(siblings):
            return
        siblings[index], siblings[target] = siblings[target], siblings[index]
        store.save(self.data)
        self.render_favorites()
        self._org_sync(select_id=node["id"])

    def _org_move_to(self):
        node = self._org_selected_node()
        if node is None:
            return
        target, ok = self.choose_favorite_dir(
            "移动到…", "把「%s」移动到哪个收藏夹目录？" % node["name"], exclude=node)
        if not ok:
            return
        found = self._find_parent(node)
        if not found:
            return
        siblings, index = found
        scope = self.data["favorites"] if target is None else target.setdefault("children", [])
        if node["type"] == "path" and any(
                item["path"].lower() == node["path"].lower()
                for item in self._iter_path_nodes(scope)):
            messagebox.showinfo("移动到…", "目标目录里已经有这个路径了。",
                                parent=self.org_win)
            return
        siblings.pop(index)
        scope.append(node)
        store.save(self.data)
        self.render_favorites()
        self._org_sync(select_id=node["id"])

    def _org_new_folder(self):
        node = self._org_selected_node()
        parent = None
        if node is not None:
            if node["type"] == "folder":
                parent = node
            else:
                found = self._find_parent(node)
                if found:
                    parent = self._folder_of_list(found[0])
        name = simpledialog.askstring("新建收藏夹文件夹", "文件夹名称：", parent=self.org_win)
        if not name or not name.strip():
            return
        folder = store.new_folder(name.strip())
        self._append_node(parent, folder)
        store.save(self.data)
        self.render_favorites()
        self._org_refresh(select_id=folder["id"])

    def _org_rename(self):
        node = self._org_selected_node()
        if node is None:
            return
        self.rename_favorite(node, parent=self.org_win)

    def _org_delete(self):
        node = self._org_selected_node()
        if node is None:
            return
        self.delete_favorite(node, parent=self.org_win)

    # ---------- 右侧：标签页组 ----------

    def render_groups(self):
        self.grp_scroll.clear()
        if not self.data["groups"]:
            self._hint(self.grp_scroll.inner,
                       "还没有保存的标签页组。\n在左侧卡片点「保存标签页组」即可。")
            return
        for group in self.data["groups"]:
            self._render_group_card(group)

    def _render_group_card(self, group):
        card = tk.Frame(self.grp_scroll.inner, bg=CARD_BG,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=2, pady=6)

        head = tk.Frame(card, bg=CARD_BG)
        head.pack(fill="x", padx=12, pady=(10, 4))

        name_var = tk.StringVar(value=group["name"])
        entry = tk.Entry(head, textvariable=name_var, font=(FONT, 11, "bold"),
                         fg=TEXT, bg=CARD_BG, relief="flat", bd=0,
                         highlightthickness=1, highlightbackground=CARD_BG,
                         highlightcolor=ACCENT, insertbackground=TEXT)
        entry.pack(side="left", fill="x", expand=True, ipady=2)
        entry.bind("<Return>", lambda _e: self.root.focus_set())
        entry.bind("<FocusOut>", lambda _e: self.rename_group(group, name_var.get()))

        flat_button(head, "删除", lambda: self.delete_group(group), fg=DANGER).pack(
            side="right", padx=(6, 0))
        flat_button(head, "恢复", lambda: self.restore_group(group), fg=ACCENT).pack(
            side="right")
        copy_btn = flat_button(head, "复制路径", None)
        copy_btn.config(command=lambda: self.copy_group_paths(group, copy_btn))
        copy_btn.pack(side="right", padx=(0, 6))

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=12, pady=(2, 6))
        for path in group["paths"]:
            row = tk.Frame(card, bg=CARD_BG)
            row.pack(fill="x", padx=12, pady=1)
            flat_button(row, "打开", lambda p=path: self.open_paths([p])).pack(side="right")
            tk.Label(row, text=path, bg=CARD_BG, fg=TEXT, font=(MONO, 9),
                     anchor="w", justify="left").pack(side="left", fill="x",
                                                     expand=True, padx=(4, 8))
        tk.Label(card, text="%s · %d 个标签页" % (group.get("created", ""), len(group["paths"])),
                 bg=CARD_BG, fg=MUTED, font=(FONT, 8)).pack(anchor="w", padx=16, pady=(6, 10))

    def save_group(self, paths):
        seen, unique = set(), []
        for path in paths:
            key = path.lower()
            if key not in seen:
                seen.add(key)
                unique.append(path)
        if not unique:
            messagebox.showinfo("保存标签页组", "这个窗口没有可保存的标签页。")
            return
        self.data["groups"].insert(0, store.new_group(time.strftime("%Y-%m-%d %H:%M"), unique))
        store.save(self.data)
        self.render_groups()

    def rename_group(self, group, name):
        name = name.strip()
        if not name or name == group["name"]:
            return
        group["name"] = name
        store.save(self.data)

    def copy_group_paths(self, group, btn=None):
        paths = list(group["paths"])
        if not paths:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(paths))
        if btn is not None:
            btn.config(text="已复制")
            self.root.after(1200, lambda: btn.config(text="复制路径"))

    def delete_group(self, group):
        if not messagebox.askyesno("删除标签页组", "确定删除「%s」吗？" % group["name"]):
            return
        self.data["groups"] = [g for g in self.data["groups"] if g["id"] != group["id"]]
        store.save(self.data)
        self.render_groups()

    def restore_group(self, group):
        paths = list(group["paths"])
        if not paths:
            return
        if self.use_etu.get() and self.etu_state is False:
            proceed = messagebox.askyesno(
                "恢复标签页组",
                "ExplorerTabUtility 当前没有运行（上次检测结果）。\n\n"
                "没有它，这些路径会各自开成独立的新窗口，而不是并入已有窗口的标签页。\n\n"
                "仍要继续吗？")
            if not proceed:
                return
        self.etu_label.config(text="正在恢复 %d 个标签页…" % len(paths), fg=ACCENT)
        self._restore_done = False

        def work():
            explorer.open_paths(paths)
            self._restore_done = True

        threading.Thread(target=work, daemon=True).start()
        self._poll_restore()

    def _poll_restore(self):
        if self._restore_done:
            self._after_restore()
        else:
            self.root.after(300, self._poll_restore)

    def _after_restore(self):
        self.refresh_windows()

    # ---------- 打开路径 / ETU ----------

    def open_paths(self, paths):
        threading.Thread(target=explorer.open_paths, args=(list(paths),), daemon=True).start()
        self.root.after(1200, self.refresh_windows)

    def choose_favorite_dir(self, title="选择收藏夹目录",
                            prompt="把路径添加到哪个收藏夹目录？", exclude=None):
        """选择收藏夹目标目录；返回 (节点, 是否确认)，根目录对应节点为 None。

        exclude 是要移动的节点：该文件夹自身及其子孙会从候选里去掉，避免移进自己。
        """
        folders = []
        for node, depth in self._iter_folders():
            if node is not None and exclude is not None and (
                    node["id"] == exclude["id"] or self._contains(exclude, node)):
                continue
            folders.append((node, depth))
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        tk.Label(win, text=prompt, bg=BG, fg=TEXT,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=16, pady=(14, 6))

        listbox = tk.Listbox(win, font=(FONT, 10), width=46,
                             height=min(12, len(folders)), activestyle="none",
                             selectmode="browse", bd=0, highlightthickness=1,
                             highlightbackground=BORDER, highlightcolor=ACCENT,
                             selectbackground=ACCENT, selectforeground="white")
        listbox.pack(fill="both", expand=True, padx=16)
        for node, depth in folders:
            text = "收藏夹（根目录）" if node is None else "    " * (depth - 1) + node["name"]
            listbox.insert("end", text)

        last = self.data.get("last_fav_dir", "")
        selected = 0
        for index, (node, _depth) in enumerate(folders):
            if ("" if node is None else node["id"]) == last:
                selected = index
                break
        listbox.selection_set(selected)
        listbox.see(selected)
        listbox.focus_set()

        result = {"node": None, "ok": False}

        def confirm(_event=None):
            pick = listbox.curselection()
            if pick:
                result["node"] = folders[pick[0]][0]
            result["ok"] = True
            win.destroy()

        row = tk.Frame(win, bg=BG)
        row.pack(fill="x", padx=16, pady=(10, 14))
        tk.Button(row, text="确定", command=confirm, font=(FONT, 9), fg="white",
                  bg=ACCENT, activebackground=ACCENT_DARK, activeforeground="white",
                  relief="flat", bd=0, padx=18, pady=4, cursor="hand2").pack(side="right")
        flat_button(row, "取消", win.destroy).pack(side="right", padx=(0, 8))

        listbox.bind("<Double-Button-1>", confirm)
        win.bind("<Return>", confirm)
        win.bind("<Escape>", lambda _e: win.destroy())

        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 3
        win.geometry("+%d+%d" % (max(x, 0), max(y, 0)))

        self.root.wait_window(win)
        return result["node"], result["ok"]

    def add_paths_to_favorites(self, paths):
        paths = list(paths)
        if not paths:
            return
        target, ok = self.choose_favorite_dir()
        if not ok:
            return
        self.data["last_fav_dir"] = "" if target is None else target["id"]
        scope = self.data["favorites"] if target is None else target.get("children", [])
        existing = {node["path"].lower() for node in self._iter_path_nodes(scope)}
        added = 0
        for path in paths:
            if path.lower() in existing:
                continue
            self._append_node(target, store.new_favorite(path))
            existing.add(path.lower())
            added += 1
        store.save(self.data)
        self.render_favorites()
        self._org_sync()
        if not added:
            messagebox.showinfo("添加到收藏夹", "这些路径已经在目标目录里了。")

    def on_toggle_full_path(self):
        self.cfg["show_full_path"] = bool(self.show_full_path.get())
        self._save_cfg()
        self.render_favorites()

    def on_toggle_etu(self):
        self.data["use_etu"] = bool(self.use_etu.get())
        store.save(self.data)
        self.apply_etu_visibility()

    def apply_etu_visibility(self):
        if self.use_etu.get():
            self.etu_btn.pack(side="right")
            self.etu_refresh.pack(side="right", padx=(0, 6))
            self.etu_path_btn.pack(side="right", padx=(0, 6))
            self.etu_label.pack(side="right", padx=(0, 10))
            self._render_etu_state()
        else:
            self.etu_btn.pack_forget()
            self.etu_refresh.pack_forget()
            self.etu_path_btn.pack_forget()
            self.etu_label.pack_forget()

    def _render_etu_state(self):
        """只按缓存状态刷新显示，不做进程检测。"""
        if self.etu_state is True:
            self.etu_label.config(text="● ExplorerTabUtility 运行中", fg=OK)
            self.etu_btn.config(state="disabled")
        elif self.etu_state is False:
            self.etu_label.config(text="● ExplorerTabUtility 未运行", fg=DANGER)
            self.etu_btn.config(state="normal")
        else:
            self.etu_label.config(text="○ 状态未知，点「刷新状态」", fg=MUTED)
            self.etu_btn.config(state="normal")

    def refresh_etu_status(self):
        """手动检测 ETU 是否运行；不做自动轮询，避免空耗 CPU。"""
        if self._etu_checking:
            return
        self._etu_checking = True
        self._etu_result = None
        self.etu_label.config(text="检测中…", fg=MUTED)
        self.etu_refresh.config(state="disabled")

        exe = self.etu_exe_path()

        def work():
            self._etu_result = explorer.etu_running(exe)

        threading.Thread(target=work, daemon=True).start()
        self._poll_etu_status()

    def _poll_etu_status(self):
        if self._etu_result is None:
            self.root.after(120, self._poll_etu_status)
            return
        self._etu_checking = False
        self.etu_state = self._etu_result
        self._etu_result = None
        self.etu_refresh.config(state="normal")
        self._render_etu_state()

    def etu_exe_path(self):
        return self.cfg.get("etu_path") or explorer.DEFAULT_ETU_EXE

    def _save_cfg(self):
        """写回 config.json，失败时提示（改动只在本次运行期间有效）。"""
        if config.save(self.cfg):
            return True
        messagebox.showwarning(
            "保存配置失败",
            "无法写入配置文件：\n%s\n\n本次修改只在当前运行期间有效。" % config.config_file())
        return False

    def set_etu_path(self):
        current = self.etu_exe_path()
        folder = os.path.dirname(current)
        path = filedialog.askopenfilename(
            title="选择 ExplorerTabUtility.exe",
            parent=self.root,
            initialdir=folder if os.path.isdir(folder) else None,
            initialfile=os.path.basename(current),
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")])
        if not path:
            return
        self.cfg["etu_path"] = os.path.normpath(path)
        self._save_cfg()
        self.refresh_etu_status()

    def start_etu(self):
        exe = self.etu_exe_path()
        if not explorer.start_etu(exe):
            messagebox.showerror(
                "启动 ETU",
                "找不到 ExplorerTabUtility.exe：\n%s\n\n"
                "请点「路径…」按钮指定它的实际位置。" % exe)
            return
        self.etu_label.config(text="正在启动 ETU…", fg=MUTED)
        self.root.after(1500, self.refresh_etu_status)

    def _hint(self, master, text, color=MUTED):
        tk.Label(master, text=text, bg=BG, fg=color, font=(FONT, 10),
                 justify="left").pack(anchor="w", padx=12, pady=12)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()