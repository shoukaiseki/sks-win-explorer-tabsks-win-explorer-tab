# -*- coding: utf-8 -*-
"""系统托盘图标：基于 pystray + Pillow。

pystray 的消息循环跑在独立线程里，它的回调不能直接操作 tkinter 控件。
这里只负责把点击事件丢进一个线程安全的队列，由 main.App 在主线程轮询取出后
再执行，避免跨线程调用 Tk 引发 "main thread is not in main loop"。
"""
import threading

TITLE = "资源管理器标签页快照"


def available():
    """pystray 和 Pillow 是否都能导入。"""
    try:
        import pystray  # noqa: F401
        from PIL import Image, ImageDraw  # noqa: F401
    except Exception:
        return False
    return True


def _make_image():
    """程序内画一个托盘图标，免去额外的 .ico 资源文件。"""
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([3, 3, size - 3, size - 3], radius=13,
                           fill=(47, 111, 237, 255))
    draw.rounded_rectangle([13, 16, 29, 25], radius=3, fill=(255, 255, 255, 255))
    draw.rounded_rectangle([13, 23, 51, 47], radius=4, fill=(255, 255, 255, 255))
    draw.line([13, 31, 51, 31], fill=(47, 111, 237, 255), width=3)
    return img


class Tray:
    """托盘图标；start() 后 run() 在后台线程里跑。"""

    def __init__(self, on_show, on_exit):
        self.on_show = on_show
        self.on_exit = on_exit
        self.icon = None
        self._thread = None

    def start(self):
        """启动托盘图标，失败返回 False。"""
        if self.icon is not None:
            return True
        try:
            import pystray
        except Exception:
            return False
        menu = pystray.Menu(
            pystray.MenuItem("显示主界面", self._show, default=True),
            pystray.MenuItem("退出", self._exit),
        )
        self.icon = pystray.Icon("sks-win-explorer-tab", _make_image(), TITLE, menu)
        self._thread = threading.Thread(target=self.icon.run, daemon=True)
        self._thread.start()
        return True

    def _show(self, _icon=None, _item=None):
        self.on_show()

    def _exit(self, _icon=None, _item=None):
        self.on_exit()

    def stop(self):
        icon, self.icon = self.icon, None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass