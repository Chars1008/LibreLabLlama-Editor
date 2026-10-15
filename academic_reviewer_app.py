import sys
import os
import json
import html
import re
from typing import List, Literal, Optional, Dict, Tuple
from pydantic import BaseModel, Field

from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTextEdit, QTextBrowser, QPushButton, QLabel, QComboBox,
    QScrollArea, QFrame, QMessageBox, QProgressBar, QMenu, QDialog,
    QLineEdit, QFormLayout
)
import subprocess
import shutil
import tempfile
import ollama
import httpx
import json_repair

APP_VERSION = "1.2.0"
DEFAULT_UPDATE_URL = "version.json"
CONFIG_FILE = "app_config.json"

def load_config() -> dict:
    default_config = {
        "engine_mode": "ollama",
        "dark_mode": False,
        "api_provider": "DeepSeek",
        "api_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "api_model": "deepseek-chat",
        "update_url": DEFAULT_UPDATE_URL
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_config.update(saved)
        except Exception:
            pass
    return default_config

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ==========================================
# 0. 本機即時前置檢查器 (無需 LLM，純 Python 規則 0.001 秒完成)
# ==========================================
class PreflightMatch:
    def __init__(self, category: str, original: str, replacement: str, explanation: str, span: Tuple[int, int]):
        self.category = category
        self.original = original
        self.replacement = replacement
        self.explanation = explanation
        self.span = span

class PreflightChecker:
    CONTRACTIONS = {
        r"\bdon't\b": ("do not", "學術論文應避免縮寫"),
        r"\bdoesn't\b": ("does not", "學術論文應避免縮寫"),
        r"\bcan't\b": ("cannot", "學術論文應避免縮寫"),
        r"\bwon't\b": ("will not", "學術論文應避免縮寫"),
        r"\bit's\b": ("it is", "學術論文應避免縮寫"),
        r"\bthey're\b": ("they are", "學術論文應避免縮寫"),
        r"\bwe're\b": ("we are", "學術論文應避免縮寫"),
        r"\bdidn't\b": ("did not", "學術論文應避免縮寫"),
        r"\bhaven't\b": ("have not", "學術論文應避免縮寫"),
        r"\bhasn't\b": ("has not", "學術論文應避免縮寫"),
        r"\bcouldn't\b": ("could not", "學術論文應避免縮寫"),
        r"\bwouldn't\b": ("would not", "學術論文應避免縮寫"),
        r"\bshouldn't\b": ("should not", "學術論文應避免縮寫"),
        r"\bisn't\b": ("is not", "學術論文應避免縮寫"),
        r"\baren't\b": ("are not", "學術論文應避免縮寫"),
    }

    INFORMAL_WORDS = {
        r"\ba lot of\b": ("a substantial number of", "口語化量詞，建議使用精確或正式學術詞彙"),
        r"\blots of\b": ("numerous / considerable", "口語化量詞，不建議使用於論文"),
        r"\bget\b": ("obtain / acquire", "口語動詞，學術寫作建議改用 obtain/acquire"),
        r"\bgot\b": ("obtained / acquired", "口語動詞，學術寫作建議改用 obtained/acquired"),
        r"\bvery fast\b": ("computationally efficient / rapid", "過度口語化的程度修飾"),
        r"\bfast\b": ("rapid / highly efficient", "建議使用更具技術精確度的詞彙"),
        r"\bhappy\b": ("satisfied / favorably disposed", "過於主觀情緒化的非學術詞彙"),
        r"\breally\b": ("notably / considerably", "口語程度副詞，論文中應避免"),
        r"\bbig\b": ("substantial / prominent / significant", "非正式形容詞，缺乏學術精確度"),
        r"\bkind of\b": ("somewhat / to an extent", "非正式模糊用語"),
        r"\bsort of\b": ("somewhat / to an extent", "非正式模糊用語"),
        r"\bdue to the fact that\b": ("because", "學術贅言（Wordiness），建議直接精簡"),
        r"\bin order to\b": ("to", "非必要冗詞，多數情況下可直接簡化為 to"),
        r"\bneedless to say\b": ("evidently / clearly", "陳詞濫調，建議使用精煉副詞"),
    }

    OVERCLAIMING_PATTERNS = {
        r"\bdefinitely prove(s|d)?\b": ("suggest(s) / provide evidence for", "過度宣稱：實驗鮮少能「絕對證明」，建議使用學術謙抑詞"),
        r"\bcompletely solve(s|d)?\b": ("substantially address(es) / alleviate(s)", "過度宣稱：極少有模型能「完全解決」複雜問題"),
        r"\bundeniably\b": ("compellingly / convincingly", "過於武斷的主觀修飾詞，易招致審稿人反感"),
        r"\bdominate(s|d)? all\b": ("outperform(s) existing / surpass(es)", "過度誇大宣稱，缺乏客觀衡量標準"),
        r"\bwithout any other factors\b": ("primarily / predominantly", "武斷排除其他變因，缺乏因果論證嚴謹性"),
    }

    @classmethod
    def scan(cls, text: str) -> List[PreflightMatch]:
        matches: List[PreflightMatch] = []
        if not text:
            return matches

        for pat, (rep, exp) in cls.CONTRACTIONS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                matches.append(PreflightMatch("縮寫禁忌", m.group(0), rep, exp, (m.start(), m.end())))

        for pat, (rep, exp) in cls.INFORMAL_WORDS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                matches.append(PreflightMatch("非正式口語", m.group(0), rep, exp, (m.start(), m.end())))

        for pat, (rep, exp) in cls.OVERCLAIMING_PATTERNS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                matches.append(PreflightMatch("過度宣稱預警", m.group(0), rep, exp, (m.start(), m.end())))

        return matches

    @classmethod
    def fix_all_contractions(cls, text: str) -> str:
        res = text
        for pat, (rep, _) in cls.CONTRACTIONS.items():
            res = re.sub(pat, rep, res, flags=re.IGNORECASE)
        return res

    @classmethod
    def fix_all_informal_and_contractions(cls, text: str) -> str:
        res = cls.fix_all_contractions(text)
        direct_reps = {
            r"\ba lot of\b": "a substantial number of",
            r"\blots of\b": "numerous",
            r"\bvery fast\b": "rapidly",
            r"\bdue to the fact that\b": "because",
            r"\bin order to\b": "to",
        }
        for pat, rep in direct_reps.items():
            res = re.sub(pat, rep, res, flags=re.IGNORECASE)
        return res

# ==========================================
# 1. 專用右鍵選單產生器與客製化文本組件 (支援深淺色主題)
# ==========================================
def create_academic_context_menu(widget: QTextEdit, is_read_only: bool = False, on_quick_fix=None, is_dark: bool = False) -> QMenu:
    menu = QMenu(widget)
    menu.setFont(QFont("Segoe UI", 10))

    if is_dark:
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 0px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft JhengHei", sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                background-color: transparent;
                color: #f8fafc;
                padding: 7px 32px 7px 16px;
                min-width: 165px;
                margin: 1px 4px;
                border-radius: 4px;
                font-weight: 500;
            }
            QMenu::item:selected {
                background-color: #334155;
                color: #38bdf8;
            }
            QMenu::item:disabled {
                color: #64748b;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 5px 8px;
            }
        """)
    else:
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px 0px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft JhengHei", sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                background-color: transparent;
                color: #0f172a;
                padding: 7px 32px 7px 16px;
                min-width: 165px;
                margin: 1px 4px;
                border-radius: 4px;
                font-weight: 500;
            }
            QMenu::item:selected {
                background-color: #eff6ff;
                color: #1d4ed8;
            }
            QMenu::item:disabled {
                color: #94a3b8;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e2e8f0;
                margin: 5px 8px;
            }
        """)

    if not is_read_only:
        undo_act = menu.addAction("↩️ 復原 (Undo)")
        undo_act.setShortcut("Ctrl+Z")
        undo_act.setEnabled(widget.document().isUndoAvailable())
        undo_act.triggered.connect(widget.undo)

        redo_act = menu.addAction("↪️ 重做 (Redo)")
        redo_act.setShortcut("Ctrl+Y")
        redo_act.setEnabled(widget.document().isRedoAvailable())
        redo_act.triggered.connect(widget.redo)

        menu.addSeparator()

        cut_act = menu.addAction("✂️ 剪下 (Cut)")
        cut_act.setShortcut("Ctrl+X")
        cut_act.setEnabled(widget.textCursor().hasSelection())
        cut_act.triggered.connect(widget.cut)

    copy_act = menu.addAction("📋 複製 (Copy)")
    copy_act.setShortcut("Ctrl+C")
    copy_act.setEnabled(widget.textCursor().hasSelection() if is_read_only else True)
    copy_act.triggered.connect(widget.copy)

    if not is_read_only:
        paste_act = menu.addAction("📥 貼上 (Paste)")
        paste_act.setShortcut("Ctrl+V")
        paste_act.setEnabled(bool(QApplication.clipboard().text()))
        paste_act.triggered.connect(widget.paste)

        del_act = menu.addAction("🗑️ 刪除 (Delete)")
        del_act.setEnabled(widget.textCursor().hasSelection())
        del_act.triggered.connect(lambda: widget.textCursor().removeSelectedText())

    menu.addSeparator()

    select_all_act = menu.addAction("📑 全選 (Select All)")
    select_all_act.setShortcut("Ctrl+A")
    select_all_act.triggered.connect(widget.selectAll)

    if not is_read_only:
        clear_act = menu.addAction("🧹 清空草稿 (Clear)")
        clear_act.setEnabled(bool(widget.toPlainText().strip()))
        clear_act.triggered.connect(widget.clear)

        if on_quick_fix:
            menu.addSeparator()
            qf_act = menu.addAction("⚡ 一鍵自動修復縮寫與口語詞")
            qf_act.triggered.connect(on_quick_fix)

    return menu

class AcademicTextEdit(QTextEdit):
    def __init__(self, parent=None, on_quick_fix=None, is_dark: bool = False):
        super().__init__(parent)
        self.on_quick_fix = on_quick_fix
        self.is_dark = is_dark

    def set_theme_mode(self, is_dark: bool):
        self.is_dark = is_dark
        text_col = QColor("#ffffff" if is_dark else "#0f172a")
        bg_col = QColor("#1e293b" if is_dark else "#ffffff")
        border_col = "#334155" if is_dark else "#cbd5e1"

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Text, text_col)
        pal.setColor(QPalette.ColorRole.Base, bg_col)
        pal.setColor(QPalette.ColorRole.WindowText, text_col)
        self.setPalette(pal)

        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {"#1e293b" if is_dark else "#ffffff"};
                color: {"#ffffff" if is_dark else "#0f172a"};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }}
        """)

        self.setTextColor(text_col)

        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        char_fmt = cursor.charFormat()
        char_fmt.setForeground(text_col)
        cursor.mergeCharFormat(char_fmt)
        cursor.clearSelection()
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def setPlainText(self, text: str):
        super().setPlainText(text)
        text_col = QColor("#ffffff" if self.is_dark else "#0f172a")
        self.setTextColor(text_col)
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        char_fmt = cursor.charFormat()
        char_fmt.setForeground(text_col)
        cursor.mergeCharFormat(char_fmt)
        cursor.clearSelection()
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def insertFromMimeData(self, source):
        text = source.text()
        cursor = self.textCursor()
        text_col = QColor("#ffffff" if self.is_dark else "#0f172a")
        fmt = cursor.charFormat()
        fmt.setForeground(text_col)
        cursor.setCharFormat(fmt)
        cursor.insertText(text, fmt)

    def contextMenuEvent(self, event):
        menu = create_academic_context_menu(self, is_read_only=False, on_quick_fix=self.on_quick_fix, is_dark=self.is_dark)
        pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
        menu.exec(pos)

class AcademicTextBrowser(QTextBrowser):
    def __init__(self, parent=None, is_dark: bool = False):
        super().__init__(parent)
        self.is_dark = is_dark

    def set_theme_mode(self, is_dark: bool):
        self.is_dark = is_dark
        text_col = QColor("#f8fafc" if is_dark else "#0f172a")
        bg_col = QColor("#1e293b" if is_dark else "#ffffff")
        border_col = "#334155" if is_dark else "#cbd5e1"
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Text, text_col)
        pal.setColor(QPalette.ColorRole.Base, bg_col)
        pal.setColor(QPalette.ColorRole.WindowText, text_col)
        self.setPalette(pal)
        self.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {"#1e293b" if is_dark else "#ffffff"};
                color: {"#f8fafc" if is_dark else "#0f172a"};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 8px;
            }}
        """)

    def contextMenuEvent(self, event):
        menu = create_academic_context_menu(self, is_read_only=True, is_dark=self.is_dark)
        pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
        menu.exec(pos)

# ==========================================
# 2. 定義 Pydantic 結構化審查報告格式 (中英雙語實證補強 + 窮舉審查)
# ==========================================
class RevisionOption(BaseModel):
    style_label: str = Field(description="風格標籤，例如：保守嚴謹（Hedged）、精簡有力（Concise）、強調創新（Assertive）")
    revised_text: str = Field(description="修改後的英文句子")
    rationale_zh: str = Field(description="正體中文理由：說明為何此修改更符合學術風格或期刊標準")

class IssueItem(BaseModel):
    category: Literal["Logic Error", "Flawed Deduction", "Grammar & Mechanics", "Rhetorical Defect"] = "Rhetorical Defect"
    category_zh: str = Field(default="修辭與學術風格", description="問題類型的正體中文")
    severity: Literal["Critical", "Major", "Minor"] = "Major"
    original_text: str = Field(description="出現問題的原文片段（必須完全精確比對輸入文本）")
    meaning_analysis_zh: str = Field(default="文意解析與翻譯", description="原句的初步中文翻譯與文意判斷解說（正體中文）")
    reviewer_comment_en: str = Field(default="Reviewer comment", description="審稿人點評意見（英文）")
    reviewer_comment_zh: str = Field(default="審稿意見", description="審稿人點評意見（正體中文）")
    revision_options: List[RevisionOption] = Field(default_factory=list, description="提供至少 2 個不同學術風格的具體修改選項")

class ResearchRecommendation(BaseModel):
    gap_identified_zh: str = Field(default="", description="上下文論述、因果推論或實驗證據鏈的缺失/不完整之處 (正體中文)")
    gap_identified_en: str = Field(default="", description="Evidence chain or methodological gap analysis (English)")
    severity: Literal["Must Address (必補/致命缺陷)", "Strongly Recommended (強烈建議補強)", "Optional (可選加分項)"] = "Strongly Recommended (強烈建議補強)"
    action_type: Literal["補充消融實驗/對照實驗", "補充統計檢驗與顯著性分析", "控制干擾變因/排除替代解釋", "補充基準模型(Baseline)對比", "補強理論前置假設與適用邊界"] = "補充統計檢驗與顯著性分析"
    concrete_proposal_zh: str = Field(default="", description="具體建議補做的研究、實驗步驟、數據收集或統計分析方案 (正體中文)")
    concrete_proposal_en: str = Field(default="", description="Concrete proposed experiments, statistical tests, or control protocols (English)")
    impact_on_acceptance_zh: str = Field(default="", description="完成此補強後對防禦 Reviewer 質疑與提高論文接受率的實質幫助 (正體中文)")
    impact_on_acceptance_en: str = Field(default="", description="How this proposal strengthens the paper to defend against peer reviewers in rebuttal (English)")

class AcademicReviewReport(BaseModel):
    article_gist_zh: str = Field(default="學術草稿診斷完成。", description="輸入文本的學術主旨判斷與整體寫作品質診斷（正體中文）")
    overall_assessment_en: str = Field(default="Peer review completed.", description="Overall review feedback in English")
    overall_assessment_zh: str = Field(default="已完成綜合審查與實證缺陷檢驗。", description="綜合投稿就緒度評審意見（正體中文）")
    research_recommendations: List[ResearchRecommendation] = Field(
        default_factory=list,
        description="檢視上下文完整度與實驗數據支撐度，提出 2 至 4 點具備中英對照的實質補做實驗或統計方案"
    )
    revised_full_text: str = Field(default="", description="綜合各項最佳建議後的完整修訂後英文文章全文")
    issues: List[IssueItem] = Field(
        default_factory=list,
        description="逐句深度窮舉排查清單，列出 6 至 10 處包含邏輯瑕疵、推論斷層、修辭語氣、文法精確度的具體改進建議"
    )

# ==========================================
# 3. 線上 API 設定視窗
# ==========================================
class ApiSettingsDialog(QDialog):
    def __init__(self, parent=None, config: dict = None, is_dark: bool = False):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 線上 LLM API 設定")
        self.resize(520, 320)
        self.config = config or {}
        self.is_dark = is_dark
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        bg = "#0f172a" if self.is_dark else "#f8fafc"
        fg = "#f8fafc" if self.is_dark else "#0f172a"
        card_bg = "#1e293b" if self.is_dark else "#ffffff"
        border_col = "#334155" if self.is_dark else "#cbd5e1"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {fg}; }}
            QLabel {{ color: {fg}; font-size: 12px; }}
            QLineEdit, QComboBox {{
                background-color: {card_bg};
                color: {fg};
                border: 1px solid {border_col};
                border-radius: 5px;
                padding: 6px 8px;
                font-size: 12px;
            }}
            QPushButton {{
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)

        form = QFormLayout()
        form.setSpacing(10)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "DeepSeek (推薦學術推理，性價比首選)",
            "OpenAI (GPT-4o / o1)",
            "Google Gemini (gemini-1.5-pro / 2.0-flash)",
            "Groq (超高速推論)",
            "自訂 OpenAI 相容端點"
        ])
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        form.addRow("服務商預設:", self.preset_combo)

        self.url_edit = QLineEdit(self.config.get("api_url", "https://api.deepseek.com/v1"))
        form.addRow("API 端點 (Base URL):", self.url_edit)

        self.key_edit = QLineEdit(self.config.get("api_key", ""))
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("請輸入您的 API Key (如 sk-...)")
        form.addRow("API 金鑰 (API Key):", self.key_edit)

        self.model_edit = QLineEdit(self.config.get("api_model", "deepseek-chat"))
        self.model_edit.setPlaceholderText("例如: deepseek-chat, gpt-4o, gemini-1.5-pro")
        form.addRow("模型名稱 (Model Name):", self.model_edit)

        layout.addLayout(form)

        # 提示訊息
        info_lbl = QLabel("💡 支援任何相容 OpenAI 規格的線上服務。金鑰僅儲存於您本機設定檔，絕不上傳。")
        info_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        # 按鈕列
        btn_box = QHBoxLayout()
        self.test_btn = QPushButton("📡 測試連線")
        self.test_btn.setStyleSheet("background-color: #e2e8f0; color: #0f172a; border: 1px solid #cbd5e1;")
        self.test_btn.clicked.connect(self.test_connection)
        btn_box.addWidget(self.test_btn)

        btn_box.addStretch()

        self.save_btn = QPushButton("儲存設定")
        self.save_btn.setStyleSheet("background-color: #2563eb; color: #ffffff; border: 1px solid #1d4ed8;")
        self.save_btn.clicked.connect(self.save_and_close)
        btn_box.addWidget(self.save_btn)

        layout.addLayout(btn_box)

    def on_preset_changed(self, idx: int):
        presets = [
            ("https://api.deepseek.com/v1", "deepseek-chat"),
            ("https://api.openai.com/v1", "gpt-4o"),
            ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-1.5-pro"),
            ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
            ("https://api.openai.com/v1", "gpt-4o-mini")
        ]
        if idx < len(presets):
            url, model = presets[idx]
            self.url_edit.setText(url)
            self.model_edit.setText(model)

    def test_connection(self):
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        model = self.model_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "請先輸入 API Key。")
            return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("連線測試中...")
        QApplication.processEvents()

        endpoint = f"{url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello! Reply with 'OK' only."}],
            "max_tokens": 10
        }
        try:
            with httpx.Client(timeout=12.0) as client:
                res = client.post(endpoint, headers=headers, json=payload)
                if res.status_code == 200:
                    QMessageBox.information(self, "成功", f"✅ API 連線成功！服務商已正常響應。\n模型: {model}")
                else:
                    QMessageBox.critical(self, "失敗", f"❌ API 回應錯誤 ({res.status_code}):\n{res.text[:300]}")
        except Exception as e:
            QMessageBox.critical(self, "連線失敗", f"無法連接到該 API 端點:\n{e}")
        finally:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("📡 測試連線")

    def save_and_close(self):
        self.config["api_url"] = self.url_edit.text().strip()
        self.config["api_key"] = self.key_edit.text().strip()
        self.config["api_model"] = self.model_edit.text().strip()
        save_config(self.config)
        self.accept()

# ==========================================
# 3.2 本機 Ollama 環境檢測與模型管理精靈
# ==========================================
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
                    self.progress.emit(0, status or "正在處理中...")
            self.finished.emit(True, f"模型【{self.model_name}】下載與部署成功！")
        except Exception as e:
            self.finished.emit(False, f"模型拉取失敗: {str(e)}")

class OllamaEnvironmentDialog(QDialog):
    def __init__(self, parent=None, is_dark: bool = False):
        super().__init__(parent)
        self.setWindowTitle("📥 本機 Ollama 環境與模型管理精靈")
        self.resize(700, 590)
        self.is_dark = is_dark
        self.download_worker = None
        self.pull_worker = None
        self.models_updated = False
        self.installed_models = []
        self.init_ui()
        self.check_status()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        bg = "#0f172a" if self.is_dark else "#f8fafc"
        fg = "#f8fafc" if self.is_dark else "#0f172a"
        card_bg = "#1e293b" if self.is_dark else "#ffffff"
        border_col = "#334155" if self.is_dark else "#cbd5e1"
        sub_fg = "#94a3b8" if self.is_dark else "#64748b"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {fg}; }}
            QLabel {{ color: {fg}; }}
            QFrame[frameShape="1"] {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 8px;
                padding: 10px;
            }}
            QLineEdit {{
                background-color: {card_bg};
                color: {fg};
                border: 1px solid {border_col};
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 12px;
            }}
        """)

        # 標題區
        title_box = QVBoxLayout()
        h_title = QLabel("📥 本機 Ollama 環境與學術模型管理精靈")
        h_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        desc = QLabel("專為論文學者設計：一鍵自動檢測推論引擎、一鍵拉取國際頂刊審稿精選大語言模型。")
        desc.setStyleSheet(f"color: {sub_fg}; font-size: 11px;")
        desc.setWordWrap(True)
        title_box.addWidget(h_title)
        title_box.addWidget(desc)
        layout.addLayout(title_box)

        # 區塊 1：Ollama 執行環境狀態
        self.ollama_card = QFrame()
        self.ollama_card.setFrameShape(QFrame.Box)
        ollama_card_layout = QVBoxLayout(self.ollama_card)
        ollama_card_layout.setSpacing(8)

        card1_title = QLabel("1. Ollama 本機推論引擎狀態:")
        card1_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        ollama_card_layout.addWidget(card1_title)

        self.ollama_status_lbl = QLabel("正在檢測本機 Ollama 環境...")
        self.ollama_status_lbl.setFont(QFont("Segoe UI", 10))
        ollama_card_layout.addWidget(self.ollama_status_lbl)

        ollama_btn_box = QHBoxLayout()
        self.install_ollama_btn = QPushButton("🌐 一鍵下載並安裝 Ollama (官方安裝檔)")
        self.install_ollama_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: #ffffff;
                font-weight: bold; border-radius: 5px; padding: 6px 12px; font-size: 11px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.install_ollama_btn.clicked.connect(self.start_download_ollama)
        ollama_btn_box.addWidget(self.install_ollama_btn)

        self.start_service_btn = QPushButton("🚀 一鍵啟動 Ollama 服務")
        self.start_service_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669; color: #ffffff;
                font-weight: bold; border-radius: 5px; padding: 6px 12px; font-size: 11px;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        self.start_service_btn.clicked.connect(self.start_ollama_service)
        ollama_btn_box.addWidget(self.start_service_btn)

        self.recheck_btn = QPushButton("🔄 重新檢測")
        self.recheck_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {card_bg}; color: {fg};
                border: 1px solid {border_col}; border-radius: 5px; padding: 6px 12px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {'#334155' if self.is_dark else '#e2e8f0'}; }}
        """)
        self.recheck_btn.clicked.connect(self.check_status)
        ollama_btn_box.addWidget(self.recheck_btn)
        ollama_btn_box.addStretch()
        ollama_card_layout.addLayout(ollama_btn_box)

        layout.addWidget(self.ollama_card)

        # 區塊 2：學術推薦大語言模型下載管理
        self.model_card = QFrame()
        self.model_card.setFrameShape(QFrame.Box)
        model_layout = QVBoxLayout(self.model_card)
        model_layout.setSpacing(10)

        card2_title = QLabel("2. 學術同儕審查精選模型 (點擊一鍵安裝):")
        card2_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        model_layout.addWidget(card2_title)

        self.model_btns = {}
        models_data = [
            ("llama3.1:8b", "⚡ 輕量通用推薦 (約 4.7 GB)", "適合筆電 / 無獨立顯卡 / 8GB 記憶體，語法潤飾迅速有力"),
            ("qwen2.5:14b", "🏆 學術深度首選 (約 9.0 GB，★ 推薦)", "適合 16GB+ 記憶體 / 獨立顯卡，中英雙語邏輯極嚴謹，同儕審查最佳"),
            ("deepseek-r1:14b", "🔬 頂會旗艦推理 (約 9.0 GB)", "適合高階 GPU 工作站，強大思維鏈推論與實驗漏洞挖掘")
        ]

        for mod_id, title_str, sub_str in models_data:
            item_box = QHBoxLayout()
            info_layout = QVBoxLayout()
            m_t = QLabel(f"<b>{mod_id}</b> ─ {title_str}")
            m_t.setStyleSheet("font-size: 11px;")
            m_s = QLabel(sub_str)
            m_s.setStyleSheet(f"color: {sub_fg}; font-size: 10px;")
            info_layout.addWidget(m_t)
            info_layout.addWidget(m_s)
            item_box.addLayout(info_layout)

            btn = QPushButton("📥 下載此模型")
            btn.setFixedWidth(130)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#1e3a8a' if self.is_dark else '#e0e7ff'};
                    color: {'#93c5fd' if self.is_dark else '#3730a3'};
                    border: 1px solid {'#3b82f6' if self.is_dark else '#6366f1'};
                    border-radius: 5px; padding: 5px 8px; font-weight: bold; font-size: 11px;
                }}
                QPushButton:hover {{ background-color: {'#2563eb' if self.is_dark else '#c7d2fe'}; color: #ffffff; }}
                QPushButton:disabled {{ background-color: {'#1e293b' if self.is_dark else '#f1f5f9'}; color: {sub_fg}; border-color: {border_col}; }}
            """)
            btn.clicked.connect(lambda _, m=mod_id: self.start_pull_model(m))
            self.model_btns[mod_id] = btn
            item_box.addWidget(btn)
            model_layout.addLayout(item_box)

        # 自訂模型名稱下載
        custom_box = QHBoxLayout()
        self.custom_model_edit = QLineEdit()
        self.custom_model_edit.setPlaceholderText("或輸入自訂 Ollama 模型名稱 (例如: qwen2.5:7b 或 gemma4:e4b)")
        custom_box.addWidget(self.custom_model_edit)

        self.custom_pull_btn = QPushButton("📥 下載自訂模型")
        self.custom_pull_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {card_bg}; color: {fg};
                border: 1px solid {border_col}; border-radius: 5px; padding: 5px 12px; font-weight: 500; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {'#334155' if self.is_dark else '#e2e8f0'}; }}
        """)
        self.custom_pull_btn.clicked.connect(self.pull_custom_model)
        custom_box.addWidget(self.custom_pull_btn)
        model_layout.addLayout(custom_box)

        layout.addWidget(self.model_card)

        # 下載進度條與狀態文字
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #334155; border-radius: 5px; text-align: center; height: 16px;
            }
            QProgressBar::chunk { background-color: #3b82f6; border-radius: 4px; }
        """)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("font-size: 11px; color: #38bdf8;")
        layout.addWidget(self.progress_label)

        # 區塊 3：替代方案 (線上 API 提示)
        cloud_card = QFrame()
        cloud_card.setFrameShape(QFrame.Box)
        cloud_layout = QHBoxLayout(cloud_card)
        cloud_info = QLabel("💡 <b>電腦硬體無獨立顯卡？</b> 您也可以隨時在工具列切換為「線上 API」，免下載數 GB 模型即可直通 DeepSeek 或 GPT-4o 頂級審查。")
        cloud_info.setStyleSheet(f"color: {sub_fg}; font-size: 11px;")
        cloud_info.setWordWrap(True)
        cloud_layout.addWidget(cloud_info)

        cloud_btn = QPushButton("⚙️ 線上 API 設定")
        cloud_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {card_bg}; color: {fg};
                border: 1px solid {border_col}; border-radius: 5px; padding: 5px 10px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {'#334155' if self.is_dark else '#e2e8f0'}; }}
        """)
        cloud_btn.clicked.connect(self.open_cloud_settings)
        cloud_layout.addWidget(cloud_btn)
        layout.addWidget(cloud_card)

        # 底部關閉按鈕
        bottom_box = QHBoxLayout()
        bottom_box.addStretch()
        close_btn = QPushButton("完成並返回主畫面")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: #ffffff;
                font-weight: bold; border-radius: 5px; padding: 7px 16px; font-size: 12px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        close_btn.clicked.connect(self.accept)
        bottom_box.addWidget(close_btn)
        layout.addLayout(bottom_box)

    def check_status(self):
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
            self.ollama_status_lbl.setText("❌ <b>尚未偵測到 Ollama 程式</b>：請點擊下方按鈕自動下載官方安裝程式。")
            self.ollama_status_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.install_ollama_btn.setVisible(True)
            self.start_service_btn.setVisible(False)
            self.model_card.setEnabled(False)
        elif not is_running:
            self.ollama_status_lbl.setText(f"⚠️ <b>Ollama 已安裝於本機，但背景服務尚未啟動</b> (路徑: {ollama_exec})")
            self.ollama_status_lbl.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.install_ollama_btn.setVisible(False)
            self.start_service_btn.setVisible(True)
            self.model_card.setEnabled(False)
        else:
            self.ollama_status_lbl.setText(f"✅ <b>Ollama 服務運作正常 (Port 11434 已連線)</b> ─ 本機推論引擎已準備就緒。")
            self.ollama_status_lbl.setStyleSheet("color: #10b981; font-size: 11px;")
            self.install_ollama_btn.setVisible(False)
            self.start_service_btn.setVisible(False)
            self.model_card.setEnabled(True)
            self.refresh_models()

    def start_ollama_service(self):
        which_path = shutil.which("ollama")
        appdata_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        exec_path = which_path or appdata_path
        if not exec_path or not os.path.exists(exec_path):
            QMessageBox.warning(self, "錯誤", "找不到 ollama.exe 執行檔。")
            return
        try:
            creation_flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
            subprocess.Popen([exec_path, "serve"], creationflags=creation_flags)
            self.ollama_status_lbl.setText("正在啟動 Ollama 服務...")
            QTimer.singleShot(2500, self.check_status)
        except Exception as e:
            QMessageBox.critical(self, "啟動失敗", f"無法啟動 Ollama 服務: {e}")

    def start_download_ollama(self):
        self.install_ollama_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("正在下載 Ollama 官方安裝程式...")

        self.download_worker = OllamaDownloadWorker()
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.progress_label.setText(msg)

    def on_download_finished(self, success: bool, msg: str, path: str):
        self.install_ollama_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        if success and path and os.path.exists(path):
            QMessageBox.information(
                self, "下載完成",
                "已成功下載 Ollama 安裝程式！即將為您啟動安裝精靈。\n請在安裝完成後回到本視窗點擊「重新檢測」。"
            )
            subprocess.Popen([path])
        else:
            QMessageBox.critical(self, "下載失敗", f"無法下載 Ollama: {msg}")

    def refresh_models(self):
        try:
            res = ollama.list()
            self.installed_models = []
            if hasattr(res, 'models'):
                for m in res.models:
                    n = getattr(m, 'model', '') or getattr(m, 'name', '')
                    if n:
                        self.installed_models.append(n)
            elif isinstance(res, dict) and 'models' in res:
                for m in res['models']:
                    n = m.get('name') or m.get('model')
                    if n:
                        self.installed_models.append(n)

            for mod_id, btn in self.model_btns.items():
                is_inst = any(mod_id in m for m in self.installed_models)
                if is_inst:
                    btn.setText("✅ 已就緒")
                    btn.setEnabled(False)
                else:
                    btn.setText("📥 下載此模型")
                    btn.setEnabled(True)
        except Exception:
            pass

    def start_pull_model(self, model_name: str):
        self.set_ui_busy(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText(f"開始準備下載模型【{model_name}】...")

        self.pull_worker = ModelPullWorker(model_name)
        self.pull_worker.progress.connect(self.on_pull_progress)
        self.pull_worker.finished.connect(lambda s, m: self.on_pull_finished(s, m, model_name))
        self.pull_worker.start()

    def pull_custom_model(self):
        m_name = self.custom_model_edit.text().strip()
        if not m_name:
            QMessageBox.warning(self, "提示", "請輸入欲下載的 Ollama 模型名稱。")
            return
        self.start_pull_model(m_name)

    def on_pull_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.progress_label.setText(msg)

    def on_pull_finished(self, success: bool, msg: str, model_name: str):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        if success:
            self.models_updated = True
            self.refresh_models()
            QMessageBox.information(self, "下載成功", f"🎉 模型【{model_name}】已成功部署至本機！\n現在可直接在主畫面進行學術論文審查。")
        else:
            QMessageBox.critical(self, "下載失敗", f"下載模型時發生錯誤:\n{msg}")

    def set_ui_busy(self, busy: bool):
        for btn in self.model_btns.values():
            btn.setEnabled(not busy)
        self.custom_pull_btn.setEnabled(not busy)
        self.custom_model_edit.setEnabled(not busy)
        self.recheck_btn.setEnabled(not busy)

    def open_cloud_settings(self):
        if hasattr(self.parent(), "open_api_settings"):
            self.parent().open_api_settings()

# ==========================================
# 3.3 軟體線上檢查更新與一鍵升級模組
# ==========================================
def parse_version_tuple(v_str: str) -> tuple:
    nums = re.findall(r"\d+", v_str)
    return tuple(map(int, nums)) if nums else (0, 0, 0)

class UpdateCheckWorker(QThread):
    check_finished = Signal(bool, str, str, str, str)  # has_update, latest_ver, changelog, download_url, err_msg

    def __init__(self, update_url: str):
        super().__init__()
        self.update_url = update_url

    def run(self):
        try:
            if self.update_url.startswith("file://") or os.path.exists(self.update_url):
                local_path = self.update_url.replace("file://", "").lstrip("/")
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                resp = httpx.get(self.update_url, timeout=8.0, follow_redirects=True)
                if resp.status_code != 200:
                    self.check_finished.emit(False, "", "", "", f"伺服器回應異常 (HTTP {resp.status_code})")
                    return
                data = resp.json()

            latest_ver = data.get("latest_version", "").strip()
            changelog = data.get("changelog", "").strip()
            download_url = data.get("download_url", "").strip()

            cur_tuple = parse_version_tuple(APP_VERSION)
            latest_tuple = parse_version_tuple(latest_ver)
            has_update = latest_tuple > cur_tuple

            self.check_finished.emit(has_update, latest_ver, changelog, download_url, "")
        except Exception as e:
            self.check_finished.emit(False, "", "", "", f"檢查更新失敗: {str(e)}")

class UpdateDownloadWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, download_url: str):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            dest_path = os.path.join(tempfile.gettempdir(), "LibreLlamaReviewer_Setup_Update.exe")
            with httpx.stream("GET", self.download_url, follow_redirects=True, timeout=180.0) as resp:
                if resp.status_code != 200:
                    self.finished.emit(False, f"下載伺服器回應錯誤 (HTTP {resp.status_code})")
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
                                self.progress.emit(pct, f"下載更新中: {mb_done:.1f} MB / {mb_tot:.1f} MB ({pct}%)")
                            else:
                                mb_done = downloaded / (1024 * 1024)
                                self.progress.emit(0, f"已下載: {mb_done:.1f} MB")
            self.finished.emit(True, dest_path)
        except Exception as e:
            self.finished.emit(False, f"下載失敗: {str(e)}")

class UpdateDialog(QDialog):
    def __init__(self, parent=None, is_dark: bool = False, config: dict = None):
        super().__init__(parent)
        self.setWindowTitle("🚀 軟體版本與線上更新")
        self.resize(560, 420)
        self.is_dark = is_dark
        self.config = config or {}
        self.check_worker = None
        self.download_worker = None
        self.latest_download_url = ""
        self.init_ui()
        self.start_check()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        bg = "#0f172a" if self.is_dark else "#f8fafc"
        fg = "#f8fafc" if self.is_dark else "#0f172a"
        card_bg = "#1e293b" if self.is_dark else "#ffffff"
        border_col = "#334155" if self.is_dark else "#cbd5e1"
        sub_fg = "#94a3b8" if self.is_dark else "#64748b"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {fg}; }}
            QLabel {{ color: {fg}; }}
            QTextBrowser {{
                background-color: {card_bg}; color: {fg};
                border: 1px solid {border_col}; border-radius: 6px; padding: 8px; font-size: 11px;
            }}
            QLineEdit {{
                background-color: {card_bg}; color: {fg};
                border: 1px solid {border_col}; border-radius: 5px; padding: 4px 8px; font-size: 11px;
            }}
        """)

        status_card = QFrame()
        status_card.setStyleSheet(f"background-color: {card_bg}; border: 1px solid {border_col}; border-radius: 8px; padding: 10px;")
        s_layout = QVBoxLayout(status_card)

        cur_v_lbl = QLabel(f"<b>目前已安裝版本:</b> v{APP_VERSION}")
        cur_v_lbl.setFont(QFont("Segoe UI", 11))
        s_layout.addWidget(cur_v_lbl)

        self.status_msg_lbl = QLabel("正在連線檢查最新版本資訊...")
        self.status_msg_lbl.setStyleSheet(f"color: {sub_fg}; font-size: 11px;")
        s_layout.addWidget(self.status_msg_lbl)

        layout.addWidget(status_card)

        cl_title = QLabel("更新日誌與新版異動 (Release Notes):")
        cl_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(cl_title)

        self.changelog_browser = QTextBrowser()
        self.changelog_browser.setPlaceholderText("檢查更新中...")
        layout.addWidget(self.changelog_browser)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.progress_lbl = QLabel("")
        self.progress_lbl.setVisible(False)
        self.progress_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        layout.addWidget(self.progress_lbl)

        adv_box = QHBoxLayout()
        url_lbl = QLabel("更新伺服器端點:")
        url_lbl.setStyleSheet(f"color: {sub_fg}; font-size: 10px;")
        adv_box.addWidget(url_lbl)

        saved_url = self.config.get("update_url", DEFAULT_UPDATE_URL)
        self.url_edit = QLineEdit(saved_url)
        adv_box.addWidget(self.url_edit)
        layout.addLayout(adv_box)

        btn_box = QHBoxLayout()
        self.recheck_btn = QPushButton("🔄 重新檢查")
        self.recheck_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {card_bg}; color: {fg}; border: 1px solid {border_col};
                border-radius: 5px; padding: 6px 14px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {'#334155' if self.is_dark else '#e2e8f0'}; }}
        """)
        self.recheck_btn.clicked.connect(self.start_check)
        btn_box.addWidget(self.recheck_btn)

        btn_box.addStretch()

        self.download_btn = QPushButton("📥 立即下載並安裝更新")
        self.download_btn.setEnabled(False)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: #ffffff; font-weight: bold;
                border-radius: 5px; padding: 6px 16px; font-size: 11px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #475569; color: #94a3b8; }
        """)
        self.download_btn.clicked.connect(self.start_download)
        btn_box.addWidget(self.download_btn)

        close_btn = QPushButton("關閉")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {card_bg}; color: {fg}; border: 1px solid {border_col};
                border-radius: 5px; padding: 6px 14px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {'#334155' if self.is_dark else '#e2e8f0'}; }}
        """)
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(close_btn)

        layout.addLayout(btn_box)

    def start_check(self):
        url = self.url_edit.text().strip()
        self.config["update_url"] = url
        save_config(self.config)

        self.recheck_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.status_msg_lbl.setText("正在查詢最新版本資訊...")
        self.status_msg_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        self.changelog_browser.clear()

        self.check_worker = UpdateCheckWorker(url)
        self.check_worker.check_finished.connect(self.on_check_finished)
        self.check_worker.start()

    def on_check_finished(self, has_update: bool, latest_ver: str, changelog: str, download_url: str, err_msg: str):
        self.recheck_btn.setEnabled(True)
        if err_msg:
            self.status_msg_lbl.setText(f"⚠️ {err_msg}")
            self.status_msg_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.changelog_browser.setPlainText("無法連線至更新伺服器。若您的機構使用特定內網，可於下方修改更新端點。")
            return

        self.latest_download_url = download_url
        if has_update:
            self.status_msg_lbl.setText(f"🎉 發現新版本：<b>v{latest_ver}</b> (建議立即升級)")
            self.status_msg_lbl.setStyleSheet("color: #10b981; font-size: 11px;")
            self.changelog_browser.setPlainText(changelog)
            self.download_btn.setEnabled(bool(download_url))
        else:
            self.status_msg_lbl.setText(f"✨ 您的軟體已是最新版本 (v{APP_VERSION})！無需更新。")
            self.status_msg_lbl.setStyleSheet("color: #10b981; font-size: 11px;")
            self.changelog_browser.setPlainText(changelog or "目前版本已具備最新學術審查、中英雙語實質建議與雙模推論引擎能力。")

    def start_download(self):
        if not self.latest_download_url:
            return
        self.recheck_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_lbl.setVisible(True)
        self.progress_lbl.setText("準備下載新版安裝檔...")

        self.download_worker = UpdateDownloadWorker(self.latest_download_url)
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.progress_lbl.setText(msg)

    def on_download_finished(self, success: bool, path_or_err: str):
        self.progress_bar.setVisible(False)
        self.progress_lbl.setVisible(False)
        self.recheck_btn.setEnabled(True)
        if success and os.path.exists(path_or_err):
            reply = QMessageBox.question(
                self, "下載完成",
                "🎉 新版安裝程式已成功下載！\n\n是否立即啟動安裝精靈自動升級？（此操作將自動關閉當前工作台）",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                subprocess.Popen([path_or_err])
                QApplication.quit()
        else:
            QMessageBox.critical(self, "更新下載失敗", f"無法下載更新檔案:\n{path_or_err}")
            self.download_btn.setEnabled(True)

# ==========================================
# 4. 背景工作線程 (支援在地 Ollama 或線上 API)
# ==========================================
class ReviewWorker(QThread):
    finished = Signal(AcademicReviewReport)
    error = Signal(str)
    chunk_received = Signal(str, int)

    def __init__(self, text: str, engine_mode: str, model_name: str, api_config: dict):
        super().__init__()
        self.text = text
        self.engine_mode = engine_mode
        self.model_name = model_name
        self.api_config = api_config

    def run(self):
        system_prompt = """你是一名世界頂級國際期刊（如 Nature, IEEE, Science, ACM, Elsevier）以嚴苛批判著稱的資深同行評審員（Reviewer #2）兼學術英文資深編輯。
請注意：本系統使用者為【正體中文（繁體中文，臺灣學術慣用語彙）】使用者，所有中文說明必須使用正體中文，切勿使用簡體字。

請對輸入的學術英文進行兩大核心維度的【深度極限審查】：

==================================================
維度一：【上下文敘述完整性與實證補強建議 (research_recommendations)】
==================================================
請跳脫純文字表面，穿透至該段落背後的【科學證據鏈與實驗設計】：
1. 檢視作者的宣稱是否缺乏足夠的實驗或數據支撐？
2. 是否將相關性（Correlation）輕率斷言為因果性（Causation），而未控制環境或硬體等混雜變因（Confounding factors）？
3. 是否缺乏關鍵的消融實驗（Ablation studies）、顯著性檢定（p-value, effect size, confidence intervals）、基準模型比較（Baselines）或代表性負載壓力測試？
4. 請列出 2 至 4 點【實質研究/實驗補強方案】。
【極重要要求】：實證補強建議的每一項目，必須具備【中英雙語對照】：
- gap_identified_zh (中文論述缺失) 與 gap_identified_en (English Gap)
- concrete_proposal_zh (中文具體補做方案) 與 concrete_proposal_en (English Proposal)
- impact_on_acceptance_zh (中文投稿防禦效益) 與 impact_on_acceptance_en (English Defense Impact)

==================================================
維度二：【逐句穿透式窮舉審查與改寫 (issues)】
==================================================
【嚴格徹底度要求（重點突破：絕不可僅抓 2~3 個問題敷衍了事）】
一段 150~300 字的草稿必然隱藏諸多不成熟之處。你【必須】進行【逐句深度掃描（Sentence-by-sentence scrutiny）】，深入挖掘出 6 至 10 個具體的改進點！絕不允許僅回傳 2-3 處！
審查面向必須全面覆蓋：
1. 邏輯矛盾（Logic Error）：隱含假設破綻、論點前後不一致。
2. 推論缺陷（Flawed Deduction）：推論跳躍、過度宣稱（Overclaiming）、因果倒置。
3. 文法與句構（Grammar & Mechanics）：被動態過度濫用、懸垂修飾、主謂不合、時態跳躍。
4. 修辭與學術風格（Rhetorical Defect）：缺乏學術謙抑（Hedging）、非正式用語、句式冗長、銜接詞過時。

對每一處問題：
- 提供原句正體中文翻譯與文意判斷 (meaning_analysis_zh)。
- 提供中英雙語 Reviewer 專業評語 (reviewer_comment_en 與 reviewer_comment_zh)。
- 提供至少 2 個不同學術風格的改寫選項 (revision_options)。

【格式嚴格規範】：在 JSON 字串內容中，若需引用英文詞彙或原句，請務必使用全形引號「」或『』，切勿在字串內部直接使用未跳脫之半形雙引號 \"，以確保 JSON 格式絕對合法。
請確保輸出為符合所提供 Schema 的純 JSON 格式。"""

        full_content = ""
        chunk_count = 0

        try:
            if self.engine_mode == "ollama":
                # 本機 Ollama 串流調用
                response_stream = ollama.chat(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Please critically and exhaustively review the following manuscript text:\n\n{self.text}"}
                    ],
                    format=AcademicReviewReport.model_json_schema(),
                    options={
                        "temperature": 0.35,
                        "num_ctx": 16384,
                        "num_predict": -1
                    },
                    stream=True
                )
                for chunk in response_stream:
                    delta = chunk.get('message', {}).get('content', '')
                    if delta:
                        full_content += delta
                        chunk_count += 1
                        self.chunk_received.emit(delta, chunk_count)
            else:
                # 線上 OpenAI 相容 API 串流調用 (DeepSeek / OpenAI / Gemini / etc.)
                api_url = self.api_config.get("api_url", "https://api.deepseek.com/v1").rstrip('/')
                api_key = self.api_config.get("api_key", "").strip()
                model = self.api_config.get("api_model", "deepseek-chat").strip()
                if not api_key:
                    raise ValueError("未設定線上 API Key，請點擊上方「⚙️ API 設定」輸入金鑰。")

                endpoint = f"{api_url}/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                schema_json = json.dumps(AcademicReviewReport.model_json_schema(), ensure_ascii=False)
                prompt_with_schema = f"{system_prompt}\n\nYou MUST respond strictly in valid JSON matching this JSON Schema:\n{schema_json}"

                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt_with_schema},
                        {"role": "user", "content": f"Please critically and exhaustively review the following manuscript text:\n\n{self.text}"}
                    ],
                    "temperature": 0.35,
                    "stream": True,
                    "response_format": {"type": "json_object"}
                }

                with httpx.Client(timeout=120.0) as client:
                    with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            err_body = response.read().decode('utf-8', errors='ignore')
                            raise ValueError(f"線上 API 呼叫失敗 ({response.status_code}):\n{err_body}")

                        for line in response.iter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    c_json = json.loads(data_str)
                                    delta = c_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta:
                                        full_content += delta
                                        chunk_count += 1
                                        self.chunk_received.emit(delta, chunk_count)
                                except Exception:
                                    continue

            # --- 清洗與雙重容錯解析 ---
            raw_content = full_content.strip()
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            elif raw_content.startswith("```"):
                raw_content = raw_content[3:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
            raw_content = raw_content.strip()

            data = None
            try:
                data = json.loads(raw_content, strict=False)
            except Exception:
                try:
                    repaired = json_repair.repair_json(raw_content, return_objects=True)
                    if isinstance(repaired, dict):
                        data = repaired
                except Exception:
                    pass

            if not data or not isinstance(data, dict):
                raise ValueError(f"無法解析模型輸出的 JSON 結構。請嘗試縮短輸入段落或重新審查。\n輸出結尾片段:\n{raw_content[-200:]}")

            # 數據搶救與寬容填充
            valid_issues = []
            for raw_issue in data.get('issues', []):
                if not isinstance(raw_issue, dict) or not raw_issue.get('original_text'):
                    continue
                if not raw_issue.get('category'):
                    raw_issue['category'] = 'Rhetorical Defect'
                if not raw_issue.get('severity'):
                    raw_issue['severity'] = 'Major'
                if not raw_issue.get('meaning_analysis_zh'):
                    raw_issue['meaning_analysis_zh'] = '學術語義精確度建議'
                if not raw_issue.get('reviewer_comment_en'):
                    raw_issue['reviewer_comment_en'] = 'Reviewer suggestion'
                if not raw_issue.get('reviewer_comment_zh'):
                    raw_issue['reviewer_comment_zh'] = '審查建議'
                if not raw_issue.get('revision_options'):
                    raw_issue['revision_options'] = [{
                        "style_label": "標準學術修改",
                        "revised_text": raw_issue.get('original_text', ''),
                        "rationale_zh": "提升學術嚴謹度"
                    }]
                try:
                    valid_issues.append(IssueItem(**raw_issue))
                except Exception:
                    continue
            data['issues'] = valid_issues

            valid_recs = []
            for raw_rec in data.get('research_recommendations', []):
                if not isinstance(raw_rec, dict):
                    continue
                # 兼容性處理：若模型只輸出單語字段，自動填補中英雙語
                if "gap_identified" in raw_rec and not raw_rec.get("gap_identified_zh"):
                    raw_rec["gap_identified_zh"] = raw_rec["gap_identified"]
                    raw_rec["gap_identified_en"] = raw_rec["gap_identified"]
                if "concrete_proposal" in raw_rec and not raw_rec.get("concrete_proposal_zh"):
                    raw_rec["concrete_proposal_zh"] = raw_rec["concrete_proposal"]
                    raw_rec["concrete_proposal_en"] = raw_rec["concrete_proposal"]
                if "impact_on_acceptance" in raw_rec and not raw_rec.get("impact_on_acceptance_zh"):
                    raw_rec["impact_on_acceptance_zh"] = raw_rec["impact_on_acceptance"]
                    raw_rec["impact_on_acceptance_en"] = raw_rec["impact_on_acceptance"]

                if not raw_rec.get('gap_identified_zh') and not raw_rec.get('gap_identified_en'):
                    continue
                try:
                    valid_recs.append(ResearchRecommendation(**raw_rec))
                except Exception:
                    continue
            data['research_recommendations'] = valid_recs

            if not data.get('article_gist_zh'):
                data['article_gist_zh'] = '本草稿探討特定學術主題，已完成同儕審查診斷。'
            if not data.get('overall_assessment_en'):
                data['overall_assessment_en'] = 'Comprehensive peer review completed.'
            if not data.get('overall_assessment_zh'):
                data['overall_assessment_zh'] = '已完成深度同儕審查與實證缺陷檢驗。'
            if not data.get('revised_full_text'):
                data['revised_full_text'] = self.text

            report = AcademicReviewReport(**data)
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))

# ==========================================
# 5. 審查問題卡片組件 (支援中英對照與深淺色主題)
# ==========================================
class ResearchRecommendationCard(QFrame):
    def __init__(self, rec: ResearchRecommendation, is_dark: bool = False):
        super().__init__()
        self.rec = rec
        self.is_dark = is_dark
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)

        if self.is_dark:
            self.setStyleSheet("""
                ResearchRecommendationCard {
                    background-color: #1e1b4b;
                    border: 1px solid #4338ca;
                    border-left: 4px solid #818cf8;
                    border-radius: 8px;
                    margin-bottom: 10px;
                }
                ResearchRecommendationCard:hover { border-color: #a5b4fc; }
            """)
            text_title = "#f8fafc"
            box_bg = "#0f172a"
            box_border = "#312e81"
            zh_color = "#e0e7ff"
            en_color = "#a5b4fc"
        else:
            self.setStyleSheet("""
                ResearchRecommendationCard {
                    background-color: #faf5ff;
                    border: 1px solid #d8b4fe;
                    border-left: 4px solid #7c3aed;
                    border-radius: 8px;
                    margin-bottom: 10px;
                }
                ResearchRecommendationCard:hover { border-color: #9333ea; }
            """)
            text_title = "#0f172a"
            box_bg = "#ffffff"
            box_border = "#e9d5ff"
            zh_color = "#3b0764"
            en_color = "#6b21a8"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # 頂部動作類型與重要度
        top_row = QHBoxLayout()
        type_badge = QLabel(f" 🧪 {self.rec.action_type} ")
        type_badge.setStyleSheet("background-color: #ede9fe; color: #6d28d9; font-weight: bold; border-radius: 4px; font-size: 11px; padding: 2px 6px;")

        severity_colors = {
            "Must Address (必補/致命缺陷)": ("#fee2e2", "#991b1b"),
            "Strongly Recommended (強烈建議補強)": ("#ffedd5", "#9a3412"),
            "Optional (可選加分項)": ("#f1f5f9", "#475569")
        }
        s_bg, s_fg = severity_colors.get(self.rec.severity, ("#ede9fe", "#6d28d9"))
        sev_badge = QLabel(f" {self.rec.severity} ")
        sev_badge.setStyleSheet(f"background-color: {s_bg}; color: {s_fg}; font-weight: bold; border-radius: 4px; font-size: 11px; padding: 2px 6px;")

        top_row.addWidget(type_badge)
        top_row.addWidget(sev_badge)
        top_row.addStretch()
        layout.addLayout(top_row)

        # 1. 缺失分析 (中英對照)
        gap_box = QFrame()
        gap_box.setStyleSheet(f"background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 6px; padding: 6px;")
        g_layout = QVBoxLayout(gap_box)
        g_layout.setContentsMargins(8, 6, 8, 6)
        g_layout.setSpacing(3)

        g_title = QLabel(f"<b>⚠️ 上下文與論點缺失分析 (Evidence Gap):</b>")
        g_title.setStyleSheet(f"font-size: 12px; color: {text_title};")
        g_layout.addWidget(g_title)

        gap_zh = QLabel(f"<b>🇹🇼 中文：</b><span style='color: {zh_color};'>{html.escape(self.rec.gap_identified_zh or self.rec.gap_identified_en)}</span>")
        gap_zh.setWordWrap(True)
        gap_zh.setStyleSheet("font-size: 12px;")
        g_layout.addWidget(gap_zh)

        if self.rec.gap_identified_en and self.rec.gap_identified_en != self.rec.gap_identified_zh:
            gap_en = QLabel(f"<b>🇺🇸 EN：</b><span style='color: {en_color}; font-style: italic;'>{html.escape(self.rec.gap_identified_en)}</span>")
            gap_en.setWordWrap(True)
            gap_en.setStyleSheet("font-size: 11px;")
            g_layout.addWidget(gap_en)

        layout.addWidget(gap_box)

        # 2. 建議補做方案 (中英對照)
        prop_box = QFrame()
        prop_box.setStyleSheet(f"background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 6px; padding: 6px;")
        p_layout = QVBoxLayout(prop_box)
        p_layout.setContentsMargins(8, 6, 8, 6)
        p_layout.setSpacing(3)

        p_title = QLabel(f"<b>💡 建議補做方案 (Proposed Protocol / Experiments):</b>")
        p_title.setStyleSheet(f"font-size: 12px; color: {text_title};")
        p_layout.addWidget(p_title)

        prop_zh = QLabel(f"<b>🇹🇼 中文：</b><span style='color: {zh_color};'>{html.escape(self.rec.concrete_proposal_zh or self.rec.concrete_proposal_en)}</span>")
        prop_zh.setWordWrap(True)
        prop_zh.setStyleSheet("font-size: 12px;")
        p_layout.addWidget(prop_zh)

        if self.rec.concrete_proposal_en and self.rec.concrete_proposal_en != self.rec.concrete_proposal_zh:
            prop_en = QLabel(f"<b>🇺🇸 EN：</b><span style='color: {en_color}; font-style: italic;'>{html.escape(self.rec.concrete_proposal_en)}</span>")
            prop_en.setWordWrap(True)
            prop_en.setStyleSheet("font-size: 11px;")
            p_layout.addWidget(prop_en)

        layout.addWidget(prop_box)

        # 3. 投稿防禦效益 (中英對照)
        impact_box = QFrame()
        impact_box.setStyleSheet(f"background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 6px; padding: 6px;")
        i_layout = QVBoxLayout(impact_box)
        i_layout.setContentsMargins(8, 6, 8, 6)
        i_layout.setSpacing(3)

        i_title = QLabel(f"<b>🛡️ 投稿防禦效益 (Defense Impact):</b>")
        i_title.setStyleSheet(f"font-size: 12px; color: {text_title};")
        i_layout.addWidget(i_title)

        impact_zh = QLabel(f"<b>🇹🇼 中文：</b><span style='color: {zh_color};'>{html.escape(self.rec.impact_on_acceptance_zh or self.rec.impact_on_acceptance_en)}</span>")
        impact_zh.setWordWrap(True)
        impact_zh.setStyleSheet("font-size: 12px;")
        i_layout.addWidget(impact_zh)

        if self.rec.impact_on_acceptance_en and self.rec.impact_on_acceptance_en != self.rec.impact_on_acceptance_zh:
            impact_en = QLabel(f"<b>🇺🇸 EN：</b><span style='color: {en_color}; font-style: italic;'>{html.escape(self.rec.impact_on_acceptance_en)}</span>")
            impact_en.setWordWrap(True)
            impact_en.setStyleSheet("font-size: 11px;")
            i_layout.addWidget(impact_en)

        layout.addWidget(impact_box)


class IssueCard(QFrame):
    def __init__(self, issue_idx: int, issue: IssueItem, on_option_selected_callback, is_dark: bool = False):
        super().__init__()
        self.issue_idx = issue_idx
        self.issue = issue
        self.on_option_selected_callback = on_option_selected_callback
        self.selected_option_idx: int = 0
        self.option_buttons: List[QPushButton] = []
        self.is_dark = is_dark
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)

        if self.is_dark:
            self.setStyleSheet("""
                IssueCard {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    margin-bottom: 12px;
                }
                IssueCard:hover { border-color: #60a5fa; }
            """)
            card_bg = "#0f172a"
            card_border = "#334155"
            text_primary = "#f8fafc"
            text_secondary = "#cbd5e1"
            comment_box_bg = "#064e3b"
            comment_box_border = "#059669"
            zh_color = "#a7f3d0"
            en_color = "#6ee7b7"
        else:
            self.setStyleSheet("""
                IssueCard {
                    background-color: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    margin-bottom: 12px;
                }
                IssueCard:hover { border-color: #3b82f6; }
            """)
            card_bg = "#f8fafc"
            card_border = "#e2e8f0"
            text_primary = "#0f172a"
            text_secondary = "#334155"
            comment_box_bg = "#f0fdf4"
            comment_box_border = "#bbf7d0"
            zh_color = "#14532d"
            en_color = "#166534"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        color_map = {
            "Logic Error": ("#fef3c7", "#92400e", "🟡 邏輯矛盾"),
            "Flawed Deduction": ("#ffedd5", "#9a3412", "🟠 推論缺陷 / 過度宣稱"),
            "Grammar & Mechanics": ("#fee2e2", "#991b1b", "🔴 文法與句構"),
            "Rhetorical Defect": ("#dbeafe", "#1e40af", "🔵 修辭與風格")
        }
        bg_col, txt_col, badge_text = color_map.get(
            self.issue.category, ("#f1f5f9", "#334155", self.issue.category_zh or self.issue.category)
        )

        top_row = QHBoxLayout()
        category_badge = QLabel(f" {badge_text} ")
        category_badge.setStyleSheet(f"background-color: {bg_col}; color: {txt_col}; font-weight: bold; border-radius: 4px; font-size: 11px; padding: 2px 6px;")
        
        severity_map = {"Critical": "嚴重缺陷 (Critical)", "Major": "主要問題 (Major)", "Minor": "細微瑕疵 (Minor)"}
        severity_label = QLabel(f"嚴重度: {severity_map.get(self.issue.severity, self.issue.severity)}")
        severity_label.setStyleSheet("color: #64748b; font-size: 11px;")
        
        top_row.addWidget(category_badge)
        top_row.addStretch()
        top_row.addWidget(severity_label)
        layout.addLayout(top_row)

        meaning_box = QFrame()
        meaning_box.setStyleSheet(f"background-color: {card_bg}; border: 1px solid {card_border}; border-radius: 6px; padding: 6px;")
        meaning_layout = QVBoxLayout(meaning_box)
        meaning_layout.setContentsMargins(8, 6, 8, 6)
        meaning_layout.setSpacing(4)

        orig_label = QLabel(f"<b>📌 原文片段：</b><span style='color: {text_primary};'>\"{html.escape(self.issue.original_text)}\"</span>")
        orig_label.setWordWrap(True)
        orig_label.setStyleSheet(f"color: {text_primary}; font-size: 12px;")
        meaning_layout.addWidget(orig_label)

        trans_label = QLabel(f"<b>🇹🇼 文意解析與翻譯：</b><span style='color: {text_secondary};'>{html.escape(self.issue.meaning_analysis_zh)}</span>")
        trans_label.setWordWrap(True)
        trans_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
        meaning_layout.addWidget(trans_label)
        layout.addWidget(meaning_box)

        comment_box = QFrame()
        comment_box.setStyleSheet(f"background-color: {comment_box_bg}; border: 1px solid {comment_box_border}; border-left: 4px solid #10b981; border-radius: 4px;")
        comment_layout = QVBoxLayout(comment_box)
        comment_layout.setContentsMargins(8, 6, 8, 6)
        comment_layout.setSpacing(4)

        comment_zh = QLabel(f"<b>🇹🇼 審稿意見 (中文)：</b><span style='color: {zh_color};'>{html.escape(self.issue.reviewer_comment_zh)}</span>")
        comment_zh.setWordWrap(True)
        comment_zh.setStyleSheet("font-size: 12px;")
        comment_layout.addWidget(comment_zh)

        comment_en = QLabel(f"<b>🇺🇸 Reviewer Comment (EN)：</b><span style='color: {en_color}; font-style: italic;'>{html.escape(self.issue.reviewer_comment_en)}</span>")
        comment_en.setWordWrap(True)
        comment_en.setStyleSheet("font-size: 11px;")
        comment_layout.addWidget(comment_en)
        layout.addWidget(comment_box)

        opt_title = QLabel("💡 建議修改選項 (點擊切換，右側修改全文將即時連動):")
        opt_title.setStyleSheet("font-weight: bold; color: #10b981; font-size: 12px; margin-top: 4px;")
        layout.addWidget(opt_title)

        for idx, opt in enumerate(self.issue.revision_options):
            opt_frame = QFrame()
            opt_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {card_bg};
                    border: 1px solid {card_border};
                    border-radius: 6px;
                }}
            """)
            opt_layout = QVBoxLayout(opt_frame)
            opt_layout.setContentsMargins(10, 8, 10, 8)
            opt_layout.setSpacing(4)

            opt_header = QHBoxLayout()
            label_badge = QLabel(f"選項 {chr(65 + idx)}：{html.escape(opt.style_label)}")
            label_badge.setStyleSheet("font-weight: bold; color: #10b981; font-size: 11px;")
            opt_header.addWidget(label_badge)
            opt_header.addStretch()

            is_active = (idx == 0)
            apply_btn = QPushButton("已套用 ✓" if is_active else "切換至此選項")
            self.style_button(apply_btn, is_active)
            apply_btn.clicked.connect(lambda checked, o_idx=idx: self.select_option(o_idx))
            self.option_buttons.append(apply_btn)
            opt_header.addWidget(apply_btn)
            opt_layout.addLayout(opt_header)

            rev_text_lbl = QLabel(f"<b>修訂句：</b><span style='color: #10b981;'>\"{html.escape(opt.revised_text)}\"</span>")
            rev_text_lbl.setWordWrap(True)
            rev_text_lbl.setStyleSheet(f"font-size: 12px; color: {text_primary};")
            opt_layout.addWidget(rev_text_lbl)

            rat_lbl = QLabel(f"<b>理由：</b><span style='color: {text_secondary};'>{html.escape(opt.rationale_zh)}</span>")
            rat_lbl.setWordWrap(True)
            rat_lbl.setStyleSheet("font-size: 11px;")
            opt_layout.addWidget(rat_lbl)

            layout.addWidget(opt_frame)

    def style_button(self, btn: QPushButton, is_active: bool):
        if is_active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #16a34a;
                    color: #ffffff;
                    border: 1px solid #15803d;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #15803d; }
            """)
        else:
            if self.is_dark:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1e293b;
                        color: #6ee7b7;
                        border: 1px solid #059669;
                        border-radius: 4px;
                        padding: 4px 10px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #064e3b; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f8fafc;
                        color: #15803d;
                        border: 1px solid #86efac;
                        border-radius: 4px;
                        padding: 4px 10px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #dcfce7;
                        border-color: #4ade80;
                    }
                """)

    def select_option(self, option_idx: int):
        self.selected_option_idx = option_idx
        for i, btn in enumerate(self.option_buttons):
            if i == option_idx:
                btn.setText("已套用 ✓")
                self.style_button(btn, True)
            else:
                btn.setText("切換至此選項")
                self.style_button(btn, False)
        
        self.on_option_selected_callback(self.issue_idx, option_idx)

# ==========================================
# 6. 主視窗 (三欄式互動介面 + 深淺模式切換 + 雙模型引擎)
# ==========================================
class AcademicReviewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LibreLlama Reviewer ─ 學術英文審查與改寫工作台")
        self.resize(1480, 890)

        self.config = load_config()
        self.is_dark_mode = self.config.get("dark_mode", False)
        self.engine_mode = self.config.get("engine_mode", "ollama")

        self.current_report: Optional[AcademicReviewReport] = None
        self.selected_options: Dict[int, int] = {}
        self.latest_revised_plain_text: str = ""

        # 計時器與串流監控
        self.elapsed_seconds: int = 0
        self.accumulated_tokens: int = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)
        self.live_stream_box: Optional[AcademicTextEdit] = None

        # 輸入防手震計時器
        self.preflight_timer = QTimer(self)
        self.preflight_timer.setSingleShot(True)
        self.preflight_timer.timeout.connect(self.run_preflight_analysis)

        self.current_preflight_matches: List[PreflightMatch] = []

        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(10)

        # --- 頂部工具列 ---
        self.toolbar_layout = QHBoxLayout()
        self.title_label = QLabel("🦙 LibreLlama Reviewer")
        self.title_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.toolbar_layout.addWidget(self.title_label)

        # 引擎來源選擇 (本機 Ollama vs 線上 API)
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["🖥️ 在地 Ollama (100% 離線隱私)", "☁️ 線上 API (DeepSeek/OpenAI/Gemini)"])
        if self.engine_mode == "api":
            self.engine_combo.setCurrentIndex(1)
        self.engine_combo.currentIndexChanged.connect(self.on_engine_mode_changed)
        self.toolbar_layout.addWidget(self.engine_combo)

        # API 設定按鈕
        self.api_settings_btn = QPushButton("⚙️ API 設定")
        self.api_settings_btn.clicked.connect(self.open_api_settings)
        self.toolbar_layout.addWidget(self.api_settings_btn)

        self.toolbar_layout.addStretch()

        self.model_label = QLabel("選擇模型:")
        self.model_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.toolbar_layout.addWidget(self.model_label)

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(190)
        self.toolbar_layout.addWidget(self.model_combo)

        self.refresh_btn = QPushButton("🔄 重新整理")
        self.refresh_btn.clicked.connect(self.load_installed_models)
        self.toolbar_layout.addWidget(self.refresh_btn)

        # 本機環境與模型精靈按鈕
        self.env_setup_btn = QPushButton("📥 本機環境精靈")
        self.env_setup_btn.clicked.connect(self.open_environment_dialog)
        self.toolbar_layout.addWidget(self.env_setup_btn)

        # 主題切換按鈕
        self.theme_btn = QPushButton("🌙 暗黑模式" if not self.is_dark_mode else "☀️ 明亮模式")
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.toolbar_layout.addWidget(self.theme_btn)

        # 軟體更新按鈕
        self.update_btn = QPushButton("🚀 檢查更新")
        self.update_btn.clicked.connect(self.open_update_dialog)
        self.toolbar_layout.addWidget(self.update_btn)

        self.main_layout.addLayout(self.toolbar_layout)

        # --- 三欄水平分割器 ---
        self.splitter = QSplitter(Qt.Horizontal)

        # ==========================================
        # 左欄：原始輸入區 + 本機秒級前置檢查器
        # ==========================================
        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)

        left_header = QHBoxLayout()
        self.editor_title = QLabel("1. 原始學術英文草稿:")
        self.editor_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        left_header.addWidget(self.editor_title)
        left_header.addStretch()

        self.word_count_lbl = QLabel("字數: 0 字")
        left_header.addWidget(self.word_count_lbl)
        left_layout.addLayout(left_header)

        self.text_editor = AcademicTextEdit(on_quick_fix=self.auto_fix_preflight_issues, is_dark=self.is_dark_mode)
        self.text_editor.setFont(QFont("Consolas", 11))
        sample_draft = (
            "Our preliminary experiments definitely prove that our new neural architecture completely solves "
            "the latency bottleneck in cloud networks. A lot of users were extremely happy because it runs very fast. "
            "Therefore, this framework will undeniably replace all classical networking algorithms within two years.\n\n"
            "Moreover, we observed a direct correlation between memory consumption and CPU temperature, which undeniably "
            "causes severe catastrophic server failures without any other factors."
        )
        self.text_editor.setPlainText(sample_draft)
        self.text_editor.textChanged.connect(self.on_editor_text_changed)
        left_layout.addWidget(self.text_editor)

        # ⚡ 本機即時快篩面板
        self.preflight_box = QFrame()
        preflight_layout = QVBoxLayout(self.preflight_box)
        preflight_layout.setContentsMargins(10, 8, 10, 8)
        preflight_layout.setSpacing(6)

        pf_top = QHBoxLayout()
        self.pf_title = QLabel("⚡ 本機秒篩 (純程式規則，0秒反應):")
        self.pf_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        pf_top.addWidget(self.pf_title)
        pf_top.addStretch()

        self.quick_fix_btn = QPushButton("⚡ 一鍵自動替換縮寫與口語詞")
        self.quick_fix_btn.clicked.connect(self.auto_fix_preflight_issues)
        pf_top.addWidget(self.quick_fix_btn)
        preflight_layout.addLayout(pf_top)

        self.preflight_status_lbl = QLabel("正在進行本機語法規則快速掃描...")
        self.preflight_status_lbl.setWordWrap(True)
        preflight_layout.addWidget(self.preflight_status_lbl)

        left_layout.addWidget(self.preflight_box)

        self.status_banner = QLabel("就緒：請確認輸入文本並點擊開始審查。")
        left_layout.addWidget(self.status_banner)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        self.review_btn = QPushButton("🚀 開始學術同儕審查 (深度實證批判與窮舉改寫)")
        self.review_btn.setFixedHeight(42)
        self.review_btn.clicked.connect(self.start_review)
        left_layout.addWidget(self.review_btn)

        self.splitter.addWidget(self.left_widget)

        # ==========================================
        # 中欄：審查意見、實證補強與多選項建議
        # ==========================================
        self.middle_widget = QWidget()
        middle_layout = QVBoxLayout(self.middle_widget)
        middle_layout.setContentsMargins(6, 0, 6, 0)

        self.middle_title = QLabel("2. 審查意見、實證補強與改寫選項 (中英雙語):")
        self.middle_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        middle_layout.addWidget(self.middle_title)

        self.assessment_box = AcademicTextBrowser(is_dark=self.is_dark_mode)
        self.assessment_box.setMaximumHeight(160)
        self.assessment_box.setHtml("<span style='color: #64748b;'>點擊左側「開始學術同儕審查」後，此處將顯示：<br>• 即時生成狀態、累計耗時與 Token 數<br>• 正體中文文意主旨解說與雙語審查總評</span>")
        middle_layout.addWidget(self.assessment_box)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.cards_container)

        middle_layout.addWidget(self.scroll_area)
        self.splitter.addWidget(self.middle_widget)

        # ==========================================
        # 右欄：修改後的文章 (高亮標籤隨選項即時連動)
        # ==========================================
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)

        right_header = QHBoxLayout()
        self.right_title = QLabel("3. 修改後全文 (高亮顏色標記修改處):")
        self.right_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        right_header.addWidget(self.right_title)
        right_header.addStretch()

        self.sync_to_left_btn = QPushButton("⬅️ 同步至左側草稿")
        self.sync_to_left_btn.clicked.connect(self.sync_revised_to_left)
        right_header.addWidget(self.sync_to_left_btn)

        self.copy_btn = QPushButton("📋 複製修訂全文")
        self.copy_btn.clicked.connect(self.copy_revised_text)
        right_header.addWidget(self.copy_btn)
        right_layout.addLayout(right_header)

        self.legend_label = QLabel(
            "<span style='background-color:#fee2e2; color:#991b1b; padding:2px 5px; border-radius:3px;'> 🔴 文法與句構 </span> "
            "<span style='background-color:#ffedd5; color:#9a3412; padding:2px 5px; border-radius:3px;'> 🟠 推論缺陷 / 過度宣稱 </span> "
            "<span style='background-color:#fef3c7; color:#92400e; padding:2px 5px; border-radius:3px;'> 🟡 邏輯矛盾 </span> "
            "<span style='background-color:#dbeafe; color:#1e40af; padding:2px 5px; border-radius:3px;'> 🔵 修辭與風格 </span>"
        )
        self.legend_label.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
        right_layout.addWidget(self.legend_label)

        self.revised_browser = AcademicTextBrowser(is_dark=self.is_dark_mode)
        self.revised_browser.setFont(QFont("Consolas", 11))
        self.revised_browser.setHtml("<span style='color: #64748b;'>審查完成後，此處將呈現綜合修訂後的完整英文文章，並以不同底色清晰標示出修改位置。<br><br>在中欄點選不同選項，此處將即時切換並更新高亮文字！</span>")
        right_layout.addWidget(self.revised_browser)

        self.splitter.addWidget(self.right_widget)

        self.splitter.setSizes([460, 520, 460])
        self.main_layout.addWidget(self.splitter)

        self.update_engine_ui()
        self.run_preflight_analysis()

    # --- 切換深色／淺色主題 ---
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.config["dark_mode"] = self.is_dark_mode
        save_config(self.config)
        self.theme_btn.setText("🌙 暗黑模式" if not self.is_dark_mode else "☀️ 明亮模式")
        self.apply_theme()

    def apply_theme(self):
        dark = self.is_dark_mode
        self.text_editor.is_dark = dark
        self.assessment_box.is_dark = dark
        self.revised_browser.is_dark = dark

        if dark:
            # 🌙 暗黑模式色彩 (Slate 900 / Slate 800)
            bg_main = "#0f172a"
            bg_card = "#1e293b"
            border_col = "#334155"
            text_main = "#f8fafc"
            text_sub = "#94a3b8"

            self.central_widget.setStyleSheet(f"background-color: {bg_main}; color: {text_main};")
            self.title_label.setStyleSheet(f"color: {text_main};")
            self.editor_title.setStyleSheet(f"color: {text_main};")
            self.middle_title.setStyleSheet(f"color: {text_main};")
            self.right_title.setStyleSheet(f"color: {text_main};")
            self.model_label.setStyleSheet(f"color: {text_sub};")
            self.word_count_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px;")
            self.pf_title.setStyleSheet(f"color: {text_main};")
            self.status_banner.setStyleSheet(f"color: {text_sub}; font-size: 11px;")

            self.text_editor.set_theme_mode(True)
            self.assessment_box.set_theme_mode(True)
            self.revised_browser.set_theme_mode(True)

            self.preflight_box.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_card};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                }}
            """)

            btn_normal = f"""
                QPushButton {{
                    background-color: {bg_card};
                    color: {text_main};
                    border: 1px solid {border_col};
                    border-radius: 5px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton:hover {{ background-color: #334155; }}
            """
            self.refresh_btn.setStyleSheet(btn_normal)
            self.env_setup_btn.setStyleSheet(btn_normal)
            self.theme_btn.setStyleSheet(btn_normal)
            self.api_settings_btn.setStyleSheet(btn_normal)
            self.sync_to_left_btn.setStyleSheet(btn_normal)
            self.copy_btn.setStyleSheet(btn_normal)
            self.update_btn.setStyleSheet(btn_normal)

            self.quick_fix_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e3a8a;
                    color: #93c5fd;
                    border: 1px solid #3b82f6;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #2563eb; color: #ffffff; }
            """)

            combo_style = f"""
                QComboBox {{
                    background-color: {bg_card};
                    color: {text_main};
                    border: 1px solid {border_col};
                    border-radius: 5px;
                    padding: 4px 8px;
                    font-size: 12px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {bg_card};
                    color: {text_main};
                    selection-background-color: #334155;
                    selection-color: #38bdf8;
                }}
            """
            self.engine_combo.setStyleSheet(combo_style)
            self.model_combo.setStyleSheet(combo_style)
            self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

            self.legend_label.setText(
                "<span style='background-color:#450a0a; color:#fecaca; border:1px solid #dc2626; padding:2px 5px; border-radius:3px;'> 🔴 文法與句構 </span> "
                "<span style='background-color:#431407; color:#fed7aa; border:1px solid #ea580c; padding:2px 5px; border-radius:3px;'> 🟠 推論缺陷 / 過度宣稱 </span> "
                "<span style='background-color:#451a03; color:#fde68a; border:1px solid #d97706; padding:2px 5px; border-radius:3px;'> 🟡 邏輯矛盾 </span> "
                "<span style='background-color:#172554; color:#bfdbfe; border:1px solid #2563eb; padding:2px 5px; border-radius:3px;'> 🔵 修辭與風格 </span>"
            )
        else:
            # ☀️ 明亮模式色彩 (Slate 50 / White)
            bg_main = "#f8fafc"
            bg_card = "#ffffff"
            border_col = "#cbd5e1"
            text_main = "#0f172a"
            text_sub = "#475569"

            self.central_widget.setStyleSheet(f"background-color: {bg_main}; color: {text_main};")
            self.title_label.setStyleSheet(f"color: {text_main};")
            self.editor_title.setStyleSheet(f"color: {text_main};")
            self.middle_title.setStyleSheet(f"color: {text_main};")
            self.right_title.setStyleSheet(f"color: {text_main};")
            self.model_label.setStyleSheet(f"color: {text_sub};")
            self.word_count_lbl.setStyleSheet(f"color: #64748b; font-size: 11px;")
            self.pf_title.setStyleSheet(f"color: {text_main};")
            self.status_banner.setStyleSheet(f"color: #64748b; font-size: 11px;")

            self.text_editor.set_theme_mode(False)
            self.assessment_box.set_theme_mode(False)
            self.revised_browser.set_theme_mode(False)

            self.preflight_box.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_card};
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                }}
            """)

            btn_normal = f"""
                QPushButton {{
                    background-color: {bg_card};
                    color: {text_main};
                    border: 1px solid {border_col};
                    border-radius: 5px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton:hover {{ background-color: #f1f5f9; }}
            """
            self.refresh_btn.setStyleSheet(btn_normal)
            self.env_setup_btn.setStyleSheet(btn_normal)
            self.theme_btn.setStyleSheet(btn_normal)
            self.api_settings_btn.setStyleSheet(btn_normal)
            self.sync_to_left_btn.setStyleSheet(btn_normal)
            self.copy_btn.setStyleSheet(btn_normal)
            self.update_btn.setStyleSheet(btn_normal)

            self.quick_fix_btn.setStyleSheet("""
                QPushButton {
                    background-color: #eff6ff;
                    color: #1d4ed8;
                    border: 1px solid #bfdbfe;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #dbeafe; }
            """)

            combo_style = f"""
                QComboBox {{
                    background-color: {bg_card};
                    color: {text_main};
                    border: 1px solid {border_col};
                    border-radius: 5px;
                    padding: 4px 8px;
                    font-size: 12px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {bg_card};
                    color: {text_main};
                    selection-background-color: #e2e8f0;
                    selection-color: {text_main};
                }}
            """
            self.engine_combo.setStyleSheet(combo_style)
            self.model_combo.setStyleSheet(combo_style)
            self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

            self.legend_label.setText(
                "<span style='background-color:#fee2e2; color:#991b1b; padding:2px 5px; border-radius:3px;'> 🔴 文法與句構 </span> "
                "<span style='background-color:#ffedd5; color:#9a3412; padding:2px 5px; border-radius:3px;'> 🟠 推論缺陷 / 過度宣稱 </span> "
                "<span style='background-color:#fef3c7; color:#92400e; padding:2px 5px; border-radius:3px;'> 🟡 邏輯矛盾 </span> "
                "<span style='background-color:#dbeafe; color:#1e40af; padding:2px 5px; border-radius:3px;'> 🔵 修辭與風格 </span>"
            )

        # 重新整理右欄修訂視圖與秒篩徽章
        self.update_revised_article_view()
        self.run_preflight_analysis()

    # --- 引擎切換 (本機 Ollama vs 線上 API) ---
    def on_engine_mode_changed(self, idx: int):
        self.engine_mode = "ollama" if idx == 0 else "api"
        self.config["engine_mode"] = self.engine_mode
        save_config(self.config)
        self.update_engine_ui()

    def update_engine_ui(self):
        if self.engine_mode == "ollama":
            self.api_settings_btn.setVisible(False)
            self.refresh_btn.setVisible(True)
            self.env_setup_btn.setVisible(True)
            self.model_label.setText("選擇在地模型:")
            self.load_installed_models()
        else:
            self.api_settings_btn.setVisible(True)
            self.refresh_btn.setVisible(False)
            self.env_setup_btn.setVisible(False)
            self.model_label.setText("線上模型:")
            self.model_combo.clear()
            cur_model = self.config.get("api_model", "deepseek-chat")
            provider = self.config.get("api_provider", "DeepSeek")
            self.model_combo.addItem(f"{cur_model} ({provider})")
            self.review_btn.setEnabled(True)

    def open_api_settings(self):
        dlg = ApiSettingsDialog(self, self.config, is_dark=self.is_dark_mode)
        if dlg.exec():
            self.config = load_config()
            self.update_engine_ui()

    def open_environment_dialog(self):
        dlg = OllamaEnvironmentDialog(self, is_dark=self.is_dark_mode)
        if dlg.exec() or dlg.models_updated:
            self.load_installed_models()

    def open_update_dialog(self):
        dlg = UpdateDialog(self, is_dark=self.is_dark_mode, config=self.config)
        dlg.exec()

    def on_editor_text_changed(self):
        self.preflight_timer.start(250)

    def run_preflight_analysis(self):
        text = self.text_editor.toPlainText().strip()
        words = text.split()
        self.word_count_lbl.setText(f"字數: {len(words)} 字")

        if not text:
            self.preflight_status_lbl.setText("請輸入文字以進行即時秒篩。")
            self.quick_fix_btn.setEnabled(False)
            return

        matches = PreflightChecker.scan(text)
        self.current_preflight_matches = matches

        c_count = sum(1 for m in matches if m.category == "縮寫禁忌")
        i_count = sum(1 for m in matches if m.category == "非正式口語")
        o_count = sum(1 for m in matches if m.category == "過度宣稱預警")

        if not matches:
            self.preflight_status_lbl.setText("✨ <b>本機秒篩通過</b>：未偵測到明顯縮寫禁忌或常見口語詞彙。")
            self.preflight_status_lbl.setStyleSheet("font-size: 11px; color: #10b981;")
            self.quick_fix_btn.setEnabled(False)
        else:
            if self.is_dark_mode:
                badge_c = "<span style='background-color:#450a0a; color:#fecaca; border:1px solid #dc2626; padding:1px 4px; border-radius:3px;'>"
                badge_i = "<span style='background-color:#431407; color:#fed7aa; border:1px solid #ea580c; padding:1px 4px; border-radius:3px;'>"
                badge_o = "<span style='background-color:#451a03; color:#fde68a; border:1px solid #d97706; padding:1px 4px; border-radius:3px;'>"
            else:
                badge_c = "<span style='background-color:#fee2e2; color:#991b1b; padding:1px 4px; border-radius:3px;'>"
                badge_i = "<span style='background-color:#ffedd5; color:#9a3412; padding:1px 4px; border-radius:3px;'>"
                badge_o = "<span style='background-color:#fef3c7; color:#92400e; padding:1px 4px; border-radius:3px;'>"

            status_html = (
                f"<b>偵測到 {len(matches)} 處建議</b>："
                f"{badge_c}縮寫: {c_count}</span> "
                f"{badge_i}口語詞: {i_count}</span> "
                f"{badge_o}宣稱預警: {o_count}</span>"
            )
            sample_tips = []
            for m in matches[:3]:
                sample_tips.append(f"• 發現 <b>\"{html.escape(m.original)}\"</b> ➔ 建議改為 <i>\"{html.escape(m.replacement)}\"</i> ({m.explanation})")
            
            full_html = status_html + "<br>" + "<br>".join(sample_tips)
            if len(matches) > 3:
                full_html += f"<br>• ...等另外 {len(matches)-3} 處可透過右方按鈕一鍵修正。"

            self.preflight_status_lbl.setText(full_html)
            color_txt = "#cbd5e1" if self.is_dark_mode else "#1e293b"
            self.preflight_status_lbl.setStyleSheet(f"font-size: 11px; color: {color_txt};")
            self.quick_fix_btn.setEnabled(True)

    def auto_fix_preflight_issues(self):
        curr_text = self.text_editor.toPlainText()
        new_text = PreflightChecker.fix_all_informal_and_contractions(curr_text)
        if new_text != curr_text:
            self.text_editor.setPlainText(new_text)
            QMessageBox.information(self, "秒級修復完成", "已自動將學術縮寫（如 don't ➔ do not）及常見口語贅詞替換為學術規範形式！")
        else:
            QMessageBox.information(self, "提示", "目前文字中已無可自動替換的縮寫或常見口語詞。")

    def load_installed_models(self):
        if self.engine_mode != "ollama":
            return
        self.model_combo.clear()
        try:
            response = ollama.list()
            models = []
            if hasattr(response, 'models'):
                for m in response.models:
                    name = getattr(m, 'model', None) or getattr(m, 'name', None) or str(m)
                    if name:
                        models.append(name)
            elif isinstance(response, dict) and 'models' in response:
                for m in response['models']:
                    name = m.get('model') or m.get('name')
                    if name:
                        models.append(name)

            if models:
                self.model_combo.addItems(models)
                self.review_btn.setEnabled(True)
            else:
                self.model_combo.addItem("未檢測到本機模型 (請點環境精靈安裝)")
                self.review_btn.setEnabled(False)
        except Exception as e:
            self.model_combo.addItem("無法連接 Ollama (請點環境精靈檢查)")
            self.review_btn.setEnabled(False)

    def start_review(self):
        text = self.text_editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "請先輸入或貼上要審查的論文草稿。")
            return

        if self.engine_mode == "ollama":
            model_name = self.model_combo.currentText().strip()
            if not model_name or "未檢測到" in model_name or "無法連接" in model_name:
                reply = QMessageBox.question(
                    self, "尚未就緒",
                    "本機尚未就緒 Ollama 服務或尚未安裝推薦模型。\n\n是否立即開啟【本機環境與模型管理精靈】協助您一鍵安裝與下載？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.open_environment_dialog()
                return
        else:
            model_name = self.config.get("api_model", "deepseek-chat")
            if not self.config.get("api_key"):
                QMessageBox.warning(self, "提示", "請先點擊上方「⚙️ API 設定」輸入線上 API Key。")
                self.open_api_settings()
                return

        self.elapsed_seconds = 0
        self.accumulated_tokens = 0
        self.timer.start(1000)

        self.review_btn.setEnabled(False)
        self.review_btn.setText("正在進行深度實證批判與窮舉審查...")
        self.progress_bar.setVisible(True)
        self.update_live_status_ui(model_name)

        self.clear_cards()
        self.setup_live_stream_console()

        self.revised_browser.setHtml("<span style='color: #64748b;'>審查進行中，完成後將即時生成高亮修訂全文...</span>")

        self.worker = ReviewWorker(text, self.engine_mode, model_name, self.config)
        self.worker.chunk_received.connect(self.on_chunk_received)
        self.worker.finished.connect(self.on_review_finished)
        self.worker.error.connect(self.on_review_error)
        self.worker.start()

    def on_timer_tick(self):
        self.elapsed_seconds += 1
        model_name = self.model_combo.currentText().strip()
        self.update_live_status_ui(model_name)

    def update_live_status_ui(self, model_name: str):
        mode_label = "本機 Ollama" if self.engine_mode == "ollama" else "線上 API"
        status_msg = f"⏳ [{mode_label} 推論中] 模型：{model_name} ｜ ⏱️ 已耗時：{self.elapsed_seconds} 秒 ｜ 📊 已生成：{self.accumulated_tokens} tokens"
        self.status_banner.setText(status_msg)
        self.status_banner.setStyleSheet("color: #3b82f6; font-weight: bold; font-size: 11px;")

        live_html = f"""
        <div style='font-family: Segoe UI, Microsoft JhengHei;'>
            <p style='margin: 0 0 6px 0;'><b style='color: #3b82f6;'>⚡ 學術同儕審查進行中 ({mode_label} 串流模式)</b></p>
            <p style='margin: 0; font-size: 11px;'>
                <b>模型名稱：</b>{html.escape(model_name)}<br>
                <b>已耗費時間：</b><span style='color: #f59e0b; font-weight: bold;'>{self.elapsed_seconds} 秒</span><br>
                <b>已產出詞元：</b><span style='color: #10b981; font-weight: bold;'>{self.accumulated_tokens} tokens</span> (下方即時輸出中)
            </p>
        </div>
        """
        self.assessment_box.setHtml(live_html)

    def setup_live_stream_console(self):
        label = QLabel("📡 即時輸出監控 (模型正於背景進行窮舉批判，保證非卡住):")
        label.setStyleSheet("font-weight: bold; font-size: 11px; margin-bottom: 4px;")
        self.cards_layout.addWidget(label)

        self.live_stream_box = AcademicTextEdit(is_dark=self.is_dark_mode)
        self.live_stream_box.setReadOnly(True)
        self.live_stream_box.setFont(QFont("Consolas", 10))
        self.live_stream_box.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
                line-height: 1.4;
            }
        """)
        self.live_stream_box.setPlaceholderText("正在等待模型送出首個 Token...")
        self.cards_layout.addWidget(self.live_stream_box)
        self.cards_layout.addStretch()

    @Slot(str, int)
    def on_chunk_received(self, delta: str, chunk_count: int):
        self.accumulated_tokens = chunk_count
        if self.live_stream_box:
            cursor = self.live_stream_box.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(delta)
            self.live_stream_box.setTextCursor(cursor)
            self.live_stream_box.ensureCursorVisible()

    @Slot(AcademicReviewReport)
    def on_review_finished(self, report: AcademicReviewReport):
        self.timer.stop()
        self.review_btn.setEnabled(True)
        self.review_btn.setText("🚀 開始學術同儕審查 (深度實證批判與窮舉改寫)")
        self.progress_bar.setVisible(False)
        self.current_report = report

        rec_count = len(getattr(report, 'research_recommendations', []))
        issue_count = len(report.issues)

        final_msg = f"✅ 審查完成！耗時 {self.elapsed_seconds} 秒，共產出 {self.accumulated_tokens} tokens ｜ 檢驗出 {issue_count} 個改進點 ｜ 提供 {rec_count} 項中英對照實質補強建議！"
        self.status_banner.setText(final_msg)
        self.status_banner.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

        self.selected_options = {idx: 0 for idx in range(issue_count)}

        assessment_html = f"""
        <div style='font-family: Segoe UI, Microsoft JhengHei;'>
            <p><b>📖 全文主旨判斷與解析 (正體中文)：</b><br><span>{html.escape(report.article_gist_zh)}</span></p>
            <hr style='border: 0; border-top: 1px solid #cbd5e1; margin: 6px 0;'>
            <p><b>🇹🇼 綜合投稿就緒評估：</b><br><span style='color: #10b981;'>{html.escape(report.overall_assessment_zh)}</span></p>
            <p><b>🇺🇸 Overall Reviewer Assessment：</b><br><span style='font-style: italic;'>{html.escape(report.overall_assessment_en)}</span></p>
        </div>
        """
        self.assessment_box.setHtml(assessment_html)

        self.clear_cards()
        self.live_stream_box = None

        recommendations = getattr(report, 'research_recommendations', [])
        if recommendations:
            rec_header = QLabel(f"🔬 審稿人實質建議：上下文完整性與實驗/統計補強 ({len(recommendations)} 項):")
            rec_header.setStyleSheet("font-weight: bold; color: #8b5cf6; font-size: 13px; margin-top: 4px; margin-bottom: 2px;")
            self.cards_layout.addWidget(rec_header)

            for rec in recommendations:
                rec_card = ResearchRecommendationCard(rec, is_dark=self.is_dark_mode)
                self.cards_layout.addWidget(rec_card)

        issues_header = QLabel(f"✍️ 逐句文意診斷與多風格改寫 ({len(report.issues)} 處改進點):")
        issues_header.setStyleSheet("font-weight: bold; color: #3b82f6; font-size: 13px; margin-top: 12px; margin-bottom: 2px;")
        self.cards_layout.addWidget(issues_header)

        if not report.issues:
            no_issue_label = QLabel("✨ 未發現明顯語言或推論問題，論述嚴謹且文法正確！")
            no_issue_label.setStyleSheet("color: #10b981; font-weight: bold; margin-top: 10px;")
            self.cards_layout.addWidget(no_issue_label)
        else:
            for idx, issue in enumerate(report.issues):
                card = IssueCard(idx, issue, self.handle_option_selection, is_dark=self.is_dark_mode)
                self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
        self.update_revised_article_view()

    @Slot(str)
    def on_review_error(self, err_msg: str):
        self.timer.stop()
        self.review_btn.setEnabled(True)
        self.review_btn.setText("🚀 開始學術同儕審查 (深度實證批判與窮舉改寫)")
        self.progress_bar.setVisible(False)
        self.status_banner.setText("❌ 審查過程中發生錯誤。")
        self.status_banner.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")

        self.assessment_box.setHtml("<span style='color: #ef4444;'>❌ 審查過程中發生錯誤。請確認下方錯誤細節。</span>")
        QMessageBox.critical(
            self,
            "連線或推論錯誤",
            f"無法完成審查，請確認：\n1. 模型服務是否正在運行\n2. 若使用線上 API，請確認 API Key 與額度是否正確\n\n錯誤細節:\n{err_msg}"
        )

    def clear_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def handle_option_selection(self, issue_idx: int, option_idx: int):
        self.selected_options[issue_idx] = option_idx
        self.update_revised_article_view()

    def find_span_in_text(self, full_text: str, snippet: str) -> Tuple[int, int]:
        clean_snippet = snippet.strip().strip('"\'')
        if not clean_snippet:
            return -1, -1

        idx = full_text.find(clean_snippet)
        if idx != -1:
            return idx, idx + len(clean_snippet)

        idx_lower = full_text.lower().find(clean_snippet.lower())
        if idx_lower != -1:
            return idx_lower, idx_lower + len(clean_snippet)

        pattern = re.sub(r'\\ ', r'\\s+', re.escape(clean_snippet))
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            return m.start(), m.end()

        prefix = clean_snippet[:min(25, len(clean_snippet))].strip()
        if len(prefix) >= 12:
            idx_pref = full_text.lower().find(prefix.lower())
            if idx_pref != -1:
                return idx_pref, min(len(full_text), idx_pref + len(clean_snippet))

        return -1, -1

    def update_revised_article_view(self):
        if not self.current_report:
            return

        original_draft = self.text_editor.toPlainText()
        issues = self.current_report.issues

        if not issues:
            self.latest_revised_plain_text = original_draft
            self.revised_browser.setPlainText(original_draft)
            return

        if self.is_dark_mode:
            style_map = {
                "Logic Error": ("#451a03", "#fde68a", "#d97706"),
                "Flawed Deduction": ("#431407", "#fed7aa", "#ea580c"),
                "Grammar & Mechanics": ("#450a0a", "#fecaca", "#dc2626"),
                "Rhetorical Defect": ("#172554", "#bfdbfe", "#2563eb")
            }
        else:
            style_map = {
                "Logic Error": ("#fef3c7", "#92400e", "#fcd34d"),
                "Flawed Deduction": ("#ffedd5", "#9a3412", "#fdba74"),
                "Grammar & Mechanics": ("#fee2e2", "#991b1b", "#fca5a5"),
                "Rhetorical Defect": ("#dbeafe", "#1e40af", "#93c5fd")
            }

        spans = []
        for idx, issue in enumerate(issues):
            s, e = self.find_span_in_text(original_draft, issue.original_text)
            if s != -1:
                spans.append((s, e, idx))

        spans.sort(key=lambda x: x[0])
        non_overlapping_spans = []
        last_end = 0
        for s, e, idx in spans:
            if s >= last_end:
                non_overlapping_spans.append((s, e, idx))
                last_end = e

        html_parts = []
        plain_parts = []
        curr_pos = 0

        for s, e, idx in non_overlapping_spans:
            if s > curr_pos:
                unmodified = original_draft[curr_pos:s]
                plain_parts.append(unmodified)
                html_parts.append(html.escape(unmodified))

            issue = issues[idx]
            opt_idx = self.selected_options.get(idx, 0)
            if opt_idx < len(issue.revision_options):
                chosen_opt = issue.revision_options[opt_idx]
            else:
                chosen_opt = issue.revision_options[0]

            revised_snippet = chosen_opt.revised_text.strip()
            plain_parts.append(revised_snippet)

            bg, txt_col, border_col = style_map.get(issue.category, ("#064e3b" if self.is_dark_mode else "#dcfce7", "#6ee7b7" if self.is_dark_mode else "#166534", "#059669" if self.is_dark_mode else "#86efac"))
            tooltip = f"[{issue.category_zh}] {issue.reviewer_comment_zh} (理由: {chosen_opt.rationale_zh})"

            highlight_span = (
                f'<span style="background-color: {bg}; color: {txt_col}; border: 1px solid {border_col}; '
                f'border-radius: 4px; padding: 2px 5px; font-weight: 600;" '
                f'title="{html.escape(tooltip)}">{html.escape(revised_snippet)}</span>'
            )
            html_parts.append(highlight_span)
            curr_pos = e

        if curr_pos < len(original_draft):
            tail = original_draft[curr_pos:]
            plain_parts.append(tail)
            html_parts.append(html.escape(tail))

        self.latest_revised_plain_text = "".join(plain_parts)
        joined_html = "".join(html_parts).replace("\n\n", "<br><br>").replace("\n", "<br>")

        text_color = "#f8fafc" if self.is_dark_mode else "#0f172a"
        final_html = f"""
        <div style='font-family: Consolas, "Courier New", monospace; font-size: 11pt; line-height: 1.7; color: {text_color};'>
            {joined_html}
        </div>
        """
        self.revised_browser.setHtml(final_html)

    def sync_revised_to_left(self):
        if not self.latest_revised_plain_text:
            QMessageBox.warning(self, "提示", "目前尚無修訂後的內容可供同步。")
            return
        
        reply = QMessageBox.question(
            self, "確認同步",
            "是否確定將右側修訂後的全文覆蓋至左側草稿輸入框？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.text_editor.setPlainText(self.latest_revised_plain_text)
            QMessageBox.information(self, "成功", "已將修訂後的全文同步至左側草稿編輯器！")

    def copy_revised_text(self):
        text_to_copy = self.latest_revised_plain_text or (self.current_report.revised_full_text if self.current_report else "")
        if text_to_copy:
            clipboard = QApplication.clipboard()
            clipboard.setText(text_to_copy)
            QMessageBox.information(self, "成功", "已將修訂後的完整英文文章複製到剪貼簿！")
        else:
            QMessageBox.warning(self, "提示", "目前尚無修訂後的文章可供複製。")

# ==========================================
# 7. 程式入口
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AcademicReviewerApp()
    window.show()
    sys.exit(app.exec())