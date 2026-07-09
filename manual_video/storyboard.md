# 政府採購公告查詢工具操作手冊 Storyboard

| Scene | Name | Duration | Screen |
| --- | --- | ---: | --- |
| 01 | opening | 5.5s | 獨立開場標題畫面 |
| 02 | tender_setup | 7.0s | 招標查詢頁，分類、關鍵字、手動條件與日期區間已填入 |
| 03 | tender_results | 8.0s | 招標查詢結果表填入安全範例公告 |
| 04 | tender_export | 7.0s | 實際匯出招標結果 Excel，狀態列顯示 demo output 路徑 |
| 05 | appeal_setup | 7.0s | 公開徵求查詢頁，分類、關鍵字與公開徵求日期區間已填入 |
| 06 | appeal_search | 6.5s | 公開徵求查詢按鈕停用、狀態顯示離線預覽查詢中 |
| 07 | appeal_results | 8.0s | 公開徵求結果表填入多筆安全範例資料 |
| 08 | appeal_detail | 6.5s | 選取公開徵求單筆資料，狀態提示可開啟徵求頁面 |
| 09 | appeal_export | 7.0s | 實際匯出公開徵求 Excel，狀態列顯示 demo output 路徑 |
| 10 | manage | 7.0s | 關鍵字管理頁顯示共用分類與關鍵字 |

## Recording Notes

- 使用真實 Tkinter 應用畫面，透過 PrintWindow 擷取視窗。
- 範例資料只寫入記憶體中的 UI 狀態；輸出檔放在 `manual_video/demo_output`。
- 第 04 段會執行 `export_excel()`，輸出招標查詢示範檔。
- 第 09 段會執行 `appeal_export_excel()`，輸出公開徵求查詢示範檔。
