# 政府採購公告查詢工具操作手冊影片工作流程

## 目標

建立 PDFToolkit 同款規格的操作手冊影片：

- Canonical output: `manual_video/output/manual.mp4`
- 1920x1080、30fps、H.264、AAC
- 固定 132px 深藍中文字幕帶
- Edge TTS `zh-TW-HsiaoChenNeural` 分段旁白
- 真實工具畫面與安全範例操作

## 新版工具分析

目標專案是 Tkinter 桌面工具，入口為 `tender_notice_ui.py`，也提供 `main_frame.py` 的 `create_frame(parent)` 供工具管理器嵌入。新版 UI 有三個主要分頁：

1. 招標查詢：依分類、關鍵字與日期條件查詢政府採購公告。
2. 公開徵求查詢：依分類、關鍵字與公開徵求日期區間查詢 `readTpAppeal` 資料。
3. 關鍵字管理：維護共用的分類與關鍵字，並支援 JSON 匯入匯出。

## 安全示範策略

影片不直接連線政府採購網。錄製時 `make_manual_video.py` 會在應用程式記憶體中放入範例分類、招標結果與公開徵求結果，並實際呼叫工具的 Excel 匯出功能，把示範檔寫入：

- `manual_video/demo_output/tender_notice_demo.xlsx`
- `manual_video/demo_output/appeal_notice_demo.xlsx`

## 產生方式

```powershell
py make_manual_video.py
```

若只需要無聲字幕版：

```powershell
py make_manual_video.py --silent
```

保留暫存影格與音訊供檢查：

```powershell
py make_manual_video.py --keep-temp
```

## 驗證

完成後以 ffprobe 確認解析度、長度與音訊串流，並輸出：

- `output=...`
- `duration_seconds=...`
- `sha256=...`
- `type=voice|silent`
