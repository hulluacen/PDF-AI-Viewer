"""Bundled read-only assets, separate from persistent data paths."""
import os
import sys


def resource_path(name: str) -> str:
    """返回资源文件绝对路径，兼容源码运行与 PyInstaller 打包（frozen）环境。

    PyInstaller 打包后会把 datas 里的文件解压到 sys._MEIPASS 临时目录，
    此时 __file__ 指向该临时目录，直接用源码目录去拼路径会找不到资源。
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


