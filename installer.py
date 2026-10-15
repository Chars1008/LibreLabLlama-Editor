import sys
import os
import shutil
import subprocess
import zipfile
import tempfile
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QCheckBox,
    QProgressBar, QStackedWidget, QFrame, QMessageBox
)
import httpx
import ollama
import winreg

def register_windows_uninstall(install_dir: str, version: str = "0.9.1"):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\LibreLlamaReviewer"
    exe_path = os.path.join(install_dir, "LibreLlamaReviewer.exe")
    uninst_path = os.path.join(install_dir, "uninstall.exe")
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "LibreLlama Reviewer (學術英文審查工作台)")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "LibreLlama Project")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{exe_path},0")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninst_path}"')
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    except Exception as e:
        print(f"註冊解除安裝資訊失敗: {e}")

def get_bundle_zip_path() -> Optional[str]:
    # 1. PyInstaller 打包時的暫存解壓目錄
    if hasattr(sys, "_MEIPASS"):
        p = os.path.join(sys._MEIPASS, "app_bundle.zip")
        if os.path.exists(p):
            return p
    # 2. 目前目錄
    cur_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_bundle.zip")
    if os.path.exists(cur_p):
        return cur_p
    return None

def create_windows_shortcut(target_exe: str, lnk_path: str, work_dir: str):
    try:
        ps_cmd = (
            f'$WshShell = New-Object -ComObject WScript.Shell; '
            f'$Shortcut = $WshShell.CreateShortcut("{lnk_path}"); '
            f'$Shortcut.TargetPath = "{target_exe}"; '
            f'$Shortcut.WorkingDirectory = "{work_dir}"; '
            f'$Shortcut.IconLocation = "{target_exe},0"; '
            f'$Shortcut.Save()'
        )
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                       capture_output=True, text=True, check=True)
    except Exception as e:
        print(f"建立捷徑失敗 ({lnk_path}): {e}")

class ExtractWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, target_dir: str, create_desktop: bool, create_start: bool):
        super().__init__()
        self.target_dir = target_dir
        self.create_desktop = create_desktop
        self.create_start = create_start

    def run(self):
        try:
            zip_path = get_bundle_zip_path()
            if not zip_path or not os.path.exists(zip_path):
                # 若無 zip，檢查是否有已編譯的 dist 資料夾
                alt_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "LibreLlamaReviewer")
                if not os.path.exists(alt_src):
                    alt_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "AcademicReviewer")
                if os.path.exists(alt_src):
                    os.makedirs(self.target_dir, exist_ok=True)
                    self.progress.emit(30, "正在複製應用程式核心檔案...")
                    for item in os.listdir(alt_src):
                        s = os.path.join(alt_src, item)
                        d = os.path.join(self.target_dir, item)
                        if os.path.isdir(s):
                            if os.path.exists(d):
                                shutil.rmtree(d, ignore_errors=True)
                            shutil.copytree(s, d)
                        else:
                            shutil.copy2(s, d)
                    self.progress.emit(90, "建立系統捷徑中...")
                else:
                    self.finished.emit(False, "找不到安裝封裝檔 (app_bundle.zip 或核心檔案目錄)！")
                    return
            else:
                os.makedirs(self.target_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, 'r') as z:
                    file_list = z.infolist()
                    total = len(file_list)
                    for idx, item in enumerate(file_list):
                        # 去除最頂層目錄路徑 (LibreLlamaReviewer/... 或 AcademicReviewer/...)
                        parts = item.filename.split('/')
                        if len(parts) > 1 and parts[0] in ["LibreLlamaReviewer", "AcademicReviewer"]:
                            rel_name = '/'.join(parts[1:])
                        else:
                            rel_name = item.filename
                        if not rel_name:
                            continue
                        dest_path = os.path.join(self.target_dir, rel_name)
                        if item.is_dir():
                            os.makedirs(dest_path, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            with z.open(item) as src, open(dest_path, 'wb') as dst:
                                shutil.copyfileobj(src, dst)
                        
                        pct = int((idx + 1) / total * 90)
                        if idx % 10 == 0:
                            self.progress.emit(pct, f"正在解壓縮檔案: {os.path.basename(rel_name)}")

            exe_path = os.path.join(self.target_dir, "LibreLlamaReviewer.exe")
            if not os.path.exists(exe_path):
                # 若舊名稱存在，自動重新命名為 LibreLlamaReviewer.exe
                old_exe = os.path.join(self.target_dir, "AcademicReviewer.exe")
                if os.path.exists(old_exe):
                    try:
                        shutil.move(old_exe, exe_path)
                    except Exception:
                        exe_path = old_exe

            # 建立捷徑
            self.progress.emit(95, "正在建立桌面與開始功能表捷徑...")
            if self.create_desktop:
                desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
                if os.path.exists(desktop_dir):
                    lnk = os.path.join(desktop_dir, "LibreLlama Reviewer.lnk")
                    create_windows_shortcut(exe_path, lnk, self.target_dir)

            if self.create_start:
                appdata = os.environ.get("APPDATA", "")
                if appdata:
                    start_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
                    if os.path.exists(start_dir):
                        lnk = os.path.join(start_dir, "LibreLlama Reviewer.lnk")
                        create_windows_shortcut(exe_path, lnk, self.target_dir)

                        uninst_exe = os.path.join(self.target_dir, "uninstall.exe")
                        if os.path.exists(uninst_exe):
                            uninst_lnk = os.path.join(start_dir, "解除安裝 LibreLlama Reviewer.lnk")
                            create_windows_shortcut(uninst_exe, uninst_lnk, self.target_dir)

            # 註冊至 Windows 設定之「應用程式與功能」
            register_windows_uninstall(self.target_dir, "0.9.1")

            self.progress.emit(100, "應用程式檔案部署完成！")
            self.finished.emit(True, "檔案解壓縮與安裝完成！")
        except Exception as e:
            self.finished.emit(False, f"安裝時發生異常: {str(e)}")

class OllamaDownloadWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str, str)

    def run(self):
        url = "https://ollama.com/download/OllamaSetup.exe"
        dest_path = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=180.0) as resp:
                if resp.status_code != 200:
                    self.finished.emit(False, f"伺服器回應錯誤 (HTTP {resp.status_code})", "")
                    return
                total_bytes = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_bytes > 0:
                                pct = int(downloaded / total_bytes * 100)
                                mb_done = downloaded / (1024 * 1024)
                                mb_tot = total_bytes / (1024 * 1024)
                                self.progress.emit(pct, f"正在下載官方安裝檔: {mb_done:.1f} MB / {mb_tot:.1f} MB ({pct}%)")
                            else:
                                mb_done = downloaded / (1024 * 1024)
                                self.progress.emit(0, f"已下載: {mb_done:.1f} MB")
            self.finished.emit(True, "官方安裝程式下載完成！", dest_path)
        except Exception as e:
            self.finished.emit(False, f"下載失敗: {str(e)}", "")

class ModelPullWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name

    def run(self):
        try:
            for part in ollama.pull(self.model_name, stream=True):
                status = getattr(part, 'status', '') or ''
                completed = getattr(part, 'completed', 0) or 0
                total = getattr(part, 'total', 0) or 0
                if total > 0 and completed > 0:
                    pct = int(completed / total * 100)
                    mb_done = completed / (1024 * 1024)
                    mb_tot = total / (1024 * 1024)
                    msg = f"{status}: {mb_done:.1f} MB / {mb_tot:.1f} MB ({pct}%)"
                    self.progress.emit(pct, msg)
                else:
                    self.progress.emit(0, status or "正在拉取模型中...")
            self.finished.emit(True, f"模型【{self.model_name}】下載完成！")
        except Exception as e:
            self.finished.emit(False, f"模型拉取失敗: {str(e)}")

class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LibreLlama Reviewer ─ 安裝精靈 v0.9.1 (封閉開發版)")
        self.resize(680, 520)
        self.target_dir = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "LibreLlamaReviewer")
        self.extract_worker: Optional[ExtractWorker] = None
        self.download_worker: Optional[OllamaDownloadWorker] = None
        self.pull_worker: Optional[ModelPullWorker] = None

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; color: #f8fafc; }
            QLabel { color: #f8fafc; }
            QLineEdit {
                background-color: #1e293b; color: #f8fafc;
                border: 1px solid #334155; border-radius: 5px; padding: 6px 8px; font-size: 12px;
            }
            QCheckBox { color: #cbd5e1; font-size: 12px; }
            QProgressBar {
                border: 1px solid #334155; border-radius: 5px; text-align: center; height: 18px;
            }
            QProgressBar::chunk { background-color: #3b82f6; border-radius: 4px; }
            QFrame.card {
                background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px;
            }
        """)

        # 頂部橫幅
        header_layout = QHBoxLayout()
        header_title = QLabel("🦙 LibreLlama Reviewer ─ 安裝精靈")
        header_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        v_tag = QLabel("版本 v0.9.1 (封閉開發版)")
        v_tag.setStyleSheet("color: #94a3b8; font-size: 11px;")
        header_layout.addWidget(v_tag)
        main_layout.addLayout(header_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #334155;")
        main_layout.addWidget(line)

        # 頁面堆疊
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Page 0: 歡迎頁
        self.stack.addWidget(self.create_welcome_page())

        # Page 1: 安裝目錄選擇頁
        self.stack.addWidget(self.create_path_page())

        # Page 2: 解壓縮進度頁
        self.stack.addWidget(self.create_extract_page())

        # Page 3: Ollama 與模型引導頁
        self.stack.addWidget(self.create_ollama_page())

        # Page 4: 完成頁
        self.stack.addWidget(self.create_finish_page())

        # 底部導覽按鈕列
        nav_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 5px; padding: 6px 14px; }
            QPushButton:hover { background-color: #334155; color: #f8fafc; }
        """)
        self.cancel_btn.clicked.connect(self.close)
        nav_layout.addWidget(self.cancel_btn)
        nav_layout.addStretch()

        self.back_btn = QPushButton("上一步")
        self.back_btn.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 5px; padding: 6px 14px; }
            QPushButton:hover { background-color: #334155; color: #ffffff; }
        """)
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setVisible(False)
        nav_layout.addWidget(self.back_btn)

        self.next_btn = QPushButton("下一步 ➔")
        self.next_btn.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: #ffffff; font-weight: bold; border-radius: 5px; padding: 6px 18px; font-size: 12px; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.next_btn.clicked.connect(self.go_next)
        nav_layout.addWidget(self.next_btn)

        main_layout.addLayout(nav_layout)

    def create_welcome_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(14)

        t = QLabel("歡迎使用【LibreLlama Reviewer】安裝精靈")
        t.setFont(QFont("Segoe UI", 13, QFont.Bold))
        l.addWidget(t)

        info = QLabel(
            "LibreLlama Reviewer 專為國際頂級期刊（Nature, IEEE, Science, ACM 等）投稿學者打造，\n"
            "具備以下核心能力：\n\n"
            "• 🔬 <b>審稿人同儕審查實質建議</b>：針對消融實驗、顯著性檢定與因果推論進行嚴密批判，並提供中英雙語對照。\n"
            "• ✍️ <b>逐句穿透式窮舉審查</b>：深入挖掘 6~10 處改寫點，大幅提升論文刊登率。\n"
            "• 🛡️ <b>混合架構雙模運算</b>：支援 100% 離線在地 Ollama 模型（極致隱私保護）與雲端旗艦 API（免下載模型）。\n"
            "• ⚡ <b>本機 0 秒秒級快篩</b>：即時攔截縮寫、口語贅詞與過度斷言。\n\n"
            "本安裝精靈將協助您在電腦上安裝工作台，並引導完成本機 Ollama 運算環境與模型配置。"
        )
        info.setStyleSheet("color: #cbd5e1; line-height: 1.5; font-size: 12px;")
        info.setWordWrap(True)
        l.addWidget(info)
        l.addStretch()
        return w

    def create_path_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(14)

        t = QLabel("選擇安裝目標資料夾")
        t.setFont(QFont("Segoe UI", 12, QFont.Bold))
        l.addWidget(t)

        tip = QLabel("安裝精靈將把程式檔案複製至以下路徑（預設路徑無需系統管理員權限，相容性最高）：")
        tip.setStyleSheet("color: #94a3b8; font-size: 11px;")
        l.addWidget(tip)

        path_box = QHBoxLayout()
        self.path_edit = QLineEdit(self.target_dir)
        path_box.addWidget(self.path_edit)

        browse_btn = QPushButton("瀏覽...")
        browse_btn.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 5px; padding: 6px 12px; }
            QPushButton:hover { background-color: #334155; }
        """)
        browse_btn.clicked.connect(self.browse_path)
        path_box.addWidget(browse_btn)
        l.addLayout(path_box)

        l.addSpacing(10)
        opt_title = QLabel("捷徑建立選項:")
        opt_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        l.addWidget(opt_title)

        self.chk_desktop = QCheckBox("在桌面上建立捷徑 (推薦)")
        self.chk_desktop.setChecked(True)
        l.addWidget(self.chk_desktop)

        self.chk_start = QCheckBox("在 Windows 開始功能表建立捷徑")
        self.chk_start.setChecked(True)
        l.addWidget(self.chk_start)

        l.addStretch()
        return w

    def browse_path(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇安裝資料夾", self.target_dir)
        if folder:
            self.target_dir = os.path.join(folder, "LibreLlamaReviewer")
            self.path_edit.setText(self.target_dir)

    def create_extract_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(16)

        t = QLabel("正在安裝應用程式核心檔案...")
        t.setFont(QFont("Segoe UI", 12, QFont.Bold))
        l.addWidget(t)

        self.extract_progress_bar = QProgressBar()
        self.extract_progress_bar.setRange(0, 100)
        self.extract_progress_bar.setValue(0)
        l.addWidget(self.extract_progress_bar)

        self.extract_status_lbl = QLabel("準備開始解壓縮與部署...")
        self.extract_status_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        l.addWidget(self.extract_status_lbl)

        l.addStretch()
        return w

    def create_ollama_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(12)

        t = QLabel("本機 Ollama 運算環境與模型安裝引導")
        t.setFont(QFont("Segoe UI", 12, QFont.Bold))
        l.addWidget(t)

        desc = QLabel("若您希望使用 100% 離線推論保護論文資料隱私，請依照下列步驟確認本機環境：")
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        l.addWidget(desc)

        # 區塊 1: Ollama 狀態
        c1 = QFrame()
        c1.setProperty("class", "card")
        c1_layout = QVBoxLayout(c1)
        self.ollama_status_lbl = QLabel("正在檢測本機 Ollama 環境...")
        c1_layout.addWidget(self.ollama_status_lbl)

        btn_box = QHBoxLayout()
        self.install_ollama_btn = QPushButton("🌐 一鍵下載並安裝 Ollama (官方安裝檔)")
        self.install_ollama_btn.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: #ffffff; font-weight: bold; border-radius: 5px; padding: 5px 12px; font-size: 11px; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.install_ollama_btn.clicked.connect(self.download_ollama)
        btn_box.addWidget(self.install_ollama_btn)

        self.start_ollama_btn = QPushButton("🚀 啟動 Ollama 服務")
        self.start_ollama_btn.setStyleSheet("""
            QPushButton { background-color: #059669; color: #ffffff; font-weight: bold; border-radius: 5px; padding: 5px 12px; font-size: 11px; }
            QPushButton:hover { background-color: #047857; }
        """)
        self.start_ollama_btn.clicked.connect(self.start_ollama_service)
        btn_box.addWidget(self.start_ollama_btn)

        self.check_btn = QPushButton("🔄 重新檢測")
        self.check_btn.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 5px; padding: 5px 10px; font-size: 11px; }
            QPushButton:hover { background-color: #334155; }
        """)
        self.check_btn.clicked.connect(self.check_ollama_status)
        btn_box.addWidget(self.check_btn)
        btn_box.addStretch()
        c1_layout.addLayout(btn_box)
        l.addWidget(c1)

        # 區塊 2: 推薦模型下載
        c2 = QFrame()
        c2.setProperty("class", "card")
        c2_layout = QVBoxLayout(c2)
        c2_title = QLabel("學術推薦模型快速安裝:")
        c2_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        c2_layout.addWidget(c2_title)

        m_box = QHBoxLayout()
        m_info = QLabel("<b>llama3.1:8b</b> (約 4.7 GB) ─ 適合一般筆電與工作站，運算快速、修辭潤飾極佳。")
        m_info.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        m_box.addWidget(m_info)

        self.pull_btn = QPushButton("📥 下載此模型")
        self.pull_btn.setStyleSheet("""
            QPushButton { background-color: #1e3a8a; color: #93c5fd; border: 1px solid #3b82f6; border-radius: 5px; padding: 5px 12px; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background-color: #2563eb; color: #ffffff; }
        """)
        self.pull_btn.clicked.connect(lambda: self.pull_model("llama3.1:8b"))
        m_box.addWidget(self.pull_btn)
        c2_layout.addLayout(m_box)
        l.addWidget(c2)

        # 下載進度條
        self.env_progress_bar = QProgressBar()
        self.env_progress_bar.setVisible(False)
        self.env_progress_bar.setRange(0, 100)
        l.addWidget(self.env_progress_bar)

        self.env_status_lbl = QLabel("")
        self.env_status_lbl.setVisible(False)
        self.env_status_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        l.addWidget(self.env_status_lbl)

        # 提示
        skip_tip = QLabel("💡 <b>若您打算使用「線上 API 模式（DeepSeek / OpenAI 等）」或欲稍後再下載模型，可直接點擊「下一步」跳過此頁。</b>")
        skip_tip.setStyleSheet("color: #94a3b8; font-size: 11px;")
        skip_tip.setWordWrap(True)
        l.addWidget(skip_tip)

        l.addStretch()
        return w

    def create_finish_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(14)

        t = QLabel("🎉 安裝已全部完成！")
        t.setFont(QFont("Segoe UI", 14, QFont.Bold))
        l.addWidget(t)

        info = QLabel(
            "【LibreLlama Reviewer】已成功部署至您的電腦。\n\n"
            "• 您可隨時從桌面捷徑或開始功能表啟動本軟體。\n"
            "• 進入工作台後，若需下載其他學術模型（如 qwen2.5:14b）或切換線上 API，均可透過頂部工具列一鍵完成。"
        )
        info.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.6;")
        info.setWordWrap(True)
        l.addWidget(info)

        l.addSpacing(10)
        self.chk_launch = QCheckBox("立即啟動 LibreLlama Reviewer")
        self.chk_launch.setChecked(True)
        self.chk_launch.setFont(QFont("Segoe UI", 11, QFont.Bold))
        l.addWidget(self.chk_launch)

        l.addStretch()
        return w

    def go_next(self):
        idx = self.stack.currentIndex()
        if idx == 0:
            # 歡迎頁 -> 目錄頁
            self.back_btn.setVisible(True)
            self.stack.setCurrentIndex(1)
        elif idx == 1:
            # 目錄頁 -> 解壓縮頁 (開始安裝)
            self.target_dir = self.path_edit.text().strip()
            self.back_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.next_btn.setText("正在安裝...")
            self.stack.setCurrentIndex(2)
            self.start_extract()
        elif idx == 2:
            # 解壓完成 -> Ollama 環境頁
            self.stack.setCurrentIndex(3)
            self.check_ollama_status()
            self.next_btn.setText("下一步 ➔")
        elif idx == 3:
            # Ollama 環境頁 -> 完成頁
            self.stack.setCurrentIndex(4)
            self.back_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.next_btn.setText("完成 (Finish)")
        elif idx == 4:
            # 完成頁 -> 啟動應用程式並關閉安裝程式
            if self.chk_launch.isChecked():
                exe_path = os.path.join(self.target_dir, "LibreLlamaReviewer.exe")
                if not os.path.exists(exe_path):
                    exe_path = os.path.join(self.target_dir, "AcademicReviewer.exe")
                if os.path.exists(exe_path):
                    subprocess.Popen([exe_path], cwd=self.target_dir)
            self.close()

    def go_back(self):
        idx = self.stack.currentIndex()
        if idx == 1:
            self.back_btn.setVisible(False)
            self.stack.setCurrentIndex(0)
        elif idx == 3:
            self.stack.setCurrentIndex(1)

    def start_extract(self):
        self.extract_worker = ExtractWorker(
            self.target_dir,
            self.chk_desktop.isChecked(),
            self.chk_start.isChecked()
        )
        self.extract_worker.progress.connect(self.on_extract_progress)
        self.extract_worker.finished.connect(self.on_extract_finished)
        self.extract_worker.start()

    def on_extract_progress(self, pct: int, msg: str):
        self.extract_progress_bar.setValue(pct)
        self.extract_status_lbl.setText(msg)

    def on_extract_finished(self, success: bool, msg: str):
        if success:
            self.next_btn.setEnabled(True)
            self.next_btn.setText("下一步 ➔")
            self.go_next()
        else:
            QMessageBox.critical(self, "安裝失敗", msg)
            self.back_btn.setEnabled(True)
            self.next_btn.setEnabled(True)
            self.next_btn.setText("重試")

    def check_ollama_status(self):
        which_path = shutil.which("ollama")
        appdata_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        is_installed = bool(which_path) or os.path.exists(appdata_path)
        ollama_exec = which_path or appdata_path if is_installed else None

        is_running = False
        try:
            r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
            if r.status_code == 200:
                is_running = True
        except Exception:
            is_running = False

        if not is_installed:
            self.ollama_status_lbl.setText("❌ <b>尚未偵測到 Ollama 運算引擎</b>")
            self.ollama_status_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.install_ollama_btn.setVisible(True)
            self.start_ollama_btn.setVisible(False)
            self.pull_btn.setEnabled(False)
        elif not is_running:
            self.ollama_status_lbl.setText(f"⚠️ <b>Ollama 已安裝，但服務尚未啟動</b> (路徑: {ollama_exec})")
            self.ollama_status_lbl.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.install_ollama_btn.setVisible(False)
            self.start_ollama_btn.setVisible(True)
            self.pull_btn.setEnabled(False)
        else:
            self.ollama_status_lbl.setText("✅ <b>Ollama 服務運作正常 (Port 11434 已連線)</b>")
            self.ollama_status_lbl.setStyleSheet("color: #10b981; font-size: 11px;")
            self.install_ollama_btn.setVisible(False)
            self.start_ollama_btn.setVisible(False)
            self.pull_btn.setEnabled(True)
            # 檢測模型
            try:
                res = ollama.list()
                names = []
                if hasattr(res, 'models'):
                    names = [getattr(m, 'model', '') or getattr(m, 'name', '') for m in res.models]
                if any("llama3.1:8b" in n for n in names):
                    self.pull_btn.setText("✅ 已安裝")
                    self.pull_btn.setEnabled(False)
                else:
                    self.pull_btn.setText("📥 下載此模型")
                    self.pull_btn.setEnabled(True)
            except Exception:
                pass

    def start_ollama_service(self):
        which_path = shutil.which("ollama")
        appdata_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        exec_path = which_path or appdata_path
        if not exec_path or not os.path.exists(exec_path):
            QMessageBox.warning(self, "錯誤", "找不到 ollama.exe 執行檔。")
            return
        try:
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            subprocess.Popen([exec_path, "serve"], creationflags=creation_flags)
            self.ollama_status_lbl.setText("正在啟動 Ollama 服務...")
            QTimer.singleShot(2500, self.check_ollama_status)
        except Exception as e:
            QMessageBox.critical(self, "啟動失敗", f"無法啟動 Ollama 服務: {e}")

    def download_ollama(self):
        self.install_ollama_btn.setEnabled(False)
        self.env_progress_bar.setVisible(True)
        self.env_progress_bar.setValue(0)
        self.env_status_lbl.setVisible(True)
        self.env_status_lbl.setText("正在下載官方 Ollama 安裝檔...")

        self.download_worker = OllamaDownloadWorker()
        self.download_worker.progress.connect(self.on_env_progress)
        self.download_worker.finished.connect(self.on_ollama_download_finished)
        self.download_worker.start()

    def on_env_progress(self, pct: int, msg: str):
        self.env_progress_bar.setValue(pct)
        self.env_status_lbl.setText(msg)

    def on_ollama_download_finished(self, success: bool, msg: str, path: str):
        self.install_ollama_btn.setEnabled(True)
        self.env_progress_bar.setVisible(False)
        self.env_status_lbl.setVisible(False)
        if success and path and os.path.exists(path):
            QMessageBox.information(
                self, "下載完成",
                "已成功下載 Ollama 安裝程式！即將啟動官方安裝精靈。\n請在安裝完成後點擊「重新檢測」。"
            )
            subprocess.Popen([path])
        else:
            QMessageBox.critical(self, "下載失敗", f"無法下載 Ollama: {msg}")

    def pull_model(self, model_name: str):
        self.pull_btn.setEnabled(False)
        self.env_progress_bar.setVisible(True)
        self.env_progress_bar.setValue(0)
        self.env_status_lbl.setVisible(True)
        self.env_status_lbl.setText(f"開始準備下載模型【{model_name}】...")

        self.pull_worker = ModelPullWorker(model_name)
        self.pull_worker.progress.connect(self.on_env_progress)
        self.pull_worker.finished.connect(self.on_pull_finished)
        self.pull_worker.start()

    def on_pull_finished(self, success: bool, msg: str):
        self.env_progress_bar.setVisible(False)
        self.env_status_lbl.setVisible(False)
        if success:
            self.pull_btn.setText("✅ 已安裝")
            self.pull_btn.setEnabled(False)
            QMessageBox.information(self, "下載成功", "模型已成功部署至本機！")
        else:
            self.pull_btn.setEnabled(True)
            QMessageBox.critical(self, "下載失敗", f"拉取模型失敗:\n{msg}")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = InstallerWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
