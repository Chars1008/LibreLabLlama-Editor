import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
import LibreLlamaLabEditor
from LibreLlamaLabEditor import (
    AcademicReviewerApp, AcademicReviewReport, IssueItem, RevisionOption, ResearchRecommendation
)

def run_test():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    window = AcademicReviewerApp()
    window.resize(1500, 900)
    window.show()

    print("[Test] App initialized successfully.")
    print(f"[Test] Left widget: {window.left_splitter}")
    print(f"[Test] Middle widget: {window.middle_widget}")
    print(f"[Test] Critique tab count: {window.critique_tab_widget.count()}")
    print(f"[Test] Right stack count: {window.right_stack.count()} (Current index: {window.right_stack.currentIndex()})")

    # Simulate Mock Report
    mock_report = AcademicReviewReport(
        article_gist_zh="本文探討低延遲雲端架構於分散式系統中之應用表現。",
        article_gist_en="This manuscript investigates the performance of a low-latency neural cloud architecture.",
        overall_assessment_zh="論文論述具備初步說服力，但關鍵實驗對照缺失且存在多處非正式用詞與邏輯宣稱過度問題。",
        overall_assessment_en="The paper presents interesting preliminary findings but suffers from evidence gaps, unidiomatic collocations, and unjustified deductive leaps.",
        research_recommendations=[
            ResearchRecommendation(
                action_type="Methodological Benchmarking",
                severity="Must Address (必補/致命缺陷)",
                gap_identified_zh="未與現行工業界主流基準（如 Kubernetes 或 eBPF 路由）進行標準消融對比，難以證實新架構優勢。",
                gap_identified_en="Lacks comparative baseline experiments against industry standards (e.g. eBPF-based routing).",
                concrete_proposal_zh="建議於第4節補入在 10Gbps 負載下與 baseline 的 latency-throughput 雙維度消融對照圖表。",
                concrete_proposal_en="Incorporate an ablation study comparing latency-throughput curves at 10Gbps against standard baselines.",
                impact_on_acceptance_zh="此項為頂會審稿員必查硬傷，補齊後可直接化解致命拒稿風險。",
                impact_on_acceptance_en="Decisively eliminates a fatal reviewer critique, boosting acceptance odds."
            )
        ],
        collocation_issues=[
            IssueItem(
                category="Collocation Defect",
                severity="Major",
                original_text="play an effect",
                meaning_analysis_zh="「play an effect」為非道地搭配，標準學術英語應使用 exert an effect 或 have an impact。",
                meaning_analysis_en="Unidiomatic verb-noun combination.",
                reviewer_comment_zh="請修改此處生硬動賓搭配，以符合頂級期刊學術寫作慣例。",
                reviewer_comment_en="Unidiomatic collocation. In formal academic discourse, 'exert an effect' or 'produce an impact' is preferred.",
                revision_options=[
                    RevisionOption(
                        style_label="High-Impact Journal Register",
                        revised_text="exert a pronounced effect",
                        rationale_zh="使用 exert 搭配 effect，權威且精準。",
                        rationale_en="Standard academic phrasing in top journals."
                    ),
                    RevisionOption(
                        style_label="Objective Analytical Tone",
                        revised_text="have a demonstrable impact",
                        rationale_zh="客觀強調可被驗證之影響。",
                        rationale_en="Emphasizes verifiable impact."
                    )
                ]
            )
        ],
        discourse_issues=[
            IssueItem(
                category="Flawed Deduction",
                severity="Critical",
                original_text="completely solves the latency bottleneck without any drawback",
                meaning_analysis_zh="過度武斷且欠缺極限負載證據之推論（Overclaiming）。",
                meaning_analysis_en="Unsubstantiated absolute claim.",
                reviewer_comment_zh="此處斷言過度絕對，任何架構皆存在資源權衡（Trade-off），建議採用學術弱化防禦（Hedging）。",
                reviewer_comment_en="Overclaim without empirical justification across extreme network jitter. Employ academic hedging.",
                revision_options=[
                    RevisionOption(
                        style_label="Hedging Defense (Safe)",
                        revised_text="substantially alleviates the latency bottleneck under tested conditions",
                        rationale_zh="增加條件限制與弱化動詞，杜絕被 Reviewer 抓包過度宣稱。",
                        rationale_en="Safely moderates the claim to tested parameters."
                    )
                ]
            )
        ],
        issues=[
            IssueItem(
                category="Collocation Defect",
                severity="Major",
                original_text="play an effect",
                meaning_analysis_zh="「play an effect」為非道地搭配，標準學術英語應使用 exert an effect 或 have an impact。",
                meaning_analysis_en="Unidiomatic verb-noun combination.",
                reviewer_comment_zh="請修改此處生硬動賓搭配，以符合頂級期刊學術寫作慣例。",
                reviewer_comment_en="Unidiomatic collocation. In formal academic discourse, 'exert an effect' or 'produce an impact' is preferred.",
                revision_options=[
                    RevisionOption(
                        style_label="High-Impact Journal Register",
                        revised_text="exert a pronounced effect",
                        rationale_zh="使用 exert 搭配 effect，權威且精準。",
                        rationale_en="Standard academic phrasing in top journals."
                    )
                ]
            ),
            IssueItem(
                category="Flawed Deduction",
                severity="Critical",
                original_text="completely solves the latency bottleneck without any drawback",
                meaning_analysis_zh="過度武斷且欠缺極限負載證據之推論（Overclaiming）。",
                meaning_analysis_en="Unsubstantiated absolute claim.",
                reviewer_comment_zh="此處斷言過度絕對，任何架構皆存在資源權衡（Trade-off），建議採用學術弱化防禦（Hedging）。",
                reviewer_comment_en="Overclaim without empirical justification across extreme network jitter. Employ academic hedging.",
                revision_options=[
                    RevisionOption(
                        style_label="Hedging Defense (Safe)",
                        revised_text="substantially alleviates the latency bottleneck under tested conditions",
                        rationale_zh="增加條件限制與弱化動詞，杜絕被 Reviewer 抓包過度宣稱。",
                        rationale_en="Safely moderates the claim to tested parameters."
                    )
                ]
            )
        ]
    )

    window.on_review_finished(mock_report)
    print(f"[Test] Report finished. Right stack index: {window.right_stack.currentIndex()} (Expected: 1 for Chat)")
    print(f"[Test] Tab 0: {window.critique_tab_widget.tabText(0)}")
    print(f"[Test] Tab 1: {window.critique_tab_widget.tabText(1)}")
    print(f"[Test] Tab 2: {window.critique_tab_widget.tabText(2)}")

    # Test Focus on Rec
    rec = mock_report.research_recommendations[0]
    window.open_chat_for_rec(rec)
    print(f"[Test] Focused on Rec. Chip text: {window.chat_context_chip.text()}")
    print(f"[Test] Chat history count: {len(window.chat_history)}")

    # Test Focus on Issue
    issue = mock_report.collocation_issues[0]
    window.open_chat_for_issue(issue)
    print(f"[Test] Focused on Issue. Chip text: {window.chat_context_chip.text()}")
    print(f"[Test] Chat history count: {len(window.chat_history)}")

    # Test Quick Prompt text generation
    window.current_chat_context = {"type": "issue", "item": issue}
    # Verify build_chat_system_prompt
    sys_prompt = window.build_chat_system_prompt()
    assert "CURRENT FOCUSED CRITIQUE POINT" in sys_prompt or "play an effect" in sys_prompt
    print("[Test] build_chat_system_prompt verified.")

    # Test theme toggle
    window.toggle_theme()
    print(f"[Test] Dark mode toggled to: {window.is_dark_mode}")
    window.toggle_theme()
    print(f"[Test] Dark mode toggled back to: {window.is_dark_mode}")

    # Test language toggle
    window.toggle_language()
    print(f"[Test] Language toggled to: {window.ui_language}")
    print(f"[Test] En Tab 0: {window.critique_tab_widget.tabText(0)}")
    print(f"[Test] En Tab 1: {window.critique_tab_widget.tabText(1)}")
    print(f"[Test] En Tab 2: {window.critique_tab_widget.tabText(2)}")
    window.toggle_language()
    print(f"[Test] Language toggled back to: {window.ui_language}")

    # Capture visual verification screenshot
    pixmap = window.grab()
    screenshot_path = "C:/Users/Chars Hsieh/.gemini/antigravity/brain/9ed82452-db3f-4e1c-a7a9-d93e5acf5d5c/test_chat_workbench_screenshot.png"
    pixmap.save(screenshot_path)
    print(f"[Test] Screenshot successfully saved to {screenshot_path}")

    print("ALL TESTS PASSED!")

if __name__ == "__main__":
    run_test()
