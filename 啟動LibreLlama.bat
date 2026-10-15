@echo off
chcp 65001 >nul
echo 正在啟動 LibreLlama Reviewer...
if exist "dist\LibreLlamaReviewer\LibreLlamaReviewer.exe" (
    start "" "dist\LibreLlamaReviewer\LibreLlamaReviewer.exe"
) else (
    python academic_reviewer_app.py
)
