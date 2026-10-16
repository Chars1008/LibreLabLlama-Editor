@echo off
chcp 65001 >nul
echo 正在啟動 LibreLlama Lab Editor...
if exist "dist\LibreLlamaLabEditor\LibreLlamaLabEditor.exe" (
    start "" "dist\LibreLlamaLabEditor\LibreLlamaLabEditor.exe"
) else (
    python LibreLlamaLabEditor.py
)
