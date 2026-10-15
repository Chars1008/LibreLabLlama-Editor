@echo off
chcp 65001 >nul
echo 正在啟動 LibreLlama Reviewer...
if exist "dist\LibreLlamaReviewer\LibreLlamaReviewer.exe" (
    start "" "dist\LibreLlamaReviewer\LibreLlamaReviewer.exe"
) else if exist "dist\AcademicReviewer\AcademicReviewer.exe" (
    start "" "dist\AcademicReviewer\AcademicReviewer.exe"
) else (
    python academic_reviewer_app.py
)
