@echo off
chcp 65001 >nul
echo 正在啟動 LibreLlama Lab Editor...
if exist "dist\LibreLlamaLabEditor\LibreLlamaLabEditor.exe" (
    start "" "dist\LibreLlamaLabEditor\LibreLlamaLabEditor.exe"
) else if exist "dist\LibreLlamaReviewer\LibreLlamaReviewer.exe" (
    start "" "dist\LibreLlamaReviewer\LibreLlamaReviewer.exe"
) else (
    python academic_reviewer_app.py
)
