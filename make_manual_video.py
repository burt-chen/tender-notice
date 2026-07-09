#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create the Tender Notice operation manual video from real application screens."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

from manual_video_common import (  # type: ignore
    HEIGHT,
    SUBTITLE_H,
    WIDTH,
    capture_tk_window,
    media_duration,
    nonblocking_messageboxes,
    sha256_file,
    subtitle_frame,
    synthesize_mp3,
    title_frame,
)


MANUAL_DIR = ROOT / "manual_video"
SCRIPT_PATH = MANUAL_DIR / "script.md"
STORYBOARD_PATH = MANUAL_DIR / "storyboard.md"
OUTPUT_DIR = MANUAL_DIR / "output"
OUTPUT_VIDEO = OUTPUT_DIR / "manual.mp4"
DEMO_OUTPUT_DIR = MANUAL_DIR / "demo_output"
FRAMES_DIR = MANUAL_DIR / "_frames"
AUDIO_DIR = MANUAL_DIR / "_audio"
FRAMES_TXT = MANUAL_DIR / "_frames.txt"
SILENT_VIDEO = MANUAL_DIR / "_silent.mp4"
FPS = 30

SCENE_PLAN = [
    ("01", "opening", 5.5),
    ("02", "tender_setup", 7.0),
    ("03", "tender_results", 8.0),
    ("04", "tender_export", 7.0),
    ("05", "appeal_setup", 7.0),
    ("06", "appeal_search", 6.5),
    ("07", "appeal_results", 8.0),
    ("08", "appeal_detail", 6.5),
    ("09", "appeal_export", 7.0),
    ("10", "manage", 7.0),
]


DEMO_CATEGORIES = {
    "資訊服務": ["系統維護", "資訊安全", "雲端服務"],
    "測量製圖": ["地籍測量", "航測製圖"],
}

DEMO_ROWS = [
    {
        "query_keyword": "系統維護",
        "item_no": "1",
        "agency": "臺北市政府資訊局",
        "tender_id": "113-IT-042",
        "is_correction": "N",
        "tender_name": "機關業務系統維護與安全更新服務案",
        "transmission_count": "01",
        "tender_method": "公開招標",
        "procurement_category": "勞務",
        "announcement_date": "2026/07/06",
        "bid_deadline": "2026/07/18",
        "budget_amount": "1280000",
        "detail_url": "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic",
    },
    {
        "query_keyword": "資訊安全",
        "item_no": "2",
        "agency": "新北市政府採購處",
        "tender_id": "NB-SEC-11507",
        "is_correction": "Y",
        "tender_name": "資安健診與弱點掃描服務採購",
        "transmission_count": "02",
        "tender_method": "公開取得報價",
        "procurement_category": "勞務",
        "announcement_date": "2026/07/07",
        "bid_deadline": "2026/07/21",
        "budget_amount": "860000",
        "detail_url": "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic",
    },
    {
        "query_keyword": "地籍測量",
        "item_no": "3",
        "agency": "桃園市政府地政局",
        "tender_id": "TY-LAND-2026-08",
        "is_correction": "N",
        "tender_name": "地籍圖資更新及測量成果整理委託案",
        "transmission_count": "01",
        "tender_method": "公開評選",
        "procurement_category": "勞務",
        "announcement_date": "2026/07/08",
        "bid_deadline": "2026/07/25",
        "budget_amount": "2450000",
        "detail_url": "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic",
    },
]

DEMO_APPEAL_ROWS = [
    {
        "query_keyword": "資訊安全",
        "agency": "臺中市政府資訊中心",
        "tender_id": "TC-APPEAL-11501",
        "tender_name": "資安監控服務公開徵求廠商意見",
        "announcement_count": "1",
        "announcement_date": "2026/07/07",
        "deadline": "2026/07/16",
        "detail_url": "https://web.pcc.gov.tw/prkms/tpAppeal/common/readTpAppeal",
    },
    {
        "query_keyword": "雲端服務",
        "agency": "高雄市政府研究發展考核委員會",
        "tender_id": "KHH-CLOUD-2026",
        "tender_name": "雲端備份平台建置公開徵求",
        "announcement_count": "2",
        "announcement_date": "2026/07/08",
        "deadline": "2026/07/18",
        "detail_url": "https://web.pcc.gov.tw/prkms/tpAppeal/common/readTpAppeal",
    },
    {
        "query_keyword": "地籍測量",
        "agency": "新竹縣政府地政處",
        "tender_id": "HC-LAND-AP-03",
        "tender_name": "地籍測量成果檢核作業公開徵求",
        "announcement_count": "1",
        "announcement_date": "2026/07/09",
        "deadline": "2026/07/20",
        "detail_url": "https://web.pcc.gov.tw/prkms/tpAppeal/common/readTpAppeal",
    },
]


def find_ffmpeg() -> tuple[str, str]:
    ffmpeg = shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"
    ffprobe = shutil.which("ffprobe") or r"C:\ffmpeg\bin\ffprobe.exe"
    if not Path(ffmpeg).exists():
        raise RuntimeError("找不到 ffmpeg，請確認 C:\\ffmpeg\\bin\\ffmpeg.exe 可用。")
    if not Path(ffprobe).exists():
        raise RuntimeError("找不到 ffprobe，請確認 C:\\ffmpeg\\bin\\ffprobe.exe 可用。")
    return ffmpeg, ffprobe


def read_script_sections() -> dict[str, str]:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    current_id: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^##\s+(\d{2})\b.*", line.strip())
        if match:
            if current_id:
                sections[current_id] = "\n".join(current_lines).strip()
            current_id = match.group(1)
            current_lines = []
        elif current_id:
            current_lines.append(line)
    if current_id:
        sections[current_id] = "\n".join(current_lines).strip()
    return sections


def pump(root, seconds: float = 0.35) -> None:
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.03)


def find_notebook(root):
    import tkinter.ttk as ttk

    stack = list(root.winfo_children())
    while stack:
        widget = stack.pop(0)
        if isinstance(widget, ttk.Notebook):
            return widget
        stack.extend(widget.winfo_children())
    raise RuntimeError("找不到主分頁 Notebook。")


def configure_demo_state(app) -> None:
    app.saved_categories = {name: values[:] for name, values in DEMO_CATEGORIES.items()}
    app.saved_keywords = app._all_saved_keywords()
    app._refresh_category_listboxes()
    app.query_category_listbox.selection_set(0)
    app._refresh_query_keyword_listbox()
    app.query_keyword_listbox.selection_set(0, 1)
    app.keyword_text.delete("1.0", "end")
    app.keyword_text.insert("1.0", "機房設備\n資料備份")
    app.date_type.set("range")
    app.start_date_var.set("2026/07/06")
    app.end_date_var.set("2026/07/08")
    app._toggle_date_entries()
    app.status_var.set("已載入操作手冊示範關鍵字")


def populate_results(app) -> None:
    app.clear_results()
    app._finish_search(DEMO_ROWS, None, False)
    first = app.tree.get_children()[0]
    app.tree.selection_set(first)
    app.tree.focus(first)
    app.tree.see(first)


def configure_appeal_state(app) -> None:
    app.saved_categories = {name: values[:] for name, values in DEMO_CATEGORIES.items()}
    app.saved_keywords = app._all_saved_keywords()
    app._refresh_category_listboxes()
    app.appeal_category_listbox.selection_clear(0, "end")
    app.appeal_category_listbox.selection_set(0)
    app._refresh_appeal_keyword_listbox()
    app.appeal_keyword_listbox.selection_set(0, 1)
    app.appeal_keyword_text.delete("1.0", "end")
    app.appeal_keyword_text.insert("1.0", "資料備份\n系統整合")
    app.appeal_start_date_var.set("2026/07/07")
    app.appeal_end_date_var.set("2026/07/09")
    app.status_var.set("已載入公開徵求查詢示範條件")


def populate_appeal_results(app) -> None:
    app.appeal_clear_results()
    app._finish_appeal_search(DEMO_APPEAL_ROWS, None, False)
    first = app.appeal_tree.get_children()[0]
    app.appeal_tree.selection_set(first)
    app.appeal_tree.focus(first)
    app.appeal_tree.see(first)


def select_manage_tab(app) -> None:
    notebook = find_notebook(app)
    notebook.select(app.manage_tab)
    app.manage_category_listbox.selection_clear(0, "end")
    app.manage_category_listbox.selection_set(0)
    app._refresh_manage_keyword_listbox()
    app.manage_keyword_listbox.selection_set(0, 1)
    app.status_var.set("關鍵字管理頁：可維護分類、匯入與匯出 JSON")


@contextmanager
def fixed_save_dialog(path: Path):
    import tkinter.filedialog as filedialog

    original = filedialog.asksaveasfilename
    filedialog.asksaveasfilename = lambda *args, **kwargs: str(path)
    try:
        yield
    finally:
        filedialog.asksaveasfilename = original


def export_demo_excel(app) -> Path:
    DEMO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = DEMO_OUTPUT_DIR / "tender_notice_demo.xlsx"
    output.unlink(missing_ok=True)
    if not app.rows:
        populate_results(app)
    with fixed_save_dialog(output):
        app.export_excel()
    return output


def export_demo_appeal_excel(app) -> Path:
    DEMO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = DEMO_OUTPUT_DIR / "appeal_notice_demo.xlsx"
    output.unlink(missing_ok=True)
    if not app.appeal_rows:
        populate_appeal_results(app)
    with fixed_save_dialog(output):
        app.appeal_export_excel()
    return output


def configure_scene(app, scene_name: str) -> None:
    notebook = find_notebook(app)
    if scene_name in {"tender_setup", "tender_results", "tender_export"}:
        notebook.select(app.query_tab)
    elif scene_name in {"appeal_setup", "appeal_search", "appeal_results", "appeal_detail", "appeal_export"}:
        notebook.select(app.appeal_tab)

    if scene_name == "tender_setup":
        configure_demo_state(app)
        app.status_var.set("自訂日期區間：2026/07/06 到 2026/07/08")
    elif scene_name == "tender_results":
        configure_demo_state(app)
        populate_results(app)
    elif scene_name == "tender_export":
        configure_demo_state(app)
        populate_results(app)
        output = export_demo_excel(app)
        app.status_var.set(f"已匯出招標示範 Excel：{output}")
    elif scene_name == "appeal_setup":
        configure_appeal_state(app)
    elif scene_name == "appeal_search":
        configure_appeal_state(app)
        app.appeal_search_button.configure(state="disabled")
        app.appeal_stop_button.configure(state="normal")
        app.status_var.set("公開徵求離線預覽查詢中：資訊安全、雲端服務、地籍測量")
    elif scene_name == "appeal_results":
        configure_appeal_state(app)
        populate_appeal_results(app)
    elif scene_name == "appeal_detail":
        configure_appeal_state(app)
        populate_appeal_results(app)
        app.status_var.set("已選取公開徵求資料，可開啟徵求頁面查看明細")
    elif scene_name == "appeal_export":
        configure_appeal_state(app)
        populate_appeal_results(app)
        output = export_demo_appeal_excel(app)
        app.status_var.set(f"已匯出公開徵求示範 Excel：{output}")
    elif scene_name == "manage":
        configure_demo_state(app)
        select_manage_tab(app)
    else:
        raise ValueError(f"unknown scene: {scene_name}")

    app.update()
    pump(app, 0.45)


def generate_frames(sections: dict[str, str]) -> list[Path]:
    import tkinter as tk
    import tender_notice_ui

    shutil.rmtree(FRAMES_DIR, ignore_errors=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    frames: list[Path] = []

    title_img = title_frame("政府採購公告查詢工具", "招標公告、公開徵求與 Excel 匯出", sections["01"])
    title_path = FRAMES_DIR / "01_opening.png"
    title_img.save(title_path)
    frames.append(title_path)

    old_cwd = Path.cwd()
    os.chdir(ROOT)
    root = tk.Tk()
    root.title("政府採購公告查詢工具")
    root.geometry("1500x900+50+40")
    root.minsize(1500, 900)
    app = tender_notice_ui.TenderNoticeApp(root)
    app.pack(fill="both", expand=True)
    try:
        with nonblocking_messageboxes():
            pump(root, 0.8)
            for scene_id, scene_name, _duration in SCENE_PLAN[1:]:
                configure_scene(app, scene_name)
                root.update()
                raw = capture_tk_window(root)
                frame = subtitle_frame(raw, sections[scene_id])
                out = FRAMES_DIR / f"{scene_id}_{scene_name}.png"
                frame.save(out)
                frames.append(out)
    finally:
        try:
            root.destroy()
        except Exception:
            pass
        os.chdir(old_cwd)
    return frames


def build_audio(ffmpeg: str, sections: dict[str, str], durations: list[float]) -> tuple[Path, list[float]]:
    shutil.rmtree(AUDIO_DIR, ignore_errors=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    adjusted = durations[:]
    wavs: list[Path] = []
    for idx, (scene_id, _scene_name, _duration) in enumerate(SCENE_PLAN):
        mp3 = AUDIO_DIR / f"{scene_id}.mp3"
        wav = AUDIO_DIR / f"{scene_id}.wav"
        synthesize_mp3(sections[scene_id], mp3)
        adjusted[idx] = max(adjusted[idx], media_duration(mp3) + 0.6)
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(mp3),
                "-af",
                f"apad,atrim=0:{adjusted[idx]:.3f}",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(wav),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        wavs.append(wav)

    concat = AUDIO_DIR / "concat_audio.txt"
    concat.write_text("".join(f"file '{path.as_posix()}'\n" for path in wavs), encoding="utf-8")
    narration = AUDIO_DIR / "narration.wav"
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "pcm_s16le", str(narration)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return narration, adjusted


def build_video(ffmpeg: str, frames: list[Path], durations: list[float], audio: Path | None) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with FRAMES_TXT.open("w", encoding="utf-8") as fh:
        for frame, duration in zip(frames, durations):
            fh.write(f"file '{frame.as_posix()}'\n")
            fh.write(f"duration {duration:.3f}\n")
        fh.write(f"file '{frames[-1].as_posix()}'\n")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(FRAMES_TXT),
            "-vf",
            f"fps={FPS},format=yuv420p",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(SILENT_VIDEO),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    OUTPUT_VIDEO.unlink(missing_ok=True)
    if audio is None:
        shutil.move(str(SILENT_VIDEO), str(OUTPUT_VIDEO))
        return

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(SILENT_VIDEO),
            "-i",
            str(audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(OUTPUT_VIDEO),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def verify_video(ffprobe: str) -> None:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate",
            "-of",
            "csv=p=0",
            str(OUTPUT_VIDEO),
        ],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    width, height, rate = result.stdout.strip().split(",")
    if (width, height) != (str(WIDTH), str(HEIGHT)) or rate != "30/1":
        raise RuntimeError(f"影片規格不符：{result.stdout.strip()}")


def cleanup_temp(keep_temp: bool) -> None:
    if keep_temp:
        return
    shutil.rmtree(FRAMES_DIR, ignore_errors=True)
    shutil.rmtree(AUDIO_DIR, ignore_errors=True)
    FRAMES_TXT.unlink(missing_ok=True)
    SILENT_VIDEO.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the Tender Notice operation manual video.")
    parser.add_argument("--silent", action="store_true", help="Generate subtitle-only video.")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary frames and audio.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not SCRIPT_PATH.exists():
        raise RuntimeError(f"Missing {SCRIPT_PATH}")
    if not STORYBOARD_PATH.exists():
        raise RuntimeError(f"Missing {STORYBOARD_PATH}")
    ffmpeg, ffprobe = find_ffmpeg()
    sections = read_script_sections()
    missing = [scene_id for scene_id, _name, _duration in SCENE_PLAN if scene_id not in sections]
    if missing:
        raise RuntimeError("script.md missing scenes: " + ", ".join(missing))

    try:
        frames = generate_frames(sections)
        durations = [duration for _scene_id, _scene_name, duration in SCENE_PLAN]
        audio = None
        if not args.silent:
            audio, durations = build_audio(ffmpeg, sections, durations)
        build_video(ffmpeg, frames, durations, audio)
        verify_video(ffprobe)
        duration = media_duration(OUTPUT_VIDEO)
        digest = sha256_file(OUTPUT_VIDEO)
        print(f"output={OUTPUT_VIDEO}")
        print(f"duration_seconds={duration:.3f}")
        print(f"sha256={digest}")
        print(f"type={'silent' if args.silent else 'voice'}")
    finally:
        cleanup_temp(args.keep_temp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
