import sys
import os
import shutil
import subprocess
import time
import tempfile
import winreg

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QProgressBar
)

REG_UNINSTALL_KEYS = [
    r"Software\Microsoft\Windows\CurrentVersion\Uninstall\LibreLlamaReviewer",
    r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AcademicReviewer"
]

def unregister_from_windows():
    for key_path in REG_UNINSTALL_KEYS:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"移除註冊表失敗 ({key_path}): {e}")

class UninstallWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, install_dir: str):
        super().__init__()
        self.install_dir = install_dir

    def run(self):
        try:
            self.progress.emit(10, "正在檢查並關閉執行中的程式...")
            if sys.platform == "win32":
                for exe_name in ["LibreLlamaReviewer.exe", "AcademicReviewer.exe"]:
                    subprocess.run(["taskkill", "/F", "/IM", exe_name], capture_output=True)
                time.sleep(0.5)

            self.progress.emit(30, "正在刪除桌面捷徑...")
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            for lnk_name in ["LibreLlama Reviewer.lnk", "學術英文審查工作台.lnk"]:
                desk_lnk = os.path.join(desktop_dir, lnk_name)
                if os.path.exists(desk_lnk):
                    try:
                        os.remove(desk_lnk)
                    except Exception:
                        pass

            self.progress.emit(50, "正在刪除開始功能表捷徑...")
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                start_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
                for lnk_name in [
                    "LibreLlama Reviewer.lnk",
                    "解除安裝 LibreLlama Reviewer.lnk",
                    "學術英文審查工作台.lnk",
                    "解除安裝 學術英文審查工作台.lnk"
                ]:
                    p = os.path.join(start_dir, lnk_name)
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass

            self.progress.emit(70, "正在註銷 Windows 應用程式資訊...")
            unregister_from_windows()

            self.progress.emit(85, "正在清理應用程式目錄...")
            # 刪除安裝目錄下除 uninstall 自身外的所有檔案
            if os.path.exists(self.install_dir):
                for item in os.listdir(self.install_dir):
                    p = os.path.join(self.install_dir, item)
                    try:
                        if os.path.isdir(p):
                            shutil.rmtree(p, ignore_errors=True)
                        else:
                            os.remove(p)
                    except Exception:
                        pass

                # 若仍有殘留目錄，透過延遲指令刪除
                cleanup_cmd = f'cmd /c ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{self.install_dir}"'
                subprocess.Popen(cleanup_cmd, shell=True, creationflags=0x08000000 if sys.platform == "win32" else 0)

            self.progress.emit(100, "解除安裝已完成！")
            self.finished.emit(True, "【LibreLlama Reviewer】已成功從此電腦完全移除。")
        except Exception as e:
            self.finished.emit(False, f"解除安裝時發生異常: {str(e)}")

class UninstallWindow(QWidget):
    def __init__(self, install_dir: str):
        super().__init__()
        self.install_dir = install_dir
        self.setWindowTitle("LibreLlama Reviewer ─ 解除安裝精靈")
        self.resize(520, 280)
        self.worker = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        self.setStyleSheet("""
            QWidget { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Microsoft JhengHei; }
            QLabel { color: #f8fafc; }
            QProgressBar {
                border: 1px solid #334155; border-radius: 5px; text-align: center; height: 18px;
            }
            QProgressBar::chunk { background-color: #ef4444; border-radius: 4px; }
        """)

        title = QLabel("您確定要解除安裝【LibreLlama Reviewer】嗎？")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        layout.addWidget(title)

        desc = QLabel(
            f"解除安裝程式將移除下列資料夾及其所有檔案，並刪除桌面捷徑與開始功能表項目：\n"
            f"<b>{self.install_dir}</b>\n\n"
            f"注意：您本機已由 Ollama 下載的模型權重不受影響，仍可保留於電腦中供其他用途使用。"
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.5;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setVisible(False)
        self.status_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.cancel_btn = QPushButton("取消返回")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: #f8fafc; border: 1px solid #334155;
                border-radius: 5px; padding: 7px 16px; font-size: 12px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        self.cancel_btn.clicked.connect(self.close)
        btn_box.addWidget(self.cancel_btn)

        self.uninstall_btn = QPushButton("確認完全移除")
        self.uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626; color: #ffffff; font-weight: bold;
                border-radius: 5px; padding: 7px 18px; font-size: 12px;
            }
            QPushButton:hover { background-color: #b91c1c; }
        """)
        self.uninstall_btn.clicked.connect(self.start_uninstall)
        btn_box.addWidget(self.uninstall_btn)

        layout.addLayout(btn_box)

    def start_uninstall(self):
        self.cancel_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_lbl.setVisible(True)
        self.status_lbl.setText("正在開始解除安裝程序...")

        self.worker = UninstallWorker(self.install_dir)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_lbl.setText(msg)

    def on_finished(self, success: bool, msg: str):
        if success:
            QMessageBox.information(self, "解除安裝完成", msg)
            self.close()
        else:
            QMessageBox.critical(self, "失敗", msg)
            self.cancel_btn.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 檢查是否為跳板執行 (如果是從安裝目錄啟動，複製自己到 TEMP 再執行，以避免自我鎖定)
    args = sys.argv[1:]
    if "--from-temp" in args:
        idx = args.index("--from-temp")
        install_dir = args[idx + 1] if idx + 1 < len(args) else os.path.dirname(os.path.abspath(__file__))
    else:
        # 當前檔案路徑
        current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        install_dir = os.path.dirname(current_exe)
        temp_exe = os.path.join(tempfile.gettempdir(), "LibreLlamaReviewer_uninstaller.exe")
        try:
            shutil.copy2(current_exe, temp_exe)
            subprocess.Popen([temp_exe, "--from-temp", install_dir])
            sys.exit(0)
        except Exception:
            # 若複製失敗，直接就地執行
            pass

    win = UninstallWindow(install_dir)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
