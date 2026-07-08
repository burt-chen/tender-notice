# 政府採購公告查詢工具操作手冊 Storyboard

| Scene | Name | Duration | Screen |
| --- | --- | ---: | --- |
| 01 | opening | 5.5s | 獨立開場標題畫面 |
| 02 | categories | 7.0s | 查詢頁，已選取範例分類並顯示關鍵字 |
| 03 | manual_date | 7.0s | 文字框加入手動關鍵字，日期區間填入最近三天 |
| 04 | safe_search | 6.5s | 搜尋按鈕停用、狀態顯示離線預覽查詢中 |
| 05 | results | 8.0s | 結果表填入多筆安全範例公告 |
| 06 | detail | 6.5s | 選取單筆公告，狀態提示可開啟明細連結 |
| 07 | manage | 7.0s | 關鍵字管理頁顯示分類與關鍵字 |
| 08 | export | 7.0s | 實際匯出 Excel 後，狀態列顯示 demo output 路徑 |

## Recording Notes

- 使用真實 Tkinter 應用畫面，透過 PrintWindow 擷取視窗。
- 範例資料只寫入記憶體中的 UI 狀態；輸出檔放在 `manual_video/demo_output`。
- 第 08 段會執行工具本身的 `export_excel()`，但儲存對話框會導向示範資料夾，避免覆蓋使用者檔案。
