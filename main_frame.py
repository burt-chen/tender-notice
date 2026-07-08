"""小工具整合入口。

小工具整合載入器會呼叫 create_frame(parent)，
把本工具的畫面(ttk.Frame)嵌進整合視窗。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from tender_notice_ui import TenderNoticeApp


def create_frame(parent: tk.Misc) -> ttk.Frame:
    return TenderNoticeApp(parent)
