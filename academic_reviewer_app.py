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

APP_VERSION = "0.9.0"
DEFAULT_UPDATE_URL = "version.json"
CONFIG_FILE = "app_config.json"

# ==========================================
# 0. 國際化多語系字典 (I18N Localization Engine)
# ==========================================
I18N = {
    "zh_TW": {
        "app_title": "LibreLlama Reviewer ─ 多情境寫作審查與改寫工作台",
        "toolbar_title": "🦙 LibreLlama Reviewer",
        "pre_release_badge": "v0.9.0 封閉開發版",
        "engine_ollama": "🖥️ 在地 Ollama (100% 離線隱私)",
        "engine_api": "☁️ 線上 API (DeepSeek/OpenAI/Gemini)",
        "api_settings": "⚙️ API 設定",
        "select_local_model": "在地模型:",
        "select_cloud_model": "線上模型:",
        "refresh": "🔄 重新整理",
        "env_wizard": "📥 本機環境精靈",
        "theme_dark": "🌙 暗黑模式",
        "theme_light": "☀️ 明亮模式",
        "check_update": "🚀 檢查更新",
        "lang_btn": "🌐 English",

        # 情境與範圍控制列
        "mode_lbl": "寫作情境:",
        "mode_academic": "🔬 學術期刊論文 (Academic Paper)",
        "mode_correspondence": "✉️ 專業書信往來 (Correspondence/Email)",
        "mode_application": "🎓 留學與求職自述 (SOP / Cover Letter)",
        "mode_business": "💼 商務決策報告 (Business Report)",

        "scope_lbl": "文章範圍:",
        "scope_full": "📄 全篇完整文章",
        "scope_partial": "📑 局部段落選取",

        "section_lbl": "章節定位:",
        "load_sample": "📋 載入情境範文",

        # 左欄
        "left_title": "1. 原始英文草稿:",
        "word_count": "字數: {n} 字",
        "pf_title": "⚡ 本機秒篩 (純程式規則，0秒反應):",
        "quick_fix_btn": "⚡ 一鍵自動替換縮寫與口語詞",
        "preflight_ready": "正在進行本機語法規則快速掃描...",
        "status_ready": "就緒：請確認輸入文本並點擊開始審查。",
        "btn_start_review": "🚀 開始智能審查 (搭配詞檢視與深度改寫)",
        "btn_reviewing": "正在進行深度情境批判與搭配詞窮舉審查...",

        # 中欄
        "middle_title": "2. 審查意見、實證補強與搭配詞選項:",
        "assessment_placeholder": "<span style='color: #64748b;'>點擊左側「開始智能審查」後，此處將顯示：<br>• 即時生成狀態、累計耗時與 Token 數<br>• 全文主旨解析與情境綜合評述</span>",
        "gist_title": "📖 全文主旨判斷與解析 (正體中文)：",
        "overall_zh_title": "🇹🇼 綜合就緒度評估：",
        "overall_en_title": "🇺🇸 Overall Assessment：",

        # 右欄
        "right_title": "3. 修改後全文 (高亮顏色標記修改處):",
        "sync_left": "⬅️ 同步至左側草稿",
        "copy_revised": "📋 複製修訂全文",
        "revised_placeholder": "<span style='color: #64748b;'>審查完成後，此處將呈現綜合修訂後的完整英文文章，並以不同底色清晰標示出修改位置。<br><br>在中欄點選不同選項，此處將即時切換並更新高亮文字！</span>",

        # 圖例 Legend
        "legend_grammar": "🔴 文法與句構",
        "legend_deduction": "🟠 推論缺陷 / 過度宣稱",
        "legend_logic": "🟡 邏輯矛盾",
        "legend_rhetoric": "🔵 修辭風格",
        "legend_collocation": "🟢 道地搭配詞",

        # 右鍵選單 Context Menu
        "undo": "↩️ 復原 (Undo)",
        "redo": "↪️ 重做 (Redo)",
        "cut": "✂️ 剪下 (Cut)",
        "copy": "📋 複製 (Copy)",
        "paste": "📥 貼上 (Paste)",
        "delete": "🗑️ 刪除 (Delete)",
        "select_all": "📑 全選 (Select All)",
        "clear": "🧹 清空草稿 (Clear)",
        "auto_fix_menu": "⚡ 一鍵自動修復縮寫與口語詞",
    },
    "en_US": {
        "app_title": "LibreLlama Reviewer ─ Multi-Context Writing & Review Workbench",
        "toolbar_title": "🦙 LibreLlama Reviewer",
        "pre_release_badge": "v0.9.0 Pre-release",
        "engine_ollama": "🖥️ Local Ollama (100% Offline Privacy)",
        "engine_api": "☁️ Cloud API (DeepSeek/OpenAI/Gemini)",
        "api_settings": "⚙️ API Settings",
        "select_local_model": "Local Model:",
        "select_cloud_model": "Cloud Model:",
        "refresh": "🔄 Refresh",
        "env_wizard": "📥 Local Wizard",
        "theme_dark": "🌙 Dark Mode",
        "theme_light": "☀️ Light Mode",
        "check_update": "🚀 Updates",
        "lang_btn": "🌐 繁體中文",

        # Mode & Scope
        "mode_lbl": "Writing Mode:",
        "mode_academic": "🔬 Academic Research Paper",
        "mode_correspondence": "✉️ Professional Correspondence / Email",
        "mode_application": "🎓 Statement of Purpose / Cover Letter",
        "mode_business": "💼 Business & Analytical Report",

        "scope_lbl": "Context Scope:",
        "scope_full": "📄 Full Document",
        "scope_partial": "📑 Partial Excerpt",

        "section_lbl": "Section Target:",
        "load_sample": "📋 Load Sample",

        # Left Column
        "left_title": "1. Original Draft:",
        "word_count": "Word Count: {n} words",
        "pf_title": "⚡ Instant Local Linter (Pure Rules, 0.001s):",
        "quick_fix_btn": "⚡ Quick Fix Contractions & Informal Phrasing",
        "preflight_ready": "Scanning local rule heuristics...",
        "status_ready": "Ready: verify input text and click Start Review.",
        "btn_start_review": "🚀 Start Deep Review (Collocations & Multi-Style Revisions)",
        "btn_reviewing": "Performing exhaustive multi-context critique and collocation analysis...",

        # Middle Column
        "middle_title": "2. Critiques, Strategic Proposals & Collocation Options:",
        "assessment_placeholder": "<span style='color: #64748b;'>Click 'Start Deep Review' on the left to display:<br>• Real-time token streaming & elapsed time<br>• Executive summary & critical assessment</span>",
        "gist_title": "📖 Executive Summary & Thesis Analysis:",
        "overall_zh_title": "Assessment:",
        "overall_en_title": "Overall Strategic Assessment:",

        # Right Column
        "right_title": "3. Revised Full Text (Real-time Highlight Matching):",
        "sync_left": "⬅️ Sync to Left Draft",
        "copy_revised": "📋 Copy Revised Text",
        "revised_placeholder": "<span style='color: #64748b;'>Upon review completion, the fully synthesized text will appear here with color highlights.<br><br>Switching options in the center column dynamically updates the text here!</span>",

        # Legend
        "legend_grammar": "🔴 Grammar & Mechanics",
        "legend_deduction": "🟠 Deductive Flaw / Overclaiming",
        "legend_logic": "🟡 Logic Error",
        "legend_rhetoric": "🔵 Rhetorical & Tone",
        "legend_collocation": "🟢 Natural Collocation",

        # Context Menu
        "undo": "↩️ Undo",
        "redo": "↪️ Redo",
        "cut": "✂️ Cut",
        "copy": "📋 Copy",
        "paste": "📥 Paste",
        "delete": "🗑️ Delete",
        "select_all": "📑 Select All",
        "clear": "🧹 Clear Draft",
        "auto_fix_menu": "⚡ Quick Fix Contractions & Informal Words",
    }
}

# ==========================================
# 0.1 情境寫作模式與章節定義
# ==========================================
WRITING_MODES = {
    "academic": {
        "id": "academic",
        "name_zh": "🔬 學術期刊論文 (Academic Paper)",
        "name_en": "🔬 Academic Research Paper",
        "persona_zh": "世界頂級期刊（如 Nature, IEEE, Science, ACM）以嚴苛批判著稱的資深同行評審員（Reviewer #2）兼學術英文資深編輯",
        "persona_en": "Senior Peer Reviewer #2 and Principal Academic Editor for top-tier international journals (Nature, IEEE, Science, ACM)",
        "sections": [
            ("abstract", "標題與摘要 (Title & Abstract)", "Title & Abstract"),
            ("intro", "引言與研究缺口 (Introduction & Research Gap)", "Introduction & Research Gap"),
            ("lit_review", "相關文獻回顧 (Literature Review)", "Literature Review"),
            ("methodology", "方法與實驗設計 (Methodology & Experiments)", "Methodology & Experiments"),
            ("results", "結果與數據分析 (Results & Empirical Data)", "Results & Empirical Data"),
            ("discussion", "討論、局限與防禦 (Discussion & Limitations)", "Discussion & Limitations"),
            ("conclusion", "結論與未來展望 (Conclusion & Future Work)", "Conclusion & Future Work")
        ],
        "sample": (
            "Our preliminary experiments definitely prove that our new neural architecture completely solves "
            "the latency bottleneck in cloud networks. A lot of users were extremely happy because it runs very fast. "
            "Therefore, this framework will undeniably replace all classical networking algorithms within two years.\n\n"
            "Moreover, we observed a direct correlation between memory consumption and CPU temperature, which undeniably "
            "causes severe catastrophic server failures without any other factors. We made an experiment to verify this."
        )
    },
    "correspondence": {
        "id": "correspondence",
        "name_zh": "✉️ 專業書信往來 (Correspondence/Email)",
        "name_en": "✉️ Professional Correspondence / Email",
        "persona_zh": "頂級學術機構與跨國企業的高級學術聯絡官兼商務通訊專家，專精高雅得體的語氣、明確的行動呼籲（Call to Action）與外交級溝通策略",
        "persona_en": "Principal Academic Liaison & Executive Communication Specialist, expert in diplomatic tone, professional etiquette, and actionable clarity",
        "sections": [
            ("salutation", "開場稱謂與問候 (Opening & Salutation)", "Opening & Salutation"),
            ("purpose", "主旨背景與核心訴求 (Context & Purpose)", "Context & Purpose"),
            ("proposal", "具體提議或反駁說明 (Specific Proposal / Inquiries)", "Specific Proposal / Inquiries"),
            ("next_steps", "後續行動時程與期待 (Next Steps & Deadline)", "Next Steps & Deadline"),
            ("closing", "結尾致意與署名 (Closing Sign-off)", "Closing Sign-off")
        ],
        "sample": (
            "Dear Professor Smith,\n\n"
            "I am writing this email because I want you to read my manuscript very fast. As you don't know me yet, "
            "I want to make an inquiry about whether your lab has money to support my postdoc. "
            "Please tell me your decision immediately due to the fact that I have lots of other offers.\n\n"
            "Looking forward to hearing from you soon."
        )
    },
    "application": {
        "id": "application",
        "name_zh": "🎓 留學與求職自述 (SOP / Cover Letter)",
        "name_en": "🎓 Statement of Purpose / Cover Letter",
        "persona_zh": "頂級常春藤名校審查委員會委員（Admissions Committee）兼資深獵頭合夥人，專精挖掘獨特個人優勢、量化成就動詞（Action Verbs）與杜絕陳詞濫調",
        "persona_en": "Ivy League Admissions Committee Member and Senior Career Strategist, expert in high-impact narrative hooks, quantified impact verbs, and personal branding",
        "sections": [
            ("hook", "動機開場與學術啟發 (Narrative Hook & Motivation)", "Narrative Hook & Motivation"),
            ("academic_bg", "學術與專案實績 (Academic & Technical Track Record)", "Academic & Technical Track Record"),
            ("professional", "實戰經歷與量化成果 (Impact Quantification & Leadership)", "Impact Quantification & Leadership"),
            ("program_fit", "目標系所/職缺契合度 (Synergy & Program Fit)", "Synergy & Program Fit"),
            ("vision", "長遠職涯抱負與承諾 (Long-term Vision & Contribution)", "Long-term Vision & Contribution")
        ],
        "sample": (
            "Ever since I was a little child, I always loved computers and was extremely interested in coding. "
            "In my college, I did a lot of research projects and got very good grades. I helped my professor with "
            "a big machine learning task and we obtained very fast accuracy improvements.\n\n"
            "Your prestigious university is undeniably the best in the world, so studying in your program will definitely "
            "make my dream come true."
        )
    },
    "business": {
        "id": "business",
        "name_zh": "💼 商務決策報告 (Business Report)",
        "name_en": "💼 Business & Analytical Report",
        "persona_zh": "麥肯錫（McKinsey）高級戰略諮詢顧問兼高階主管簡報專家，專精以假說為導向的結構化思考（Pyramid Principle）、高密度數據洞察與決策驅動陳述",
        "persona_en": "Senior Strategy Partner at McKinsey & Company, expert in Pyramid Principle structured communication, executive conciseness, and decision-driven analytics",
        "sections": [
            ("exec_summary", "執行摘要與核心洞察 (Executive Summary)", "Executive Summary"),
            ("problem_diag", "痛點診斷與市場分析 (Market & Problem Diagnosis)", "Market & Problem Diagnosis"),
            ("strategic_plan", "戰略方案與ROI預估 (Strategic Plan & ROI)", "Strategic Plan & ROI"),
            ("risk_mitigation", "風險評估與因應對策 (Risk Assessment & Mitigation)", "Risk Assessment & Mitigation"),
            ("roadmap", "執行路線圖與資源分配 (Roadmap & Next Steps)", "Roadmap & Next Steps")
        ],
        "sample": (
            "This report definitely proves that our product dominates all competitors in the market. "
            "A lot of customers think our software is really good due to the fact that it is completely bug-free. "
            "Therefore, if we invest a lot of budget into social media, we will undeniably achieve 1000% ROI "
            "without any other risks."
        )
    }
}

def load_config() -> dict:
    default_config = {
        "engine_mode": "ollama",
        "dark_mode": False,
        "ui_language": "zh_TW",
        "writing_mode": "academic",
        "context_scope": "full",
        "section_target": "abstract",
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
# 1. 本機即時前置檢查器 (適配各寫作模式與搭配詞)
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
        r"\bdon't\b": ("do not", "正式寫作中應避免縮寫 (Avoid contractions in formal writing)"),
        r"\bdoesn't\b": ("does not", "正式寫作中應避免縮寫"),
        r"\bcan't\b": ("cannot", "正式寫作中應避免縮寫"),
        r"\bwon't\b": ("will not", "正式寫作中應避免縮寫"),
        r"\bit's\b": ("it is", "正式寫作中應避免縮寫"),
        r"\bthey're\b": ("they are", "正式寫作中應避免縮寫"),
        r"\bwe're\b": ("we are", "正式寫作中應避免縮寫"),
        r"\bdidn't\b": ("did not", "正式寫作中應避免縮寫"),
        r"\bhaven't\b": ("have not", "正式寫作中應避免縮寫"),
        r"\bhasn't\b": ("has not", "正式寫作中應避免縮寫"),
        r"\bcouldn't\b": ("could not", "正式寫作中應避免縮寫"),
        r"\bwouldn't\b": ("would not", "正式寫作中應避免縮寫"),
        r"\bshouldn't\b": ("should not", "正式寫作中應避免縮寫"),
        r"\bisn't\b": ("is not", "正式寫作中應避免縮寫"),
        r"\baren't\b": ("are not", "正式寫作中應避免縮寫"),
    }

    INFORMAL_WORDS = {
        r"\ba lot of\b": ("a substantial number of", "口語化量詞，建議使用精確正式詞彙"),
        r"\blots of\b": ("numerous / considerable", "口語化量詞，不建議使用於正式文件"),
        r"\bget\b": ("obtain / acquire", "口語動詞，正式寫作建議改用 obtain/acquire"),
        r"\bgot\b": ("obtained / acquired", "口語動詞，正式寫作建議改用 obtained/acquired"),
        r"\bvery fast\b": ("rapidly / with high computational efficiency", "過度口語化的程度修飾"),
        r"\bfast\b": ("rapid / highly efficient", "建議使用更具精確度的詞彙"),
        r"\bhappy\b": ("satisfied / favorably disposed", "過於主觀情緒化的詞彙"),
        r"\breally\b": ("notably / considerably", "口語程度副詞，正式文件中應避免"),
        r"\bbig\b": ("substantial / prominent / significant", "非正式形容詞，缺乏技術精確度"),
        r"\bkind of\b": ("somewhat / to an extent", "非正式模糊用語"),
        r"\bsort of\b": ("somewhat / to an extent", "非正式模糊用語"),
        r"\bdue to the fact that\b": ("because", "贅言（Wordiness），建議直接精簡為 because"),
        r"\bin order to\b": ("to", "非必要冗詞，多數情況下可直接簡化為 to"),
        r"\bneedless to say\b": ("evidently / clearly", "陳詞濫調，建議使用精煉副詞"),
    }

    AWKWARD_COLLOCATIONS = {
        r"\bmake an experiment\b": ("conduct an experiment / perform an experiment", "搭配詞缺陷：英文應使用 conduct/perform/carry out an experiment"),
        r"\bmake research\b": ("conduct research / undertake research", "搭配詞缺陷：應使用 conduct/carry out research"),
        r"\bdo a decision\b": ("make a decision / reach a decision", "搭配詞缺陷：應使用 make/reach a decision"),
        r"\bplay an effect\b": ("exert an effect / produce an impact", "搭配詞缺陷：應使用 exert/have an effect"),
        r"\btake attention\b": ("pay attention / draw attention", "搭配詞缺陷：應使用 pay/draw attention"),
    }

    OVERCLAIMING_PATTERNS = {
        r"\bdefinitely prove(s|d)?\b": ("suggest(s) / provide evidence for", "過度宣稱：論證鮮少能「絕對證明」，建議使用謙抑詞"),
        r"\bcompletely solve(s|d)?\b": ("substantially address(es) / mitigate(s)", "過度宣稱：極少有方案能「完全解決」複雜問題"),
        r"\bundeniably\b": ("compellingly / convincingly", "過於武斷的主觀修飾詞，易招致審閱者反感"),
        r"\bdominate(s|d)? all\b": ("outperform(s) existing / surpass(es)", "過度誇大宣稱，缺乏客觀衡量標準"),
        r"\bwithout any other factors\b": ("primarily / predominantly", "武斷排除其他變因，缺乏因果論證嚴謹性"),
    }

    @classmethod
    def scan(cls, text: str, mode: str = "academic") -> List[PreflightMatch]:
        matches: List[PreflightMatch] = []
        if not text:
            return matches

        # 縮寫檢測
        for pat, (rep, exp) in cls.CONTRACTIONS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                matches.append(PreflightMatch("縮寫禁忌", m.group(0), rep, exp, (m.start(), m.end())))

        # 口語檢測
        for pat, (rep, exp) in cls.INFORMAL_WORDS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                matches.append(PreflightMatch("非正式口語", m.group(0), rep, exp, (m.start(), m.end())))

        # 生硬搭配詞檢測
        for pat, (rep, exp) in cls.AWKWARD_COLLOCATIONS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                matches.append(PreflightMatch("搭配詞缺陷", m.group(0), rep, exp, (m.start(), m.end())))

        # 過度斷言檢測
        for pat, (rep, exp) in cls.OVERCLAIMING_PATTERNS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                matches.append(PreflightMatch("過度宣稱預警", m.group(0), rep, exp, (m.start(), m.end())))

        return matches

    @classmethod
    def fix_all_issues(cls, text: str) -> str:
        res = text
        for pat, (rep, _) in cls.CONTRACTIONS.items():
            res = re.sub(pat, rep, res, flags=re.IGNORECASE)
        for pat, (rep, _) in cls.AWKWARD_COLLOCATIONS.items():
            first_rep = rep.split('/')[0].strip()
            res = re.sub(pat, first_rep, res, flags=re.IGNORECASE)
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
# 2. 右鍵選單與專屬文字組件 (深淺模式與純白高對比)
# ==========================================
def create_academic_context_menu(widget: QTextEdit, is_read_only: bool = False, on_quick_fix=None, is_dark: bool = False, lang: str = "zh_TW") -> QMenu:
    menu = QMenu(widget)
    menu.setFont(QFont("Segoe UI", 10))
    t = I18N.get(lang, I18N["zh_TW"])

    if is_dark:
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b; color: #f8fafc; border: 1px solid #334155;
                border-radius: 8px; padding: 6px 0px; font-family: Segoe UI, sans-serif; font-size: 12px;
            }
            QMenu::item {
                background-color: transparent; color: #f8fafc; padding: 7px 32px 7px 16px;
                min-width: 165px; margin: 1px 4px; border-radius: 4px; font-weight: 500;
            }
            QMenu::item:selected { background-color: #334155; color: #38bdf8; }
            QMenu::item:disabled { color: #64748b; }
            QMenu::separator { height: 1px; background-color: #334155; margin: 5px 8px; }
        """)
    else:
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 8px; padding: 6px 0px; font-family: Segoe UI, sans-serif; font-size: 12px;
            }
            QMenu::item {
                background-color: transparent; color: #0f172a; padding: 7px 32px 7px 16px;
                min-width: 165px; margin: 1px 4px; border-radius: 4px; font-weight: 500;
            }
            QMenu::item:selected { background-color: #eff6ff; color: #1d4ed8; }
            QMenu::item:disabled { color: #94a3b8; }
            QMenu::separator { height: 1px; background-color: #e2e8f0; margin: 5px 8px; }
        """)

    if not is_read_only:
        undo_act = menu.addAction(t["undo"])
        undo_act.setShortcut("Ctrl+Z")
        undo_act.setEnabled(widget.document().isUndoAvailable())
        undo_act.triggered.connect(widget.undo)

        redo_act = menu.addAction(t["redo"])
        redo_act.setShortcut("Ctrl+Y")
        redo_act.setEnabled(widget.document().isRedoAvailable())
        redo_act.triggered.connect(widget.redo)

        menu.addSeparator()

        cut_act = menu.addAction(t["cut"])
        cut_act.setShortcut("Ctrl+X")
        cut_act.setEnabled(widget.textCursor().hasSelection())
        cut_act.triggered.connect(widget.cut)

    copy_act = menu.addAction(t["copy"])
    copy_act.setShortcut("Ctrl+C")
    copy_act.setEnabled(widget.textCursor().hasSelection() if is_read_only else True)
    copy_act.triggered.connect(widget.copy)

    if not is_read_only:
        paste_act = menu.addAction(t["paste"])
        paste_act.setShortcut("Ctrl+V")
        paste_act.setEnabled(bool(QApplication.clipboard().text()))
        paste_act.triggered.connect(widget.paste)

        del_act = menu.addAction(t["delete"])
        del_act.setEnabled(widget.textCursor().hasSelection())
        del_act.triggered.connect(lambda: widget.textCursor().removeSelectedText())

    menu.addSeparator()

    select_all_act = menu.addAction(t["select_all"])
    select_all_act.setShortcut("Ctrl+A")
    select_all_act.triggered.connect(widget.selectAll)

    if not is_read_only:
        clear_act = menu.addAction(t["clear"])
        clear_act.setEnabled(bool(widget.toPlainText().strip()))
        clear_act.triggered.connect(widget.clear)

        if on_quick_fix:
            menu.addSeparator()
            qf_act = menu.addAction(t["auto_fix_menu"])
            qf_act.triggered.connect(on_quick_fix)

    return menu

class AcademicTextEdit(QTextEdit):
    def __init__(self, parent=None, on_quick_fix=None, is_dark: bool = False, lang: str = "zh_TW"):
        super().__init__(parent)
        self.on_quick_fix = on_quick_fix
        self.is_dark = is_dark
        self.lang = lang

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
        menu = create_academic_context_menu(self, is_read_only=False, on_quick_fix=self.on_quick_fix, is_dark=self.is_dark, lang=self.lang)
        pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
        menu.exec(pos)

class AcademicTextBrowser(QTextBrowser):
    def __init__(self, parent=None, is_dark: bool = False, lang: str = "zh_TW"):
        super().__init__(parent)
        self.is_dark = is_dark
        self.lang = lang

    def set_theme_mode(self, is_dark: bool):
        self.is_dark = is_dark
        text_col = "#ffffff" if is_dark else "#0f172a"
        bg_col = "#1e293b" if is_dark else "#ffffff"
        border_col = "#334155" if is_dark else "#cbd5e1"

        self.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg_col};
                color: {text_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 10px;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }}
        """)

    def contextMenuEvent(self, event):
        menu = create_academic_context_menu(self, is_read_only=True, is_dark=self.is_dark, lang=self.lang)
        pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
        menu.exec(pos)

# ==========================================
# 3. 結構化 Schema 定義 (支援 3~4 種多樣改寫與搭配詞選項)
# ==========================================
class RevisionOption(BaseModel):
    style_label: str = Field(description="修改選項標籤（如：標準道地搭配 / 簡潔有力 / 謹慎謙抑 / 權威書面語）")
    revised_text: str = Field(description="修改後的英文句子")
    rationale_zh: str = Field(default="", description="中文理由說明（若英文模式請填純英文理由）")
    rationale_en: str = Field(default="", description="Stylistic or grammatical rationale in English")

class IssueItem(BaseModel):
    category: Literal["Logic Error", "Flawed Deduction", "Grammar & Mechanics", "Rhetorical Defect", "Collocation Defect"] = "Collocation Defect"
    category_zh: str = Field(default="道地搭配詞", description="問題類型的中文名稱")
    severity: Literal["Critical", "Major", "Minor"] = "Major"
    original_text: str = Field(description="出現問題的原文片段（必須完全精確比對輸入文本）")
    meaning_analysis_zh: str = Field(default="", description="原句文意解析（正體中文；英文模式請填純英文）")
    meaning_analysis_en: str = Field(default="", description="Semantic and contextual analysis in English")
    reviewer_comment_en: str = Field(default="", description="Reviewer/Editor critique in English")
    reviewer_comment_zh: str = Field(default="", description="審查員評論意見（正體中文；英文模式請填純英文）")
    revision_options: List[RevisionOption] = Field(
        default_factory=list,
        description="提供 3 至 4 個不同語感風格或道地搭配詞的具體修改選項 (Option A, B, C, D)"
    )

class ResearchRecommendation(BaseModel):
    gap_identified_zh: str = Field(default="", description="論述、實證缺失或溝通策略盲點 (正體中文；若英文模式填純英文)")
    gap_identified_en: str = Field(default="", description="Strategic evidence gap or communication misalignment (English)")
    severity: Literal["Must Address (必補/致命缺陷)", "Strongly Recommended (強烈建議補強)", "Optional (可選加分項)"] = "Strongly Recommended (強烈建議補強)"
    action_type: str = Field(default="補充消融實驗/顯著性分析", description="補強類型或具體維度")
    concrete_proposal_zh: str = Field(default="", description="具體補做或策略提升方案 (正體中文；若英文模式填純英文)")
    concrete_proposal_en: str = Field(default="", description="Concrete actionable proposal or protocol (English)")
    impact_on_acceptance_zh: str = Field(default="", description="對審核防禦、錄用率或說服力的實質助益 (正體中文；若英文模式填純英文)")
    impact_on_acceptance_en: str = Field(default="", description="Defense impact or persuasive uplift (English)")

class AcademicReviewReport(BaseModel):
    article_gist_zh: str = Field(default="", description="輸入文本的主旨判斷與整體寫作品質診斷（正體中文；若英文模式填純英文）")
    article_gist_en: str = Field(default="", description="Executive summary of the manuscript/draft in English")
    overall_assessment_en: str = Field(default="Comprehensive review completed.", description="Overall review feedback in English")
    overall_assessment_zh: str = Field(default="已完成綜合審查與實證缺陷檢驗。", description="綜合就緒度評審意見（正體中文；若英文模式填純英文）")
    research_recommendations: List[ResearchRecommendation] = Field(
        default_factory=list,
        description="提出 2 至 4 點實質情境補強建議（如實驗、論據、架構或說服力補強）"
    )
    revised_full_text: str = Field(default="", description="綜合各項最佳建議後的完整修訂後英文文章全文")
    issues: List[IssueItem] = Field(
        default_factory=list,
        description="逐句深度窮舉排查清單，列出 6 至 10 處包含搭配詞缺陷、修辭語氣、邏輯瑕疵、文法精確度的具體改進點，每項皆提供 3~4 個替代選項"
    )

# ==========================================
# 4. 線上 API 設定與精靈視窗
# ==========================================
class ApiSettingsDialog(QDialog):
    def __init__(self, parent=None, config: dict = None, is_dark: bool = False, lang: str = "zh_TW"):
        super().__init__(parent)
        self.config = config or {}
        self.is_dark = is_dark
        self.lang = lang
        is_en = (lang == "en_US")
        self.setWindowTitle("⚙️ Cloud LLM API Settings" if is_en else "⚙️ 線上 LLM API 設定")
        self.resize(540, 340)
        self.init_ui()

    def init_ui(self):
        is_en = (self.lang == "en_US")
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
                background-color: {card_bg}; color: {fg};
                border: 1px solid {border_col}; border-radius: 5px; padding: 6px 8px; font-size: 12px;
            }}
            QPushButton {{ border-radius: 5px; padding: 6px 14px; font-size: 12px; font-weight: bold; }}
        """)

        form = QFormLayout()
        form.setSpacing(10)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "DeepSeek (Recommended / Cost-effective)" if is_en else "DeepSeek (推薦學術推理，性價比首選)",
            "OpenAI (GPT-4o / o1)",
            "Google Gemini (gemini-1.5-pro / 2.0-flash)",
            "Groq (Ultra-fast Inference)" if is_en else "Groq (超高速推論)",
            "Custom OpenAI Endpoint" if is_en else "自訂 OpenAI 相容端點"
        ])
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        form.addRow("Provider Preset:" if is_en else "服務商預設:", self.preset_combo)

        self.url_edit = QLineEdit(self.config.get("api_url", "https://api.deepseek.com/v1"))
        form.addRow("Base URL:" if is_en else "API 端點 (Base URL):", self.url_edit)

        self.key_edit = QLineEdit(self.config.get("api_key", ""))
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("Enter API Key (sk-...)" if is_en else "請輸入您的 API Key (如 sk-...)")
        form.addRow("API Key:" if is_en else "API 金鑰 (API Key):", self.key_edit)

        self.model_edit = QLineEdit(self.config.get("api_model", "deepseek-chat"))
        form.addRow("Model Name:" if is_en else "模型名稱 (Model Name):", self.model_edit)

        layout.addLayout(form)

        info_lbl = QLabel(
            "💡 Compatible with all standard OpenAI API providers. Your key is stored strictly on your local computer." if is_en
            else "💡 支援任何相容 OpenAI 規格的線上服務。金鑰僅儲存於您本機設定檔，絕不上傳。"
        )
        info_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        btn_box = QHBoxLayout()
        self.test_btn = QPushButton("📡 Test Connection" if is_en else "📡 測試連線")
        self.test_btn.setStyleSheet("background-color: #e2e8f0; color: #0f172a; border: 1px solid #cbd5e1;")
        self.test_btn.clicked.connect(self.test_connection)
        btn_box.addWidget(self.test_btn)
        btn_box.addStretch()

        self.save_btn = QPushButton("Save Settings" if is_en else "儲存設定")
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
        is_en = (self.lang == "en_US")
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        model = self.model_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "Notice" if is_en else "提示", "Please enter your API Key first." if is_en else "請先輸入 API Key。")
            return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("Testing..." if is_en else "連線測試中...")
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
                    QMessageBox.information(self, "Success" if is_en else "成功", f"✅ Connection verified! Provider responded.\nModel: {model}")
                else:
                    QMessageBox.critical(self, "Error" if is_en else "失敗", f"❌ API Error ({res.status_code}):\n{res.text[:300]}")
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed" if is_en else "連線失敗", f"Cannot connect:\n{e}")
        finally:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("📡 Test Connection" if is_en else "📡 測試連線")

    def save_and_close(self):
        self.config["api_url"] = self.url_edit.text().strip()
        self.config["api_key"] = self.key_edit.text().strip()
        self.config["api_model"] = self.model_edit.text().strip()
        save_config(self.config)
        self.accept()

# ==========================================
# 4.1 本機 Ollama 環境精靈 (支援中英文)
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
                    self.finished.emit(False, f"HTTP {resp.status_code}", "")
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
                                self.progress.emit(pct, f"Downloading: {mb_done:.1f} MB / {mb_tot:.1f} MB ({pct}%)")
                            else:
                                mb_done = downloaded / (1024 * 1024)
                                self.progress.emit(0, f"Downloaded: {mb_done:.1f} MB")
            self.finished.emit(True, "Done", dest_path)
        except Exception as e:
            self.finished.emit(False, str(e), "")

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
                    self.progress.emit(0, status or "Processing...")
            self.finished.emit(True, f"Model [{self.model_name}] deployed successfully!")
        except Exception as e:
            self.finished.emit(False, str(e))

class OllamaEnvironmentDialog(QDialog):
    def __init__(self, parent=None, is_dark: bool = False, lang: str = "zh_TW"):
        super().__init__(parent)
        self.is_dark = is_dark
        self.lang = lang
        is_en = (lang == "en_US")
        self.setWindowTitle("📥 Local Ollama & Model Wizard" if is_en else "📥 本機 Ollama 環境與模型管理精靈")
        self.resize(700, 590)
        self.download_worker = None
        self.pull_worker = None
        self.models_updated = False
        self.installed_models = []
        self.init_ui()
        self.check_status()

    def init_ui(self):
        is_en = (self.lang == "en_US")
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
                background-color: {card_bg}; border: 1px solid {border_col}; border-radius: 8px; padding: 10px;
            }}
            QLineEdit {{
                background-color: {card_bg}; color: {fg}; border: 1px solid {border_col};
                border-radius: 5px; padding: 5px 8px; font-size: 12px;
            }}
        """)

        title_box = QVBoxLayout()
        h_title = QLabel("📥 Local Ollama Environment & Model Manager" if is_en else "📥 本機 Ollama 環境與學術模型管理精靈")
        h_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        desc = QLabel(
            "Automatic inference engine detection and one-click deployment for top-tier open-source models." if is_en
            else "專為學者打造：自動檢測本機推論引擎、一鍵拉取國際頂刊審稿精選大語言模型。"
        )
        desc.setStyleSheet(f"color: {sub_fg}; font-size: 11px;")
        desc.setWordWrap(True)
        title_box.addWidget(h_title)
        title_box.addWidget(desc)
        layout.addLayout(title_box)

        # 區塊 1：Ollama 執行環境
        self.ollama_card = QFrame()
        self.ollama_card.setFrameShape(QFrame.Box)
        ollama_card_layout = QVBoxLayout(self.ollama_card)
        ollama_card_layout.setSpacing(8)

        card1_title = QLabel("1. Ollama Engine Status:" if is_en else "1. Ollama 本機推論引擎狀態:")
        card1_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        ollama_card_layout.addWidget(card1_title)

        self.ollama_status_lbl = QLabel("Detecting local Ollama environment..." if is_en else "正在檢測本機 Ollama 環境...")
        self.ollama_status_lbl.setFont(QFont("Segoe UI", 10))
        ollama_card_layout.addWidget(self.ollama_status_lbl)

        ollama_btn_box = QHBoxLayout()
        self.install_ollama_btn = QPushButton("🌐 Download Ollama Installer" if is_en else "🌐 一鍵下載並安裝 Ollama (官方安裝檔)")
        self.install_ollama_btn.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: #ffffff; font-weight: bold; border-radius: 5px; padding: 6px 12px; font-size: 11px; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.install_ollama_btn.clicked.connect(self.start_download_ollama)
        ollama_btn_box.addWidget(self.install_ollama_btn)

        self.start_service_btn = QPushButton("🚀 Start Ollama Service" if is_en else "🚀 一鍵啟動 Ollama 服務")
        self.start_service_btn.setStyleSheet("""
            QPushButton { background-color: #059669; color: #ffffff; font-weight: bold; border-radius: 5px; padding: 6px 12px; font-size: 11px; }
            QPushButton:hover { background-color: #047857; }
        """)
        self.start_service_btn.clicked.connect(self.start_ollama_service)
        ollama_btn_box.addWidget(self.start_service_btn)

        self.recheck_btn = QPushButton("🔄 Re-check" if is_en else "🔄 重新檢測")
        self.recheck_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {card_bg}; color: {fg}; border: 1px solid {border_col}; border-radius: 5px; padding: 6px 12px; font-size: 11px; }}
            QPushButton:hover {{ background-color: {'#334155' if self.is_dark else '#e2e8f0'}; }}
        """)
        self.recheck_btn.clicked.connect(self.check_status)
        ollama_btn_box.addWidget(self.recheck_btn)
        ollama_btn_box.addStretch()
        ollama_card_layout.addLayout(ollama_btn_box)
        layout.addWidget(self.ollama_card)

        # 區塊 2：精選模型推薦
        self.model_card = QFrame()
        self.model_card.setFrameShape(QFrame.Box)
        model_layout = QVBoxLayout(self.model_card)
        model_layout.setSpacing(10)

        card2_title = QLabel("2. Curated Language Models for Peer Review:" if is_en else "2. 學術同儕審查精選模型 (點擊一鍵安裝):")
        card2_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        model_layout.addWidget(card2_title)

        self.model_btns = {}
        models_data = [
            ("llama3.1:8b", "⚡ Lightweight & Agile (~4.7 GB)" if is_en else "⚡ 輕量通用推薦 (約 4.7 GB)", "Suitable for 8GB+ RAM, fast and robust phrasing"),
            ("qwen2.5:14b", "🏆 Academic Benchmark (~9.0 GB, Recommended)" if is_en else "🏆 學術深度首選 (約 9.0 GB，★ 推薦)", "Rigorous bilingual logic & peer-review critique"),
            ("deepseek-r1:14b", "🔬 Deep Reasoning Flagship (~9.0 GB)" if is_en else "🔬 頂會旗艦推理 (約 9.0 GB)", "Uncompromised chain-of-thought analysis")
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

            btn = QPushButton("📥 Pull Model" if is_en else "📥 下載此模型")
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

        # 自訂模型輸入
        custom_box = QHBoxLayout()
        self.custom_model_edit = QLineEdit()
        self.custom_model_edit.setPlaceholderText("Or enter custom Ollama model (e.g. qwen2.5:7b)" if is_en else "或輸入自訂 Ollama 模型名稱 (例如: qwen2.5:7b)")
        custom_box.addWidget(self.custom_model_edit)

        self.custom_pull_btn = QPushButton("📥 Pull Custom" if is_en else "📥 下載自訂模型")
        self.custom_pull_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {card_bg}; color: {fg}; border: 1px solid {border_col}; border-radius: 5px; padding: 5px 12px; font-weight: 500; font-size: 11px; }}
            QPushButton:hover {{ background-color: {'#334155' if self.is_dark else '#e2e8f0'}; }}
        """)
        self.custom_pull_btn.clicked.connect(self.pull_custom_model)
        custom_box.addWidget(self.custom_pull_btn)
        model_layout.addLayout(custom_box)
        layout.addWidget(self.model_card)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("font-size: 11px; color: #38bdf8;")
        layout.addWidget(self.progress_label)

        bottom_box = QHBoxLayout()
        bottom_box.addStretch()
        close_btn = QPushButton("Done and Return" if is_en else "完成並返回主畫面")
        close_btn.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: #ffffff; font-weight: bold; border-radius: 5px; padding: 7px 16px; font-size: 12px; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        close_btn.clicked.connect(self.accept)
        bottom_box.addWidget(close_btn)
        layout.addLayout(bottom_box)

    def check_status(self):
        is_en = (self.lang == "en_US")
        which_path = shutil.which("ollama")
        appdata_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        is_installed = bool(which_path) or os.path.exists(appdata_path)
        is_running = False
        try:
            r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
            if r.status_code == 200:
                is_running = True
        except Exception:
            is_running = False

        if not is_installed:
            self.ollama_status_lbl.setText("❌ <b>Ollama not detected</b>: click below to download the official installer." if is_en else "❌ <b>尚未偵測到 Ollama 程式</b>：請點擊下方按鈕自動下載官方安裝程式。")
            self.ollama_status_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.install_ollama_btn.setVisible(True)
            self.start_service_btn.setVisible(False)
            self.model_card.setEnabled(False)
        elif not is_running:
            self.ollama_status_lbl.setText("⚠️ <b>Ollama is installed, but the background service is not running.</b>" if is_en else "⚠️ <b>Ollama 已安裝於本機，但背景服務尚未啟動</b>")
            self.ollama_status_lbl.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.install_ollama_btn.setVisible(False)
            self.start_service_btn.setVisible(True)
            self.model_card.setEnabled(False)
        else:
            self.ollama_status_lbl.setText("✅ <b>Ollama service running normally (Port 11434 connected).</b>" if is_en else "✅ <b>Ollama 服務運作正常 (Port 11434 已連線)</b> ─ 本機推論引擎已準備就緒。")
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
            QMessageBox.warning(self, "Error", "ollama.exe not found.")
            return
        try:
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            subprocess.Popen([exec_path, "serve"], creationflags=creation_flags)
            self.ollama_status_lbl.setText("Starting service...")
            QTimer.singleShot(2500, self.check_status)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not launch Ollama: {e}")

    def start_download_ollama(self):
        self.install_ollama_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Downloading official Ollama installer...")

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
            QMessageBox.information(self, "Download Complete", "Ollama installer downloaded! Launching setup wizard now.")
            subprocess.Popen([path])
        else:
            QMessageBox.critical(self, "Error", f"Failed: {msg}")

    def refresh_models(self):
        is_en = (self.lang == "en_US")
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
                    btn.setText("✅ Ready" if is_en else "✅ 已就緒")
                    btn.setEnabled(False)
                else:
                    btn.setText("📥 Pull Model" if is_en else "📥 下載此模型")
                    btn.setEnabled(True)
        except Exception:
            pass

    def start_pull_model(self, model_name: str):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText(f"Preparing to pull model [{model_name}]...")

        self.pull_worker = ModelPullWorker(model_name)
        self.pull_worker.progress.connect(self.on_pull_progress)
        self.pull_worker.finished.connect(lambda s, m: self.on_pull_finished(s, m, model_name))
        self.pull_worker.start()

    def pull_custom_model(self):
        m_name = self.custom_model_edit.text().strip()
        if not m_name:
            return
        self.start_pull_model(m_name)

    def on_pull_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.progress_label.setText(msg)

    def on_pull_finished(self, success: bool, msg: str, model_name: str):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        if success:
            self.models_updated = True
            self.refresh_models()
            QMessageBox.information(self, "Success", f"🎉 Model [{model_name}] deployed successfully!")
        else:
            QMessageBox.critical(self, "Error", f"Model pull failed:\n{msg}")

# ==========================================
# 4.2 軟體線上更新視窗
# ==========================================
def parse_version_tuple(v_str: str) -> tuple:
    nums = re.findall(r"\d+", v_str)
    return tuple(map(int, nums)) if nums else (0, 0, 0)

class UpdateCheckWorker(QThread):
    check_finished = Signal(bool, str, str, str, str)

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
                    self.check_finished.emit(False, "", "", "", f"HTTP {resp.status_code}")
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
            self.check_finished.emit(False, "", "", "", str(e))

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
                    self.finished.emit(False, f"HTTP {resp.status_code}")
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
                                self.progress.emit(pct, f"Downloading: {mb_done:.1f} MB / {mb_tot:.1f} MB ({pct}%)")
                            else:
                                mb_done = downloaded / (1024 * 1024)
                                self.progress.emit(0, f"Downloaded: {mb_done:.1f} MB")
            self.finished.emit(True, dest_path)
        except Exception as e:
            self.finished.emit(False, str(e))

class UpdateDialog(QDialog):
    def __init__(self, parent=None, is_dark: bool = False, config: dict = None, lang: str = "zh_TW"):
        super().__init__(parent)
        self.is_dark = is_dark
        self.config = config or {}
        self.lang = lang
        is_en = (lang == "en_US")
        self.setWindowTitle("🚀 Check for Updates" if is_en else "🚀 軟體版本與線上更新")
        self.resize(560, 420)
        self.check_worker = None
        self.download_worker = None
        self.latest_download_url = ""
        self.init_ui()
        self.start_check()

    def init_ui(self):
        is_en = (self.lang == "en_US")
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
            QTextBrowser {{ background-color: {card_bg}; color: {fg}; border: 1px solid {border_col}; border-radius: 6px; padding: 8px; font-size: 11px; }}
            QLineEdit {{ background-color: {card_bg}; color: {fg}; border: 1px solid {border_col}; border-radius: 5px; padding: 4px 8px; font-size: 11px; }}
        """)

        status_card = QFrame()
        status_card.setStyleSheet(f"background-color: {card_bg}; border: 1px solid {border_col}; border-radius: 8px; padding: 10px;")
        s_layout = QVBoxLayout(status_card)

        cur_v_lbl = QLabel(f"<b>Current Installed Version:</b> v{APP_VERSION} (Pre-release)" if is_en else f"<b>目前已安裝版本:</b> v{APP_VERSION} (封閉開發版)")
        cur_v_lbl.setFont(QFont("Segoe UI", 11))
        s_layout.addWidget(cur_v_lbl)

        self.status_msg_lbl = QLabel("Querying update server..." if is_en else "正在連線檢查最新版本資訊...")
        self.status_msg_lbl.setStyleSheet(f"color: {sub_fg}; font-size: 11px;")
        s_layout.addWidget(self.status_msg_lbl)
        layout.addWidget(status_card)

        cl_title = QLabel("Release Notes:" if is_en else "更新日誌與新版異動 (Release Notes):")
        cl_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(cl_title)

        self.changelog_browser = QTextBrowser()
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
        url_lbl = QLabel("Update Endpoint:" if is_en else "更新伺服器端點:")
        url_lbl.setStyleSheet(f"color: {sub_fg}; font-size: 10px;")
        adv_box.addWidget(url_lbl)

        saved_url = self.config.get("update_url", DEFAULT_UPDATE_URL)
        self.url_edit = QLineEdit(saved_url)
        adv_box.addWidget(self.url_edit)
        layout.addLayout(adv_box)

        btn_box = QHBoxLayout()
        self.recheck_btn = QPushButton("🔄 Check Again" if is_en else "🔄 重新檢查")
        self.recheck_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {card_bg}; color: {fg}; border: 1px solid {border_col}; border-radius: 5px; padding: 6px 14px; font-size: 11px; }}
            QPushButton:hover {{ background-color: {'#334155' if self.is_dark else '#e2e8f0'}; }}
        """)
        self.recheck_btn.clicked.connect(self.start_check)
        btn_box.addWidget(self.recheck_btn)
        btn_box.addStretch()

        self.download_btn = QPushButton("📥 Download & Upgrade" if is_en else "📥 立即下載並安裝更新")
        self.download_btn.setEnabled(False)
        self.download_btn.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: #ffffff; font-weight: bold; border-radius: 5px; padding: 6px 16px; font-size: 11px; }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #475569; color: #94a3b8; }
        """)
        self.download_btn.clicked.connect(self.start_download)
        btn_box.addWidget(self.download_btn)

        close_btn = QPushButton("Close" if is_en else "關閉")
        close_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {card_bg}; color: {fg}; border: 1px solid {border_col}; border-radius: 5px; padding: 6px 14px; font-size: 11px; }}
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
        self.status_msg_lbl.setText("Querying..." if self.lang == "en_US" else "正在查詢最新版本資訊...")
        self.status_msg_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        self.changelog_browser.clear()

        self.check_worker = UpdateCheckWorker(url)
        self.check_worker.check_finished.connect(self.on_check_finished)
        self.check_worker.start()

    def on_check_finished(self, has_update: bool, latest_ver: str, changelog: str, download_url: str, err_msg: str):
        is_en = (self.lang == "en_US")
        self.recheck_btn.setEnabled(True)
        if err_msg:
            self.status_msg_lbl.setText(f"⚠️ {err_msg}")
            self.status_msg_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.changelog_browser.setPlainText("Cannot connect to update server.")
            return

        self.latest_download_url = download_url
        if has_update:
            self.status_msg_lbl.setText(f"🎉 New update available: <b>v{latest_ver}</b>" if is_en else f"🎉 發現新版本：<b>v{latest_ver}</b> (建議立即升級)")
            self.status_msg_lbl.setStyleSheet("color: #10b981; font-size: 11px;")
            self.changelog_browser.setPlainText(changelog)
            self.download_btn.setEnabled(bool(download_url))
        else:
            self.status_msg_lbl.setText(f"✨ Up to date (v{APP_VERSION})!" if is_en else f"✨ 您的軟體已是最新版本 (v{APP_VERSION})！無需更新。")
            self.status_msg_lbl.setStyleSheet("color: #10b981; font-size: 11px;")
            self.changelog_browser.setPlainText(changelog or "Current build is operating with latest features.")

    def start_download(self):
        if not self.latest_download_url:
            return
        self.recheck_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_lbl.setVisible(True)
        self.progress_lbl.setText("Downloading...")

        self.download_worker = UpdateDownloadWorker(self.latest_download_url)
        self.download_worker.progress.connect(lambda p, m: (self.progress_bar.setValue(p), self.progress_lbl.setText(m)))
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_finished(self, success: bool, path_or_err: str):
        is_en = (self.lang == "en_US")
        self.progress_bar.setVisible(False)
        self.progress_lbl.setVisible(False)
        self.recheck_btn.setEnabled(True)
        if success and os.path.exists(path_or_err):
            reply = QMessageBox.question(
                self, "Ready to Install" if is_en else "下載完成",
                "New version downloaded. Launch installer now to upgrade?" if is_en else "🎉 新版安裝程式已成功下載！\n\n是否立即啟動安裝精靈自動升級？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                subprocess.Popen([path_or_err])
                QApplication.quit()
        else:
            QMessageBox.critical(self, "Download Failed", f"Error:\n{path_or_err}")
            self.download_btn.setEnabled(True)

# ==========================================
# 5. 後端推論線程 (多情境、章節局部針對性、純英文指令集)
# ==========================================
class ReviewWorker(QThread):
    finished = Signal(AcademicReviewReport)
    error = Signal(str)
    chunk_received = Signal(str, int)

    def __init__(self, text: str, engine_mode: str, model_name: str, api_config: dict,
                 ui_language: str, writing_mode: str, context_scope: str, section_target: str):
        super().__init__()
        self.text = text
        self.engine_mode = engine_mode
        self.model_name = model_name
        self.api_config = api_config
        self.ui_language = ui_language
        self.writing_mode = writing_mode
        self.context_scope = context_scope
        self.section_target = section_target

    def build_system_prompt(self) -> str:
        mode_info = WRITING_MODES.get(self.writing_mode, WRITING_MODES["academic"])
        is_en = (self.ui_language == "en_US")

        # 找尋章節名稱
        section_name = self.section_target
        for s_id, s_zh, s_en in mode_info["sections"]:
            if s_id == self.section_target:
                section_name = s_en if is_en else s_zh
                break

        persona = mode_info["persona_en"] if is_en else mode_info["persona_zh"]

        # 範疇提示
        if self.context_scope == "partial":
            scope_prompt = (
                f"【IMPORTANT CONTEXT SCOPE】: The user has indicated that this input text is a SPECIFIC PARTIAL EXCERPT "
                f"from the [{section_name}] section. You must focus your critique specifically on the conventions, "
                f"standards, and requirements of this particular section. Do NOT penalize the text for omitting "
                f"information that belongs in other sections of the document."
            )
        else:
            scope_prompt = (
                "【IMPORTANT CONTEXT SCOPE】: This is a COMPREHENSIVE / FULL text. Evaluate its overarching narrative arc, "
                "logical continuity, thesis cohesion, and complete structural balance."
            )

        if is_en:
            prompt = f"""You are the {persona}.
CRITICAL OPERATING DIRECTIVE:
1. PURE ENGLISH REQUIREMENT: The user has set the workspace language to ENGLISH. You MUST output ALL texts, critiques, comments, recommendations, rationales, and assessments in 100% PURE, PROFESSIONAL ENGLISH.
DO NOT include any Chinese characters anywhere in your JSON output.
All fields (including *_zh fields) MUST contain high-standard English text.

{scope_prompt}

You must evaluate the input draft across two critical dimensions:

DIMENSION 1: STRATEGIC & EMPIRICAL RECOMMENDATIONS (research_recommendations)
- Point out 2 to 4 actionable, high-impact improvements tailored to this writing context ({mode_info['name_en']}).
- For academic writing: ablation studies, statistical significance, causal validation, confounding variables.
- For correspondence: tone diplomacy, explicit calls-to-action, risk mitigation.
- For application: impact quantification, action verbs, personal differentiation.
- For business: strategic feasibility, ROI, execution roadmaps.
- Provide gap_identified_en, concrete_proposal_en, impact_on_acceptance_en.

DIMENSION 2: SENTENCE-BY-SENTENCE EXHAUSTIVE SCRUTINY & REVISION (issues)
【EXHAUSTIVE THOROUGHNESS】:
A draft of 150-300 words always has multiple subtle weaknesses. You MUST scan sentence-by-sentence and identify 6 to 10 concrete improvement items. Do NOT return merely 2 or 3 issues!

CATEGORIES TO COVER:
1. "Collocation Defect" (CRITICAL FOCUS): Flag unnatural, unidiomatic, or loose word pairings (e.g. 'make an experiment', 'play a big role', 'do a decision', 'statistically big difference').
2. "Logic Error": Contradictions, unsupported presuppositions, internal inconsistencies.
3. "Flawed Deduction": Leaps in logic, overclaiming, hasty generalization.
4. "Grammar & Mechanics": Faulty parallelism, dangling modifiers, subject-verb agreement, tense shifts.
5. "Rhetorical Defect": Lack of hedging, wordiness, inappropriate register.

【MULTI-OPTION GENERATION REQUIREMENT (3 to 4 Options per issue)】:
For EVERY issue (especially Collocations and Rhetoric), you MUST provide 3 to 4 distinct, authentic alternative revisions in `revision_options`:
- Option A: Standard / High-Frequency Native Phrasing
- Option B: High-Impact Concise / Action-Oriented
- Option C: Cautious & Hedged / Nuanced
- Option D: Authoritative / Formal Register
Explain the exact stylistic nuance of each option in rationale_en.

JSON FORMATTING: Ensure output is strictly valid JSON matching the schema."""
        else:
            prompt = f"""你是一名【{persona}】。
請注意：本系統使用者為【正體中文（繁體中文，臺灣慣用語彙）】使用者，所有中文說明與解析必須使用道地正體中文，切勿使用簡體字。

{scope_prompt}

請針對輸入的英文草稿，在【{mode_info['name_zh']}】情境下進行兩大核心維度的【深度極限審查】：

==================================================
維度一：【上下文論點完整性與實證/策略補強建議 (research_recommendations)】
==================================================
請穿透至該段落背後的邏輯與證據鏈：
- 若為學術論文：檢視因果推論、消融實驗、顯著性檢定、混雜變因控制與防禦審稿人質疑之方案。
- 若為專業書信：檢視語氣得體性、溝通透明度、明確行動呼籲與利益關係人對齊。
- 若為申請文件：檢視個人動機說服力、成就量化動詞、避免陳詞濫調與目標契合度。
- 若為商務報告：檢視數據洞察支撐、執行可行性與ROI決策論述。
- 列出 2 至 4 點實質補強方案，每一項均需提供【中英雙語對照】。

==================================================
維度二：【逐句穿透式窮舉審查與道地搭配詞改寫 (issues)】
==================================================
【徹底度嚴格要求】：一段 150~300 字的草稿必然隱藏諸多不成熟之處。你【必須】進行逐句深度排查，深入挖掘出 6 至 10 個具體的改進點！絕不允許僅回傳 2-3 處！

審查面向必須全面覆蓋：
1. 道地搭配詞 (Collocation Defect，★核心重點)：精準標記中式英文搭配、動名不合、非自然詞組（如 make research ➔ conduct research; play an effect ➔ exert an effect; statistically big ➔ statistically significant）。
2. 邏輯矛盾 (Logic Error)：隱含假設破綻、論點前後抵觸。
3. 推論缺陷 (Flawed Deduction)：推論跳躍、過度宣稱（Overclaiming）、因果倒置。
4. 文法與句構 (Grammar & Mechanics)：懸垂修飾、被動語態濫用、主謂不合、平行結構瑕疵。
5. 修辭風格 (Rhetorical Defect)：缺乏謙抑修辭、非正式俚語、贅詞冗長。

【多選項生成規範 (每項問題提供 3 至 4 個風格選項)】：
對於每處問題，必須在 revision_options 提供 3 至 4 個不同語感與搭配維度的改寫選項：
- 選項 A：標準規範／高頻道地搭配
- 選項 B：簡練高能／行動導向
- 選項 C：學術謙抑／謹慎精確
- 選項 D：權威正式／書面典雅
每一選項均需詳述其語境與語感差異！

【格式規範】：JSON 字串中若引用英文詞句，請務必使用全形引號「」或『』，切勿直接使用未跳脫的半形雙引號。請確保輸出為符合 Schema 的合法 JSON。"""

        return prompt

    def run(self):
        system_prompt = self.build_system_prompt()
        full_content = ""
        chunk_count = 0

        try:
            if self.engine_mode == "ollama":
                response_stream = ollama.chat(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Please critically and exhaustively review the following text:\n\n{self.text}"}
                    ],
                    format=AcademicReviewReport.model_json_schema(),
                    options={"temperature": 0.35, "num_ctx": 16384, "num_predict": -1},
                    stream=True
                )
                for chunk in response_stream:
                    delta = chunk.get('message', {}).get('content', '')
                    if delta:
                        full_content += delta
                        chunk_count += 1
                        self.chunk_received.emit(delta, chunk_count)
            else:
                api_url = self.api_config.get("api_url", "https://api.deepseek.com/v1").rstrip('/')
                api_key = self.api_config.get("api_key", "").strip()
                model = self.api_config.get("api_model", "deepseek-chat").strip()
                if not api_key:
                    raise ValueError("API Key not configured. Please open API Settings.")

                endpoint = f"{api_url}/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                schema_json = json.dumps(AcademicReviewReport.model_json_schema(), ensure_ascii=False)
                prompt_with_schema = f"{system_prompt}\n\nYou MUST respond strictly in valid JSON matching this JSON Schema:\n{schema_json}"

                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt_with_schema},
                        {"role": "user", "content": f"Please critically and exhaustively review the following text:\n\n{self.text}"}
                    ],
                    "temperature": 0.35,
                    "stream": True,
                    "response_format": {"type": "json_object"}
                }

                with httpx.Client(timeout=120.0) as client:
                    with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            err_body = response.read().decode('utf-8', errors='ignore')
                            raise ValueError(f"API Error ({response.status_code}):\n{err_body}")

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
                raise ValueError(f"Could not parse model JSON response.\nFragment:\n{raw_content[-200:]}")

            # 數據容錯與補齊
            valid_issues = []
            for raw_issue in data.get('issues', []):
                if not isinstance(raw_issue, dict) or not raw_issue.get('original_text'):
                    continue
                if not raw_issue.get('category'):
                    raw_issue['category'] = 'Collocation Defect'
                if not raw_issue.get('severity'):
                    raw_issue['severity'] = 'Major'
                if not raw_issue.get('revision_options'):
                    raw_issue['revision_options'] = [{
                        "style_label": "Standard Idiomatic Phrasing",
                        "revised_text": raw_issue.get('original_text', ''),
                        "rationale_zh": "優化道地語感與表達",
                        "rationale_en": "Optimized for natural native register."
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
                try:
                    valid_recs.append(ResearchRecommendation(**raw_rec))
                except Exception:
                    continue
            data['research_recommendations'] = valid_recs

            if not data.get('revised_full_text'):
                data['revised_full_text'] = self.text

            report = AcademicReviewReport(**data)
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))

# ==========================================
# 6. 建議卡片組件 (中英對照或純英文)
# ==========================================
class ResearchRecommendationCard(QFrame):
    def __init__(self, rec: ResearchRecommendation, is_dark: bool = False, lang: str = "zh_TW"):
        super().__init__()
        self.rec = rec
        self.is_dark = is_dark
        self.lang = lang
        self.init_ui()

    def init_ui(self):
        is_en = (self.lang == "en_US")
        self.setFrameShape(QFrame.StyledPanel)

        if self.is_dark:
            self.setStyleSheet("""
                ResearchRecommendationCard {
                    background-color: #1e1b4b; border: 1px solid #4338ca; border-left: 4px solid #a855f7;
                    border-radius: 8px; margin-bottom: 10px;
                }
                ResearchRecommendationCard:hover { border-color: #c084fc; }
            """)
            text_title = "#f8fafc"
            box_bg = "#0f172a"
            box_border = "#334155"
            zh_color = "#e9d5ff"
            en_color = "#c084fc"
        else:
            self.setStyleSheet("""
                ResearchRecommendationCard {
                    background-color: #faf5ff; border: 1px solid #d8b4fe; border-left: 4px solid #7c3aed;
                    border-radius: 8px; margin-bottom: 10px;
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

        # 1. 缺失分析
        gap_box = QFrame()
        gap_box.setStyleSheet(f"background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 6px; padding: 6px;")
        g_layout = QVBoxLayout(gap_box)
        g_layout.setContentsMargins(8, 6, 8, 6)
        g_layout.setSpacing(3)

        title_text = "<b>⚠️ Strategic / Empirical Gap Analysis:</b>" if is_en else "<b>⚠️ 上下文與論點缺失分析 (Evidence Gap):</b>"
        g_title = QLabel(title_text)
        g_title.setStyleSheet(f"font-size: 12px; color: {text_title};")
        g_layout.addWidget(g_title)

        if not is_en and self.rec.gap_identified_zh:
            gap_zh = QLabel(f"<b>🇹🇼 中文：</b><span style='color: {zh_color};'>{html.escape(self.rec.gap_identified_zh)}</span>")
            gap_zh.setWordWrap(True)
            gap_zh.setStyleSheet("font-size: 12px;")
            g_layout.addWidget(gap_zh)

        en_val = self.rec.gap_identified_en or self.rec.gap_identified_zh
        gap_en = QLabel(f"{'<b>Critique:</b> ' if is_en else '<b>🇺🇸 EN：</b>'}<span style='color: {en_color}; font-style: italic;'>{html.escape(en_val)}</span>")
        gap_en.setWordWrap(True)
        gap_en.setStyleSheet("font-size: 11px;")
        g_layout.addWidget(gap_en)
        layout.addWidget(gap_box)

        # 2. 建議補做方案
        prop_box = QFrame()
        prop_box.setStyleSheet(f"background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 6px; padding: 6px;")
        p_layout = QVBoxLayout(prop_box)
        p_layout.setContentsMargins(8, 6, 8, 6)
        p_layout.setSpacing(3)

        prop_title_text = "<b>💡 Actionable Strategic Proposal:</b>" if is_en else "<b>💡 建議補做方案 (Proposed Protocol / Experiments):</b>"
        p_title = QLabel(prop_title_text)
        p_title.setStyleSheet(f"font-size: 12px; color: {text_title};")
        p_layout.addWidget(p_title)

        if not is_en and self.rec.concrete_proposal_zh:
            prop_zh = QLabel(f"<b>🇹🇼 中文：</b><span style='color: {zh_color};'>{html.escape(self.rec.concrete_proposal_zh)}</span>")
            prop_zh.setWordWrap(True)
            prop_zh.setStyleSheet("font-size: 12px;")
            p_layout.addWidget(prop_zh)

        prop_en_val = self.rec.concrete_proposal_en or self.rec.concrete_proposal_zh
        prop_en = QLabel(f"{'<b>Proposal:</b> ' if is_en else '<b>🇺🇸 EN：</b>'}<span style='color: {en_color}; font-style: italic;'>{html.escape(prop_en_val)}</span>")
        prop_en.setWordWrap(True)
        prop_en.setStyleSheet("font-size: 11px;")
        p_layout.addWidget(prop_en)
        layout.addWidget(prop_box)

        # 3. 效益評估
        impact_box = QFrame()
        impact_box.setStyleSheet(f"background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 6px; padding: 6px;")
        i_layout = QVBoxLayout(impact_box)
        i_layout.setContentsMargins(8, 6, 8, 6)
        i_layout.setSpacing(3)

        impact_title_text = "<b>🛡️ Strategic Uplift & Acceptance Impact:</b>" if is_en else "<b>🛡️ 投稿防禦效益 (Defense Impact):</b>"
        i_title = QLabel(impact_title_text)
        i_title.setStyleSheet(f"font-size: 12px; color: {text_title};")
        i_layout.addWidget(i_title)

        if not is_en and self.rec.impact_on_acceptance_zh:
            impact_zh = QLabel(f"<b>🇹🇼 中文：</b><span style='color: {zh_color};'>{html.escape(self.rec.impact_on_acceptance_zh)}</span>")
            impact_zh.setWordWrap(True)
            impact_zh.setStyleSheet("font-size: 12px;")
            i_layout.addWidget(impact_zh)

        impact_en_val = self.rec.impact_on_acceptance_en or self.rec.impact_on_acceptance_zh
        impact_en = QLabel(f"{'<b>Impact:</b> ' if is_en else '<b>🇺🇸 EN：</b>'}<span style='color: {en_color}; font-style: italic;'>{html.escape(impact_en_val)}</span>")
        impact_en.setWordWrap(True)
        impact_en.setStyleSheet("font-size: 11px;")
        i_layout.addWidget(impact_en)
        layout.addWidget(impact_box)

class IssueCard(QFrame):
    def __init__(self, issue_idx: int, issue: IssueItem, on_option_selected_callback, is_dark: bool = False, lang: str = "zh_TW"):
        super().__init__()
        self.issue_idx = issue_idx
        self.issue = issue
        self.on_option_selected_callback = on_option_selected_callback
        self.selected_option_idx: int = 0
        self.option_buttons: List[QPushButton] = []
        self.is_dark = is_dark
        self.lang = lang
        self.init_ui()

    def init_ui(self):
        is_en = (self.lang == "en_US")
        self.setFrameShape(QFrame.StyledPanel)

        if self.is_dark:
            self.setStyleSheet("""
                IssueCard {
                    background-color: #1e293b; border: 1px solid #334155;
                    border-radius: 8px; margin-bottom: 12px;
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
                    background-color: #ffffff; border: 1px solid #cbd5e1;
                    border-radius: 8px; margin-bottom: 12px;
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
            "Logic Error": ("#fef3c7", "#92400e", "🟡 邏輯矛盾" if not is_en else "🟡 Logic Error"),
            "Flawed Deduction": ("#ffedd5", "#9a3412", "🟠 推論缺陷 / 過度宣稱" if not is_en else "🟠 Deductive Flaw"),
            "Grammar & Mechanics": ("#fee2e2", "#991b1b", "🔴 文法與句構" if not is_en else "🔴 Grammar & Mechanics"),
            "Rhetorical Defect": ("#dbeafe", "#1e40af", "🔵 修辭與風格" if not is_en else "🔵 Rhetoric & Tone"),
            "Collocation Defect": ("#d1fae5", "#065f46", "🟢 道地搭配詞" if not is_en else "🟢 Natural Collocation")
        }
        bg_col, txt_col, badge_text = color_map.get(
            self.issue.category, ("#f1f5f9", "#334155", self.issue.category_zh if not is_en else self.issue.category)
        )

        top_row = QHBoxLayout()
        category_badge = QLabel(f" {badge_text} ")
        category_badge.setStyleSheet(f"background-color: {bg_col}; color: {txt_col}; font-weight: bold; border-radius: 4px; font-size: 11px; padding: 2px 6px;")

        severity_map = {
            "Critical": ("Critical Severity" if is_en else "嚴重缺陷 (Critical)"),
            "Major": ("Major Issue" if is_en else "主要問題 (Major)"),
            "Minor": ("Minor Polish" if is_en else "細微瑕疵 (Minor)")
        }
        severity_label = QLabel(f"{severity_map.get(self.issue.severity, self.issue.severity)}")
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

        orig_label = QLabel(f"{'<b>📌 Original Snippet:</b> ' if is_en else '<b>📌 原文片段：</b>'}<span style='color: {text_primary};'>\"{html.escape(self.issue.original_text)}\"</span>")
        orig_label.setWordWrap(True)
        orig_label.setStyleSheet(f"color: {text_primary}; font-size: 12px;")
        meaning_layout.addWidget(orig_label)

        analysis_txt = self.issue.meaning_analysis_en if is_en else (self.issue.meaning_analysis_zh or self.issue.meaning_analysis_en)
        if analysis_txt:
            trans_label = QLabel(f"{'<b>Semantic Analysis:</b> ' if is_en else '<b>文意解析與翻譯：</b>'}<span style='color: {text_secondary};'>{html.escape(analysis_txt)}</span>")
            trans_label.setWordWrap(True)
            trans_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
            meaning_layout.addWidget(trans_label)
        layout.addWidget(meaning_box)

        # 評論區
        comment_box = QFrame()
        comment_box.setStyleSheet(f"background-color: {comment_box_bg}; border: 1px solid {comment_box_border}; border-left: 4px solid #10b981; border-radius: 4px;")
        comment_layout = QVBoxLayout(comment_box)
        comment_layout.setContentsMargins(8, 6, 8, 6)
        comment_layout.setSpacing(4)

        if not is_en and self.issue.reviewer_comment_zh:
            comment_zh = QLabel(f"<b>🇹🇼 審稿意見 (中文)：</b><span style='color: {zh_color};'>{html.escape(self.issue.reviewer_comment_zh)}</span>")
            comment_zh.setWordWrap(True)
            comment_zh.setStyleSheet("font-size: 12px;")
            comment_layout.addWidget(comment_zh)

        en_comm = self.issue.reviewer_comment_en or self.issue.reviewer_comment_zh
        comment_en = QLabel(f"{'<b>Reviewer Critique:</b> ' if is_en else '<b>🇺🇸 Reviewer Comment (EN)：</b>'}<span style='color: {en_color}; font-style: italic;'>{html.escape(en_comm)}</span>")
        comment_en.setWordWrap(True)
        comment_en.setStyleSheet("font-size: 11px;")
        comment_layout.addWidget(comment_en)
        layout.addWidget(comment_box)

        # 3~4 多選項展示
        opt_title_text = "💡 Revision Options (Click to select, full text syncs dynamically):" if is_en else "💡 建議修改選項 (點擊切換，右側修改全文將即時連動):"
        opt_title = QLabel(opt_title_text)
        opt_title.setStyleSheet("font-weight: bold; color: #10b981; font-size: 12px; margin-top: 4px;")
        layout.addWidget(opt_title)

        for idx, opt in enumerate(self.issue.revision_options):
            opt_frame = QFrame()
            opt_frame.setStyleSheet(f"QFrame {{ background-color: {card_bg}; border: 1px solid {card_border}; border-radius: 6px; }}")
            opt_layout = QVBoxLayout(opt_frame)
            opt_layout.setContentsMargins(10, 8, 10, 8)
            opt_layout.setSpacing(4)

            opt_header = QHBoxLayout()
            label_text = f"Option {chr(65 + idx)}: {html.escape(opt.style_label)}" if is_en else f"選項 {chr(65 + idx)}：{html.escape(opt.style_label)}"
            label_badge = QLabel(label_text)
            label_badge.setStyleSheet("font-weight: bold; color: #10b981; font-size: 11px;")
            opt_header.addWidget(label_badge)
            opt_header.addStretch()

            is_active = (idx == 0)
            apply_text = ("Applied ✓" if is_en else "已套用 ✓") if is_active else ("Use This" if is_en else "切換至此選項")
            apply_btn = QPushButton(apply_text)
            self.style_button(apply_btn, is_active)
            apply_btn.clicked.connect(lambda checked, o_idx=idx: self.select_option(o_idx))
            self.option_buttons.append(apply_btn)
            opt_header.addWidget(apply_btn)
            opt_layout.addLayout(opt_header)

            rev_title = "Revised: " if is_en else "修訂句："
            rev_text_lbl = QLabel(f"<b>{rev_title}</b><span style='color: #10b981;'>\"{html.escape(opt.revised_text)}\"</span>")
            rev_text_lbl.setWordWrap(True)
            rev_text_lbl.setStyleSheet(f"font-size: 12px; color: {text_primary};")
            opt_layout.addWidget(rev_text_lbl)

            rat_val = opt.rationale_en if is_en else (opt.rationale_zh or opt.rationale_en)
            if rat_val:
                rat_title = "Rationale: " if is_en else "理由："
                rat_lbl = QLabel(f"<b>{rat_title}</b><span style='color: {text_secondary};'>{html.escape(rat_val)}</span>")
                rat_lbl.setWordWrap(True)
                rat_lbl.setStyleSheet("font-size: 11px;")
                opt_layout.addWidget(rat_lbl)

            layout.addWidget(opt_frame)

    def select_option(self, option_idx: int):
        is_en = (self.lang == "en_US")
        self.selected_option_idx = option_idx
        for idx, btn in enumerate(self.option_buttons):
            if idx == option_idx:
                btn.setText("Applied ✓" if is_en else "已套用 ✓")
                self.style_button(btn, True)
            else:
                btn.setText("Use This" if is_en else "切換至此選項")
                self.style_button(btn, False)
        if self.on_option_selected_callback:
            self.on_option_selected_callback(self.issue_idx, option_idx)

    def style_button(self, btn: QPushButton, is_active: bool):
        if is_active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #16a34a; color: #ffffff; border: 1px solid #15803d;
                    border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;
                }
                QPushButton:hover { background-color: #15803d; }
            """)
        else:
            if self.is_dark:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1e293b; color: #6ee7b7; border: 1px solid #059669;
                        border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #064e3b; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f8fafc; color: #15803d; border: 1px solid #86efac;
                        border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #dcfce7; }
                """)

# ==========================================
# 7. 主視窗 (三欄式 + 多語言 + 多情境模式 + 章節局部針對性)
# ==========================================
class AcademicReviewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1520, 920)

        self.config = load_config()
        self.is_dark_mode = self.config.get("dark_mode", False)
        self.ui_language = self.config.get("ui_language", "zh_TW")
        self.writing_mode = self.config.get("writing_mode", "academic")
        self.context_scope = self.config.get("context_scope", "full")
        self.section_target = self.config.get("section_target", "abstract")
        self.engine_mode = self.config.get("engine_mode", "ollama")

        self.current_report: Optional[AcademicReviewReport] = None
        self.selected_options: Dict[int, int] = {}
        self.latest_revised_plain_text: str = ""

        self.elapsed_seconds: int = 0
        self.accumulated_tokens: int = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)
        self.live_stream_box: Optional[AcademicTextEdit] = None

        self.preflight_timer = QTimer(self)
        self.preflight_timer.setSingleShot(True)
        self.preflight_timer.timeout.connect(self.run_preflight_analysis)

        self.current_preflight_matches: List[PreflightMatch] = []

        self.init_ui()
        self.apply_language()
        self.apply_theme()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(16, 10, 16, 12)
        self.main_layout.setSpacing(8)

        # --- 頂部工具列 (Row 1) ---
        self.toolbar_layout = QHBoxLayout()
        self.title_label = QLabel("🦙 LibreLlama Reviewer")
        self.title_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.toolbar_layout.addWidget(self.title_label)

        self.v_badge = QLabel(f"v{APP_VERSION} (Pre-release)")
        self.v_badge.setStyleSheet("color: #94a3b8; font-size: 11px; margin-right: 8px;")
        self.toolbar_layout.addWidget(self.v_badge)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["🖥️ 在地 Ollama (100% 離線隱私)", "☁️ 線上 API (DeepSeek/OpenAI/Gemini)"])
        if self.engine_mode == "api":
            self.engine_combo.setCurrentIndex(1)
        self.engine_combo.currentIndexChanged.connect(self.on_engine_mode_changed)
        self.toolbar_layout.addWidget(self.engine_combo)

        self.api_settings_btn = QPushButton("⚙️ API 設定")
        self.api_settings_btn.clicked.connect(self.open_api_settings)
        self.toolbar_layout.addWidget(self.api_settings_btn)

        self.toolbar_layout.addStretch()

        self.model_label = QLabel("模型:")
        self.model_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.toolbar_layout.addWidget(self.model_label)

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(180)
        self.toolbar_layout.addWidget(self.model_combo)

        self.refresh_btn = QPushButton("🔄 重新整理")
        self.refresh_btn.clicked.connect(self.load_installed_models)
        self.toolbar_layout.addWidget(self.refresh_btn)

        self.env_setup_btn = QPushButton("📥 本機環境精靈")
        self.env_setup_btn.clicked.connect(self.open_environment_dialog)
        self.toolbar_layout.addWidget(self.env_setup_btn)

        # 語言切換按鈕
        self.lang_btn = QPushButton("🌐 English" if self.ui_language == "zh_TW" else "🌐 繁體中文")
        self.lang_btn.clicked.connect(self.toggle_language)
        self.toolbar_layout.addWidget(self.lang_btn)

        # 主題切換
        self.theme_btn = QPushButton("🌙 暗黑模式" if not self.is_dark_mode else "☀️ 明亮模式")
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.toolbar_layout.addWidget(self.theme_btn)

        # 更新按鈕
        self.update_btn = QPushButton("🚀 檢查更新")
        self.update_btn.clicked.connect(self.open_update_dialog)
        self.toolbar_layout.addWidget(self.update_btn)

        self.main_layout.addLayout(self.toolbar_layout)

        # --- 控制列 (Row 2): 寫作情境模式 + 文章範圍 + 章節定位 ---
        self.mode_control_frame = QFrame()
        self.mode_control_frame.setFrameShape(QFrame.StyledPanel)
        mode_ctrl_layout = QHBoxLayout(self.mode_control_frame)
        mode_ctrl_layout.setContentsMargins(10, 6, 10, 6)
        mode_ctrl_layout.setSpacing(10)

        self.mode_lbl = QLabel("寫作情境:")
        self.mode_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        mode_ctrl_layout.addWidget(self.mode_lbl)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            WRITING_MODES["academic"]["name_zh"],
            WRITING_MODES["correspondence"]["name_zh"],
            WRITING_MODES["application"]["name_zh"],
            WRITING_MODES["business"]["name_zh"]
        ])
        mode_idx_map = {"academic": 0, "correspondence": 1, "application": 2, "business": 3}
        self.mode_combo.setCurrentIndex(mode_idx_map.get(self.writing_mode, 0))
        self.mode_combo.currentIndexChanged.connect(self.on_writing_mode_changed)
        mode_ctrl_layout.addWidget(self.mode_combo)

        mode_ctrl_layout.addSpacing(10)

        self.scope_lbl = QLabel("文章範圍:")
        self.scope_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        mode_ctrl_layout.addWidget(self.scope_lbl)

        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["📄 全篇完整文章", "📑 局部段落選取"])
        self.scope_combo.setCurrentIndex(1 if self.context_scope == "partial" else 0)
        self.scope_combo.currentIndexChanged.connect(self.on_context_scope_changed)
        mode_ctrl_layout.addWidget(self.scope_combo)

        self.section_lbl = QLabel("章節定位:")
        self.section_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        mode_ctrl_layout.addWidget(self.section_lbl)

        self.section_combo = QComboBox()
        mode_ctrl_layout.addWidget(self.section_combo)

        mode_ctrl_layout.addStretch()

        self.load_sample_btn = QPushButton("📋 載入情境範文")
        self.load_sample_btn.clicked.connect(self.load_mode_sample_text)
        mode_ctrl_layout.addWidget(self.load_sample_btn)

        self.main_layout.addWidget(self.mode_control_frame)

        # --- 三欄分割器 ---
        self.splitter = QSplitter(Qt.Horizontal)

        # 左欄
        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)

        left_header = QHBoxLayout()
        self.left_title_lbl = QLabel("1. 原始英文草稿:")
        self.left_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        left_header.addWidget(self.left_title_lbl)
        left_header.addStretch()

        self.word_count_lbl = QLabel("字數: 0 字")
        left_header.addWidget(self.word_count_lbl)
        left_layout.addLayout(left_header)

        self.text_editor = AcademicTextEdit(on_quick_fix=self.auto_fix_preflight_issues, is_dark=self.is_dark_mode, lang=self.ui_language)
        self.text_editor.setFont(QFont("Consolas", 11))
        self.text_editor.setPlainText(WRITING_MODES["academic"]["sample"])
        self.text_editor.textChanged.connect(self.on_editor_text_changed)
        left_layout.addWidget(self.text_editor)

        self.preflight_box = QFrame()
        preflight_layout = QVBoxLayout(self.preflight_box)
        preflight_layout.setContentsMargins(10, 8, 10, 8)
        preflight_layout.setSpacing(6)

        pf_top = QHBoxLayout()
        self.pf_title_lbl = QLabel("⚡ 本機秒篩 (純程式規則，0秒反應):")
        self.pf_title_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        pf_top.addWidget(self.pf_title_lbl)
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

        self.review_btn = QPushButton("🚀 開始智能審查 (搭配詞檢視與深度改寫)")
        self.review_btn.setFixedHeight(42)
        self.review_btn.clicked.connect(self.start_review)
        left_layout.addWidget(self.review_btn)

        self.splitter.addWidget(self.left_widget)

        # 中欄
        self.middle_widget = QWidget()
        middle_layout = QVBoxLayout(self.middle_widget)
        middle_layout.setContentsMargins(6, 0, 6, 0)

        self.middle_title_lbl = QLabel("2. 審查意見、實證補強與搭配詞選項:")
        self.middle_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        middle_layout.addWidget(self.middle_title_lbl)

        self.assessment_box = AcademicTextBrowser(is_dark=self.is_dark_mode, lang=self.ui_language)
        self.assessment_box.setMaximumHeight(160)
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

        # 右欄
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)

        right_header = QHBoxLayout()
        self.right_title_lbl = QLabel("3. 修改後全文 (高亮顏色標記修改處):")
        self.right_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        right_header.addWidget(self.right_title_lbl)
        right_header.addStretch()

        self.sync_to_left_btn = QPushButton("⬅️ 同步至左側草稿")
        self.sync_to_left_btn.clicked.connect(self.sync_revised_to_left)
        right_header.addWidget(self.sync_to_left_btn)

        self.copy_btn = QPushButton("📋 複製修訂全文")
        self.copy_btn.clicked.connect(self.copy_revised_text)
        right_header.addWidget(self.copy_btn)
        right_layout.addLayout(right_header)

        self.legend_label = QLabel()
        self.legend_label.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
        right_layout.addWidget(self.legend_label)

        self.revised_browser = AcademicTextBrowser(is_dark=self.is_dark_mode, lang=self.ui_language)
        self.revised_browser.setFont(QFont("Consolas", 11))
        right_layout.addWidget(self.revised_browser)

        self.splitter.addWidget(self.right_widget)
        self.splitter.setSizes([470, 540, 470])
        self.main_layout.addWidget(self.splitter)

        self.refresh_section_combo()
        self.update_engine_ui()
        self.run_preflight_analysis()

    # --- 語言切換邏輯 (繁體中文 / Pure English) ---
    def toggle_language(self):
        self.ui_language = "en_US" if self.ui_language == "zh_TW" else "zh_TW"
        self.config["ui_language"] = self.ui_language
        save_config(self.config)
        self.text_editor.lang = self.ui_language
        self.assessment_box.lang = self.ui_language
        self.revised_browser.lang = self.ui_language
        self.apply_language()
        self.apply_theme()

    def apply_language(self):
        is_en = (self.ui_language == "en_US")
        t = I18N.get(self.ui_language, I18N["zh_TW"])

        self.setWindowTitle(t["app_title"])
        self.v_badge.setText(t["pre_release_badge"])
        self.lang_btn.setText(t["lang_btn"])
        self.refresh_btn.setText(t["refresh"])
        self.env_setup_btn.setText(t["env_wizard"])
        self.update_btn.setText(t["check_update"])
        self.api_settings_btn.setText(t["api_settings"])
        self.theme_btn.setText(t["theme_dark"] if not self.is_dark_mode else t["theme_light"])

        # Row 2 Mode & Scope
        self.mode_lbl.setText(t["mode_lbl"])
        self.scope_lbl.setText(t["scope_lbl"])
        self.section_lbl.setText(t["section_lbl"])
        self.load_sample_btn.setText(t["load_sample"])

        cur_mode_idx = self.mode_combo.currentIndex()
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItems([
            WRITING_MODES["academic"]["name_en" if is_en else "name_zh"],
            WRITING_MODES["correspondence"]["name_en" if is_en else "name_zh"],
            WRITING_MODES["application"]["name_en" if is_en else "name_zh"],
            WRITING_MODES["business"]["name_en" if is_en else "name_zh"]
        ])
        self.mode_combo.setCurrentIndex(cur_mode_idx if cur_mode_idx >= 0 else 0)
        self.mode_combo.blockSignals(False)

        cur_scope_idx = self.scope_combo.currentIndex()
        self.scope_combo.blockSignals(True)
        self.scope_combo.clear()
        self.scope_combo.addItems([t["scope_full"], t["scope_partial"]])
        self.scope_combo.setCurrentIndex(cur_scope_idx if cur_scope_idx >= 0 else 0)
        self.scope_combo.blockSignals(False)

        self.refresh_section_combo()

        # 三欄標題
        self.left_title_lbl.setText(t["left_title"])
        self.pf_title_lbl.setText(t["pf_title"])
        self.quick_fix_btn.setText(t["quick_fix_btn"])
        self.review_btn.setText(t["btn_start_review"])
        self.middle_title_lbl.setText(t["middle_title"])
        self.right_title_lbl.setText(t["right_title"])
        self.sync_to_left_btn.setText(t["sync_left"])
        self.copy_btn.setText(t["copy_revised"])

        if not self.current_report:
            self.assessment_box.setHtml(t["assessment_placeholder"])
            self.revised_browser.setHtml(t["revised_placeholder"])
            self.status_banner.setText(t["status_ready"])

        self.update_engine_ui()
        self.update_legend_text()

    def update_legend_text(self):
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        if self.is_dark_mode:
            self.legend_label.setText(
                f"<span style='background-color:#450a0a; color:#fecaca; border:1px solid #dc2626; padding:2px 5px; border-radius:3px;'> {t['legend_grammar']} </span> "
                f"<span style='background-color:#431407; color:#fed7aa; border:1px solid #ea580c; padding:2px 5px; border-radius:3px;'> {t['legend_deduction']} </span> "
                f"<span style='background-color:#451a03; color:#fde68a; border:1px solid #d97706; padding:2px 5px; border-radius:3px;'> {t['legend_logic']} </span> "
                f"<span style='background-color:#172554; color:#bfdbfe; border:1px solid #2563eb; padding:2px 5px; border-radius:3px;'> {t['legend_rhetoric']} </span> "
                f"<span style='background-color:#022c22; color:#a7f3d0; border:1px solid #059669; padding:2px 5px; border-radius:3px;'> {t['legend_collocation']} </span>"
            )
        else:
            self.legend_label.setText(
                f"<span style='background-color:#fee2e2; color:#991b1b; padding:2px 5px; border-radius:3px;'> {t['legend_grammar']} </span> "
                f"<span style='background-color:#ffedd5; color:#9a3412; padding:2px 5px; border-radius:3px;'> {t['legend_deduction']} </span> "
                f"<span style='background-color:#fef3c7; color:#92400e; padding:2px 5px; border-radius:3px;'> {t['legend_logic']} </span> "
                f"<span style='background-color:#dbeafe; color:#1e40af; padding:2px 5px; border-radius:3px;'> {t['legend_rhetoric']} </span> "
                f"<span style='background-color:#d1fae5; color:#065f46; padding:2px 5px; border-radius:3px;'> {t['legend_collocation']} </span>"
            )

    def on_writing_mode_changed(self, idx: int):
        modes = ["academic", "correspondence", "application", "business"]
        if idx < len(modes):
            self.writing_mode = modes[idx]
            self.config["writing_mode"] = self.writing_mode
            save_config(self.config)
            self.refresh_section_combo()
            self.run_preflight_analysis()

    def on_context_scope_changed(self, idx: int):
        self.context_scope = "partial" if idx == 1 else "full"
        self.config["context_scope"] = self.context_scope
        save_config(self.config)
        self.section_lbl.setVisible(self.context_scope == "partial")
        self.section_combo.setVisible(self.context_scope == "partial")

    def refresh_section_combo(self):
        is_en = (self.ui_language == "en_US")
        mode_data = WRITING_MODES.get(self.writing_mode, WRITING_MODES["academic"])
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        for s_id, s_zh, s_en in mode_data["sections"]:
            self.section_combo.addItem(s_en if is_en else s_zh, s_id)

        self.section_combo.blockSignals(False)
        self.section_lbl.setVisible(self.context_scope == "partial")
        self.section_combo.setVisible(self.context_scope == "partial")

    def load_mode_sample_text(self):
        mode_data = WRITING_MODES.get(self.writing_mode, WRITING_MODES["academic"])
        sample = mode_data.get("sample", "")
        self.text_editor.setPlainText(sample)

    # --- 主題外觀設置 ---
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.config["dark_mode"] = self.is_dark_mode
        save_config(self.config)
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        self.theme_btn.setText(t["theme_dark"] if not self.is_dark_mode else t["theme_light"])
        self.apply_theme()

    def apply_theme(self):
        dark = self.is_dark_mode
        self.text_editor.is_dark = dark
        self.assessment_box.is_dark = dark
        self.revised_browser.is_dark = dark

        if dark:
            bg_main = "#0f172a"
            bg_card = "#1e293b"
            border_col = "#334155"
            text_main = "#f8fafc"
            text_sub = "#94a3b8"

            self.central_widget.setStyleSheet(f"background-color: {bg_main}; color: {text_main};")
            self.title_label.setStyleSheet(f"color: {text_main};")
            self.left_title_lbl.setStyleSheet(f"color: {text_main};")
            self.middle_title_lbl.setStyleSheet(f"color: {text_main};")
            self.right_title_lbl.setStyleSheet(f"color: {text_main};")
            self.model_label.setStyleSheet(f"color: {text_sub};")
            self.word_count_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px;")
            self.pf_title_lbl.setStyleSheet(f"color: {text_main};")
            self.status_banner.setStyleSheet(f"color: {text_sub}; font-size: 11px;")

            self.text_editor.set_theme_mode(True)
            self.assessment_box.set_theme_mode(True)
            self.revised_browser.set_theme_mode(True)

            self.mode_control_frame.setStyleSheet(f"background-color: {bg_card}; border: 1px solid {border_col}; border-radius: 6px;")
            self.preflight_box.setStyleSheet(f"background-color: {bg_card}; border: 1px solid {border_col}; border-radius: 6px;")

            btn_normal = f"""
                QPushButton {{
                    background-color: {bg_card}; color: {text_main}; border: 1px solid {border_col};
                    border-radius: 5px; padding: 5px 10px; font-size: 11px; font-weight: 500;
                }}
                QPushButton:hover {{ background-color: #334155; }}
            """
            for b in [self.refresh_btn, self.env_setup_btn, self.theme_btn, self.api_settings_btn,
                      self.sync_to_left_btn, self.copy_btn, self.update_btn, self.lang_btn, self.load_sample_btn]:
                b.setStyleSheet(btn_normal)

            self.quick_fix_btn.setStyleSheet("""
                QPushButton { background-color: #1e3a8a; color: #93c5fd; border: 1px solid #3b82f6; border-radius: 4px; padding: 3px 8px; font-size: 11px; font-weight: bold; }
                QPushButton:hover { background-color: #2563eb; color: #ffffff; }
            """)

            combo_style = f"""
                QComboBox {{ background-color: {bg_card}; color: {text_main}; border: 1px solid {border_col}; border-radius: 5px; padding: 4px 8px; font-size: 12px; }}
                QComboBox QAbstractItemView {{ background-color: {bg_card}; color: {text_main}; selection-background-color: #334155; selection-color: #38bdf8; }}
            """
            for c in [self.engine_combo, self.model_combo, self.mode_combo, self.scope_combo, self.section_combo]:
                c.setStyleSheet(combo_style)

            self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        else:
            bg_main = "#f8fafc"
            bg_card = "#ffffff"
            border_col = "#cbd5e1"
            text_main = "#0f172a"
            text_sub = "#475569"

            self.central_widget.setStyleSheet(f"background-color: {bg_main}; color: {text_main};")
            self.title_label.setStyleSheet(f"color: {text_main};")
            self.left_title_lbl.setStyleSheet(f"color: {text_main};")
            self.middle_title_lbl.setStyleSheet(f"color: {text_main};")
            self.right_title_lbl.setStyleSheet(f"color: {text_main};")
            self.model_label.setStyleSheet(f"color: {text_sub};")
            self.word_count_lbl.setStyleSheet(f"color: #64748b; font-size: 11px;")
            self.pf_title_lbl.setStyleSheet(f"color: {text_main};")
            self.status_banner.setStyleSheet(f"color: #64748b; font-size: 11px;")

            self.text_editor.set_theme_mode(False)
            self.assessment_box.set_theme_mode(False)
            self.revised_browser.set_theme_mode(False)

            self.mode_control_frame.setStyleSheet(f"background-color: {bg_card}; border: 1px solid #e2e8f0; border-radius: 6px;")
            self.preflight_box.setStyleSheet(f"background-color: {bg_card}; border: 1px solid #e2e8f0; border-radius: 6px;")

            btn_normal = f"""
                QPushButton {{
                    background-color: {bg_card}; color: {text_main}; border: 1px solid {border_col};
                    border-radius: 5px; padding: 5px 10px; font-size: 11px; font-weight: 500;
                }}
                QPushButton:hover {{ background-color: #f1f5f9; }}
            """
            for b in [self.refresh_btn, self.env_setup_btn, self.theme_btn, self.api_settings_btn,
                      self.sync_to_left_btn, self.copy_btn, self.update_btn, self.lang_btn, self.load_sample_btn]:
                b.setStyleSheet(btn_normal)

            self.quick_fix_btn.setStyleSheet("""
                QPushButton { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 4px; padding: 3px 8px; font-size: 11px; font-weight: bold; }
                QPushButton:hover { background-color: #dbeafe; }
            """)

            combo_style = f"""
                QComboBox {{ background-color: {bg_card}; color: {text_main}; border: 1px solid {border_col}; border-radius: 5px; padding: 4px 8px; font-size: 12px; }}
                QComboBox QAbstractItemView {{ background-color: {bg_card}; color: {text_main}; selection-background-color: #e2e8f0; selection-color: {text_main}; }}
            """
            for c in [self.engine_combo, self.model_combo, self.mode_combo, self.scope_combo, self.section_combo]:
                c.setStyleSheet(combo_style)

            self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.update_legend_text()
        self.update_revised_article_view()
        self.run_preflight_analysis()

    # --- 引擎選擇 ---
    def on_engine_mode_changed(self, idx: int):
        self.engine_mode = "ollama" if idx == 0 else "api"
        self.config["engine_mode"] = self.engine_mode
        save_config(self.config)
        self.update_engine_ui()

    def update_engine_ui(self):
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        if self.engine_mode == "ollama":
            self.api_settings_btn.setVisible(False)
            self.refresh_btn.setVisible(True)
            self.env_setup_btn.setVisible(True)
            self.model_label.setText(t["select_local_model"])
            self.load_installed_models()
        else:
            self.api_settings_btn.setVisible(True)
            self.refresh_btn.setVisible(False)
            self.env_setup_btn.setVisible(False)
            self.model_label.setText(t["select_cloud_model"])
            self.model_combo.clear()
            cur_model = self.config.get("api_model", "deepseek-chat")
            provider = self.config.get("api_provider", "DeepSeek")
            self.model_combo.addItem(f"{cur_model} ({provider})")
            self.review_btn.setEnabled(True)

    def load_installed_models(self):
        if self.engine_mode != "ollama":
            return
        is_en = (self.ui_language == "en_US")
        self.model_combo.clear()
        try:
            res = ollama.list()
            names = []
            if hasattr(res, 'models'):
                for m in res.models:
                    n = getattr(m, 'model', '') or getattr(m, 'name', '')
                    if n:
                        names.append(n)
            elif isinstance(res, dict) and 'models' in res:
                for m in res['models']:
                    n = m.get('name') or m.get('model')
                    if n:
                        names.append(n)

            if not names:
                self.model_combo.addItem("No models found" if is_en else "未找到本地模型")
                self.review_btn.setEnabled(False)
            else:
                for name in names:
                    self.model_combo.addItem(name)
                self.review_btn.setEnabled(True)
        except Exception:
            self.model_combo.addItem("Ollama not running" if is_en else "Ollama 未啟動")
            self.review_btn.setEnabled(False)

    def open_api_settings(self):
        dlg = ApiSettingsDialog(self, self.config, is_dark=self.is_dark_mode, lang=self.ui_language)
        if dlg.exec():
            self.config = load_config()
            self.update_engine_ui()

    def open_environment_dialog(self):
        dlg = OllamaEnvironmentDialog(self, is_dark=self.is_dark_mode, lang=self.ui_language)
        if dlg.exec() or dlg.models_updated:
            self.load_installed_models()

    def open_update_dialog(self):
        dlg = UpdateDialog(self, is_dark=self.is_dark_mode, config=self.config, lang=self.ui_language)
        dlg.exec()

    def on_editor_text_changed(self):
        self.preflight_timer.start(250)

    def run_preflight_analysis(self):
        text = self.text_editor.toPlainText().strip()
        words = text.split()
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        self.word_count_lbl.setText(t["word_count"].format(n=len(words)))

        if not text:
            self.preflight_status_lbl.setText("Ready: input text to scan." if self.ui_language == "en_US" else "就緒：請輸入英文草稿以執行秒級快篩。")
            self.quick_fix_btn.setEnabled(False)
            self.current_preflight_matches = []
            return

        self.current_preflight_matches = PreflightChecker.scan(text, self.writing_mode)
        is_en = (self.ui_language == "en_US")
        if not self.current_preflight_matches:
            self.preflight_status_lbl.setText("✨ No obvious contractions or awkward collocations detected." if is_en else "✨ 語法規則檢測通過！未發現縮寫、口語贅詞或生硬搭配詞。")
            self.preflight_status_lbl.setStyleSheet("color: #10b981; font-size: 11px;")
            self.quick_fix_btn.setEnabled(False)
        else:
            cnt = len(self.current_preflight_matches)
            preview = ", ".join([f"'{m.original}' ➔ '{m.replacement}'" for m in self.current_preflight_matches[:3]])
            if cnt > 3:
                preview += f"... (+{cnt - 3} more)"
            msg = f"⚠️ Detected {cnt} rule warnings: {preview}" if is_en else f"⚠️ 本機秒篩偵測到 {cnt} 處待改進項：{preview}"
            self.preflight_status_lbl.setText(msg)
            self.preflight_status_lbl.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.quick_fix_btn.setEnabled(True)

    def auto_fix_preflight_issues(self):
        text = self.text_editor.toPlainText()
        if not text:
            return
        fixed_text = PreflightChecker.fix_all_issues(text)
        self.text_editor.setPlainText(fixed_text)
        self.run_preflight_analysis()
        is_en = (self.ui_language == "en_US")
        msg = "Fixed contractions and informal words automatically!" if is_en else "已一鍵完成縮寫與口語詞自動替換！"
        self.status_banner.setText(msg)
        self.status_banner.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

    # --- 啟動審查 ---
    def start_review(self):
        text = self.text_editor.toPlainText().strip()
        is_en = (self.ui_language == "en_US")
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        if not text:
            QMessageBox.warning(self, "Notice" if is_en else "提示", "Please enter text to review." if is_en else "請輸入欲審查的文章。")
            return

        model_name = self.model_combo.currentText().strip()
        if self.engine_mode == "ollama":
            if not model_name or "未找到" in model_name or "未啟動" in model_name or "No models" in model_name:
                QMessageBox.warning(self, "Notice" if is_en else "提示", "Please select a valid local Ollama model." if is_en else "請先確認已選擇本機模型。")
                return
        else:
            model_name = self.config.get("api_model", "deepseek-chat")
            if not self.config.get("api_key"):
                QMessageBox.warning(self, "Notice" if is_en else "提示", "Please configure your API Key first." if is_en else "請先點擊上方「⚙️ API 設定」輸入線上 API Key。")
                self.open_api_settings()
                return

        section_val = self.section_combo.currentData() or "general"

        self.elapsed_seconds = 0
        self.accumulated_tokens = 0
        self.timer.start(1000)

        self.review_btn.setEnabled(False)
        self.review_btn.setText(t["btn_reviewing"])
        self.progress_bar.setVisible(True)
        self.update_live_status_ui(model_name)

        self.clear_cards()
        self.setup_live_stream_console()

        self.revised_browser.setHtml(
            "<span style='color: #64748b;'>Reviewing draft... full revised text with highlights will appear upon completion.</span>" if is_en
            else "<span style='color: #64748b;'>審查進行中，完成後將即時生成高亮修訂全文...</span>"
        )

        self.worker = ReviewWorker(
            text=text,
            engine_mode=self.engine_mode,
            model_name=model_name,
            api_config=self.config,
            ui_language=self.ui_language,
            writing_mode=self.writing_mode,
            context_scope=self.context_scope,
            section_target=section_val
        )
        self.worker.chunk_received.connect(self.on_chunk_received)
        self.worker.finished.connect(self.on_review_finished)
        self.worker.error.connect(self.on_review_error)
        self.worker.start()

    def on_timer_tick(self):
        self.elapsed_seconds += 1
        model_name = self.model_combo.currentText().strip()
        self.update_live_status_ui(model_name)

    def update_live_status_ui(self, model_name: str):
        is_en = (self.ui_language == "en_US")
        mode_label = "Local Ollama" if self.engine_mode == "ollama" else "Cloud API"
        if is_en:
            status_msg = f"⏳ [{mode_label}] Model: {model_name} | Elapsed: {self.elapsed_seconds}s | Tokens: {self.accumulated_tokens}"
        else:
            status_msg = f"⏳ [{mode_label} 推論中] 模型：{model_name} ｜ ⏱️ 已耗時：{self.elapsed_seconds} 秒 ｜ 📊 已生成：{self.accumulated_tokens} tokens"
        self.status_banner.setText(status_msg)
        self.status_banner.setStyleSheet("color: #3b82f6; font-weight: bold; font-size: 11px;")

        live_html = f"""
        <div style='font-family: Segoe UI, sans-serif;'>
            <p style='margin: 0 0 6px 0;'><b style='color: #3b82f6;'>⚡ {'Reviewing Draft in Stream Mode' if is_en else '智能審查進行中 (串流模式)'}</b></p>
            <p style='margin: 0; font-size: 11px;'>
                <b>{'Model' if is_en else '模型名稱'}：</b>{html.escape(model_name)}<br>
                <b>{'Elapsed Time' if is_en else '已耗費時間'}：</b><span style='color: #f59e0b; font-weight: bold;'>{self.elapsed_seconds} s</span><br>
                <b>{'Tokens Streamed' if is_en else '已產出詞元'}：</b><span style='color: #10b981; font-weight: bold;'>{self.accumulated_tokens} tokens</span>
            </p>
        </div>
        """
        self.assessment_box.setHtml(live_html)

    def setup_live_stream_console(self):
        is_en = (self.ui_language == "en_US")
        label = QLabel("📡 Live Token Stream Monitor:" if is_en else "📡 即時輸出監控 (模型正於背景進行窮舉批判，保證非卡住):")
        label.setStyleSheet("font-weight: bold; font-size: 11px; margin-bottom: 4px;")
        self.cards_layout.addWidget(label)

        self.live_stream_box = AcademicTextEdit(is_dark=self.is_dark_mode, lang=self.ui_language)
        self.live_stream_box.setReadOnly(True)
        self.live_stream_box.setFont(QFont("Consolas", 10))
        self.live_stream_box.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a; color: #38bdf8; border: 1px solid #334155;
                border-radius: 6px; padding: 10px; line-height: 1.4;
            }
        """)
        self.live_stream_box.setPlaceholderText("Waiting for model stream tokens..." if is_en else "正在等待模型送出首個 Token...")
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
        is_en = (self.ui_language == "en_US")
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        self.review_btn.setText(t["btn_start_review"])
        self.progress_bar.setVisible(False)
        self.current_report = report

        rec_count = len(getattr(report, 'research_recommendations', []))
        issue_count = len(report.issues)

        if is_en:
            final_msg = f"✅ Review Complete! Time: {self.elapsed_seconds}s | {self.accumulated_tokens} tokens | Found {issue_count} revision items | Provided {rec_count} strategic recommendations!"
        else:
            final_msg = f"✅ 審查完成！耗時 {self.elapsed_seconds} 秒，共產出 {self.accumulated_tokens} tokens ｜ 檢驗出 {issue_count} 個改進點 ｜ 提供 {rec_count} 項實質補強建議！"

        self.status_banner.setText(final_msg)
        self.status_banner.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

        self.selected_options = {idx: 0 for idx in range(issue_count)}

        gist_val = report.article_gist_en if is_en else (report.article_gist_zh or report.article_gist_en)
        assessment_html = f"""
        <div style='font-family: Segoe UI, sans-serif;'>
            <p><b>{t['gist_title']}</b><br><span>{html.escape(gist_val)}</span></p>
            <hr style='border: 0; border-top: 1px solid #cbd5e1; margin: 6px 0;'>
        """
        if not is_en and report.overall_assessment_zh:
            assessment_html += f"<p><b>{t['overall_zh_title']}</b><br><span style='color: #10b981;'>{html.escape(report.overall_assessment_zh)}</span></p>"
        assessment_html += f"<p><b>{t['overall_en_title']}</b><br><span style='font-style: italic;'>{html.escape(report.overall_assessment_en)}</span></p></div>"
        self.assessment_box.setHtml(assessment_html)

        self.clear_cards()
        self.live_stream_box = None

        recommendations = getattr(report, 'research_recommendations', [])
        if recommendations:
            rec_header_text = f"🔬 Strategic & Contextual Recommendations ({len(recommendations)} Items):" if is_en else f"🔬 審查員實質建議：上下文完整性與論證/實驗補強 ({len(recommendations)} 項):"
            rec_header = QLabel(rec_header_text)
            rec_header.setStyleSheet("font-weight: bold; color: #8b5cf6; font-size: 13px; margin-top: 4px; margin-bottom: 2px;")
            self.cards_layout.addWidget(rec_header)

            for rec in recommendations:
                rec_card = ResearchRecommendationCard(rec, is_dark=self.is_dark_mode, lang=self.ui_language)
                self.cards_layout.addWidget(rec_card)

        issues_header_text = f"✍️ Sentence-by-Sentence Diagnostics & Collocation Options ({len(report.issues)} Points):" if is_en else f"✍️ 逐句文意診斷、搭配詞與多風格改寫 ({len(report.issues)} 處改進點):"
        issues_header = QLabel(issues_header_text)
        issues_header.setStyleSheet("font-weight: bold; color: #3b82f6; font-size: 13px; margin-top: 12px; margin-bottom: 2px;")
        self.cards_layout.addWidget(issues_header)

        if not report.issues:
            no_issue = QLabel("✨ Outstanding draft! No significant stylistic or linguistic defects found." if is_en else "✨ 未發現明顯語言或推論問題，論述嚴謹且文法正確！")
            no_issue.setStyleSheet("color: #10b981; font-weight: bold; margin-top: 10px;")
            self.cards_layout.addWidget(no_issue)
        else:
            for idx, issue in enumerate(report.issues):
                card = IssueCard(idx, issue, self.handle_option_selection, is_dark=self.is_dark_mode, lang=self.ui_language)
                self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
        self.update_revised_article_view()

    @Slot(str)
    def on_review_error(self, err_msg: str):
        self.timer.stop()
        self.review_btn.setEnabled(True)
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        self.review_btn.setText(t["btn_start_review"])
        self.progress_bar.setVisible(False)
        self.status_banner.setText("❌ Error occurred during review.")
        self.status_banner.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")
        self.assessment_box.setHtml(f"<span style='color: #ef4444;'>❌ Error: {html.escape(err_msg)}</span>")
        QMessageBox.critical(self, "Review Failed", f"Could not complete review:\n{err_msg}")

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
                "Rhetorical Defect": ("#172554", "#bfdbfe", "#2563eb"),
                "Collocation Defect": ("#022c22", "#a7f3d0", "#059669")
            }
        else:
            style_map = {
                "Logic Error": ("#fef3c7", "#92400e", "#fcd34d"),
                "Flawed Deduction": ("#ffedd5", "#9a3412", "#fdba74"),
                "Grammar & Mechanics": ("#fee2e2", "#991b1b", "#fca5a5"),
                "Rhetorical Defect": ("#dbeafe", "#1e40af", "#93c5fd"),
                "Collocation Defect": ("#d1fae5", "#065f46", "#6ee7b7")
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

            bg_c, fg_c, border_c = style_map.get(issue.category, ("#d1fae5", "#065f46", "#6ee7b7"))
            tip = f"{issue.category}: {chosen_opt.style_label}"
            styled_chunk = (
                f"<span style='background-color: {bg_c}; color: {fg_c}; border-bottom: 2px solid {border_c}; "
                f"border-radius: 3px; padding: 1px 3px;' title='{html.escape(tip)}'>{html.escape(revised_snippet)}</span>"
            )
            html_parts.append(styled_chunk)
            curr_pos = e

        if curr_pos < len(original_draft):
            remainder = original_draft[curr_pos:]
            plain_parts.append(remainder)
            html_parts.append(html.escape(remainder))

        self.latest_revised_plain_text = "".join(plain_parts)
        full_html = "".join(html_parts).replace("\n", "<br>")
        self.revised_browser.setHtml(full_html)

    def sync_revised_to_left(self):
        if not self.latest_revised_plain_text:
            return
        self.text_editor.setPlainText(self.latest_revised_plain_text)
        is_en = (self.ui_language == "en_US")
        msg = "Synchronized revised full text to draft editor." if is_en else "已將右側修訂後全文同步至左側草稿區。"
        self.status_banner.setText(msg)
        self.status_banner.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

    def copy_revised_text(self):
        if not self.latest_revised_plain_text:
            return
        QApplication.clipboard().setText(self.latest_revised_plain_text)
        is_en = (self.ui_language == "en_US")
        msg = "Copied revised full text to clipboard!" if is_en else "已複製修訂後全文至剪貼簿！"
        self.status_banner.setText(msg)
        self.status_banner.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AcademicReviewerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()