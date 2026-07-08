# 政府採購公告查詢工具操作手冊影片工作流程

## 目標

建立 PDFToolkit 同款規格的操作手冊影片：

- Canonical output: `manual_video/output/manual.mp4`
- 1920x1080、30fps、H.264、AAC
- 固定 132px 深藍中文字幕帶
- Edge TTS `zh-TW-HsiaoChenNeural` 分段旁白
- 真實工具畫面與安全範例操作

## 工具分析

目標專案是 Tkinter 桌面工具，入口為 `tender_notice_ui.py`，日常啟動指令為 `run_ui.bat`。核心流程是：

1. 從 `keywords.json` 載入分類與關鍵字。
2. 選擇分類或手動輸入關鍵字。
3. 設定今日、最近期間或自訂日期區間。
4. 查詢政府採購網公告並顯示表格結果。
5. 選取公告開啟明細連結，或匯出 Excel。
6. 在管理頁維護關鍵字 JSON。

## 安全示範策略

影片不直接連線政府採購網。錄製時 `make_manual_video.py` 會在應用程式記憶體中放入範例分類、關鍵字與公告結果，並實際呼叫工具的 Excel 匯出功能，把示範檔寫入：

`manual_video/demo_output/tender_notice_demo.xlsx`

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
