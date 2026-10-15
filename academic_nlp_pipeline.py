# -*- coding: utf-8 -*-
"""
academic_nlp_pipeline.py
==================================================
LibreLlama Reviewer ─ 零 LLM 依賴學術語言學規則處理管線 (Academic NLP Rule Pipeline)
==================================================
核心職責：
1. Auto-Sanitize (自動無損修正)：
   - 科學單位空格規範化 (如 10mL -> 10 mL, 50uM -> 50 uM, 37°C -> 37 °C)
   - 及物動詞後錯誤介系詞清除 (如 discuss about -> discuss, emphasize on -> emphasize)
2. Rule-Based Diagnostics (規則診斷報告)：
   - 跨子句主謂單複數一致性檢核 (SVA: Subject-Verb Agreement across clauses)
   - 中式雙重連接詞 (Double Conjunctions: Although... but, Because... so)
   - 句首裸露指示代名詞 (Bare Demonstrative: This/These directly as nsubj)
   - 過度名詞化結構 (Heavy Nominalization: conduct/perform/make an analysis of -> analyze)
   - 被動語態 (Passive Voice) 與長句標記 (> 35 words)
"""

import re
import json
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Any, Optional

try:
    import spacy
    from spacy.matcher import Matcher
    from spacy.tokens import Doc, Span, Token
except ImportError:
    spacy = None
    Matcher = None

# ==========================================
# 1. 結構化資料模型 (Data Models)
# ==========================================
@dataclass
class DiagnosticItem:
    rule_id: str
    category: str
    category_zh: str
    severity: str  # Critical, Major, Minor, Info
    span: Tuple[int, int]  # (start_char, end_char)
    matched_text: str
    message: str
    suggestion: str
    replacement: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "category_zh": self.category_zh,
            "severity": self.severity,
            "span": list(self.span),
            "matched_text": self.matched_text,
            "message": self.message,
            "suggestion": self.suggestion,
            "replacement": self.replacement,
        }

@dataclass
class AutoSanitizeChange:
    rule: str
    original: str
    replacement: str
    span: Tuple[int, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "original": self.original,
            "replacement": self.replacement,
            "span": list(self.span),
        }

@dataclass
class PipelineResult:
    original_text: str
    sanitized_text: str
    sanitize_changes: List[AutoSanitizeChange] = field(default_factory=list)
    diagnostics: List[DiagnosticItem] = field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps({
            "original_text": self.original_text,
            "sanitized_text": self.sanitized_text,
            "sanitize_changes": [c.to_dict() for c in self.sanitize_changes],
            "diagnostics": [d.to_dict() for d in self.diagnostics]
        }, ensure_ascii=False, indent=indent)

# ==========================================
# 2. 名詞化對應字典 (Nominalization Mapping)
# ==========================================
NOMINALIZATION_MAP = {
    "analysis": ("analyze", "analyzed"),
    "investigation": ("investigate", "investigated"),
    "evaluation": ("evaluate", "evaluated"),
    "measurement": ("measure", "measured"),
    "assessment": ("assess", "assessed"),
    "examination": ("examine", "examined"),
    "observation": ("observe", "observed"),
    "demonstration": ("demonstrate", "demonstrated"),
    "calculation": ("calculate", "calculated"),
    "determination": ("determine", "determined"),
    "identification": ("identify", "identified"),
    "characterization": ("characterize", "characterized"),
    "discussion": ("discuss", "discussed"),
    "explanation": ("explain", "explained"),
    "comparison": ("compare", "compared"),
    "conclusion": ("conclude", "concluded"),
    "improvement": ("improve", "improved"),
    "decision": ("decide", "decided"),
    "exploration": ("explore", "explored"),
    "description": ("describe", "described"),
    "presentation": ("present", "presented"),
    "classification": ("classify", "classified"),
    "modification": ("modify", "modified"),
    "isolation": ("isolate", "isolated"),
    "amplification": ("amplify", "amplified"),
    "quantification": ("quantify", "quantified"),
    "purification": ("purify", "purified"),
    "estimation": ("estimate", "estimated"),
    "synthesis": ("synthesize", "synthesized"),
    "formulation": ("formulate", "formulated")
}

# ==========================================
# 3. 核心處理管線類別 (AcademicNLPPipeline)
# ==========================================
class AcademicNLPPipeline:
    _nlp_instance = None

    @classmethod
    def get_nlp(cls):
        """惰性加載 spaCy 模型 (Singleton 模式，避免重複加載)"""
        if cls._nlp_instance is None:
            if spacy is None:
                raise RuntimeError("spaCy is not installed in the current environment.")
            try:
                import en_core_web_sm
                cls._nlp_instance = en_core_web_sm.load()
            except Exception:
                try:
                    cls._nlp_instance = spacy.load("en_core_web_sm")
                except OSError:
                    import subprocess
                    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
                    cls._nlp_instance = spacy.load("en_core_web_sm")
        return cls._nlp_instance

    # ---------------------------------------------------------
    # 功能職責 A：Auto-Sanitize（自動無損修正）
    # ---------------------------------------------------------
    @classmethod
    def auto_sanitize(cls, text: str) -> Tuple[str, List[AutoSanitizeChange]]:
        """
        在文本送進 LLM 前，直接以確定性正規表示式與語法規則完成無損修正。
        1. 科學單位空格補全 (10mL -> 10 mL, 50uM -> 50 uM, 37°C -> 37 °C)
        2. 及物動詞後錯誤介系詞清除 (discuss about -> discuss, emphasize on -> emphasize)
        """
        if not text:
            return text, []

        changes: List[AutoSanitizeChange] = []
        result = text

        # --------------------------------------------------
        # 規則 1：科學單位空格自動補全 (Scientific Units Spacing)
        # --------------------------------------------------
        # 涵蓋容量、質量、摩爾濃度、維度、時間、頻率、壓力、溫度等國際標準單位
        units_pattern = (
            r"(?:"
            r"m[lL]|u[lL]|μ[lL]|n[lL]|p[lL]|[lL]|"
            r"kg|mg|u[gg]|μ[gg]|ng|pg|fg|"
            r"mmol|μmol|umol|nmol|pmol|mol|"
            r"mM|uM|μM|nM|pM|fM|"
            r"kDa|Da|bp|kb|Mb|Gb|"
            r"km|cm|mm|um|μm|nm|pm|"
            r"rpm|"
            r"mins?|hrs?|secs?|ms|ns|ps|"
            r"kV|mV|mA|μA|uA|kHz|MHz|GHz|Hz|"
            r"kW|mW|kJ|kcal|cal|"
            r"kPa|MPa|Pa|mbar|bar|psi|"
            r"°[CF]|℃|K|"
            r"wt%|vol%|mol%"
            r")"
        )
        
        # 配對數值緊接單位且中間無空格 (如 10mL, 0.05uM, 12000rpm, 37°C)
        # 避免配對年份如 1990s 或 DNA 序列或序數 1st, 2nd, 3rd, 2D, 3D
        unit_regex = re.compile(rf"\b(\d+(?:\.\d+)?)\s*({units_pattern})\b")

        def unit_replacer(match):
            val, unit = match.group(1), match.group(2)
            orig = match.group(0)
            rep = f"{val} {unit}"
            if orig != rep:
                changes.append(AutoSanitizeChange(
                    rule="Scientific Unit Spacing",
                    original=orig,
                    replacement=rep,
                    span=match.span()
                ))
            return rep

        result = unit_regex.sub(unit_replacer, result)

        # 針對單獨的溫度符號如 37°C / 37℃（° 可能不在 \b 內）
        temp_regex = re.compile(r"\b(\d+(?:\.\d+)?)\s*([°℃][CF]?)\b")
        def temp_replacer(match):
            val, unit = match.group(1), match.group(2)
            orig = match.group(0)
            rep = f"{val} {unit}"
            if orig != rep:
                changes.append(AutoSanitizeChange(
                    rule="Temperature Unit Spacing",
                    original=orig,
                    replacement=rep,
                    span=match.span()
                ))
            return rep
        result = temp_regex.sub(temp_replacer, result)

        # 針對時間 h (例如 24h -> 24 h, 48h -> 48 h)
        hour_regex = re.compile(r"\b(\d+(?:\.\d+)?)\s*([hH])\b")
        def hour_replacer(match):
            val, unit = match.group(1), match.group(2)
            orig = match.group(0)
            rep = f"{val} {unit}"
            if orig != rep:
                changes.append(AutoSanitizeChange(
                    rule="Hour Unit Spacing",
                    original=orig,
                    replacement=rep,
                    span=match.span()
                ))
            return rep
        result = hour_regex.sub(hour_replacer, result)

        # --------------------------------------------------
        # 規則 2：及物動詞後錯誤贅餘介系詞清除 (Transitive Verbs)
        # --------------------------------------------------
        # 常見中式英文及物動詞誤加介系詞模式
        transitive_preps = [
            (r"\b(discuss(?:es|ed|ing)?)\s+about\b", r"\1", "discuss about -> discuss"),
            (r"\b(mention(?:s|ed|ing)?)\s+about\b", r"\1", "mention about -> mention"),
            (r"\b(emphasiz(?:e|es|ed|ing))\s+(?:on|upon)\b", r"\1", "emphasize on -> emphasize"),
            (r"\b(stress(?:es|ed|ing)?)\s+(?:on|upon)\b", r"\1", "stress on -> stress"),
            (r"\b(contact(?:s|ed|ing)?)\s+with\b", r"\1", "contact with -> contact"),
            (r"\b(oppos(?:e|es|ed|ing))\s+against\b", r"\1", "oppose against -> oppose"),
            (r"\b(marr(?:y|ies|ied|ying))\s+with\b", r"\1", "marry with -> marry"),
            (r"\b(reach(?:es|ed|ing)?)\s+to\b", r"\1", "reach to -> reach"),
            (r"\b(compris(?:e|es|ed|ing))\s+of\b", r"\1", "comprise of -> comprise"),
            (r"\b(consider(?:s|ed|ing)?)\s+about\b", r"\1", "consider about -> consider"),
        ]

        for pat_str, rep_str, rule_desc in transitive_preps:
            pat = re.compile(pat_str, re.IGNORECASE)
            for m in pat.finditer(result):
                orig_match = m.group(0)
                # 保留原有大小寫動詞
                verb_part = m.group(1)
                changes.append(AutoSanitizeChange(
                    rule="Transitive Verb Redundant Preposition",
                    original=orig_match,
                    replacement=verb_part,
                    span=m.span()
                ))
            result = pat.sub(rep_str, result)

        return result, changes

    # ---------------------------------------------------------
    # 功能職責 B：Rule-Based Diagnostics（規則診斷報告）
    # ---------------------------------------------------------
    @classmethod
    def diagnose(cls, text: str) -> List[DiagnosticItem]:
        """
        使用 spaCy 依存句法樹 (Dependency Parsing)、詞性標註 (POS) 與 Matcher，
        進行確定性學術語言學診斷，回傳結構化 DiagnosticItem 清單。
        """
        diagnostics: List[DiagnosticItem] = []
        if not text or not text.strip():
            return diagnostics

        nlp = cls.get_nlp()
        doc = nlp(text)

        # 1. 跨子句主謂單複數不一致 (Subject-Verb Agreement Across Clauses)
        diagnostics.extend(cls._diagnose_sva(doc))

        # 2. 中式英文雙重連接詞 (Chinese Double Conjunctions)
        diagnostics.extend(cls._diagnose_double_conjunctions(doc))

        # 3. 句首裸露指示代名詞 (Bare Demonstratives at Sentence Start)
        diagnostics.extend(cls._diagnose_bare_demonstratives(doc))

        # 4. 過度名詞化結構 (Heavy Nominalization Fluff)
        diagnostics.extend(cls._diagnose_nominalization(doc))

        # 5. 被動語態與超長句標記 (Passive Voice & Overly Long Sentences)
        diagnostics.extend(cls._diagnose_passive_and_length(doc))

        # 依字元起始位置排序
        diagnostics.sort(key=lambda d: d.span[0])
        return diagnostics

    # ---------------------------------------------------------
    # 內部檢測方法 1：主謂一致性 (SVA)
    # ---------------------------------------------------------
    @classmethod
    def _diagnose_sva(cls, doc: Doc) -> List[DiagnosticItem]:
        items = []
        for token in doc:
            if token.dep_ in ("nsubj", "nsubjpass", "nsubj:pass"):
                subj = token
                head_verb = subj.head

                # 尋找真正承擔時態與人稱變化的動詞/助動詞
                # 例如 "The cells were observed": head 是 observed (VBN)，助動詞 were (VBD) 承擔數變化
                aux_verbs = [c for c in head_verb.children if c.dep_ in ("aux", "auxpass", "aux:pass")]
                inflected_verb = aux_verbs[0] if aux_verbs else head_verb

                if inflected_verb.pos_ not in ("VERB", "AUX"):
                    continue

                # 排除第一、第二人稱代名詞 (I, you, we)
                if subj.text.lower() in ("i", "you", "we"):
                    continue

                subj_num_list = subj.morph.get("Number")
                subj_num = subj_num_list[0] if subj_num_list else None
                # 若無 morph 資訊，以 POS Tag 備援 (NN/NNP -> Sing, NNS/NNPS -> Plur)
                if not subj_num:
                    if subj.tag_ in ("NN", "NNP"):
                        subj_num = "Sing"
                    elif subj.tag_ in ("NNS", "NNPS"):
                        subj_num = "Plur"

                verb_tag = inflected_verb.tag_
                verb_num_list = inflected_verb.morph.get("Number")
                verb_num = verb_num_list[0] if verb_num_list else None

                # 檢查複合主詞 (如 "Expression and activity were...") -> 視為複數
                has_and_conj = any(c.dep_ == "conj" for c in subj.children) and any(c.text.lower() == "and" for c in subj.children)
                if has_and_conj:
                    subj_num = "Plur"

                mismatch = False
                correct_suggestion = ""

                # 情境 1: 單數主詞配複數動詞 (e.g. "The mechanism are...", "The analysis show...")
                if subj_num == "Sing":
                    if verb_tag == "VBP":  # 現在式非單三動詞 (如 are, show, indicate)
                        mismatch = True
                        if inflected_verb.lemma_ == "be":
                            correct_suggestion = "is"
                        elif inflected_verb.lemma_ == "have":
                            correct_suggestion = "has"
                        else:
                            correct_suggestion = inflected_verb.lemma_ + ("es" if inflected_verb.lemma_.endswith(("s", "x", "ch", "sh", "o")) else "s")
                    elif inflected_verb.text.lower() == "were":
                        mismatch = True
                        correct_suggestion = "was"

                # 情境 2: 複數主詞配單數動詞 (e.g. "These results indicates...", "The patients was treated...")
                elif subj_num == "Plur":
                    if verb_tag == "VBZ":  # 現在式單三動詞 (如 is, shows, indicates)
                        mismatch = True
                        if inflected_verb.lemma_ == "be":
                            correct_suggestion = "are"
                        elif inflected_verb.lemma_ == "have":
                            correct_suggestion = "have"
                        else:
                            correct_suggestion = inflected_verb.lemma_
                    elif inflected_verb.text.lower() == "was":
                        mismatch = True
                        correct_suggestion = "were"

                if mismatch and correct_suggestion:
                    span_start = min(subj.idx, inflected_verb.idx)
                    span_end = max(subj.idx + len(subj.text), inflected_verb.idx + len(inflected_verb.text))
                    matched_snippet = doc.text[span_start:span_end]

                    msg = (
                        f"主謂一致性錯誤 (Subject-Verb Agreement Mismatch)：主詞「{subj.text}」為{('單數 (Singular)' if subj_num == 'Sing' else '複數 (Plural)')}，"
                        f"但修飾動詞「{inflected_verb.text}」卻採用{('複數型態' if subj_num == 'Sing' else '單三單數型態')}。"
                    )
                    items.append(DiagnosticItem(
                        rule_id="RULE_SVA_MISMATCH",
                        category="Subject-Verb Agreement",
                        category_zh="主謂單複數不一致",
                        severity="Critical",
                        span=(inflected_verb.idx, inflected_verb.idx + len(inflected_verb.text)),
                        matched_text=inflected_verb.text,
                        message=msg,
                        suggestion=f"建議將動詞「{inflected_verb.text}」修訂為「{correct_suggestion}」，使主詞「{subj.text}」與謂語保持單複數一致。",
                        replacement=correct_suggestion
                    ))
        return items

    # ---------------------------------------------------------
    # 內部檢測方法 2：中式雙重連接詞 (Double Conjunctions)
    # ---------------------------------------------------------
    @classmethod
    def _diagnose_double_conjunctions(cls, doc: Doc) -> List[DiagnosticItem]:
        items = []
        for sent in doc.sents:
            tokens_lower = [t.text.lower() for t in sent]

            has_although = any(t in ("although", "though") for t in tokens_lower)
            has_but = any(t in ("but", "yet") for t in tokens_lower)

            if has_although and has_but:
                # 找出 but/yet 的位置
                for t in sent:
                    if t.text.lower() in ("but", "yet"):
                        items.append(DiagnosticItem(
                            rule_id="RULE_DOUBLE_CONJUNCTION_ALTHOUGH_BUT",
                            category="Chinese-English Conjunction",
                            category_zh="中式雙重連接詞",
                            severity="Critical",
                            span=(t.idx, t.idx + len(t.text)),
                            matched_text=t.text,
                            message="中式英文雙重連接詞錯誤：同一句中不可同時出現從屬連詞「Although/Though」與對等連詞「But/Yet」。",
                            suggestion="英語習慣僅保留一個連接詞。建議直接移除「but」，或將子句拆成兩句並使用副詞「However, ...」連接。",
                            replacement=""
                        ))

            has_because = any(t in ("because", "since") for t in tokens_lower)
            has_so = any(t == "so" for t in tokens_lower)

            if has_because and has_so:
                for t in sent:
                    if t.text.lower() == "so":
                        items.append(DiagnosticItem(
                            rule_id="RULE_DOUBLE_CONJUNCTION_BECAUSE_SO",
                            category="Chinese-English Conjunction",
                            category_zh="中式雙重連接詞",
                            severity="Critical",
                            span=(t.idx, t.idx + len(t.text)),
                            matched_text=t.text,
                            message="中式英文雙重連接詞錯誤：同一句中不可同時出現「Because/Since」與「So」。",
                            suggestion="英語邏輯嚴禁因果雙連詞並存。建議直接移除「so」，或拆句使用「Therefore, ...」引導結果句。",
                            replacement=""
                        ))
        return items

    # ---------------------------------------------------------
    # 內部檢測方法 3：句首裸露代名詞 (Bare Demonstratives)
    # ---------------------------------------------------------
    @classmethod
    def _diagnose_bare_demonstratives(cls, doc: Doc) -> List[DiagnosticItem]:
        items = []
        for sent in doc.sents:
            # 檢視句首或逗號後的代名詞主詞
            for tok in sent[:4]:
                if tok.text.lower() in ("this", "these"):
                    # 判斷是否為主詞且自身為代名詞（非限定名詞之指示形容詞）
                    if tok.dep_ in ("nsubj", "nsubjpass", "nsubj:pass") and tok.pos_ == "PRON":
                        verb_text = tok.head.text
                        items.append(DiagnosticItem(
                            rule_id="RULE_BARE_DEMONSTRATIVE",
                            category="Vague Demonstrative Pronoun",
                            category_zh="句首裸露指示代名詞",
                            severity="Major",
                            span=(tok.idx, tok.idx + len(tok.text)),
                            matched_text=tok.text,
                            message=(
                                f"句首裸露代名詞 (Vague Demonstrative Pronoun)：單獨使用「{tok.text}」作為句首主詞接動詞「{verb_text}」，"
                                "易導致國際期刊審稿人質疑前述指涉對象模糊 (Unclear Referent)。"
                            ),
                            suggestion=(
                                f"建議於「{tok.text}」後補上精確的實質名詞，例如："
                                f"「{tok.text} finding / {tok.text} result / {tok.text} mechanism {verb_text}」以增強論述指涉明確度。"
                            ),
                            replacement=f"{tok.text} finding"
                        ))
        return items

    # ---------------------------------------------------------
    # 內部檢測方法 4：過度名詞化結構 (Heavy Nominalization)
    # ---------------------------------------------------------
    @classmethod
    def _diagnose_nominalization(cls, doc: Doc) -> List[DiagnosticItem]:
        items = []
        matcher = Matcher(doc.vocab)

        # 模式：虛動詞 + (out) + (限定詞) + 抽象名詞 + 介系詞 (of/into/for/to/that)
        pattern = [
            {"LEMMA": {"IN": ["conduct", "perform", "make", "carry", "provide", "give", "reach", "undertake"]}},
            {"LEMMA": "out", "OP": "?"},
            {"POS": "DET", "OP": "?"},
            {"POS": "NOUN"},
            {"LEMMA": {"IN": ["of", "into", "for", "to", "that"]}}
        ]
        matcher.add("HEAVY_NOMINALIZATION", [pattern])
        matches = matcher(doc)

        for match_id, start, end in matches:
            span = doc[start:end]
            # 找出名詞 token
            noun_tok = None
            for tok in span:
                if tok.pos_ == "NOUN":
                    noun_tok = tok
                    break

            if noun_tok and noun_tok.lemma_.lower() in NOMINALIZATION_MAP:
                verb_base, verb_past = NOMINALIZATION_MAP[noun_tok.lemma_.lower()]
                verb_lemma = span[0].tag_
                suggested_verb = verb_past if verb_lemma == "VBD" else verb_base

                items.append(DiagnosticItem(
                    rule_id="RULE_HEAVY_NOMINALIZATION",
                    category="Nominalization Fluff",
                    category_zh="過度名詞化結構",
                    severity="Major",
                    span=(span.start_char, span.end_char),
                    matched_text=span.text,
                    message=(
                        f"過度名詞化結構 (Heavy Nominalization)：短語「{span.text}」使用虛詞動詞搭配名詞化單詞，"
                        "會稀釋句子力量並增加多餘字數。"
                    ),
                    suggestion=f"建議直接簡化為精準強力的主動動詞「{suggested_verb}」，使學術文風更明快緊湊。",
                    replacement=suggested_verb
                ))
        return items

    # ---------------------------------------------------------
    # 內部檢測方法 5：被動語態與超長句標記 (Passive & Sentence Length)
    # ---------------------------------------------------------
    @classmethod
    def _diagnose_passive_and_length(cls, doc: Doc) -> List[DiagnosticItem]:
        items = []
        for sent in doc.sents:
            # 1. 檢測長句 (> 35 字)
            words = [t for t in sent if not t.is_punct and not t.is_space]
            word_count = len(words)
            if word_count > 35:
                items.append(DiagnosticItem(
                    rule_id="RULE_OVERLY_LONG_SENTENCE",
                    category="Style & Readability",
                    category_zh="過長複雜句 (> 35 字)",
                    severity="Minor",
                    span=(sent.start_char, sent.end_char),
                    matched_text=sent.text[:60] + "...",
                    message=(
                        f"長句警示 (Sentence Length: {word_count} words)：此句包含超過 35 個單詞，"
                        "包含過多從屬子句或巢狀修飾語，易加重審閱者認知負擔並分散論點核心。"
                    ),
                    suggestion="建議依語意起承轉合拆分為 2 至 3 個語意獨立的句子，提升論文的清晰度與易讀性。"
                ))

            # 2. 檢測被動語態 (Passive Voice)
            for tok in sent:
                if tok.dep_ in ("auxpass", "aux:pass"):
                    passive_span = doc[tok.i:tok.head.i + 1] if tok.i < tok.head.i else doc[tok.head.i:tok.i + 1]
                    items.append(DiagnosticItem(
                        rule_id="RULE_PASSIVE_VOICE",
                        category="Voice & Register",
                        category_zh="被動語態結構",
                        severity="Info",
                        span=(passive_span.start_char, passive_span.end_char),
                        matched_text=passive_span.text,
                        message=(
                            f"被動語態標記：此處使用被動語態「{passive_span.text}」。"
                            "現代頂級學術期刊（如 Nature, Science）鼓勵在闡述研究核心發現與貢獻時適度採用主動語態 (Active Voice)。"
                        ),
                        suggestion="若為描述團隊的主要發現或主動行動，建議轉為主動句式（如以主體研究者或發現作為主詞）。"
                    ))
        return items

    # ---------------------------------------------------------
    # 整合執行管線入口 (Pipeline Orchestrator)
    # ---------------------------------------------------------
    @classmethod
    def process(cls, text: str) -> PipelineResult:
        """
        完整執行 Pipeline 流程：
        1. Auto-Sanitize 產生乾淨格式文本與變更記錄
        2. Rule-Based Diagnostics 對原文本產生完整語言學診斷報告
        """
        sanitized_text, changes = cls.auto_sanitize(text)
        diagnostics = cls.diagnose(text)
        return PipelineResult(
            original_text=text,
            sanitized_text=sanitized_text,
            sanitize_changes=changes,
            diagnostics=diagnostics
        )

# ==========================================
# 4. CLI 測試與演示驗證
# ==========================================
if __name__ == "__main__":
    sample = (
        "Although the experiment was difficult, but we succeeded.\n"
        "Cells were incubated at 37°C for 24h with 10mL of 50uM drug, then centrifuged at 12000rpm for 15min.\n"
        "We will discuss about the results and emphasize on the main findings.\n"
        "The mechanism of these cells are not completely understood, and these results indicates a positive trend.\n"
        "This demonstrates that the hypothesis is valid.\n"
        "We conducted an analysis of the proteins and performed a measurement of the velocity.\n"
        "The biological reaction which occurred during the early exponential growth phase in the controlled bioreactor environment was observed to be influenced by multiple interdependent variables that were not originally accounted for in the preliminary mathematical models."
    )

    print("==================================================")
    print("LibreLlama Lab Editor -- NLP Rule Pipeline Test")
    print("==================================================")
    res = AcademicNLPPipeline.process(sample)

    print(f"\n[1] Auto-Sanitize Changes ({len(res.sanitize_changes)} items applied):")
    for c in res.sanitize_changes:
        print(f"  * [{c.rule}] '{c.original}' -> '{c.replacement}'")

    print(f"\n[2] Rule-Based Diagnostics ({len(res.diagnostics)} items found):")
    for d in res.diagnostics:
        print(f"  * [{d.rule_id} | {d.severity}] '{d.matched_text}'")
        print(f"    Message: {d.message}")
        print(f"    Suggestion: {d.suggestion}\n")
