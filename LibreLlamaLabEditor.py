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
    QLineEdit, QFormLayout, QTabWidget, QStackedWidget
)
import subprocess
import shutil
import tempfile
import ollama
import httpx
import json_repair

from academic_nlp_pipeline import (
    AcademicNLPPipeline, DiagnosticItem, AutoSanitizeChange, PipelineResult
)

APP_VERSION = "0.9.3"
DEFAULT_UPDATE_URL = "https://raw.githubusercontent.com/Chars1008/LibreLabLlama-Editor/main/version.json"
FALLBACK_UPDATE_URL = "https://raw.githubusercontent.com/Chars1008/LibreLlama-Lab-Editor/main/version.json"
FALLBACK_UPDATE_URL_2 = "https://raw.githubusercontent.com/Chars1008/LibreLlama-Reviewer/main/version.json"
CONFIG_FILE = "app_config.json"

# ==========================================
# 0. 國際化多語系字典 (I18N Localization Engine)
# ==========================================
I18N = {
    "zh_TW": {
        "app_title": "LibreLlama Lab Editor ─ 多情境寫作審查與改寫工作台",
        "toolbar_title": "🦙 LibreLlama Lab Editor",
        "pre_release_badge": "v0.9.3 封閉開發版",
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

        # 左欄 (1/3)
        "draft_title": "原始英文草稿",
        "left_title": "原始英文草稿",
        "word_count": "字數: {n} 字",
        "pf_title": "⚡ 本機秒篩 (純程式規則，0秒反應):",
        "quick_fix_btn": "⚡ 一鍵自動替換縮寫與口語詞",
        "preflight_ready": "正在進行本機語法規則快速掃描...",
        "status_ready": "就緒：請確認輸入文本並點擊開始審查。",
        "btn_start_review": "🚀 開始智能審查 (搭配詞檢視與深度改寫)",
        "btn_reviewing": "正在進行深度情境批判與搭配詞窮舉審查...",
        "revised_title": "修改後全文",
        "sync_left": "⬆️ 同步至草稿",
        "copy_revised": "📋 複製修訂全文",
        "revised_placeholder": "<span style='color: #64748b;'>輸入英文草稿後，此處將即時呈現本機規則快篩檢測結果（刪除線為原詞，綠色為推薦替換詞）；點擊下方「開始智能審查」後，將進一步生成 LLM 深度審查與高亮對照！</span>",

        # 中欄 (1/3)
        "middle_title": "審查實質建議與搭配詞替換",
        "recs_title": "審查實質建議與實證缺失分析",
        "colloc_title": "搭配詞替換選項與精準用詞編修",
        "assessment_placeholder": "<span style='color: #64748b;'>點擊下方「開始智能審查」後，此處將顯示：<br>• 即時生成狀態、累計耗時與 Token 數<br>• 全文主旨解析與情境綜合評述</span>",
        "gist_title": "📖 全文主旨判斷與解析 (正體中文)：",
        "overall_zh_title": "🇹🇼 綜合就緒度評估：",
        "overall_en_title": "🇺🇸 Overall Assessment：",
        "recs_placeholder_text": "🔬 審查完成後，將在此呈現論文上下文缺失、實驗補強與研究方法改進建議 (Evidence Gap & Proposed Protocol)。",
        "colloc_placeholder_text": "🟢 審查完成後，將在此列出道地搭配詞替換選項 (Collocations) 與精準用詞修訂。",

        # 右欄 (1/3)
        "right_title": "文法句構、推論缺陷、修辭風格與邏輯矛盾",
        "discourse_title": "文法句構、推論缺陷、修辭風格與邏輯矛盾",
        "discourse_placeholder_text": "✍️ 審查完成後，將在此列出逐句文法句構、推論缺陷、修辭風格與邏輯矛盾診斷卡片。",

        # 中欄分頁與右欄互動工作台
        "tab_recs": "💡 實證補強",
        "tab_colloc": "🔤 搭配詞選項",
        "tab_discourse": "⚖️ 句構與邏輯",
        "monitor_title": "📡 智能審查執行監控",
        "monitor_badge_ready": "就緒",
        "monitor_badge_running": "🔄 審查進行中...",
        "monitor_badge_done": "✅ 審查完成",
        "chat_general_context": "🌐 全文綜合討論",
        "chat_general_btn": "🌐 全文討論",
        "chat_clear_btn": "🧹 清空",
        "chat_input_placeholder": "輸入訊息與審閱模型討論或辯護... (Enter 發送，Shift+Enter 換行)",
        "chat_send_btn": "🚀 發送",
        "pill_defend": "🛡️ 領域慣用辯護",
        "pill_top_tier": "✍️ 頂刊風格升級",
        "pill_hedging": "🔬 語氣弱化防禦",
        "pill_adopt": "🔄 產出替換句",

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
        "app_title": "LibreLlama Lab Editor ─ Multi-Context Writing & Review Workbench",
        "toolbar_title": "🦙 LibreLlama Lab Editor",
        "pre_release_badge": "v0.9.3 Pre-release",
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

        # Left Column (1/3)
        "draft_title": "Original Draft",
        "left_title": "Original Draft",
        "word_count": "Word Count: {n} words",
        "pf_title": "⚡ Instant Local Linter (Pure Rules, 0.001s):",
        "quick_fix_btn": "⚡ Quick Fix Contractions & Informal Phrasing",
        "preflight_ready": "Scanning local rule heuristics...",
        "status_ready": "Ready: verify input text and click Start Review.",
        "btn_start_review": "🚀 Start Deep Review (Collocations & Multi-Style Revisions)",
        "btn_reviewing": "Performing exhaustive multi-context critique and collocation analysis...",
        "revised_title": "Revised Full Text",
        "sync_left": "⬆️ Sync to Draft",
        "copy_revised": "📋 Copy Revised Text",
        "revised_placeholder": "<span style='color: #64748b;'>Enter text in the draft editor to see instant rule linter results here. Click 'Start Deep Review' below to generate full LLM revisions!</span>",

        # Middle Column (1/3)
        "middle_title": "Critiques, Strategic Proposals & Collocations",
        "recs_title": "Strategic Recommendations & Evidence Gap Analysis",
        "colloc_title": "Collocation Options & Lexical Precision",
        "assessment_placeholder": "<span style='color: #64748b;'>Click 'Start Deep Review' below to display:<br>• Real-time token streaming & elapsed time<br>• Executive summary & critical assessment</span>",
        "gist_title": "📖 Executive Summary & Thesis Analysis:",
        "overall_zh_title": "Assessment:",
        "overall_en_title": "Overall Strategic Assessment:",
        "recs_placeholder_text": "🔬 Strategic recommendations, evidence gap analyses, and proposed protocols will appear here upon review completion.",
        "colloc_placeholder_text": "🟢 Idiomatic collocation replacement options and lexical precision revisions will appear here.",

        # Right Column (1/3)
        "right_title": "Discourse, Logic, Rhetoric & Grammar",
        "discourse_title": "Discourse, Logic, Rhetoric & Grammar Critiques",
        "discourse_placeholder_text": "✍️ Sentence-by-sentence grammar diagnostics, deductive flaws, tone, and logic critique cards will appear here.",

        # Middle Tabs & Right Discussion Workbench
        "tab_recs": "💡 Evidence Defenses",
        "tab_colloc": "🔤 Collocations",
        "tab_discourse": "⚖️ Syntax & Logic",
        "monitor_title": "📡 Review Stream Monitor",
        "monitor_badge_ready": "Ready",
        "monitor_badge_running": "🔄 Reviewing...",
        "monitor_badge_done": "✅ Complete",
        "chat_general_context": "🌐 General Full-Text Discussion",
        "chat_general_btn": "🌐 General Chat",
        "chat_clear_btn": "🧹 Clear",
        "chat_input_placeholder": "Type message to discuss or debate with reviewer... (Enter sends, Shift+Enter newline)",
        "chat_send_btn": "🚀 Send",
        "pill_defend": "🛡️ Defend (Domain Norm)",
        "pill_top_tier": "✍️ Top-Tier Style",
        "pill_hedging": "🔬 Hedging Defense",
        "pill_adopt": "🔄 Generate Alternatives",

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
            ("auto", "🔍 其他 / 由模型判斷 (Auto-Detect / Other)", "🔍 Other / Auto-Detect by Model"),
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
            ("auto", "🔍 其他 / 由模型判斷 (Auto-Detect / Other)", "🔍 Other / Auto-Detect by Model"),
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
            ("auto", "🔍 其他 / 由模型判斷 (Auto-Detect / Other)", "🔍 Other / Auto-Detect by Model"),
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
            ("auto", "🔍 其他 / 由模型判斷 (Auto-Detect / Other)", "🔍 Other / Auto-Detect by Model"),
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
                # 自動修正舊版設定檔中的 "version.json" 成為正式 GitHub 端點
                if saved.get("update_url") in ("version.json", "", None):
                    saved["update_url"] = DEFAULT_UPDATE_URL
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
    def __init__(self, category: str, original: str, replacement: str, explanation: str,
                 span: Tuple[int, int], rule_id: str = "", severity: str = "Major"):
        self.category = category
        self.original = original
        self.replacement = replacement
        self.explanation = explanation
        self.span = span
        self.rule_id = rule_id
        self.severity = severity

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
    def scan(cls, text: str, mode: str = "academic", is_en: bool = False) -> List[PreflightMatch]:
        matches: List[PreflightMatch] = []
        if not text:
            return matches

        # 1. 縮寫檢測
        for pat, (rep, exp) in cls.CONTRACTIONS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                cat = "Contraction" if is_en else "縮寫禁忌"
                expl = "Avoid contractions in formal writing" if is_en else exp
                matches.append(PreflightMatch(cat, m.group(0), rep, expl, (m.start(), m.end()), "RULE_CONTRACTION", "Major"))

        # 2. 口語檢測
        for pat, (rep, exp) in cls.INFORMAL_WORDS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                cat = "Informal Word" if is_en else "非正式口語"
                expl = "Use formal academic precision" if is_en else exp
                matches.append(PreflightMatch(cat, m.group(0), rep, expl, (m.start(), m.end()), "RULE_INFORMAL_WORD", "Minor"))

        # 3. 生硬搭配詞檢測
        for pat, (rep, exp) in cls.AWKWARD_COLLOCATIONS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                cat = "Awkward Collocation" if is_en else "搭配詞缺陷"
                expl = "Unidiomatic collocation in English" if is_en else exp
                matches.append(PreflightMatch(cat, m.group(0), rep, exp, (m.start(), m.end()), "RULE_AWKWARD_COLLOCATION", "Major"))

        # 4. 過度斷言檢測
        for pat, (rep, exp) in cls.OVERCLAIMING_PATTERNS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                cat = "Overclaiming" if is_en else "過度宣稱預警"
                expl = "Avoid absolute dogmatic claims" if is_en else exp
                matches.append(PreflightMatch(cat, m.group(0), rep, exp, (m.start(), m.end()), "RULE_OVERCLAIMING", "Minor"))

        # 5. spaCy + Regex NLP Pipeline 深入規則診斷 (零 LLM 依賴)
        try:
            pipeline_diagnostics = AcademicNLPPipeline.diagnose(text)
            for d in pipeline_diagnostics:
                cat = d.category if is_en else d.category_zh
                expl = d.suggestion if is_en else f"{d.message} | {d.suggestion}"
                matches.append(PreflightMatch(
                    category=cat,
                    original=d.matched_text,
                    replacement=d.replacement,
                    explanation=expl,
                    span=d.span,
                    rule_id=d.rule_id,
                    severity=d.severity
                ))
        except Exception:
            pass

        return matches

    @classmethod
    def fix_all_issues(cls, text: str) -> str:
        # Step 1: spaCy/Regex Auto-Sanitize (確定性科學單位空格 + 及物動詞多餘介系詞移除)
        sanitized, _ = AcademicNLPPipeline.auto_sanitize(text)
        res = sanitized

        # Step 2: 縮寫自動展開
        for pat, (rep, _) in cls.CONTRACTIONS.items():
            res = re.sub(pat, rep, res, flags=re.IGNORECASE)

        # Step 3: 常見搭配詞自動校正
        for pat, (rep, _) in cls.AWKWARD_COLLOCATIONS.items():
            first_rep = rep.split('/')[0].strip()
            res = re.sub(pat, first_rep, res, flags=re.IGNORECASE)

        # Step 4: 口語詞直接替換
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
    severity: str = Field(default="Strongly Recommended (強烈建議補強)", description="嚴重程度 (Must Address / Strongly Recommended / Optional)")
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
    collocation_issues: List[IssueItem] = Field(
        default_factory=list,
        description="專門針對詞彙/片語層級：列出 3 至 6 處生硬搭配詞 (Collocation Defect) 與精準用詞替換選項，每項提供 3~4 個替代風格選項"
    )
    discourse_issues: List[IssueItem] = Field(
        default_factory=list,
        description="專門針對句子/篇章層級：列出 3 至 6 處文法句構 (Grammar & Mechanics)、邏輯矛盾 (Logic Error)、推論缺陷 (Flawed Deduction)、修辭風格 (Rhetorical Defect) 的具體改進點"
    )
    issues: List[IssueItem] = Field(
        default_factory=list,
        description="所有問題清單（由系統自動整合）"
    )
    revised_full_text: str = Field(default="", description="綜合各項最佳建議後的完整修訂後英文文章全文")

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
        self.update_url = (update_url or "").strip()

    def run(self):
        try:
            url_to_use = self.update_url
            app_dir = os.path.dirname(os.path.abspath(__file__))

            # 1. 處理本地檔案路徑或空字串
            data = None
            if not url_to_use or url_to_use == "version.json":
                # 優先檢查本地是否有可用的 version.json
                local_v = os.path.join(app_dir, "version.json")
                if os.path.exists(local_v):
                    try:
                        with open(local_v, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        pass
                if data is None:
                    url_to_use = DEFAULT_UPDATE_URL
            elif url_to_use.startswith("file://"):
                local_path = url_to_use.replace("file://", "").lstrip("/")
                if os.path.exists(local_path):
                    with open(local_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
            elif not (url_to_use.startswith("http://") or url_to_use.startswith("https://")):
                cand_abs = os.path.abspath(url_to_use)
                cand_rel = os.path.join(app_dir, url_to_use)
                if os.path.exists(cand_abs):
                    with open(cand_abs, "r", encoding="utf-8") as f:
                        data = json.load(f)
                elif os.path.exists(cand_rel):
                    with open(cand_rel, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    url_to_use = DEFAULT_UPDATE_URL

            # 2. 透過遠端 HTTP(S) 查詢（支援 Primary 與 Fallback 多軌切換）
            if data is None:
                candidates = [url_to_use]
                for fb in [FALLBACK_UPDATE_URL, FALLBACK_UPDATE_URL_2]:
                    if fb not in candidates:
                        candidates.append(fb)

                last_err = ""
                for target in candidates:
                    try:
                        resp = httpx.get(target, timeout=8.0, follow_redirects=True)
                        if resp.status_code == 200:
                            data = resp.json()
                            break
                        elif resp.status_code == 404:
                            last_err = f"HTTP 404 (端點不存在: {target})"
                        else:
                            last_err = f"HTTP {resp.status_code}"
                    except Exception as ex:
                        last_err = str(ex)

                # 若遠端伺服器存取失敗（例如目前 GitHub 為 Private 倉庫），自動嘗試讀取本地檔案作為後備
                if data is None:
                    local_v = os.path.join(app_dir, "version.json")
                    if os.path.exists(local_v):
                        try:
                            with open(local_v, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        except Exception:
                            pass

                if data is None:
                    err_msg = last_err or "Cannot connect to update server."
                    if "404" in err_msg:
                        err_msg += "（若 GitHub 倉庫目前為私人 Private 狀態，請於發布時切換為 Public 公開）"
                    self.check_finished.emit(False, "", "", "", err_msg)
                    return

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
            dest_path = os.path.join(tempfile.gettempdir(), "LibreLlamaLabEditor_Setup_Update.exe")
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
        if saved_url in ("version.json", "", None):
            saved_url = DEFAULT_UPDATE_URL
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
        # 範疇提示
        if self.context_scope == "partial":
            if self.section_target == "auto":
                scope_prompt = (
                    "【IMPORTANT CONTEXT SCOPE & AUTO-DETECTION】: The user has indicated that this input text is a PARTIAL EXCERPT, "
                    "but the exact section type is unspecified. You MUST first determine the most likely section type of this excerpt "
                    "(e.g. Methodology, Literature Review, Discussion, Executive Summary), explicitly state your classification in "
                    "article_gist, and evaluate the draft against appropriate international standards for that section."
                ) if is_en else (
                    "【重要文章範圍與自動章節識別】：使用者標記此輸入為「局部段落選取」，但章節類型設為「其他 / 由模型自動判斷」。"
                    "你必須首先自行判讀此段落最可能所屬的章節性質（例如方法、結果、引言、文獻探討、執行摘要等），"
                    "並在全文主旨診斷 (article_gist) 中明確註明你的章節判斷，隨後依該章節之最高國際專業標準進行審查。"
                )
            else:
                scope_prompt = (
                    f"【IMPORTANT CONTEXT SCOPE】: The user has indicated that this input text is a SPECIFIC PARTIAL EXCERPT "
                    f"from the [{section_name}] section. You must focus your critique specifically on the conventions, "
                    f"standards, and requirements of this particular section. Do NOT penalize the text for omitting "
                    f"information that belongs in other sections of the document."
                ) if is_en else (
                    f"【重要文章範圍】：使用者已明確標記此文本為【{section_name}】的局部選取段落。"
                    f"你的審查與修改必須緊密契合此章節的國際期刊／商務寫作慣例與結構標準，絕不可因為該段落未包含其他章節的內容而予以扣分！"
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

You must evaluate the input draft across three distinct, parallel, non-mutually-exclusive dimensions:

==================================================
DIMENSION 1: STRATEGIC & EMPIRICAL RECOMMENDATIONS (`research_recommendations`)
==================================================
- You MUST provide 2 to 4 actionable, high-impact improvements (gap_identified_en, concrete_proposal_en, impact_on_acceptance_en, severity).
- For academic writing: ablation studies, statistical significance, causal validation, confounding variables, methodological defenses.
- For correspondence: diplomatic etiquette, actionable clarity, boundary setting.
- For application: quantified achievements, narrative arc, personal differentiation.
- For business: strategic feasibility, ROI, execution roadmaps.

==================================================
DIMENSION 2: COLLOCATION & LEXICAL REVISION (`collocation_issues`)
==================================================
- Focus strictly on word- and phrase-level pairings: unnatural verb-noun combinations (e.g. 'make an experiment' -> conduct), loose prepositions, unidiomatic academic collocations.
- Provide 3 to 6 distinct items.
- For EVERY issue, provide 3 to 4 authentic stylistic options in `revision_options` (Option A: Standard, Option B: High-Impact, Option C: Cautious/Hedged, Option D: Authoritative).

==================================================
DIMENSION 3: DISCOURSE, GRAMMAR & LOGIC CRITIQUES (`discourse_issues`)
==================================================
- Focus on sentence-level and discourse-level flaws: Grammar & Mechanics, Logic Error (contradictions, internal inconsistencies), Flawed Deduction (leaps in logic, overclaiming), and Rhetorical Defect.
- Provide 3 to 6 distinct items.

【CRITICAL RULE: DUAL NON-MUTUALLY-EXCLUSIVE TRACK】:
A single sentence often contains BOTH a lexical/collocation flaw AND a grammatical or logical error.
DO NOT skip grammar or logic critique just because you already flagged a collocation in that sentence!
Both arrays (`collocation_issues` and `discourse_issues`) must be populated in parallel!

JSON FORMATTING: Ensure output is strictly valid JSON matching the schema."""
        else:
            prompt = f"""你是一名【{persona}】。
請注意：本系統使用者為【正體中文（繁體中文，臺灣慣用語彙）】使用者，所有中文說明與解析必須使用道地正體中文，切勿使用簡體字。

{scope_prompt}

請針對輸入的英文草稿，在【{mode_info['name_zh']}】情境下進行三大平行且【絕不互斥】的【深度極限審查】：

==================================================
維度一：【上下文論點完整性與實證/策略補強建議 (`research_recommendations`)】
==================================================
【絕對必須產出】：你【必須】提出 2 至 4 點深層實質補強建議：
- 若為學術論文：深入檢核實驗方法、因果推論、消融實驗、顯著性檢定、混雜變因控制與審稿防禦方案。
- 若為專業書信：檢視語氣得體性、溝通透明度、明確行動呼籲與利益關係人對齊。
- 若為申請文件：檢視個人動機說服力、成就量化動詞、避免陳詞濫調與目標契合度。
- 若為商務報告：檢視數據洞察支撐、執行可行性與ROI決策論述。
- 【雙語對照嚴格要求】：每一項建議皆必須【同時】填寫正體中文與道地英文專業評述：
  * gap_identified_zh (中文缺失分析) 與 gap_identified_en (Rigorous English analysis of the empirical gap)
  * concrete_proposal_zh (中文具體補做方案) 與 concrete_proposal_en (Actionable concrete protocol in English)
  * impact_on_acceptance_zh (中文錄用防禦效益) 與 impact_on_acceptance_en (Defense impact in English)
  * action_type 與 severity ("Must Address" / "Strongly Recommended" / "Optional")。

==================================================
維度二：【搭配詞與精準用詞替換選項 (`collocation_issues`)】
==================================================
- 專注詞彙與片語層級：精準抓出中式英文、生硬搭配、動名不合、非自然介系詞（如 make research ➔ conduct research; play an effect ➔ exert an effect; statistically big ➔ statistically significant）。
- 產出 3 至 6 處改進點。
- 每一處問題均【必須】填寫：
  * reviewer_comment_en: 1~2 句專業且道地的英文審稿評語 (Rigorous peer-reviewer critique in pure English，絕不可為空)！
  * reviewer_comment_zh: 正體中文審稿意見。
  * revision_options: 提供 3 至 4 個不同語感風格的替代選項 (Option A, B, C, D)，每個選項附上 revised_text, style_label, rationale_zh, rationale_en！

==================================================
維度三：【文法句構、推論缺陷、修辭風格與邏輯矛盾 (`discourse_issues`)】
==================================================
- 專注句子結構與篇章邏輯：懸垂修飾、主謂不合、平行結構、過度宣稱（Overclaiming）、推論跳躍、邏輯矛盾與非正式語氣。
- 產出 3 至 6 處改進點。
- 每一處問題同樣【必須】填寫 reviewer_comment_en (專業英文評語，絕不可為空) 與 reviewer_comment_zh (正體中文評語) 及 revision_options！

==================================================
【關鍵核心規則：雙軌並行、絕不互斥 (Non-Mutually Exclusive)】
==================================================
一個句子若同時存在「詞彙搭配生硬（如 make an experiment）」與「文法結構錯誤（如缺少主詞/時態矛盾）」或「邏輯推論漏洞（如過度斷言 without any other factors）」，你【必須同時分開提出】！
絕不能因為該句已在 `collocation_issues` 中被挑出，就在 `discourse_issues` 中忽略整句的結構或邏輯問題！兩者必須並存！

【精簡精確輸出原則】：每處評語與分析請保持精煉（1~2 句話即可），切勿重複贅述相同觀點，嚴防產生冗長循環。

【格式規範】：請確保輸出為符合 Schema 的合法 JSON。"""

        return prompt

    def run(self):
        system_prompt = self.build_system_prompt()
        full_content = ""
        chunk_count = 0
        salvaged_after_abort = False

        try:
            if self.engine_mode == "ollama":
                response_stream = ollama.chat(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Please critically and exhaustively review the following text:\n\n{self.text}"}
                    ],
                    format=AcademicReviewReport.model_json_schema(),
                    options={
                        "temperature": 0.45,
                        "top_p": 0.90,
                        "top_k": 40,
                        "repeat_penalty": 1.18,
                        "repeat_last_n": 128,
                        "num_ctx": 16384,
                        "num_predict": -1
                    },
                    stream=True
                )
                try:
                    for chunk in response_stream:
                        delta = chunk.get('message', {}).get('content', '')
                        if delta:
                            full_content += delta
                            chunk_count += 1
                            self.chunk_received.emit(delta, chunk_count)

                            # 即時檢測退化循環 (Degenerate Repetition Detection)
                            # 若結尾有 2~15 字元的模式重複超過 6 次，或單一字元重複超過 12 次，提早截斷串流以防崩潰
                            if len(full_content) > 80:
                                if re.search(r'(.{2,15}?)\1{6,}$', full_content) or re.search(r'(.)\1{12,}$', full_content):
                                    print("[ReviewWorker] Degenerate repetition detected in Ollama stream, breaking early to salvage JSON.")
                                    salvaged_after_abort = True
                                    break
                except Exception as stream_err:
                    err_msg = str(stream_err).lower()
                    # 捕捉 Ollama/llama.cpp 的 token repeat limit 或 status code -1 中斷
                    if ("repeat limit" in err_msg or "prediction aborted" in err_msg or "status code: -1" in err_msg or "-1" in err_msg) and len(full_content) > 60:
                        print(f"[ReviewWorker] Intercepted Ollama stream abort: {stream_err}. Salvaging {len(full_content)} chars.")
                        salvaged_after_abort = True
                    else:
                        raise
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
                    "temperature": 0.45,
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

                                        if len(full_content) > 80:
                                            if re.search(r'(.{2,15}?)\1{6,}$', full_content) or re.search(r'(.)\1{12,}$', full_content):
                                                print("[ReviewWorker] Degenerate repetition detected in API stream, breaking early.")
                                                salvaged_after_abort = True
                                                break
                                except Exception:
                                    continue

            # 清除結尾退化重複文字（如 ackackackack... 或 aaaaaa...）
            full_content = re.sub(r'(.{2,15}?)\1{4,}$', '', full_content)
            full_content = re.sub(r'(.)\1{8,}$', '', full_content)

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
                pass

            if data is None or not isinstance(data, dict):
                try:
                    repaired = json_repair.repair_json(raw_content, return_objects=True)
                    if isinstance(repaired, dict):
                        data = repaired
                except Exception:
                    pass

            if not data or not isinstance(data, dict):
                raise ValueError(f"Could not parse model JSON response.\nFragment:\n{raw_content[-200:]}")

            if salvaged_after_abort:
                note_zh = "（系統提示：模型尾段因字詞重複提早終止，系統已自動修復並呈現完整審查建議）"
                note_en = " (System Note: Output stream was auto-repaired to prevent token repetition loop)"
                curr_zh = str(data.get('overall_assessment_zh') or '')
                curr_en = str(data.get('overall_assessment_en') or '')
                if curr_zh:
                    data['overall_assessment_zh'] = f"{curr_zh}\n{note_zh}"
                else:
                    data['overall_assessment_zh'] = f"審查已完成。{note_zh}"
                if curr_en:
                    data['overall_assessment_en'] = f"{curr_en}\n{note_en}"
                else:
                    data['overall_assessment_en'] = f"Review completed.{note_en}"

            # 數據容錯與補齊：雙軌獨立解析與中英雙語評論 100% 健全保證
            def has_cjk(s: str) -> bool:
                return bool(re.search(r'[\u4e00-\u9fff]', s)) if s else False

            def parse_issue_item(raw_issue: dict, default_category: str = "Collocation Defect") -> Optional[IssueItem]:
                if not isinstance(raw_issue, dict) or not raw_issue.get('original_text'):
                    return None
                orig = str(raw_issue.get('original_text', '')).strip()
                if not raw_issue.get('category'):
                    raw_issue['category'] = default_category
                cat = raw_issue['category']
                if not raw_issue.get('severity'):
                    raw_issue['severity'] = 'Major'
                if not raw_issue.get('revision_options') or not isinstance(raw_issue['revision_options'], list):
                    raw_issue['revision_options'] = [{
                        "style_label": "Standard Academic Register",
                        "revised_text": orig,
                        "rationale_zh": "優化道地語感與表達",
                        "rationale_en": "Optimized for natural native register."
                    }]

                # 確保英文審稿意見 (reviewer_comment_en) 存在且為純英文
                comm_en = str(raw_issue.get('reviewer_comment_en', '')).strip()
                if not comm_en or has_cjk(comm_en):
                    opt_rationale_en = ""
                    first_opt = raw_issue['revision_options'][0]
                    if isinstance(first_opt, dict) and first_opt.get('rationale_en'):
                        candidate = str(first_opt['rationale_en']).strip()
                        if candidate and not has_cjk(candidate):
                            opt_rationale_en = candidate

                    if opt_rationale_en:
                        comm_en = f"Reviewer Note ({cat}): {opt_rationale_en}"
                    elif cat == "Collocation Defect":
                        comm_en = f"Unidiomatic collocation in \"{orig}\". Recommend adopting standard academic/formal phrasing for natural register and precision."
                    elif cat == "Grammar & Mechanics":
                        comm_en = f"Grammatical or syntactic irregularity detected in \"{orig}\". Restructure sentence to conform to standard conventions."
                    elif cat == "Logic Error":
                        comm_en = f"Logical contradiction or incoherence in \"{orig}\". Clarify premise or ensure contextual alignment."
                    elif cat == "Flawed Deduction":
                        comm_en = f"Unjustified deductive leap or overclaim in \"{orig}\". Moderate assertion with appropriate academic hedging."
                    elif cat == "Rhetorical Defect":
                        comm_en = f"Rhetorical defect or informal tone in \"{orig}\". Revise to maintain an objective academic tone."
                    else:
                        comm_en = f"Peer-review critique: Revise \"{orig}\" to enhance precision, clarity, and academic rigor."
                raw_issue['reviewer_comment_en'] = comm_en

                # 確保正體中文審稿意見 (reviewer_comment_zh) 存在
                comm_zh = str(raw_issue.get('reviewer_comment_zh', '')).strip()
                if not comm_zh:
                    raw_issue['reviewer_comment_zh'] = f"針對「{orig}」之{cat}，建議採用更嚴謹、道地之表達以增強文章說服力。"

                try:
                    return IssueItem(**raw_issue)
                except Exception:
                    return None

            valid_colloc = []
            for item in data.get('collocation_issues', []):
                p = parse_issue_item(item, default_category="Collocation Defect")
                if p:
                    p.category = "Collocation Defect"
                    valid_colloc.append(p)

            valid_discourse = []
            for item in data.get('discourse_issues', []):
                p = parse_issue_item(item, default_category="Grammar & Mechanics")
                if p:
                    valid_discourse.append(p)

            # 相容性回退：若模型回傳舊版單一 `issues`
            if not valid_colloc and not valid_discourse:
                for item in data.get('issues', []):
                    p = parse_issue_item(item)
                    if p:
                        if p.category == "Collocation Defect":
                            valid_colloc.append(p)
                        else:
                            valid_discourse.append(p)

            data['collocation_issues'] = valid_colloc
            data['discourse_issues'] = valid_discourse
            data['issues'] = valid_colloc + valid_discourse

            # 實證與策略補強建議解析（高容錯雙語防禦，絕無中文出現在英文欄位）
            valid_recs = []
            for raw_rec in data.get('research_recommendations', []):
                if not isinstance(raw_rec, dict):
                    continue
                act = str(raw_rec.get('action_type') or "Methodological & Empirical Defense")
                sev = str(raw_rec.get('severity') or "Strongly Recommended (強烈建議補強)")

                gap_zh = str(raw_rec.get('gap_identified_zh') or raw_rec.get('gap_identified') or "").strip()
                gap_en = str(raw_rec.get('gap_identified_en') or "").strip()
                if not gap_en or has_cjk(gap_en):
                    gap_en = f"Critical strategic/empirical gap identified regarding {act}. Lacks rigorous validation and explicit context continuity."
                if not gap_zh:
                    gap_zh = f"於「{act}」維度發現實證論據不足或上下文銜接落差，易引發審閱人質疑。"

                prop_zh = str(raw_rec.get('concrete_proposal_zh') or raw_rec.get('concrete_proposal') or "").strip()
                prop_en = str(raw_rec.get('concrete_proposal_en') or "").strip()
                if not prop_en or has_cjk(prop_en):
                    prop_en = f"Actionable protocol: Incorporate quantitative benchmarking, ablation validation, or explicit contextual defenses for {act}."
                if not prop_zh:
                    prop_zh = f"建議具體補充消融實驗、顯著性檢定或對照基準，以建立不可動搖之論證防禦。"

                impact_zh = str(raw_rec.get('impact_on_acceptance_zh') or raw_rec.get('impact_on_acceptance') or "").strip()
                impact_en = str(raw_rec.get('impact_on_acceptance_en') or "").strip()
                if not impact_en or has_cjk(impact_en):
                    impact_en = f"Preempts reviewer skepticism, reinforces internal consistency, and substantively boosts manuscript acceptance rate."
                if not impact_zh:
                    impact_zh = f"主動化解審稿人潛在質疑，封堵邏輯漏洞，大幅提升文章錄用與說服機率。"

                try:
                    rec_obj = ResearchRecommendation(
                        gap_identified_zh=gap_zh,
                        gap_identified_en=gap_en,
                        severity=sev,
                        action_type=act,
                        concrete_proposal_zh=prop_zh,
                        concrete_proposal_en=prop_en,
                        impact_on_acceptance_zh=impact_zh,
                        impact_on_acceptance_en=impact_en
                    )
                    valid_recs.append(rec_obj)
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
# 5.1 互動對話輸入與背景工作線程 (ChatInputEdit & InteractiveChatWorker)
# ==========================================
class ChatInputEdit(QTextEdit):
    send_requested = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_requested.emit()
                event.accept()
        else:
            super().keyPressEvent(event)

class InteractiveChatWorker(QThread):
    chunk_received = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        engine_mode: str,
        model_name: str,
        api_config: dict,
        messages: List[Dict[str, str]],
        system_prompt: str
    ):
        super().__init__()
        self.engine_mode = engine_mode
        self.model_name = model_name
        self.api_config = api_config
        self.messages = messages
        self.system_prompt = system_prompt
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        full_reply = ""
        try:
            full_msgs = [{"role": "system", "content": self.system_prompt}] + self.messages
            if self.engine_mode == "ollama":
                response_stream = ollama.chat(
                    model=self.model_name,
                    messages=full_msgs,
                    options={
                        "temperature": 0.5,
                        "top_p": 0.90,
                        "repeat_penalty": 1.18,
                        "repeat_last_n": 128
                    },
                    stream=True
                )
                for chunk in response_stream:
                    if self._is_cancelled:
                        break
                    delta = chunk.get('message', {}).get('content', '')
                    if delta:
                        full_reply += delta
                        self.chunk_received.emit(delta)
            else:
                api_url = self.api_config.get("api_url", "https://api.deepseek.com/v1").rstrip('/')
                api_key = self.api_config.get("api_key", "").strip()
                model = self.api_config.get("api_model", "deepseek-chat").strip()
                if not api_key:
                    raise ValueError("API Key not configured. Please open API Settings.")
                endpoint = f"{api_url}/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": model,
                    "messages": full_msgs,
                    "temperature": 0.5,
                    "stream": True
                }
                with httpx.Client(timeout=90.0) as client:
                    with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            err_body = response.read().decode('utf-8', errors='ignore')
                            raise ValueError(f"API Error ({response.status_code}): {err_body}")
                        for line in response.iter_lines():
                            if self._is_cancelled:
                                break
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                c_json = json.loads(data_str)
                                delta = c_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    full_reply += delta
                                    self.chunk_received.emit(delta)
                            except Exception:
                                continue

            self.finished.emit(full_reply)
        except Exception as e:
            self.error.emit(str(e))

# ==========================================
# 6. 建議卡片組件 (中英對照或純英文)
# ==========================================
class ResearchRecommendationCard(QFrame):
    def __init__(self, rec: ResearchRecommendation, is_dark: bool = False, lang: str = "zh_TW", on_discuss_callback=None):
        super().__init__()
        self.rec = rec
        self.is_dark = is_dark
        self.lang = lang
        self.on_discuss_callback = on_discuss_callback
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

        if self.on_discuss_callback:
            self.discuss_btn = QPushButton("💬 辯護 / 討論" if not is_en else "💬 Discuss / Rebuttal")
            self.discuss_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6366f1; color: #ffffff; border: none;
                    border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: bold;
                }
                QPushButton:hover { background-color: #4f46e5; }
            """)
            self.discuss_btn.clicked.connect(lambda: self.on_discuss_callback(self.rec))
            top_row.addWidget(self.discuss_btn)

        layout.addLayout(top_row)

        box_css = f"QFrame {{ background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 6px; padding: 6px; }} QLabel {{ border: none; background: transparent; color: {text_title}; }}"

        # 1. 缺失分析
        gap_box = QFrame()
        gap_box.setStyleSheet(box_css)
        g_layout = QVBoxLayout(gap_box)
        g_layout.setContentsMargins(8, 6, 8, 6)
        g_layout.setSpacing(3)

        title_text = "<b>⚠️ Strategic / Empirical Gap Analysis:</b>" if is_en else "<b>⚠️ 上下文與論點缺失分析 (Evidence Gap):</b>"
        g_title = QLabel(title_text)
        g_title.setStyleSheet(f"font-size: 12px; color: {text_title}; font-weight: bold;")
        g_layout.addWidget(g_title)

        if not is_en and self.rec.gap_identified_zh:
            gap_zh = QLabel(f"<b>🇹🇼 中文：</b><span style='color: {zh_color};'>{html.escape(self.rec.gap_identified_zh)}</span>")
            gap_zh.setWordWrap(True)
            gap_zh.setStyleSheet(f"font-size: 12px; color: {zh_color};")
            g_layout.addWidget(gap_zh)

        en_val = self.rec.gap_identified_en.strip() if self.rec.gap_identified_en else ""
        if en_val:
            gap_en = QLabel(f"{'<b>Critique:</b> ' if is_en else '<b>🇺🇸 EN：</b>'}<span style='color: {en_color}; font-style: italic;'>{html.escape(en_val)}</span>")
            gap_en.setWordWrap(True)
            gap_en.setStyleSheet(f"font-size: 11px; color: {en_color};")
            g_layout.addWidget(gap_en)
        layout.addWidget(gap_box)

        # 2. 建議補做方案
        prop_box = QFrame()
        prop_box.setStyleSheet(box_css)
        p_layout = QVBoxLayout(prop_box)
        p_layout.setContentsMargins(8, 6, 8, 6)
        p_layout.setSpacing(3)

        prop_title_text = "<b>💡 Actionable Strategic Proposal:</b>" if is_en else "<b>💡 建議補做方案 (Proposed Protocol / Experiments):</b>"
        p_title = QLabel(prop_title_text)
        p_title.setStyleSheet(f"font-size: 12px; color: {text_title}; font-weight: bold;")
        p_layout.addWidget(p_title)

        if not is_en and self.rec.concrete_proposal_zh:
            prop_zh = QLabel(f"<b>🇹🇼 中文：</b><span style='color: {zh_color};'>{html.escape(self.rec.concrete_proposal_zh)}</span>")
            prop_zh.setWordWrap(True)
            prop_zh.setStyleSheet(f"font-size: 12px; color: {zh_color};")
            p_layout.addWidget(prop_zh)

        prop_en_val = self.rec.concrete_proposal_en.strip() if self.rec.concrete_proposal_en else ""
        if prop_en_val:
            prop_en = QLabel(f"{'<b>Proposal:</b> ' if is_en else '<b>🇺🇸 EN：</b>'}<span style='color: {en_color}; font-style: italic;'>{html.escape(prop_en_val)}</span>")
            prop_en.setWordWrap(True)
            prop_en.setStyleSheet(f"font-size: 11px; color: {en_color};")
            p_layout.addWidget(prop_en)
        layout.addWidget(prop_box)

        # 3. 效益評估
        impact_box = QFrame()
        impact_box.setStyleSheet(box_css)
        i_layout = QVBoxLayout(impact_box)
        i_layout.setContentsMargins(8, 6, 8, 6)
        i_layout.setSpacing(3)

        impact_title_text = "<b>🛡️ Strategic Uplift & Acceptance Impact:</b>" if is_en else "<b>🛡️ 投稿防禦效益 (Defense Impact):</b>"
        i_title = QLabel(impact_title_text)
        i_title.setStyleSheet(f"font-size: 12px; color: {text_title}; font-weight: bold;")
        i_layout.addWidget(i_title)

        if not is_en and self.rec.impact_on_acceptance_zh:
            impact_zh = QLabel(f"<b>🇹🇼 中文：</b><span style='color: {zh_color};'>{html.escape(self.rec.impact_on_acceptance_zh)}</span>")
            impact_zh.setWordWrap(True)
            impact_zh.setStyleSheet(f"font-size: 12px; color: {zh_color};")
            i_layout.addWidget(impact_zh)

        impact_en_val = self.rec.impact_on_acceptance_en.strip() if self.rec.impact_on_acceptance_en else ""
        if impact_en_val:
            impact_en = QLabel(f"{'<b>Impact:</b> ' if is_en else '<b>🇺🇸 EN：</b>'}<span style='color: {en_color}; font-style: italic;'>{html.escape(impact_en_val)}</span>")
            impact_en.setWordWrap(True)
            impact_en.setStyleSheet(f"font-size: 11px; color: {en_color};")
            i_layout.addWidget(impact_en)
        layout.addWidget(impact_box)

class IssueCard(QFrame):
    def __init__(self, issue_idx: int, issue: IssueItem, on_option_selected_callback, is_dark: bool = False, lang: str = "zh_TW", on_discuss_callback=None):
        super().__init__()
        self.issue_idx = issue_idx
        self.issue = issue
        self.on_option_selected_callback = on_option_selected_callback
        self.selected_option_idx: int = 0
        self.option_buttons: List[QPushButton] = []
        self.is_dark = is_dark
        self.lang = lang
        self.on_discuss_callback = on_discuss_callback
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

        if self.on_discuss_callback:
            self.discuss_btn = QPushButton("💬 辯護 / 討論" if not is_en else "💬 Discuss / Rebuttal")
            self.discuss_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2563eb; color: #ffffff; border: none;
                    border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: bold;
                }
                QPushButton:hover { background-color: #1d4ed8; }
            """)
            self.discuss_btn.clicked.connect(lambda: self.on_discuss_callback(self.issue))
            top_row.addWidget(self.discuss_btn)

        layout.addLayout(top_row)

        meaning_box = QFrame()
        meaning_box.setStyleSheet(f"QFrame {{ background-color: {card_bg}; border: 1px solid {card_border}; border-radius: 6px; padding: 6px; }} QLabel {{ border: none; background: transparent; }}")
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

        # 評論區 (有評論才渲染，杜絕空綠框)
        has_comment = False
        comment_box = QFrame()
        comment_box.setStyleSheet(f"QFrame {{ background-color: {comment_box_bg}; border: 1px solid {comment_box_border}; border-left: 4px solid #10b981; border-radius: 4px; }} QLabel {{ border: none; background: transparent; }}")
        comment_layout = QVBoxLayout(comment_box)
        comment_layout.setContentsMargins(8, 6, 8, 6)
        comment_layout.setSpacing(4)

        if not is_en and self.issue.reviewer_comment_zh:
            zh_comm = self.issue.reviewer_comment_zh.strip()
            if zh_comm:
                comment_zh = QLabel(f"<b>🇹🇼 審稿意見 (中文)：</b><span style='color: {zh_color};'>{html.escape(zh_comm)}</span>")
                comment_zh.setWordWrap(True)
                comment_zh.setStyleSheet("font-size: 12px;")
                comment_layout.addWidget(comment_zh)
                has_comment = True

        en_comm = self.issue.reviewer_comment_en.strip() if self.issue.reviewer_comment_en else ""
        if en_comm:
            comment_en = QLabel(f"{'<b>Reviewer Critique:</b> ' if is_en else '<b>🇺🇸 Reviewer Comment (EN)：</b>'}<span style='color: {en_color}; font-style: italic;'>{html.escape(en_comm)}</span>")
            comment_en.setWordWrap(True)
            comment_en.setStyleSheet("font-size: 11px;")
            comment_layout.addWidget(comment_en)
            has_comment = True

        if has_comment:
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

        # 互動辯護與對話狀態 (Interactive Discussion State)
        self.chat_history: List[Dict[str, str]] = []
        self.current_chat_context: Optional[Dict[str, Any]] = None
        self.chat_worker: Optional[InteractiveChatWorker] = None
        self.is_chat_generating: bool = False
        self._active_streaming_text: str = ""

        self.init_ui()
        self.apply_language()
        self.apply_theme()

    def init_ui(self):
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(12, 8, 12, 10)
        self.main_layout.setSpacing(6)

        # --- 整合型頂部工具列 (Unified Sleek Top Toolbar) ---
        self.unified_toolbar = QFrame()
        self.unified_toolbar.setObjectName("unifiedToolbar")
        self.unified_toolbar.setFixedHeight(70)
        self.mode_control_frame = self.unified_toolbar

        toolbar_container_layout = QVBoxLayout(self.unified_toolbar)
        toolbar_container_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_container_layout.setSpacing(4)

        # Row 1: 品牌標誌、引擎模式、API設定、模型選擇、環境精靈、語系、主題、更新
        row1_layout = QHBoxLayout()
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(6)

        self.title_label = QLabel(t["toolbar_title"])
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        row1_layout.addWidget(self.title_label)

        self.v_badge = QLabel(f"v{APP_VERSION} (Pre-release)")
        self.v_badge.setStyleSheet("color: #94a3b8; font-size: 11px; margin-right: 6px;")
        row1_layout.addWidget(self.v_badge)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["🖥️ 在地 Ollama (100% 離線隱私)", "☁️ 線上 API (DeepSeek/OpenAI/Gemini)"])
        if self.engine_mode == "api":
            self.engine_combo.setCurrentIndex(1)
        self.engine_combo.currentIndexChanged.connect(self.on_engine_mode_changed)
        row1_layout.addWidget(self.engine_combo)

        self.api_settings_btn = QPushButton("⚙️ API 設定")
        self.api_settings_btn.clicked.connect(self.open_api_settings)
        row1_layout.addWidget(self.api_settings_btn)

        row1_layout.addSpacing(4)

        self.model_label = QLabel("模型:")
        self.model_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        row1_layout.addWidget(self.model_label)

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(150)
        row1_layout.addWidget(self.model_combo)

        self.refresh_btn = QPushButton("🔄 重新整理")
        self.refresh_btn.clicked.connect(self.load_installed_models)
        row1_layout.addWidget(self.refresh_btn)

        row1_layout.addStretch()

        self.env_setup_btn = QPushButton("📥 本機環境精靈")
        self.env_setup_btn.clicked.connect(self.open_environment_dialog)
        row1_layout.addWidget(self.env_setup_btn)

        self.lang_btn = QPushButton("🌐 English" if self.ui_language == "zh_TW" else "🌐 繁體中文")
        self.lang_btn.clicked.connect(self.toggle_language)
        row1_layout.addWidget(self.lang_btn)

        self.theme_btn = QPushButton("🌙 暗黑模式" if not self.is_dark_mode else "☀️ 明亮模式")
        self.theme_btn.clicked.connect(self.toggle_theme)
        row1_layout.addWidget(self.theme_btn)

        self.update_btn = QPushButton("🚀 檢查更新")
        self.update_btn.clicked.connect(self.open_update_dialog)
        row1_layout.addWidget(self.update_btn)

        toolbar_container_layout.addLayout(row1_layout)

        # Row 2: 寫作情境模式 + 文章範圍 + 章節定位 + 載入情境範文
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(6)

        self.mode_lbl = QLabel("寫作情境:")
        self.mode_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        row2_layout.addWidget(self.mode_lbl)

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
        row2_layout.addWidget(self.mode_combo)

        row2_layout.addSpacing(10)

        self.scope_lbl = QLabel("文章範圍:")
        self.scope_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        row2_layout.addWidget(self.scope_lbl)

        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["📄 全篇完整文章", "📑 局部段落選取"])
        self.scope_combo.setCurrentIndex(1 if self.context_scope == "partial" else 0)
        self.scope_combo.currentIndexChanged.connect(self.on_context_scope_changed)
        row2_layout.addWidget(self.scope_combo)

        row2_layout.addSpacing(10)

        self.section_lbl = QLabel("章節定位:")
        self.section_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        row2_layout.addWidget(self.section_lbl)

        self.section_combo = QComboBox()
        row2_layout.addWidget(self.section_combo)

        row2_layout.addSpacing(10)

        self.load_sample_btn = QPushButton("📋 載入情境範文")
        self.load_sample_btn.clicked.connect(self.load_mode_sample_text)
        row2_layout.addWidget(self.load_sample_btn)

        row2_layout.addStretch()

        toolbar_container_layout.addLayout(row2_layout)

        self.main_layout.addWidget(self.unified_toolbar, 0)

        # --- 主水平分割器 (平分三欄，各佔約 1/3) ---
        self.splitter = QSplitter(Qt.Horizontal)

        # ==========================================
        # 左側欄位 (1/3)：垂直上下分割，上為草稿區，下為修訂全文區
        # ==========================================
        self.left_splitter = QSplitter(Qt.Vertical)

        # 原始英文草稿區 (上部)
        self.draft_widget = QWidget()
        draft_layout = QVBoxLayout(self.draft_widget)
        draft_layout.setContentsMargins(0, 0, 4, 4)
        draft_layout.setSpacing(5)

        draft_header = QHBoxLayout()
        self.draft_title_lbl = QLabel("原始英文草稿")
        self.draft_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        draft_header.addWidget(self.draft_title_lbl)
        draft_header.addStretch()

        self.word_count_lbl = QLabel("字數: 0 字")
        draft_header.addWidget(self.word_count_lbl)
        draft_layout.addLayout(draft_header)

        self.text_editor = AcademicTextEdit(on_quick_fix=self.auto_fix_preflight_issues, is_dark=self.is_dark_mode, lang=self.ui_language)
        self.text_editor.setFont(QFont("Consolas", 11))
        self.text_editor.setPlainText(WRITING_MODES["academic"]["sample"])
        self.text_editor.textChanged.connect(self.on_editor_text_changed)
        draft_layout.addWidget(self.text_editor, 1)

        self.left_splitter.addWidget(self.draft_widget)

        # 修改後全文區 (下部)
        self.revised_widget = QWidget()
        revised_layout = QVBoxLayout(self.revised_widget)
        revised_layout.setContentsMargins(0, 4, 4, 0)
        revised_layout.setSpacing(5)

        revised_header = QHBoxLayout()
        self.revised_title_lbl = QLabel("修改後全文")
        self.revised_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        revised_header.addWidget(self.revised_title_lbl)
        revised_header.addStretch()

        self.sync_to_left_btn = QPushButton("⬆️ 同步至草稿")
        self.sync_to_left_btn.clicked.connect(self.sync_revised_to_left)
        revised_header.addWidget(self.sync_to_left_btn)

        self.copy_btn = QPushButton("📋 複製修訂全文")
        self.copy_btn.clicked.connect(self.copy_revised_text)
        revised_header.addWidget(self.copy_btn)
        revised_layout.addLayout(revised_header)

        self.legend_label = QLabel()
        self.legend_label.setStyleSheet("font-size: 11px; margin-bottom: 2px;")
        revised_layout.addWidget(self.legend_label)

        self.revised_browser = AcademicTextBrowser(is_dark=self.is_dark_mode, lang=self.ui_language)
        self.revised_browser.setFont(QFont("Consolas", 11))
        revised_layout.addWidget(self.revised_browser, 1)

        self.left_splitter.addWidget(self.revised_widget)
        self.left_splitter.setSizes([450, 450])

        self.splitter.addWidget(self.left_splitter)

        # ==========================================
        # 中間欄位 (1/3)：審查意見整合區（實證建議、搭配詞、句構與邏輯三合一）
        # ==========================================
        self.middle_widget = QWidget()
        middle_layout = QVBoxLayout(self.middle_widget)
        middle_layout.setContentsMargins(4, 0, 4, 0)
        middle_layout.setSpacing(6)

        # 頂部：綜合就緒度與主旨解析
        self.assessment_box = AcademicTextBrowser(is_dark=self.is_dark_mode, lang=self.ui_language)
        self.assessment_box.setMaximumHeight(130)
        middle_layout.addWidget(self.assessment_box)

        # 審查意見分類分頁標籤 (QTabWidget)
        self.critique_tab_widget = QTabWidget()
        self.critique_tab_widget.setFont(QFont("Segoe UI", 10))

        # Tab 1: 實質建議與實證缺失分析
        self.recs_page = QWidget()
        recs_page_layout = QVBoxLayout(self.recs_page)
        recs_page_layout.setContentsMargins(4, 4, 4, 4)
        recs_page_layout.setSpacing(4)
        self.recs_title_lbl = QLabel(t["recs_title"])
        self.recs_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        recs_page_layout.addWidget(self.recs_title_lbl)

        self.recs_scroll_area = QScrollArea()
        self.recs_scroll_area.setWidgetResizable(True)
        self.recs_container = QWidget()
        self.recs_layout = QVBoxLayout(self.recs_container)
        self.recs_layout.setContentsMargins(0, 0, 0, 0)
        self.recs_layout.addStretch()
        self.recs_scroll_area.setWidget(self.recs_container)
        recs_page_layout.addWidget(self.recs_scroll_area, 1)

        # Tab 2: 搭配詞替換選項與精準用詞編修
        self.colloc_page = QWidget()
        colloc_page_layout = QVBoxLayout(self.colloc_page)
        colloc_page_layout.setContentsMargins(4, 4, 4, 4)
        colloc_page_layout.setSpacing(4)
        self.colloc_title_lbl = QLabel(t["colloc_title"])
        self.colloc_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        colloc_page_layout.addWidget(self.colloc_title_lbl)

        self.colloc_scroll_area = QScrollArea()
        self.colloc_scroll_area.setWidgetResizable(True)
        self.colloc_container = QWidget()
        self.colloc_layout = QVBoxLayout(self.colloc_container)
        self.colloc_layout.setContentsMargins(0, 0, 0, 0)
        self.colloc_layout.addStretch()
        self.colloc_scroll_area.setWidget(self.colloc_container)
        colloc_page_layout.addWidget(self.colloc_scroll_area, 1)

        # Tab 3: 文法句構、推論缺陷、修辭風格與邏輯矛盾
        self.discourse_page = QWidget()
        discourse_page_layout = QVBoxLayout(self.discourse_page)
        discourse_page_layout.setContentsMargins(4, 4, 4, 4)
        discourse_page_layout.setSpacing(4)
        self.discourse_title_lbl = QLabel(t["discourse_title"])
        self.discourse_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        discourse_page_layout.addWidget(self.discourse_title_lbl)

        self.discourse_scroll_area = QScrollArea()
        self.discourse_scroll_area.setWidgetResizable(True)
        self.discourse_container = QWidget()
        self.discourse_layout = QVBoxLayout(self.discourse_container)
        self.discourse_layout.setContentsMargins(0, 0, 0, 0)
        self.discourse_layout.addStretch()
        self.discourse_scroll_area.setWidget(self.discourse_container)
        discourse_page_layout.addWidget(self.discourse_scroll_area, 1)

        self.critique_tab_widget.addTab(self.recs_page, "💡 實證補強")
        self.critique_tab_widget.addTab(self.colloc_page, "🔤 搭配詞選項")
        self.critique_tab_widget.addTab(self.discourse_page, "⚖️ 句構與邏輯")
        middle_layout.addWidget(self.critique_tab_widget, 1)

        self.splitter.addWidget(self.middle_widget)

        # ==========================================
        # 右側欄位 (1/3)：雙態切換面板（審查進度監控 ➔ LLM 互動辯護工作台）
        # ==========================================
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(6)

        self.right_stack = QStackedWidget()

        # --- 狀態 0：審查進度監控頁面 (Live Progress & Stream Monitor) ---
        self.monitor_page = QWidget()
        mon_layout = QVBoxLayout(self.monitor_page)
        mon_layout.setContentsMargins(0, 0, 0, 0)
        mon_layout.setSpacing(6)

        mon_header = QHBoxLayout()
        self.monitor_title_lbl = QLabel("📡 智能審查執行監控")
        self.monitor_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        mon_header.addWidget(self.monitor_title_lbl)
        mon_header.addStretch()
        self.monitor_badge_lbl = QLabel("就緒")
        self.monitor_badge_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        mon_header.addWidget(self.monitor_badge_lbl)
        mon_layout.addLayout(mon_header)

        self.live_stream_box = AcademicTextEdit(is_dark=self.is_dark_mode, lang=self.ui_language)
        self.live_stream_box.setReadOnly(True)
        self.live_stream_box.setFont(QFont("Consolas", 10))
        self.live_stream_box.setPlaceholderText("模型審查產出即時監控：當點擊下方「開始智能審查」時，模型將在此逐字串流輸出批判分析與 JSON...")
        mon_layout.addWidget(self.live_stream_box, 1)

        self.right_stack.addWidget(self.monitor_page)  # Index 0

        # --- 狀態 1：互動辯護與對話工作台 (Interactive Peer-Review Co-Pilot) ---
        self.chat_page = QWidget()
        chat_layout = QVBoxLayout(self.chat_page)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(6)

        # 對話頂部控制列 (Context Header)
        chat_header = QHBoxLayout()
        self.chat_context_chip = QLabel("🌐 全文綜合討論")
        self.chat_context_chip.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.chat_context_chip.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; border-radius: 4px; padding: 4px 8px;")
        chat_header.addWidget(self.chat_context_chip, 1)

        self.chat_switch_general_btn = QPushButton("🌐 全文討論")
        self.chat_switch_general_btn.setFont(QFont("Segoe UI", 9))
        self.chat_switch_general_btn.clicked.connect(self.switch_to_general_chat)
        chat_header.addWidget(self.chat_switch_general_btn)

        self.chat_clear_btn = QPushButton("🧹 清空")
        self.chat_clear_btn.setFont(QFont("Segoe UI", 9))
        self.chat_clear_btn.clicked.connect(self.clear_chat_history)
        chat_header.addWidget(self.chat_clear_btn)
        chat_layout.addLayout(chat_header)

        # 對話歷史區域 (Chat History Browser)
        self.chat_browser = QTextBrowser()
        self.chat_browser.setOpenExternalLinks(False)
        self.chat_browser.setFont(QFont("Segoe UI", 10))
        chat_layout.addWidget(self.chat_browser, 1)

        # 一鍵快捷辯護行動選鈕列 (Quick Action Pills)
        self.quick_pills_frame = QFrame()
        pills_layout = QHBoxLayout(self.quick_pills_frame)
        pills_layout.setContentsMargins(0, 2, 0, 2)
        pills_layout.setSpacing(4)

        self.pill_defend_btn = QPushButton("🛡️ 領域慣用辯護")
        self.pill_defend_btn.setFont(QFont("Segoe UI", 9))
        self.pill_defend_btn.clicked.connect(lambda: self.send_quick_prompt("defend"))
        pills_layout.addWidget(self.pill_defend_btn)

        self.pill_top_tier_btn = QPushButton("✍️ 頂刊風格升級")
        self.pill_top_tier_btn.setFont(QFont("Segoe UI", 9))
        self.pill_top_tier_btn.clicked.connect(lambda: self.send_quick_prompt("top_tier"))
        pills_layout.addWidget(self.pill_top_tier_btn)

        self.pill_hedging_btn = QPushButton("🔬 語氣弱化防禦")
        self.pill_hedging_btn.setFont(QFont("Segoe UI", 9))
        self.pill_hedging_btn.clicked.connect(lambda: self.send_quick_prompt("hedging"))
        pills_layout.addWidget(self.pill_hedging_btn)

        self.pill_adopt_btn = QPushButton("🔄 產出替換句")
        self.pill_adopt_btn.setFont(QFont("Segoe UI", 9))
        self.pill_adopt_btn.clicked.connect(lambda: self.send_quick_prompt("adopt"))
        pills_layout.addWidget(self.pill_adopt_btn)

        chat_layout.addWidget(self.quick_pills_frame)

        # 輸入列與發送按鈕
        input_box_layout = QHBoxLayout()
        input_box_layout.setSpacing(6)

        self.chat_input = ChatInputEdit()
        self.chat_input.setFixedHeight(50)
        self.chat_input.setFont(QFont("Segoe UI", 10))
        self.chat_input.setPlaceholderText("輸入訊息與審閱模型討論或辯護... (Enter 發送，Shift+Enter 換行)")
        self.chat_input.send_requested.connect(self.on_chat_send_clicked)
        input_box_layout.addWidget(self.chat_input, 1)

        self.chat_send_btn = QPushButton("🚀 發送")
        self.chat_send_btn.setFixedHeight(50)
        self.chat_send_btn.setFixedWidth(75)
        self.chat_send_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.chat_send_btn.setStyleSheet("background-color: #2563eb; color: #ffffff; border-radius: 6px;")
        self.chat_send_btn.clicked.connect(self.on_chat_send_clicked)
        input_box_layout.addWidget(self.chat_send_btn)

        chat_layout.addLayout(input_box_layout)

        self.right_stack.addWidget(self.chat_page)     # Index 1
        right_layout.addWidget(self.right_stack, 1)

        self.splitter.addWidget(self.right_widget)

        # 平分三欄 (各佔約 1/3: 480, 520, 520)
        self.splitter.setSizes([480, 520, 520])
        self.main_layout.addWidget(self.splitter, 1)

        # ==========================================
        # 整合型底部操作與狀態工具列 (Bottom Action Toolbar)
        # ==========================================
        self.bottom_action_toolbar = QFrame()
        self.bottom_action_toolbar.setObjectName("bottomActionToolbar")
        self.bottom_action_toolbar.setFixedHeight(48)
        bottom_layout = QHBoxLayout(self.bottom_action_toolbar)
        bottom_layout.setContentsMargins(12, 6, 12, 6)
        bottom_layout.setSpacing(10)

        self.status_banner = QLabel("就緒：請確認輸入文本並點擊開始審查。")
        self.status_banner.setFont(QFont("Segoe UI", 9))
        bottom_layout.addWidget(self.status_banner, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setFixedHeight(18)
        bottom_layout.addWidget(self.progress_bar)

        bottom_layout.addSpacing(6)

        self.quick_fix_btn = QPushButton("⚡ 一鍵自動替換縮寫與口語詞")
        self.quick_fix_btn.setFixedHeight(34)
        self.quick_fix_btn.clicked.connect(self.auto_fix_preflight_issues)
        bottom_layout.addWidget(self.quick_fix_btn)

        self.review_btn = QPushButton("🚀 開始智能審查 (搭配詞檢視與深度改寫)")
        self.review_btn.setFixedHeight(34)
        self.review_btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.review_btn.clicked.connect(self.start_review)
        bottom_layout.addWidget(self.review_btn)

        self.main_layout.addWidget(self.bottom_action_toolbar, 0)

        # 相容舊有名稱別名 (防止 AttributeError)
        self.left_widget = self.left_splitter
        self.left_title_lbl = self.draft_title_lbl
        self.right_title_lbl = self.revised_title_lbl
        self.middle_title_lbl = self.recs_title_lbl
        self.scroll_area = self.discourse_scroll_area
        self.cards_layout = self.discourse_layout

        self.refresh_section_combo()
        self.update_engine_ui()
        self.run_preflight_analysis()
        self.reset_card_placeholders()

    def reset_card_placeholders(self):
        if self.current_report:
            return
        self.clear_cards()
        t = I18N.get(self.ui_language, I18N["zh_TW"])

        lbl_recs = QLabel(t["recs_placeholder_text"])
        lbl_recs.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 10px;")
        lbl_recs.setWordWrap(True)
        self.recs_layout.addWidget(lbl_recs)
        self.recs_layout.addStretch()

        lbl_colloc = QLabel(t["colloc_placeholder_text"])
        lbl_colloc.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 10px;")
        lbl_colloc.setWordWrap(True)
        self.colloc_layout.addWidget(lbl_colloc)
        self.colloc_layout.addStretch()

        lbl_disc = QLabel(t["discourse_placeholder_text"])
        lbl_disc.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 10px;")
        lbl_disc.setWordWrap(True)
        self.discourse_layout.addWidget(lbl_disc)
        self.discourse_layout.addStretch()

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
        self.title_label.setText(t["toolbar_title"])
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

        # 各欄位標題
        self.draft_title_lbl.setText(t["draft_title"])
        self.revised_title_lbl.setText(t["revised_title"])
        self.recs_title_lbl.setText(t["recs_title"])
        self.colloc_title_lbl.setText(t["colloc_title"])
        self.discourse_title_lbl.setText(t["discourse_title"])
        self.quick_fix_btn.setText(t["quick_fix_btn"])
        self.review_btn.setText(t["btn_start_review"])
        self.sync_to_left_btn.setText(t["sync_left"])
        self.copy_btn.setText(t["copy_revised"])

        # 中欄分頁標籤與數量徽章
        if self.current_report:
            rec_cnt = len(getattr(self.current_report, 'research_recommendations', []))
            colloc_cnt = len([i for i in self.current_report.issues if i.category == "Collocation Defect"])
            disc_cnt = len([i for i in self.current_report.issues if i.category != "Collocation Defect"])
            self.critique_tab_widget.setTabText(0, f"💡 {'Evidence Defenses' if is_en else '實證補強'} ({rec_cnt})")
            self.critique_tab_widget.setTabText(1, f"🔤 {'Collocations' if is_en else '搭配詞選項'} ({colloc_cnt})")
            self.critique_tab_widget.setTabText(2, f"⚖️ {'Syntax & Logic' if is_en else '句構與邏輯'} ({disc_cnt})")
        else:
            self.critique_tab_widget.setTabText(0, t.get("tab_recs", "💡 實證補強"))
            self.critique_tab_widget.setTabText(1, t.get("tab_colloc", "🔤 搭配詞選項"))
            self.critique_tab_widget.setTabText(2, t.get("tab_discourse", "⚖️ 句構與邏輯"))

        # 右欄監控頁面
        self.monitor_title_lbl.setText(t.get("monitor_title", "📡 智能審查執行監控"))
        if self.timer.isActive():
            self.monitor_badge_lbl.setText(t.get("monitor_badge_running", "🔄 審查進行中..."))
        else:
            self.monitor_badge_lbl.setText(t.get("monitor_badge_ready", "就緒") if not self.current_report else t.get("monitor_badge_done", "✅ 審查完成"))

        # 右欄互動辯護工作台
        if not self.current_chat_context:
            self.chat_context_chip.setText(t.get("chat_general_context", "🌐 全文綜合討論"))
        self.chat_switch_general_btn.setText(t.get("chat_general_btn", "🌐 全文討論"))
        self.chat_clear_btn.setText(t.get("chat_clear_btn", "🧹 清空"))
        self.chat_input.setPlaceholderText(t.get("chat_input_placeholder", "輸入訊息與審閱模型討論或辯護... (Enter 發送，Shift+Enter 換行)"))
        if not self.is_chat_generating:
            self.chat_send_btn.setText(t.get("chat_send_btn", "🚀 發送"))

        self.pill_defend_btn.setText(t.get("pill_defend", "🛡️ 領域慣用辯護"))
        self.pill_top_tier_btn.setText(t.get("pill_top_tier", "✍️ 頂刊風格升級"))
        self.pill_hedging_btn.setText(t.get("pill_hedging", "🔬 語氣弱化防禦"))
        self.pill_adopt_btn.setText(t.get("pill_adopt", "🔄 產出替換句"))

        if not self.chat_history:
            self.init_chat_welcome_ui()

        if not self.current_report:
            self.assessment_box.setHtml(t["assessment_placeholder"])
            self.status_banner.setText(t["status_ready"])
            self.reset_card_placeholders()

        self.update_engine_ui()
        self.update_legend_text()

    def update_legend_text(self):
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        is_en = (self.ui_language == "en_US")
        if self.current_report is None:
            if self.is_dark_mode:
                self.legend_label.setText(
                    f"<span style='color:#94a3b8; font-size:11px;'>{'⚡ Local Rule Linter: ' if is_en else '⚡ 本機規則秒篩圖例: '}</span>"
                    f"<span style='color:#f87171; background-color:#450a0a; text-decoration:line-through; padding:2px 5px; border-radius:3px;'>{'Contraction / Informal' if is_en else '原縮寫 / 口語贅詞'}</span> "
                    f"<span style='color:#34d399; background-color:#064e3b; font-weight:bold; padding:2px 5px; border-radius:3px;'>{'➔ Recommended Replacement' if is_en else '➔ 推薦替換詞'}</span>"
                )
            else:
                self.legend_label.setText(
                    f"<span style='color:#64748b; font-size:11px;'>{'⚡ Local Rule Linter: ' if is_en else '⚡ 本機規則秒篩圖例: '}</span>"
                    f"<span style='color:#dc2626; background-color:#fee2e2; text-decoration:line-through; padding:2px 5px; border-radius:3px;'>{'Contraction / Informal' if is_en else '原縮寫 / 口語贅詞'}</span> "
                    f"<span style='color:#15803d; background-color:#dcfce7; font-weight:bold; padding:2px 5px; border-radius:3px;'>{'➔ Recommended Replacement' if is_en else '➔ 推薦替換詞'}</span>"
                )
        else:
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
            self.draft_title_lbl.setStyleSheet(f"color: {text_main};")
            self.revised_title_lbl.setStyleSheet(f"color: {text_main};")
            self.recs_title_lbl.setStyleSheet(f"color: {text_main};")
            self.colloc_title_lbl.setStyleSheet(f"color: {text_main};")
            self.discourse_title_lbl.setStyleSheet(f"color: {text_main};")
            self.model_label.setStyleSheet(f"color: {text_sub};")
            self.word_count_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px;")
            self.status_banner.setStyleSheet(f"color: {text_sub}; font-size: 11px;")

            self.text_editor.set_theme_mode(True)
            self.assessment_box.set_theme_mode(True)
            self.revised_browser.set_theme_mode(True)

            self.unified_toolbar.setStyleSheet(f"#unifiedToolbar {{ background-color: {bg_card}; border: 1px solid {border_col}; border-radius: 6px; }}")
            self.mode_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px; font-weight: bold;")
            self.scope_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px; font-weight: bold;")
            self.section_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px; font-weight: bold;")
            self.bottom_action_toolbar.setStyleSheet(f"#bottomActionToolbar {{ background-color: {bg_card}; border: 1px solid {border_col}; border-radius: 6px; }}")

            btn_normal = f"""
                QPushButton {{
                    background-color: {bg_card}; color: {text_main}; border: 1px solid {border_col};
                    border-radius: 4px; padding: 3px 8px; font-size: 11px; font-weight: 500; min-height: 20px;
                }}
                QPushButton:hover {{ background-color: #334155; }}
            """
            for b in [self.refresh_btn, self.env_setup_btn, self.theme_btn, self.api_settings_btn,
                      self.sync_to_left_btn, self.copy_btn, self.update_btn, self.lang_btn, self.load_sample_btn,
                      self.chat_switch_general_btn, self.chat_clear_btn]:
                b.setStyleSheet(btn_normal)

            self.quick_fix_btn.setStyleSheet("""
                QPushButton { background-color: #1e3a8a; color: #93c5fd; border: 1px solid #3b82f6; border-radius: 4px; padding: 3px 8px; font-size: 11px; font-weight: bold; }
                QPushButton:hover { background-color: #2563eb; color: #ffffff; }
            """)

            combo_style = f"""
                QComboBox {{ background-color: {bg_card}; color: {text_main}; border: 1px solid {border_col}; border-radius: 4px; padding: 2px 6px; font-size: 11px; min-height: 20px; }}
                QComboBox QAbstractItemView {{ background-color: {bg_card}; color: {text_main}; selection-background-color: #334155; selection-color: #38bdf8; }}
            """
            for c in [self.engine_combo, self.model_combo, self.mode_combo, self.scope_combo, self.section_combo]:
                c.setStyleSheet(combo_style)

            for sa in [self.recs_scroll_area, self.colloc_scroll_area, self.discourse_scroll_area]:
                sa.setStyleSheet("QScrollArea { border: none; background: transparent; }")

            # 中欄分頁標籤樣式 (Dark)
            self.critique_tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    background-color: {bg_card};
                }}
                QTabBar::tab {{
                    background-color: {bg_main};
                    color: {text_sub};
                    border: 1px solid {border_col};
                    border-bottom: none;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                    padding: 5px 12px;
                    font-size: 11px;
                    font-weight: bold;
                    margin-right: 2px;
                }}
                QTabBar::tab:selected {{
                    background-color: {bg_card};
                    color: {text_main};
                    border-bottom: 2px solid #3b82f6;
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: #334155;
                }}
            """)

            # 右欄工作台組件樣式 (Dark)
            self.monitor_badge_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
            self.chat_context_chip.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; border-radius: 4px; padding: 4px 8px;")
            self.chat_browser.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {bg_card};
                    color: {text_main};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    padding: 6px;
                }}
            """)
            self.chat_input.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {bg_card};
                    color: {text_main};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    padding: 6px;
                }}
                QTextEdit:focus {{
                    border: 1px solid #3b82f6;
                }}
            """)
            pill_style_dark = f"""
                QPushButton {{
                    background-color: {bg_card};
                    color: #cbd5e1;
                    border: 1px solid {border_col};
                    border-radius: 12px;
                    padding: 3px 8px;
                    font-size: 10px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: #2563eb;
                    color: #ffffff;
                    border-color: #2563eb;
                }}
            """
            for pill in [self.pill_defend_btn, self.pill_top_tier_btn, self.pill_hedging_btn, self.pill_adopt_btn]:
                pill.setStyleSheet(pill_style_dark)

            self.chat_send_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2563eb; color: #ffffff; border: none; border-radius: 6px; font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1d4ed8;
                }
                QPushButton:disabled {
                    background-color: #475569; color: #94a3b8;
                }
            """)

            splitter_style = "QSplitter::handle { background-color: #334155; }"
            self.left_splitter.setStyleSheet(splitter_style)
            self.splitter.setStyleSheet(splitter_style)
        else:
            bg_main = "#f8fafc"
            bg_card = "#ffffff"
            border_col = "#cbd5e1"
            text_main = "#0f172a"
            text_sub = "#475569"

            self.central_widget.setStyleSheet(f"background-color: {bg_main}; color: {text_main};")
            self.title_label.setStyleSheet(f"color: {text_main};")
            self.draft_title_lbl.setStyleSheet(f"color: {text_main};")
            self.revised_title_lbl.setStyleSheet(f"color: {text_main};")
            self.recs_title_lbl.setStyleSheet(f"color: {text_main};")
            self.colloc_title_lbl.setStyleSheet(f"color: {text_main};")
            self.discourse_title_lbl.setStyleSheet(f"color: {text_main};")
            self.model_label.setStyleSheet(f"color: {text_sub};")
            self.word_count_lbl.setStyleSheet(f"color: #64748b; font-size: 11px;")
            self.status_banner.setStyleSheet(f"color: #64748b; font-size: 11px;")

            self.text_editor.set_theme_mode(False)
            self.assessment_box.set_theme_mode(False)
            self.revised_browser.set_theme_mode(False)

            self.unified_toolbar.setStyleSheet(f"#unifiedToolbar {{ background-color: {bg_card}; border: 1px solid #e2e8f0; border-radius: 6px; }}")
            self.mode_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px; font-weight: bold;")
            self.scope_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px; font-weight: bold;")
            self.section_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px; font-weight: bold;")
            self.bottom_action_toolbar.setStyleSheet(f"#bottomActionToolbar {{ background-color: {bg_card}; border: 1px solid #e2e8f0; border-radius: 6px; }}")

            btn_normal = f"""
                QPushButton {{
                    background-color: {bg_card}; color: {text_main}; border: 1px solid {border_col};
                    border-radius: 4px; padding: 3px 8px; font-size: 11px; font-weight: 500; min-height: 20px;
                }}
                QPushButton:hover {{ background-color: #f1f5f9; }}
            """
            for b in [self.refresh_btn, self.env_setup_btn, self.theme_btn, self.api_settings_btn,
                      self.sync_to_left_btn, self.copy_btn, self.update_btn, self.lang_btn, self.load_sample_btn,
                      self.chat_switch_general_btn, self.chat_clear_btn]:
                b.setStyleSheet(btn_normal)

            self.quick_fix_btn.setStyleSheet("""
                QPushButton { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 4px; padding: 3px 8px; font-size: 11px; font-weight: bold; }
                QPushButton:hover { background-color: #dbeafe; }
            """)

            combo_style = f"""
                QComboBox {{ background-color: {bg_card}; color: {text_main}; border: 1px solid {border_col}; border-radius: 4px; padding: 2px 6px; font-size: 11px; min-height: 20px; }}
                QComboBox QAbstractItemView {{ background-color: {bg_card}; color: {text_main}; selection-background-color: #e2e8f0; selection-color: {text_main}; }}
            """
            for c in [self.engine_combo, self.model_combo, self.mode_combo, self.scope_combo, self.section_combo]:
                c.setStyleSheet(combo_style)

            for sa in [self.recs_scroll_area, self.colloc_scroll_area, self.discourse_scroll_area]:
                sa.setStyleSheet("QScrollArea { border: none; background: transparent; }")

            # 中欄分頁標籤樣式 (Light)
            self.critique_tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    background-color: {bg_card};
                }}
                QTabBar::tab {{
                    background-color: {bg_main};
                    color: {text_sub};
                    border: 1px solid {border_col};
                    border-bottom: none;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                    padding: 5px 12px;
                    font-size: 11px;
                    font-weight: bold;
                    margin-right: 2px;
                }}
                QTabBar::tab:selected {{
                    background-color: {bg_card};
                    color: {text_main};
                    border-bottom: 2px solid #2563eb;
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: #f1f5f9;
                }}
            """)

            # 右欄工作台組件樣式 (Light)
            self.monitor_badge_lbl.setStyleSheet("color: #0284c7; font-size: 11px;")
            self.chat_context_chip.setStyleSheet("background-color: #f0f9ff; color: #0284c7; border: 1px solid #bae6fd; border-radius: 4px; padding: 4px 8px;")
            self.chat_browser.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {bg_card};
                    color: {text_main};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    padding: 6px;
                }}
            """)
            self.chat_input.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {bg_card};
                    color: {text_main};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    padding: 6px;
                }}
                QTextEdit:focus {{
                    border: 1px solid #2563eb;
                }}
            """)
            pill_style_light = f"""
                QPushButton {{
                    background-color: #f8fafc;
                    color: #334155;
                    border: 1px solid {border_col};
                    border-radius: 12px;
                    padding: 3px 8px;
                    font-size: 10px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: #2563eb;
                    color: #ffffff;
                    border-color: #2563eb;
                }}
            """
            for pill in [self.pill_defend_btn, self.pill_top_tier_btn, self.pill_hedging_btn, self.pill_adopt_btn]:
                pill.setStyleSheet(pill_style_light)

            self.chat_send_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2563eb; color: #ffffff; border: none; border-radius: 6px; font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1d4ed8;
                }
                QPushButton:disabled {
                    background-color: #94a3b8; color: #f1f5f9;
                }
            """)

            splitter_style = "QSplitter::handle { background-color: #cbd5e1; }"
            self.left_splitter.setStyleSheet(splitter_style)
            self.splitter.setStyleSheet(splitter_style)

        self.update_legend_text()
        self.update_revised_article_view()
        self.run_preflight_analysis()
        self.render_all_chat_messages(self._active_streaming_text)

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
        self.current_report = None
        self.preflight_timer.start(250)

    def run_preflight_analysis(self):
        text = self.text_editor.toPlainText().strip()
        words = text.split()
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        is_en = (self.ui_language == "en_US")
        self.word_count_lbl.setText(t["word_count"].format(n=len(words)))

        if not text:
            self.status_banner.setText("Ready: input text to scan." if is_en else "就緒：請輸入英文草稿以執行秒級快篩。")
            self.status_banner.setStyleSheet("color: #64748b; font-size: 11px;")
            self.quick_fix_btn.setEnabled(False)
            self.current_preflight_matches = []
            self.latest_revised_plain_text = ""
            if self.current_report is None:
                self.revised_browser.setHtml(t["revised_placeholder"])
                self.update_legend_text()
            return

        self.current_preflight_matches = PreflightChecker.scan(text, self.writing_mode, is_en=is_en)

        # 當尚未執行 LLM 審查時，直接將本機規則快篩結果呈現在「修改後全文」中 (以刪除號與推薦替換詞標記)
        if self.current_report is None:
            self.render_preflight_diff_in_revised(text)

        if not self.current_preflight_matches:
            self.status_banner.setText("✨ No obvious contractions, grammar violations, or awkward collocations detected." if is_en else "✨ 語法規則檢測通過！未發現縮寫、主謂矛盾、連詞重複、贅詞或生硬搭配詞。")
            self.status_banner.setStyleSheet("color: #10b981; font-size: 11px;")
            self.quick_fix_btn.setEnabled(False)
        else:
            cnt = len(self.current_preflight_matches)
            preview = ", ".join([f"'{m.original}' ➔ '{m.replacement.split('/')[0].strip() if m.replacement else m.category}'" for m in self.current_preflight_matches[:3]])
            if cnt > 3:
                preview += f"... (+{cnt - 3} more)"
            msg = f"⚠️ Preflight NLP linter found {cnt} issues (marked with strikethrough in Revised Text): {preview}" if is_en else f"⚠️ 本機規則檢驗偵測到 {cnt} 處待改進項（已於修改後全文標記刪除號與替換詞）：{preview}"
            self.status_banner.setText(msg)
            self.status_banner.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.quick_fix_btn.setEnabled(True)

    def render_preflight_diff_in_revised(self, text: str):
        if not self.current_preflight_matches:
            self.revised_browser.setPlainText(text)
            self.latest_revised_plain_text = text
            self.update_legend_text()
            return

        sorted_matches = sorted(self.current_preflight_matches, key=lambda m: m.span[0])
        non_overlapping = []
        last_end = 0
        for m in sorted_matches:
            if m.span[0] >= last_end:
                non_overlapping.append(m)
                last_end = m.span[1]

        html_parts = []
        curr_pos = 0
        for m in non_overlapping:
            s, e = m.span
            if s > curr_pos:
                html_parts.append(html.escape(text[curr_pos:s]))

            if self.is_dark_mode:
                del_style = "color: #f87171; background-color: #450a0a; text-decoration: line-through; padding: 1px 4px; border-radius: 3px; font-weight: bold;"
                ins_style = "color: #34d399; background-color: #064e3b; font-weight: bold; padding: 1px 4px; border-radius: 3px; margin-left: 2px;"
            else:
                del_style = "color: #dc2626; background-color: #fee2e2; text-decoration: line-through; padding: 1px 4px; border-radius: 3px; font-weight: bold;"
                ins_style = "color: #15803d; background-color: #dcfce7; font-weight: bold; padding: 1px 4px; border-radius: 3px; margin-left: 2px;"

            first_rep = m.replacement.split('/')[0].strip() if ('/' in m.replacement) else m.replacement
            tip = f"{m.category}: {m.explanation}"
            if first_rep:
                chunk = (
                    f"<span title='{html.escape(tip)}'>"
                    f"<del style='{del_style}'>{html.escape(m.original)}</del>"
                    f"<span style='{ins_style}'> ➔ {html.escape(first_rep)}</span>"
                    f"</span>"
                )
            else:
                flag_style = "color: #38bdf8; text-decoration: underline wavy #38bdf8; font-weight: 500;" if self.is_dark_mode else "color: #0284c7; text-decoration: underline wavy #0284c7; font-weight: 500;"
                badge_style = "color: #38bdf8; background-color: #0c4a6e; font-size: 11px; padding: 1px 4px; border-radius: 3px; margin-left: 2px;" if self.is_dark_mode else "color: #0369a1; background-color: #e0f2fe; font-size: 11px; padding: 1px 4px; border-radius: 3px; margin-left: 2px;"
                chunk = (
                    f"<span title='{html.escape(tip)}' style='{flag_style}'>"
                    f"{html.escape(m.original)}"
                    f"<span style='{badge_style}'>[{html.escape(m.category)}]</span>"
                    f"</span>"
                )
            html_parts.append(chunk)
            curr_pos = e

        if curr_pos < len(text):
            html_parts.append(html.escape(text[curr_pos:]))

        full_html = "".join(html_parts).replace("\n", "<br>")
        self.revised_browser.setHtml(full_html)
        self.latest_revised_plain_text = PreflightChecker.fix_all_issues(text)
        self.update_legend_text()

    def auto_fix_preflight_issues(self):
        text = self.text_editor.toPlainText()
        if not text:
            return
        fixed_text = PreflightChecker.fix_all_issues(text)
        self.text_editor.setPlainText(fixed_text)
        self.run_preflight_analysis()
        is_en = (self.ui_language == "en_US")
        msg = "Auto-sanitized units, prepositions, contractions & collocations!" if is_en else "已透過 NLP 規則管線完成單位空格、介系詞、縮寫與搭配詞自動修正！"
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

        # Pipeline Step 1: Auto-Sanitize (零 LLM 依賴，確定性自動無損格式與及物動詞介系詞修正)
        sanitized_text, sanitize_changes = AcademicNLPPipeline.auto_sanitize(text)
        if sanitize_changes:
            self.text_editor.setPlainText(sanitized_text)
            text = sanitized_text

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

        # 1. 切換右側欄位至監控分頁 (Index 0) 並重設狀態
        self.right_stack.setCurrentIndex(0)
        self.live_stream_box.clear()
        self.monitor_badge_lbl.setText("🔄 審查進行中..." if not is_en else "🔄 Reviewing...")

        # 2. 於中間各分頁顯示進行中指示
        recs_hint = QLabel("⏳ 審查進行中：正在生成研究策略與實證缺失分析..." if not is_en else "⏳ Reviewing: generating strategic proposals and evidence gaps...")
        recs_hint.setStyleSheet("color: #a855f7; font-size: 11px; font-weight: bold; padding: 10px;")
        self.recs_layout.addWidget(recs_hint)
        self.recs_layout.addStretch()

        colloc_hint = QLabel("⏳ 審查進行中：正在窮舉道地搭配詞與多風格替換..." if not is_en else "⏳ Reviewing: evaluating idiomatic collocations and lexical options...")
        colloc_hint.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold; padding: 10px;")
        self.colloc_layout.addWidget(colloc_hint)
        self.colloc_layout.addStretch()

        discourse_hint = QLabel("⏳ 審查進行中：正在檢視文法句構、推論缺陷與邏輯矛盾..." if not is_en else "⏳ Reviewing: analyzing discourse structure, grammar and logic...")
        discourse_hint.setStyleSheet("color: #3b82f6; font-size: 11px; font-weight: bold; padding: 10px;")
        self.discourse_layout.addWidget(discourse_hint)
        self.discourse_layout.addStretch()

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
            <p style='margin: 0 0 4px 0;'><b>{t['gist_title']}</b><br><span>{html.escape(gist_val)}</span></p>
            <hr style='border: 0; border-top: 1px solid #cbd5e1; margin: 4px 0;'>
        """
        if not is_en and report.overall_assessment_zh:
            assessment_html += f"<p style='margin: 0 0 3px 0;'><b>{t['overall_zh_title']}</b><br><span style='color: #10b981;'>{html.escape(report.overall_assessment_zh)}</span></p>"
        assessment_html += f"<p style='margin: 0;'><b>{t['overall_en_title']}</b><br><span style='font-style: italic;'>{html.escape(report.overall_assessment_en)}</span></p></div>"
        self.assessment_box.setHtml(assessment_html)

        self.clear_cards()

        # 1. 渲染中欄 Tab 1：審查實質建議與實證缺失分析 (Research Recommendations)
        recommendations = getattr(report, 'research_recommendations', [])
        if recommendations:
            rec_header_text = f"🔬 Strategic & Contextual Recommendations ({len(recommendations)} Items):" if is_en else f"🔬 審查員實質建議：上下文完整性與論證/實驗補強 ({len(recommendations)} 項):"
            rec_header = QLabel(rec_header_text)
            rec_header.setStyleSheet("font-weight: bold; color: #8b5cf6; font-size: 12px; margin-top: 2px; margin-bottom: 4px;")
            self.recs_layout.addWidget(rec_header)

            for rec in recommendations:
                rec_card = ResearchRecommendationCard(rec, is_dark=self.is_dark_mode, lang=self.ui_language, on_discuss_callback=self.open_chat_for_rec)
                self.recs_layout.addWidget(rec_card)
        else:
            no_rec = QLabel("✨ Solid reasoning; no critical evidence gaps identified." if is_en else "✨ 論點完整嚴謹，未發現重大實證或方法缺失。")
            no_rec.setStyleSheet("color: #10b981; font-weight: bold; margin-top: 6px; padding: 8px;")
            self.recs_layout.addWidget(no_rec)
        self.recs_layout.addStretch()

        # 分流搭配詞與文法/邏輯問題，確保雙軌並行且不互斥
        colloc_items = [(idx, issue) for idx, issue in enumerate(report.issues) if issue.category == "Collocation Defect"]
        discourse_items = [(idx, issue) for idx, issue in enumerate(report.issues) if issue.category != "Collocation Defect"]

        # 2. 渲染中欄 Tab 2：搭配詞替換選項與精準用詞編修 (Collocations)
        if colloc_items:
            c_header_text = f"🟢 Natural Collocations & Lexical Precision ({len(colloc_items)} Points):" if is_en else f"🟢 道地搭配詞替換與精準用詞 ({len(colloc_items)} 處):"
            c_header = QLabel(c_header_text)
            c_header.setStyleSheet("font-weight: bold; color: #059669; font-size: 12px; margin-top: 2px; margin-bottom: 4px;")
            self.colloc_layout.addWidget(c_header)

            for idx, issue in colloc_items:
                card = IssueCard(idx, issue, self.handle_option_selection, is_dark=self.is_dark_mode, lang=self.ui_language, on_discuss_callback=self.open_chat_for_issue)
                self.colloc_layout.addWidget(card)
        else:
            no_colloc = QLabel("✨ Idiomatic and natural word pairings throughout." if is_en else "✨ 搭配詞自然道地，無明顯生硬用詞！")
            no_colloc.setStyleSheet("color: #10b981; font-weight: bold; margin-top: 6px; padding: 8px;")
            self.colloc_layout.addWidget(no_colloc)
        self.colloc_layout.addStretch()

        # 3. 渲染中欄 Tab 3：文法句構、推論缺陷、修辭風格與邏輯矛盾 (Discourse, Logic & Grammar)
        if discourse_items:
            d_header_text = f"✍️ Discourse, Logic, Rhetoric & Grammar Critiques ({len(discourse_items)} Points):" if is_en else f"✍️ 文法句構、推論缺陷、修辭風格與邏輯矛盾 ({len(discourse_items)} 處改進點):"
            d_header = QLabel(d_header_text)
            d_header.setStyleSheet("font-weight: bold; color: #3b82f6; font-size: 12px; margin-top: 2px; margin-bottom: 4px;")
            self.discourse_layout.addWidget(d_header)

            for idx, issue in discourse_items:
                card = IssueCard(idx, issue, self.handle_option_selection, is_dark=self.is_dark_mode, lang=self.ui_language, on_discuss_callback=self.open_chat_for_issue)
                self.discourse_layout.addWidget(card)
        else:
            no_disc = QLabel("✨ Flawless grammar and logically sound discourse." if is_en else "✨ 文法正確，論證嚴密，無邏輯或修辭缺陷！")
            no_disc.setStyleSheet("color: #10b981; font-weight: bold; margin-top: 6px; padding: 8px;")
            self.discourse_layout.addWidget(no_disc)
        self.discourse_layout.addStretch()

        # 4. 更新中欄 Tab 標題與數量徽章
        self.critique_tab_widget.setTabText(0, f"💡 {'Evidence Defenses' if is_en else '實證補強'} ({len(recommendations)})")
        self.critique_tab_widget.setTabText(1, f"🔤 {'Collocations' if is_en else '搭配詞選項'} ({len(colloc_items)})")
        self.critique_tab_widget.setTabText(2, f"⚖️ {'Syntax & Logic' if is_en else '句構與邏輯'} ({len(discourse_items)})")

        self.update_revised_article_view()

        # 5. 自動切換右側欄位至互動辯護與對話工作台 (Index 1)
        self.right_stack.setCurrentIndex(1)
        self.monitor_badge_lbl.setText("✅ 審查完成" if not is_en else "✅ Complete")
        if not self.chat_history:
            self.init_chat_welcome_ui()

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
        for layout in [self.recs_layout, self.colloc_layout, self.discourse_layout]:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.hide()
                    widget.setParent(None)
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
        msg = "Synchronized revised full text to draft editor." if is_en else "已將修訂後全文同步至上方草稿區。"
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

    # ==========================================
    # 互動式同儕審查辯護與對話工作台 (Interactive Peer-Review Co-Pilot Methods)
    # ==========================================
    def init_chat_welcome_ui(self):
        is_en = (self.ui_language == "en_US")
        dark = self.is_dark_mode
        t_sub = "#94a3b8" if dark else "#64748b"
        h_col = "#38bdf8" if dark else "#0284c7"

        if is_en:
            welcome_html = f"""
            <div style='padding: 8px 4px; font-family: Segoe UI, sans-serif;'>
                <h3 style='margin: 0 0 8px 0; color: {h_col}; font-size: 13px;'>💬 Peer-Review Discussion & Rebuttal Workbench</h3>
                <p style='color: {t_sub}; font-size: 11px; line-height: 1.5;'>
                    Collaborate and debate review feedback with your AI reviewer co-pilot.<br><br>
                    💡 <b>How to interact:</b><br>
                    1. Click <b>「💬 Discuss / Rebuttal」</b> on any critique card in the middle column to focus debate on that issue.<br>
                    2. Click the quick action pills below (e.g., <b>🛡️ Defend (Domain Norm)</b>, <b>✍️ Top-Tier Style</b>, or <b>🔬 Hedging Defense</b>).<br>
                    3. Ask any questions about journal rebuttal letters or phrasing in the input box below.
                </p>
            </div>
            """
        else:
            welcome_html = f"""
            <div style='padding: 8px 4px; font-family: Segoe UI, sans-serif;'>
                <h3 style='margin: 0 0 8px 0; color: {h_col}; font-size: 13px;'>💬 學術審查互動辯護工作台 (Review Discussion & Rebuttal)</h3>
                <p style='color: {t_sub}; font-size: 11px; line-height: 1.5;'>
                    在此工作台，您可以與審閱模型進行深度互動，針對任何審查意見進行<b>專業辯護</b>、<b>頂刊風格升級</b>或<b>語氣弱化防禦</b>。<br><br>
                    💡 <b>如何開始互動：</b><br>
                    1. 點擊中欄任一卡片右上方的 <b>「💬 辯護 / 討論」</b> 按鈕，即可鎖定該項意見為討論焦點。<br>
                    2. 點擊下方的快捷選鈕（如 <b>🛡️ 領域慣用辯護</b> 或 <b>✍️ 頂刊風格升級</b>），快速生成專業論據。<br>
                    3. 在下方輸入框輸入任何問題，探討投稿回覆信（Rebuttal Letter）或改寫策略。
                </p>
            </div>
            """
        self.chat_browser.setHtml(welcome_html)

    def open_chat_for_rec(self, rec: ResearchRecommendation):
        is_en = (self.ui_language == "en_US")
        self.right_stack.setCurrentIndex(1)
        self.current_chat_context = {"type": "rec", "item": rec}
        chip_text = f"🔬 {rec.action_type}" if len(rec.action_type) < 22 else f"🔬 {rec.action_type[:20]}..."
        self.chat_context_chip.setText(chip_text)

        gap_txt = rec.gap_identified_en if is_en else (rec.gap_identified_zh or rec.gap_identified_en)
        prop_txt = rec.concrete_proposal_en if is_en else (rec.concrete_proposal_zh or rec.concrete_proposal_en)
        if not is_en:
            intro_content = (
                f"🎯 **[已選定實質補強建議]**\n"
                f"- **類型**: `{rec.action_type}` ({rec.severity})\n"
                f"- **缺失分析**: {gap_txt}\n"
                f"- **建議補做**: {prop_txt}\n\n"
                f"💡 *您可以點擊下方快捷按鈕（如【🛡️ 領域慣用辯護】探討免補實驗的答辯策略），或在下方輸入具體想法進行推敲。*"
            )
        else:
            intro_content = (
                f"🎯 **[Selected Strategic Recommendation]**\n"
                f"- **Type**: `{rec.action_type}` ({rec.severity})\n"
                f"- **Evidence Gap**: {gap_txt}\n"
                f"- **Proposed Action**: {prop_txt}\n\n"
                f"💡 *Click a quick action pill below (e.g. 【🛡️ Defend (Domain Norm)】 to argue why this can be excused) or type your message.*"
            )
        self.chat_history.append({"role": "assistant", "content": intro_content})
        self.render_all_chat_messages()
        self.chat_input.setFocus()

    def open_chat_for_issue(self, issue: IssueItem):
        is_en = (self.ui_language == "en_US")
        self.right_stack.setCurrentIndex(1)
        self.current_chat_context = {"type": "issue", "item": issue}
        orig_snip = issue.original_text[:18] + ("..." if len(issue.original_text) > 18 else "")
        self.chat_context_chip.setText(f"🎯 {issue.category}: \"{orig_snip}\"")

        comm_txt = issue.reviewer_comment_en if is_en else (issue.reviewer_comment_zh or issue.reviewer_comment_en)
        if not is_en:
            intro_content = (
                f"🎯 **[已選定審查改進點]**\n"
                f"- **類別**: `{issue.category}` ({issue.severity})\n"
                f"- **原文片段**: \"{issue.original_text}\"\n"
                f"- **審稿評語**: {comm_txt}\n\n"
                f"💡 *您可以點擊下方快捷按鈕（如【🛡️ 領域慣用辯護】、【✍️ 頂刊風格升級】或【🔬 語氣弱化防禦】），或直接輸入訊息與我深入推敲。*"
            )
        else:
            intro_content = (
                f"🎯 **[Selected Critique Point]**\n"
                f"- **Category**: `{issue.category}` ({issue.severity})\n"
                f"- **Original Snippet**: \"{issue.original_text}\"\n"
                f"- **Reviewer Critique**: {comm_txt}\n\n"
                f"💡 *Click a quick action pill below (e.g. 【🛡️ Defend (Domain Norm)】, 【✍️ Top-Tier Style】, or 【🔬 Hedging Defense】) or type your message to begin.*"
            )
        self.chat_history.append({"role": "assistant", "content": intro_content})
        self.render_all_chat_messages()
        self.chat_input.setFocus()

    def switch_to_general_chat(self):
        self.current_chat_context = None
        is_en = (self.ui_language == "en_US")
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        self.chat_context_chip.setText(t.get("chat_general_context", "🌐 全文綜合討論"))
        intro_msg = (
            "🌐 **[已切換至全文綜合討論]**\n您現在可以針對整篇論文的架構、邏輯連貫性、投稿目標期刊的風格偏好、或撰寫整體 Rebuttal Letter 進行廣泛討論。"
            if not is_en else
            "🌐 **[Switched to General Full-Text Discussion]**\nYou can now discuss manuscript structure, overall narrative flow, journal selection considerations, or general rebuttal strategies."
        )
        self.chat_history.append({"role": "assistant", "content": intro_msg})
        self.render_all_chat_messages()
        self.chat_input.setFocus()

    def clear_chat_history(self):
        if self.chat_worker and self.is_chat_generating:
            self.chat_worker.cancel()
        self.is_chat_generating = False
        self.chat_history = []
        self._active_streaming_text = ""
        self.chat_send_btn.setEnabled(True)
        is_en = (self.ui_language == "en_US")
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        self.chat_send_btn.setText(t.get("chat_send_btn", "🚀 發送"))
        self.init_chat_welcome_ui()

    def build_chat_system_prompt(self) -> str:
        is_en = (self.ui_language == "en_US")
        mode_data = WRITING_MODES.get(self.writing_mode, WRITING_MODES["academic"])
        persona = mode_data.get("persona_en" if is_en else "persona_zh", "Senior Academic Peer Reviewer and Editor")

        draft_sample = self.text_editor.toPlainText()[:1500]

        context_desc = ""
        if self.current_chat_context:
            ctx_type = self.current_chat_context.get("type")
            item = self.current_chat_context.get("item")
            if ctx_type == "rec" and isinstance(item, ResearchRecommendation):
                context_desc = f"""
CURRENT FOCUSED RECOMMENDATION:
- Action Type: {item.action_type}
- Severity: {item.severity}
- Gap Analysis: {item.gap_identified_en} (ZH: {item.gap_identified_zh})
- Proposed Action: {item.concrete_proposal_en} (ZH: {item.concrete_proposal_zh})
- Acceptance Impact: {item.impact_on_acceptance_en} (ZH: {item.impact_on_acceptance_zh})
"""
            elif ctx_type == "issue" and isinstance(item, IssueItem):
                options_summary = "\n".join([f"  * Option {chr(65+idx)} ({opt.style_label}): \"{opt.revised_text}\" - Rationale: {opt.rationale_en}" for idx, opt in enumerate(item.revision_options)])
                context_desc = f"""
CURRENT FOCUSED CRITIQUE POINT:
- Category: {item.category}
- Severity: {item.severity}
- Original Text: "{item.original_text}"
- Meaning Analysis: {item.meaning_analysis_en}
- Reviewer Critique: {item.reviewer_comment_en} (ZH: {item.reviewer_comment_zh})
- Available Options:
{options_summary}
"""

        if is_en:
            sys_prompt = f"""You are an elite, highly constructive Academic Co-Pilot and Senior Peer Reviewer ({persona}).
You are pair-collaborating with an author to polish their manuscript, debate reviewer critiques, formulate polite and persuasive rebuttal letter arguments, craft academic hedging defenses, and refine prose to top-tier journal standards (e.g., Nature, Science, Cell, IEEE Transactions, ACM).

AUTHOR'S WRITING REGISTER & SECTION:
- Writing Mode: {mode_data.get('name_en')}
- Target Scope: {self.context_scope}

{context_desc}

DRAFT EXCERPT FOR CONTEXT:
\"\"\"{draft_sample}\"\"\"

GUIDELINES:
1. Always maintain a collegial, constructive, and intellectually rigorous tone.
2. If the author wants to DEFEND their phrasing or study design, evaluate whether the defense is scientifically sound and provide persuasive, courteous phrasing suitable for a Point-by-Point Rebuttal Letter.
3. If the author asks for HEDGING, provide nuanced academic hedging (e.g., "These observations lend credence to the hypothesis that...", "While not definitive, the data strongly imply...").
4. If the author requests TOP-TIER JOURNAL STYLE, deliver concise, punchy, high-impact academic English with sophisticated syntax and flawless collocation.
5. Provide actionable revision suggestions with clear explanations.
6. Reply in English with crystal-clear markdown formatting (bolding key terms, using code blocks for suggested sentences).
"""
        else:
            sys_prompt = f"""你是一位頂級學術同儕審閱與改寫專家（{persona}）。
你正在與論文作者共同推敲、討論審查意見，協助作者進行「專業辯護」、「審稿意見回覆信（Point-by-Point Rebuttal）」、「頂級期刊風格升級（如 Nature, IEEE, Cell, Science 等）」以及「語氣弱化防禦（Academic Hedging）」。

作者目前的寫作設定：
- 寫作情境：{mode_data.get('name_zh')}
- 審查範圍：{self.context_scope}

{context_desc}

作者原始草稿片段供背景參考：
\"\"\"{draft_sample}\"\"\"

你的核心職責與應對原則：
1. 保持專業、建設性且嚴謹的學術對話態度。
2. 當作者想要【辯護（Rebuttal）】原寫法或實驗時：
   - 評估該辯護在該學術領域是否站得住腳。
   - 若站得住腳，協助作者撰寫委婉、禮貌且具說服力的回覆信（Rebuttal Letter）句子，向審稿員清楚解釋領域慣例或研究範圍局限。
   - 若站不住腳，客觀指出潛在風險，並提供折衷改寫方案。
3. 當作者想要【語氣弱化（Hedging）】時：
   - 提供 2~3 種不同防禦強度的學術弱化句型（如 "These findings suggest...", "It is conceivable that..."），避免被 Reviewer 指責為 Overclaiming。
4. 當作者想要【頂刊風格升級】時：
   - 產出極具權威感、行文精煉且結構緊湊的頂級期刊句構。
5. 請主要使用正體中文進行解說與策略分析，但在提供修訂建議句或 Rebuttal 範例句時，提供高水準的道地英文。排版採用清晰的 Markdown 格式。
"""
        return sys_prompt.strip()

    def on_chat_send_clicked(self):
        text = self.chat_input.toPlainText()
        self.send_chat_message(text)

    def send_chat_message(self, user_text: str):
        if not user_text or not user_text.strip():
            return
        if self.is_chat_generating:
            return

        is_en = (self.ui_language == "en_US")
        model_name = self.model_combo.currentText().strip()
        if self.engine_mode == "ollama":
            if not model_name or "未找到" in model_name or "未啟動" in model_name or "No models" in model_name:
                QMessageBox.warning(self, "Notice" if is_en else "提示", "Please select a valid local Ollama model." if is_en else "請先確認已選擇本機模型。")
                return
        else:
            if not self.config.get("api_key"):
                QMessageBox.warning(self, "Notice" if is_en else "提示", "Please configure your API Key first." if is_en else "請先點擊上方「⚙️ API 設定」輸入線上 API Key。")
                self.open_api_settings()
                return

        clean_text = user_text.strip()
        self.chat_history.append({"role": "user", "content": clean_text})
        self.chat_input.clear()

        self.is_chat_generating = True
        self._active_streaming_text = ""
        self.chat_send_btn.setEnabled(False)
        self.chat_send_btn.setText("⏳...")

        sys_prompt = self.build_chat_system_prompt()

        self.chat_worker = InteractiveChatWorker(
            engine_mode=self.engine_mode,
            model_name=model_name if self.engine_mode == "ollama" else self.config.get("api_model", "deepseek-chat"),
            api_config=self.config,
            system_prompt=sys_prompt,
            messages=self.chat_history
        )
        self.chat_worker.chunk_received.connect(self.on_chat_chunk_received)
        self.chat_worker.finished.connect(self.on_chat_finished)
        self.chat_worker.error.connect(self.on_chat_error)
        self.chat_worker.start()

        self.render_all_chat_messages()

    @Slot(str)
    def on_chat_chunk_received(self, delta: str):
        self._active_streaming_text += delta
        self.render_all_chat_messages(self._active_streaming_text)

    @Slot(str)
    def on_chat_finished(self, full_reply: str):
        self.is_chat_generating = False
        self.chat_history.append({"role": "assistant", "content": full_reply})
        self._active_streaming_text = ""
        self.chat_send_btn.setEnabled(True)
        is_en = (self.ui_language == "en_US")
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        self.chat_send_btn.setText(t.get("chat_send_btn", "🚀 發送"))
        self.render_all_chat_messages()

    @Slot(str)
    def on_chat_error(self, err_msg: str):
        self.is_chat_generating = False
        self.chat_history.append({"role": "assistant", "content": f"⚠️ **Error**: {err_msg}"})
        self._active_streaming_text = ""
        self.chat_send_btn.setEnabled(True)
        is_en = (self.ui_language == "en_US")
        t = I18N.get(self.ui_language, I18N["zh_TW"])
        self.chat_send_btn.setText(t.get("chat_send_btn", "🚀 發送"))
        self.render_all_chat_messages()

    def send_quick_prompt(self, action: str):
        is_en = (self.ui_language == "en_US")
        ctx = self.current_chat_context
        if action == "defend":
            if ctx and ctx.get("type") == "rec":
                text = (
                    "針對這項實質補強建議，由於實驗資源或論文篇幅限制無法立即補做，請教我如何在論文討論段（Discussion）中進行嚴密的防禦性說明（Limitation defense），並為我撰寫一段委婉禮貌的審查回覆信範例（Rebuttal response）。"
                    if not is_en else
                    "Regarding this strategic recommendation, due to experimental or page constraints, we cannot conduct this additional experiment. Please advise on how to formulate a defensible limitation discussion in the paper and draft a courteous point-by-point rebuttal response."
                )
            elif ctx and ctx.get("type") == "issue":
                issue: IssueItem = ctx.get("item")
                text = (
                    f"針對此處被挑出的問題（\"{issue.original_text}\"），我想堅持保留作者原有的寫法或表達邏輯。請幫我從領域專業慣例的角度，評估其可行性，並撰寫一份委婉而堅定的審查意見回覆（Rebuttal statement）。"
                    if not is_en else
                    f"Regarding the critique on \"{issue.original_text}\", I would like to defend and retain my original phrasing. Please evaluate whether this is justifiable by domain conventions and draft a polite, persuasive rebuttal statement."
                )
            else:
                text = (
                    "請針對目前的審查意見，提供投稿回覆信（Point-by-Point Rebuttal Letter）的通用攻防策略與禮貌應對範本。"
                    if not is_en else
                    "Please provide strategic advice and a polite template for responding to peer-review critiques in a point-by-point rebuttal letter."
                )
        elif action == "top_tier":
            if ctx and ctx.get("type") == "issue":
                issue: IssueItem = ctx.get("item")
                text = (
                    f"請將「{issue.original_text}」以頂級期刊（如 Nature, IEEE TPAMI, Cell）的高權威度、精煉行文風格進行升級重寫，提供 2 個最具學術影響力的修訂句。"
                    if not is_en else
                    f"Please elevate \"{issue.original_text}\" to a top-tier journal standard (e.g., Nature, IEEE TPAMI). Provide 2 high-impact, refined alternative sentences."
                )
            else:
                text = (
                    "請針對我當前的草稿重點，指出最能提升至頂刊風格（Top-tier journal style）的關鍵修辭與句構升級建議。"
                    if not is_en else
                    "Please highlight key rhetorical and stylistic upgrades in my draft to elevate it to a top-tier journal caliber."
                )
        elif action == "hedging":
            if ctx and ctx.get("type") == "issue":
                issue: IssueItem = ctx.get("item")
                text = (
                    f"此處原文「{issue.original_text}」是否可能有過度宣稱（Overclaiming）或語氣過於武斷的風險？請為我提供 3 種不同程度的學術語氣弱化（Academic Hedging）改寫方案。"
                    if not is_en else
                    f"Does the original phrasing \"{issue.original_text}\" risk overclaiming? Please provide 3 levels of academic hedging rewrites to moderate the claim safely."
                )
            else:
                text = (
                    "請檢視我草稿中的主張與結論，提供常用的學術語氣弱化（Academic Hedging）句型與防禦建議，以避免審稿員質疑。"
                    if not is_en else
                    "Please review assertions in my draft and suggest standard academic hedging techniques to preempt reviewer skepticism."
                )
        elif action == "adopt":
            if ctx and ctx.get("type") == "issue":
                issue: IssueItem = ctx.get("item")
                text = (
                    f"請針對「{issue.original_text}」直接產出 3 個可直接替換的最佳修訂句子，並分別標注各自適合的語境與修辭優勢。"
                    if not is_en else
                    f"Please generate 3 drop-in replacement sentences for \"{issue.original_text}\", annotating the specific context and stylistic advantage of each."
                )
            else:
                text = (
                    "請為目前審查中最重要的 3 處問題，產出立即可替換的改寫句對照表。"
                    if not is_en else
                    "Please generate a table of drop-in alternative sentences for the most critical issues identified in the review."
                )
        else:
            text = action

        self.send_chat_message(text)

    def render_all_chat_messages(self, current_streaming_delta: str = ""):
        is_en = (self.ui_language == "en_US")
        dark = self.is_dark_mode

        if dark:
            user_bg = "#1e3a8a"
            user_border = "#2563eb"
            user_title = "#93c5fd"
            user_text = "#eff6ff"

            asst_bg = "#1e293b"
            asst_border = "#334155"
            asst_title = "#38bdf8"
            asst_text = "#f8fafc"
        else:
            user_bg = "#eff6ff"
            user_border = "#bfdbfe"
            user_title = "#1d4ed8"
            user_text = "#1e293b"

            asst_bg = "#f8fafc"
            asst_border = "#e2e8f0"
            asst_title = "#0284c7"
            asst_text = "#0f172a"

        html_blocks = []

        for msg in self.chat_history:
            role = msg.get("role", "user")
            raw_content = msg.get("content", "")
            formatted = self.format_markdown_for_browser(raw_content)

            if role == "user":
                block = f"""
                <div style='margin: 8px 0; padding: 8px 12px; background-color: {user_bg}; border: 1px solid {user_border}; border-radius: 8px;'>
                    <div style='font-size: 11px; font-weight: bold; color: {user_title}; margin-bottom: 4px;'>{'👤 Author / You:' if is_en else '👤 作者 (您)：'}</div>
                    <div style='font-size: 12px; color: {user_text}; line-height: 1.45;'>{formatted}</div>
                </div>
                """
            else:
                block = f"""
                <div style='margin: 8px 0; padding: 8px 12px; background-color: {asst_bg}; border: 1px solid {asst_border}; border-radius: 8px;'>
                    <div style='font-size: 11px; font-weight: bold; color: {asst_title}; margin-bottom: 4px;'>{'🦙 Reviewer Co-Pilot:' if is_en else '🦙 審稿與辯護顧問 (Co-Pilot)：'}</div>
                    <div style='font-size: 12px; color: {asst_text}; line-height: 1.45;'>{formatted}</div>
                </div>
                """
            html_blocks.append(block)

        if current_streaming_delta:
            formatted_stream = self.format_markdown_for_browser(current_streaming_delta)
            stream_block = f"""
            <div style='margin: 8px 0; padding: 8px 12px; background-color: {asst_bg}; border: 1px solid #38bdf8; border-radius: 8px;'>
                <div style='font-size: 11px; font-weight: bold; color: #38bdf8; margin-bottom: 4px;'>{'🦙 Reviewer Co-Pilot (Generating...):' if is_en else '🦙 審稿與辯護顧問 (正在思考生成...):'}</div>
                <div style='font-size: 12px; color: {asst_text}; line-height: 1.45;'>{formatted_stream} <span style='color: #38bdf8; font-weight: bold;'>▋</span></div>
            </div>
            """
            html_blocks.append(stream_block)

        full_html = "".join(html_blocks)
        self.chat_browser.setHtml(full_html)

        cursor = self.chat_browser.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_browser.setTextCursor(cursor)
        self.chat_browser.ensureCursorVisible()

    def format_markdown_for_browser(self, text: str) -> str:
        if not text:
            return ""
        dark = self.is_dark_mode
        code_bg = "#0f172a" if dark else "#e2e8f0"
        code_fg = "#38bdf8" if dark else "#0369a1"
        quote_border = "#3b82f6"
        quote_bg = "#1e293b" if dark else "#f1f5f9"

        def replace_code_block(match):
            code = match.group(1)
            escaped_code = html.escape(code.strip())
            return f"<pre style='background-color: {code_bg}; color: {code_fg}; padding: 8px; border-radius: 4px; font-family: Consolas, monospace; font-size: 11px; margin: 4px 0;'>{escaped_code}</pre>"

        res = re.sub(r'```(?:[\w]*\n)?(.*?)```', replace_code_block, text, flags=re.DOTALL)

        lines = res.split('\n')
        processed_lines = []
        in_code_block = False

        for line in lines:
            if "<pre " in line:
                in_code_block = True
            if "</pre>" in line:
                in_code_block = False
                processed_lines.append(line)
                continue

            if in_code_block:
                processed_lines.append(line)
                continue

            l_str = line

            if l_str.startswith('&gt; ') or l_str.startswith('> '):
                quote_content = l_str[l_str.find(' ') + 1:]
                l_str = f"<div style='border-left: 3px solid {quote_border}; background-color: {quote_bg}; padding: 4px 8px; margin: 3px 0;'>{quote_content}</div>"
            elif re.match(r'^\s*[-*]\s+', l_str):
                l_str = re.sub(r'^\s*[-*]\s+', '• ', l_str)
                l_str = f"<div style='margin-left: 10px;'>{l_str}</div>"

            l_str = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', l_str)
            l_str = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', l_str)
            l_str = re.sub(r'`([^`]+)`', f"<code style='background-color: {code_bg}; color: {code_fg}; padding: 1px 4px; border-radius: 3px; font-family: Consolas, monospace; font-size: 11px;'>\\1</code>", l_str)

            processed_lines.append(l_str)

        return "<br>".join(processed_lines)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AcademicReviewerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()